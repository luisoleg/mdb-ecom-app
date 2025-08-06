/**
 * Cart Redux Slice
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { CartService, Cart } from '../../services/api';

interface CartState {
  cart: Cart | null;
  itemCount: number;
  loading: boolean;
  error: string | null;
}

const initialState: CartState = {
  cart: null,
  itemCount: 0,
  loading: false,
  error: null,
};

// Async thunks
export const getCart = createAsyncThunk(
  'cart/getCart',
  async (_, { rejectWithValue }) => {
    try {
      const cart = await CartService.getCart();
      return cart;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get cart');
    }
  }
);

export const addToCart = createAsyncThunk(
  'cart/addToCart',
  async (item: {
    product_id: string;
    variant_id: string;
    quantity: number;
  }, { rejectWithValue }) => {
    try {
      const cart = await CartService.addToCart(item);
      return cart;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to add to cart');
    }
  }
);

export const updateCartItem = createAsyncThunk(
  'cart/updateCartItem',
  async (item: {
    product_id: string;
    variant_id: string;
    quantity: number;
  }, { rejectWithValue }) => {
    try {
      const cart = await CartService.updateCartItem(item);
      return cart;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to update cart item');
    }
  }
);

export const removeFromCart = createAsyncThunk(
  'cart/removeFromCart',
  async (item: {
    product_id: string;
    variant_id: string;
  }, { rejectWithValue }) => {
    try {
      const cart = await CartService.removeFromCart(item);
      return cart;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to remove from cart');
    }
  }
);

export const clearCart = createAsyncThunk(
  'cart/clearCart',
  async (_, { rejectWithValue }) => {
    try {
      const cart = await CartService.clearCart();
      return cart;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to clear cart');
    }
  }
);

export const getCartCount = createAsyncThunk(
  'cart/getCartCount',
  async (_, { rejectWithValue }) => {
    try {
      const response = await CartService.getCartCount();
      return response.count;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get cart count');
    }
  }
);

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setItemCount: (state, action: PayloadAction<number>) => {
      state.itemCount = action.payload;
    },
  },
  extraReducers: (builder) => {
    // Get cart
    builder
      .addCase(getCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(getCart.fulfilled, (state, action: PayloadAction<Cart>) => {
        state.loading = false;
        state.cart = action.payload;
        state.itemCount = action.payload.totals.items_count;
      })
      .addCase(getCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Add to cart
    builder
      .addCase(addToCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(addToCart.fulfilled, (state, action: PayloadAction<Cart>) => {
        state.loading = false;
        state.cart = action.payload;
        state.itemCount = action.payload.totals.items_count;
      })
      .addCase(addToCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Update cart item
    builder
      .addCase(updateCartItem.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateCartItem.fulfilled, (state, action: PayloadAction<Cart>) => {
        state.loading = false;
        state.cart = action.payload;
        state.itemCount = action.payload.totals.items_count;
      })
      .addCase(updateCartItem.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Remove from cart
    builder
      .addCase(removeFromCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(removeFromCart.fulfilled, (state, action: PayloadAction<Cart>) => {
        state.loading = false;
        state.cart = action.payload;
        state.itemCount = action.payload.totals.items_count;
      })
      .addCase(removeFromCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Clear cart
    builder
      .addCase(clearCart.fulfilled, (state, action: PayloadAction<Cart>) => {
        state.cart = action.payload;
        state.itemCount = 0;
      });

    // Get cart count
    builder
      .addCase(getCartCount.fulfilled, (state, action: PayloadAction<number>) => {
        state.itemCount = action.payload;
      });
  },
});

export const { clearError, setItemCount } = cartSlice.actions;
export default cartSlice.reducer;