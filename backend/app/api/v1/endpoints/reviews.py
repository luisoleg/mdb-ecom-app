"""
Product Reviews endpoints
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
import math

from app.core.security import get_current_user_id
from app.models.review import (
    Review,
    ReviewVote,
    ReviewCreate,
    ReviewUpdate,
    ReviewVoteCreate,
    ReviewResponse,
    ReviewListResponse,
    ReviewStatsResponse,
    ReviewQuery
)
from app.models.product import Product
from app.models.order import Order
from app.models.user import User

router = APIRouter()


async def populate_review_response(review: Review) -> ReviewResponse:
    """Populate review response with user information"""
    user = await User.get(review.user_id)
    reviewer_name = "Anonymous"
    reviewer_avatar = None
    
    if user:
        reviewer_name = f"{user.profile.first_name} {user.profile.last_name[0]}."
        reviewer_avatar = user.profile.avatar
    
    return ReviewResponse(
        id=str(review.id),
        product_id=review.product_id,
        variant_id=review.variant_id,
        user_id=review.user_id,
        rating=review.rating,
        title=review.title,
        content=review.content,
        pros=review.pros,
        cons=review.cons,
        verified_purchase=review.verified_purchase,
        helpful_votes=review.helpful_votes,
        total_votes=review.total_votes,
        helpfulness_score=review.calculate_helpfulness_score(),
        images=review.images,
        status=review.status,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewer_name=reviewer_name,
        reviewer_avatar=reviewer_avatar
    )


@router.get("/", response_model=ReviewListResponse)
async def get_reviews(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    verified_only: Optional[bool] = Query(None, description="Show only verified purchases"),
    status: Optional[str] = Query("approved", description="Filter by status"),
    sort_by: Optional[str] = Query("newest", description="Sort by: newest, oldest, rating_high, rating_low, helpful"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page")
) -> Any:
    """Get product reviews with filtering and pagination"""
    
    # Build query
    filters = []
    if product_id:
        filters.append(Review.product_id == product_id)
    if user_id:
        filters.append(Review.user_id == user_id)
    if rating:
        filters.append(Review.rating == rating)
    if verified_only:
        filters.append(Review.verified_purchase == True)
    if status:
        filters.append(Review.status == status)
    
    query = Review.find({})
    if filters:
        for filter_condition in filters:
            query = query.find(filter_condition)
    
    # Apply sorting
    if sort_by == "oldest":
        query = query.sort(+Review.created_at)
    elif sort_by == "rating_high":
        query = query.sort(-Review.rating)
    elif sort_by == "rating_low":
        query = query.sort(+Review.rating)
    elif sort_by == "helpful":
        query = query.sort(-Review.helpful_votes)
    else:  # newest
        query = query.sort(-Review.created_at)
    
    # Get total count
    total = await query.count()
    
    # Apply pagination
    skip = (page - 1) * limit
    reviews = await query.skip(skip).limit(limit).to_list()
    
    # Convert to response format
    review_responses = []
    for review in reviews:
        review_response = await populate_review_response(review)
        review_responses.append(review_response)
    
    # Calculate stats for the product if filtering by product_id
    average_rating = 0.0
    rating_distribution = {}
    if product_id:
        product_reviews = await Review.find(
            Review.product_id == product_id,
            Review.status == "approved"
        ).to_list()
        
        if product_reviews:
            total_rating = sum(r.rating for r in product_reviews)
            average_rating = total_rating / len(product_reviews)
            
            rating_distribution = {str(i): 0 for i in range(1, 6)}
            for review in product_reviews:
                rating_distribution[str(review.rating)] += 1
    
    total_pages = math.ceil(total / limit)
    
    return ReviewListResponse(
        reviews=review_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        average_rating=round(average_rating, 2),
        rating_distribution=rating_distribution
    )


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Create a product review"""
    
    # Check if product exists
    product = await Product.get(review_data.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user already reviewed this product
    existing_review = await Review.find_one(
        Review.product_id == review_data.product_id,
        Review.user_id == current_user_id
    )
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product"
        )
    
    # Check if this is a verified purchase
    verified_purchase = False
    if review_data.order_id:
        order = await Order.find_one(
            Order.id == review_data.order_id,
            Order.user_id == current_user_id
        )
        if order:
            # Check if the product is in the order
            for item in order.items:
                if item.product_id == review_data.product_id:
                    verified_purchase = True
                    break
    
    # Create review
    review = Review(
        product_id=review_data.product_id,
        variant_id=review_data.variant_id,
        user_id=current_user_id,
        order_id=review_data.order_id,
        rating=review_data.rating,
        title=review_data.title,
        content=review_data.content,
        pros=review_data.pros,
        cons=review_data.cons,
        verified_purchase=verified_purchase
    )
    
    await review.save()
    
    # Update product rating
    product.update_rating(review_data.rating)
    await product.save()
    
    return await populate_review_response(review)


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    review_data: ReviewUpdate,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Update a review (only by review author)"""
    
    review = await Review.get(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if user owns the review
    if review.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own reviews"
        )
    
    # Update fields
    update_data = review_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    from datetime import datetime
    review.updated_at = datetime.utcnow()
    
    await review.save()
    
    return await populate_review_response(review)


@router.post("/{review_id}/vote", status_code=status.HTTP_200_OK)
async def vote_on_review(
    review_id: str,
    vote_data: ReviewVoteCreate,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Vote on review helpfulness"""
    
    review = await Review.get(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if user already voted on this review
    existing_vote = await ReviewVote.find_one(
        ReviewVote.review_id == review_id,
        ReviewVote.user_id == current_user_id
    )
    
    if existing_vote:
        # Update existing vote
        existing_vote.is_helpful = vote_data.is_helpful
        await existing_vote.save()
    else:
        # Create new vote
        vote = ReviewVote(
            review_id=review_id,
            user_id=current_user_id,
            is_helpful=vote_data.is_helpful
        )
        await vote.save()
        
        # Update review vote counts
        review.add_helpful_vote(vote_data.is_helpful)
        await review.save()
    
    return {"message": "Vote recorded successfully"}


@router.get("/stats/{product_id}", response_model=ReviewStatsResponse)
async def get_review_stats(product_id: str) -> Any:
    """Get review statistics for a product"""
    
    reviews = await Review.find(
        Review.product_id == product_id,
        Review.status == "approved"
    ).to_list()
    
    if not reviews:
        return ReviewStatsResponse(
            total_reviews=0,
            average_rating=0.0,
            rating_distribution={str(i): 0 for i in range(1, 6)},
            verified_purchases_percentage=0.0
        )
    
    total_reviews = len(reviews)
    total_rating = sum(r.rating for r in reviews)
    average_rating = total_rating / total_reviews
    
    rating_distribution = {str(i): 0 for i in range(1, 6)}
    verified_count = 0
    
    for review in reviews:
        rating_distribution[str(review.rating)] += 1
        if review.verified_purchase:
            verified_count += 1
    
    verified_percentage = (verified_count / total_reviews) * 100
    
    return ReviewStatsResponse(
        total_reviews=total_reviews,
        average_rating=round(average_rating, 2),
        rating_distribution=rating_distribution,
        verified_purchases_percentage=round(verified_percentage, 2)
    )