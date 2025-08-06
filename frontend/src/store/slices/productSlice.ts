/**
 * Product Redux Slice
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ProductService, Product } from '../../services/api';

interface ProductState {
  products: Product[];
  currentProduct: Product | null;
  recommendations: Product[];
  totalProducts: number;
  currentPage: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  searchQuery: string;
  filters: {
    category?: string;
    brand?: string;
    minPrice?: number;
    maxPrice?: number;
    minRating?: number;
    inStock?: boolean;
    tags?: string[];
    sortBy?: string;
  };
}

const initialState: ProductState = {
  products: [],
  currentProduct: null,
  recommendations: [],
  totalProducts: 0,
  currentPage: 1,
  totalPages: 0,
  loading: false,
  error: null,
  searchQuery: '',
  filters: {},
};

// Async thunks
export const searchProducts = createAsyncThunk(
  'products/search',
  async (params: {
    q?: string;
    category?: string;
    brand?: string;
    min_price?: number;
    max_price?: number;
    min_rating?: number;
    in_stock?: boolean;
    tags?: string[];
    sort_by?: string;
    page?: number;
    limit?: number;
  }, { rejectWithValue }) => {
    try {
      const response = await ProductService.searchProducts(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to search products');
    }
  }
);

export const getProduct = createAsyncThunk(
  'products/getProduct',
  async (productId: string, { rejectWithValue }) => {
    try {
      const product = await ProductService.getProduct(productId);
      return product;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get product');
    }
  }
);

export const getProductRecommendations = createAsyncThunk(
  'products/getRecommendations',
  async (productId: string, { rejectWithValue }) => {
    try {
      const recommendations = await ProductService.getProductRecommendations(productId);
      return recommendations;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get recommendations');
    }
  }
);

const productSlice = createSlice({
  name: 'products',
  initialState,
  reducers: {
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    setFilters: (state, action: PayloadAction<Partial<ProductState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = {};
      state.searchQuery = '';
    },
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentProduct: (state) => {
      state.currentProduct = null;
      state.recommendations = [];
    },
  },
  extraReducers: (builder) => {
    // Search products
    builder
      .addCase(searchProducts.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(searchProducts.fulfilled, (state, action) => {
        state.loading = false;
        state.products = action.payload.products;
        state.totalProducts = action.payload.total;
        state.currentPage = action.payload.page;
        state.totalPages = action.payload.total_pages;
      })
      .addCase(searchProducts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Get product
    builder
      .addCase(getProduct.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(getProduct.fulfilled, (state, action: PayloadAction<Product>) => {
        state.loading = false;
        state.currentProduct = action.payload;
      })
      .addCase(getProduct.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Get recommendations
    builder
      .addCase(getProductRecommendations.fulfilled, (state, action: PayloadAction<Product[]>) => {
        state.recommendations = action.payload;
      });
  },
});

export const {
  setSearchQuery,
  setFilters,
  clearFilters,
  clearError,
  clearCurrentProduct,
} = productSlice.actions;

export default productSlice.reducer;