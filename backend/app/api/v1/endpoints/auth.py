"""
Authentication endpoints
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    validate_password_strength,
    create_reset_token,
    verify_reset_token,
    get_current_user_id
)
from app.models.user import (
    User,
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    PasswordReset,
    PasswordResetConfirm,
    UserProfile
)

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate) -> Any:
    """
    Register a new user account
    
    Args:
        user_data: User registration data
    
    Returns:
        JWT token and user information
    
    Raises:
        HTTPException: If email already exists or password is weak
    """
    # Check if user already exists
    existing_user = await User.find_one(User.email == user_data.email.lower())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet strength requirements"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user_profile = UserProfile(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone
    )
    
    new_user = User(
        email=user_data.email.lower(),
        password_hash=hashed_password,
        profile=user_profile
    )
    
    await new_user.save()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(new_user.id),
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        profile=new_user.profile,
        preferences=new_user.preferences,
        loyalty=new_user.loyalty,
        status=new_user.status,
        created_at=new_user.created_at
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin) -> Any:
    """
    Authenticate user and return JWT token
    
    Args:
        login_data: User login credentials
    
    Returns:
        JWT token and user information
    
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = await User.find_one(User.email == login_data.email.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active"
        )
    
    # Update login information
    from datetime import datetime
    user.auth.last_login = datetime.utcnow()
    user.auth.login_count += 1
    await user.save()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.post("/password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(reset_data: PasswordReset) -> Any:
    """
    Request password reset
    
    Args:
        reset_data: Password reset request data
    
    Returns:
        Success message
    
    Note:
        In production, this would send an email with reset token
    """
    # Find user by email
    user = await User.find_one(User.email == reset_data.email.lower())
    if not user:
        # Don't reveal if email exists
        return {"message": "If email exists, reset instructions will be sent"}
    
    # Generate reset token
    reset_token = create_reset_token(user.email)
    
    # Store reset token (in production, you might want to store this in Redis)
    user.auth.reset_token = reset_token
    await user.save()
    
    # TODO: Send email with reset token
    # In production, you would send an email here
    print(f"Password reset token for {user.email}: {reset_token}")
    
    return {"message": "If email exists, reset instructions will be sent"}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(reset_confirm: PasswordResetConfirm) -> Any:
    """
    Confirm password reset with token
    
    Args:
        reset_confirm: Password reset confirmation data
    
    Returns:
        Success message
    
    Raises:
        HTTPException: If token is invalid or password is weak
    """
    # Verify reset token
    email = verify_reset_token(reset_confirm.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user
    user = await User.find_one(User.email == email)
    if not user or user.auth.reset_token != reset_confirm.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate new password
    if not validate_password_strength(reset_confirm.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet strength requirements"
        )
    
    # Update password
    from datetime import datetime
    user.password_hash = get_password_hash(reset_confirm.new_password)
    user.auth.reset_token = None
    user.updated_at = datetime.utcnow()
    await user.save()
    
    return {"message": "Password reset successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user_id: str = Depends(get_current_user_id)) -> Any:
    """
    Refresh JWT token
    
    Args:
        current_user_id: Current user ID from token
    
    Returns:
        New JWT token and user information
    
    Raises:
        HTTPException: If user not found
    """
    # Find user
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user_id: str = Depends(get_current_user_id)) -> Any:
    """
    Get current user information
    
    Args:
        current_user_id: Current user ID from token
    
    Returns:
        Current user information
    
    Raises:
        HTTPException: If user not found
    """
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at
    )