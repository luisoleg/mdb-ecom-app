"""
User management endpoints
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user_id
from app.models.user import (
    Address,
    AddressCreate,
    Location,
    User,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user_id: str = Depends(get_current_user_id),
) -> Any:
    """Get current user profile"""
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at,
    )


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    user_data: UserUpdate, current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Update user profile"""
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update profile fields
    update_data = user_data.dict(exclude_unset=True)
    if "first_name" in update_data:
        user.profile.first_name = update_data["first_name"]
    if "last_name" in update_data:
        user.profile.last_name = update_data["last_name"]
    if "phone" in update_data:
        user.profile.phone = update_data["phone"]
    if "preferences" in update_data:
        user.preferences = update_data["preferences"]

    from datetime import datetime

    user.updated_at = datetime.utcnow()
    await user.save()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at,
    )


@router.post("/addresses", response_model=UserResponse)
async def add_user_address(
    address_data: AddressCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Any:
    """Add new address to user profile"""
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Generate address ID
    import uuid

    address_id = f"addr_{uuid.uuid4().hex[:8]}"

    # Create location if coordinates provided
    location = None
    if address_data.coordinates:
        location = Location(coordinates=address_data.coordinates)

    # Create address
    address = Address(
        address_id=address_id,
        type=address_data.type,
        is_default=address_data.is_default,
        recipient_name=address_data.recipient_name,
        street=address_data.street,
        city=address_data.city,
        state=address_data.state,
        postal_code=address_data.postal_code,
        country=address_data.country,
        location=location,
    )

    # If this is set as default, unset other defaults of same type
    if address_data.is_default:
        for addr in user.addresses:
            if addr.type == address_data.type:
                addr.is_default = False

    user.addresses.append(address)
    from datetime import datetime

    user.updated_at = datetime.utcnow()
    await user.save()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at,
    )


@router.delete("/addresses/{address_id}", response_model=UserResponse)
async def delete_user_address(
    address_id: str, current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Delete user address"""
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find and remove address
    for i, address in enumerate(user.addresses):
        if address.address_id == address_id:
            user.addresses.pop(i)
            from datetime import datetime

            user.updated_at = datetime.utcnow()
            await user.save()
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=user.profile,
        preferences=user.preferences,
        loyalty=user.loyalty,
        status=user.status,
        created_at=user.created_at,
    )
