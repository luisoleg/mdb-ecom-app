/**
 * Review Redux Slice
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ReviewService, Review } from '../../services/api';

interface ReviewState {
  reviews: Review[];
  totalReviews: number;
  currentPage: number;
  totalPages: number;
  averageRating: number;
  ratingDistribution: Record<string, number>;
  loading: boolean;
  error: string | null;
}

const initialState: ReviewState = {
  reviews: [],
  totalReviews: 0,
  currentPage: 1,
  totalPages: 0,
  averageRating: 0,
  ratingDistribution: {},
  loading: false,
  error: null,
};

// Async thunks
export const getProductReviews = createAsyncThunk(
  'reviews/getProductReviews',
  async (params: {
    productId: string;
    rating?: number;
    verified_only?: boolean;
    sort_by?: string;
    page?: number;
    limit?: number;
  }, { rejectWithValue }) => {
    try {
      const { productId, ...queryParams } = params;
      const response = await ReviewService.getProductReviews(productId, queryParams);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get reviews');
    }
  }
);

export const createReview = createAsyncThunk(
  'reviews/createReview',
  async (reviewData: {
    product_id: string;
    variant_id?: string;
    order_id?: string;
    rating: number;
    title: string;
    content: string;
    pros?: string[];
    cons?: string[];
  }, { rejectWithValue }) => {
    try {
      const review = await ReviewService.createReview(reviewData);
      return review;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to create review');
    }
  }
);

export const voteOnReview = createAsyncThunk(
  'reviews/voteOnReview',
  async (params: {
    reviewId: string;
    isHelpful: boolean;
  }, { rejectWithValue }) => {
    try {
      await ReviewService.voteOnReview(params.reviewId, params.isHelpful);
      return params;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to vote on review');
    }
  }
);

const reviewSlice = createSlice({
  name: 'reviews',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearReviews: (state) => {
      state.reviews = [];
      state.totalReviews = 0;
      state.currentPage = 1;
      state.totalPages = 0;
      state.averageRating = 0;
      state.ratingDistribution = {};
    },
  },
  extraReducers: (builder) => {
    // Get product reviews
    builder
      .addCase(getProductReviews.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(getProductReviews.fulfilled, (state, action) => {
        state.loading = false;
        state.reviews = action.payload.reviews;
        state.totalReviews = action.payload.total;
        state.currentPage = action.payload.page;
        state.totalPages = action.payload.total_pages;
        state.averageRating = action.payload.average_rating;
        state.ratingDistribution = action.payload.rating_distribution;
      })
      .addCase(getProductReviews.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Create review
    builder
      .addCase(createReview.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createReview.fulfilled, (state, action: PayloadAction<Review>) => {
        state.loading = false;
        state.reviews.unshift(action.payload);
        state.totalReviews += 1;
      })
      .addCase(createReview.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Vote on review
    builder
      .addCase(voteOnReview.fulfilled, (state, action) => {
        // Update the review in the list to reflect the vote
        const review = state.reviews.find(r => r.id === action.payload.reviewId);
        if (review) {
          review.total_votes += 1;
          if (action.payload.isHelpful) {
            review.helpful_votes += 1;
          }
          review.helpfulness_score = (review.helpful_votes / review.total_votes) * 100;
        }
      });
  },
});

export const { clearError, clearReviews } = reviewSlice.actions;
export default reviewSlice.reducer;