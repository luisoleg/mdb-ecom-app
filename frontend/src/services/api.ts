/**
 * API Service Layer with Axios Configuration
 */
import axios, { AxiosResponse, AxiosError } from 'axios';

// Types
export interface User {
  id: string;
  email: string;
  profile: {
    first_name: string;
    last_name: string;
    phone?: string;
    avatar?: string;
  };
  preferences: {
    currency: string;
    language: string;
  };
  loyalty: {
    points: number;
    tier: string;
    lifetime_spent: number;
  };
  status: string;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  description: string;
  brand: string;
  categories: string[];
  base_price: number;
  variants: ProductVariant[];
  specifications: Record<string, any>;
  rating_summary: {
    average_rating: number;
    total_reviews: number;
  };
  status: string;
  tags: string[];
  primary_image?: string;
  price_range: [number, number];
  in_stock: boolean;
  created_at: string;
}

export interface ProductVariant {
  variant_id: string;
  name: string;
  sku: string;
  price: number;
  attributes: Record<string, string>;
  inventory: {
    quantity: number;
    reserved: number;
  };
  images: ProductImage[];
  is_active: boolean;
}

export interface ProductImage {
  url: string;
  alt: string;
  is_primary: boolean;
}

export interface CartItem {
  product_id: string;
  variant_id: string;
  quantity: number;
  price: number;
  total: number;
  added_at: string;
  product_name?: string;
  variant_name?: string;
  product_image?: string;
  sku?: string;
}

export interface Cart {
  id: string;
  user_id?: string;
  session_id?: string;
  items: CartItem[];
  totals: {
    items_count: number;
    subtotal: number;
    estimated_tax: number;
    estimated_shipping: number;
    estimated_total: number;
  };
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  user_id: string;
  status: string;
  items: OrderItem[];
  summary: {
    subtotal: number;
    tax: number;
    shipping: number;
    discount: number;
    total: number;
  };
  shipping_address: Address;
  billing_address: Address;
  payment: PaymentInfo;
  timeline: OrderTimeline[];
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  product_id: string;
  variant_id: string;
  sku: string;
  name: string;
  price: number;
  quantity: number;
  total: number;
}

export interface Address {
  address_id: string;
  type: string;
  is_default: boolean;
  recipient_name: string;
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface PaymentInfo {
  method: string;
  status: string;
  transaction_id: string;
  amount: number;
  currency: string;
  processed_at?: string;
}

export interface OrderTimeline {
  status: string;
  timestamp: string;
  note?: string;
}

export interface Review {
  id: string;
  product_id: string;
  variant_id?: string;
  user_id: string;
  rating: number;
  title: string;
  content: string;
  pros: string[];
  cons: string[];
  verified_purchase: boolean;
  helpful_votes: number;
  total_votes: number;
  helpfulness_score: number;
  status: string;
  created_at: string;
  reviewer_name?: string;
  reviewer_avatar?: string;
}

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add session ID for anonymous users
    const sessionId = localStorage.getItem('session_id');
    if (sessionId) {
      config.headers['X-Session-ID'] = sessionId;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token expiration
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API Service Classes
export class AuthService {
  static async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', credentials);
    return response.data;
  }

  static async register(userData: RegisterData): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/register', userData);
    return response.data;
  }

  static async refreshToken(): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/refresh');
    return response.data;
  }

  static async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  }

  static async requestPasswordReset(email: string): Promise<void> {
    await api.post('/auth/password-reset', { email });
  }

  static async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    });
  }
}

export class ProductService {
  static async searchProducts(params: {
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
  }): Promise<{ products: Product[]; total: number; page: number; total_pages: number }> {
    const response = await api.get('/products/search', { params });
    return response.data;
  }

  static async getProduct(productId: string): Promise<Product> {
    const response = await api.get<Product>(`/products/${productId}`);
    return response.data;
  }

  static async getProductRecommendations(productId: string): Promise<Product[]> {
    const response = await api.get(`/products/${productId}/recommendations`);
    return response.data.products;
  }
}

export class CartService {
  static async getCart(): Promise<Cart> {
    const response = await api.get<Cart>('/cart');
    return response.data;
  }

  static async addToCart(item: {
    product_id: string;
    variant_id: string;
    quantity: number;
  }): Promise<Cart> {
    const response = await api.post<Cart>('/cart/items', item);
    return response.data;
  }

  static async updateCartItem(item: {
    product_id: string;
    variant_id: string;
    quantity: number;
  }): Promise<Cart> {
    const response = await api.patch<Cart>('/cart/items', item);
    return response.data;
  }

  static async removeFromCart(item: {
    product_id: string;
    variant_id: string;
  }): Promise<Cart> {
    const response = await api.delete<Cart>('/cart/items', { data: item });
    return response.data;
  }

  static async clearCart(): Promise<Cart> {
    const response = await api.delete<Cart>('/cart');
    return response.data;
  }

  static async getCartCount(): Promise<{ count: number }> {
    const response = await api.get('/cart/count');
    return response.data;
  }
}

export class OrderService {
  static async createOrder(orderData: {
    items: { product_id: string; variant_id: string; quantity: number }[];
    shipping_address_id: string;
    billing_address_id?: string;
    payment_method_id: string;
    shipping_method?: string;
    notes?: string;
  }): Promise<Order> {
    const response = await api.post<Order>('/orders', orderData);
    return response.data;
  }

  static async getUserOrders(params?: {
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<{ orders: Order[]; total: number; page: number; total_pages: number }> {
    const response = await api.get('/orders', { params });
    return response.data;
  }

  static async getOrder(orderId: string): Promise<Order> {
    const response = await api.get<Order>(`/orders/${orderId}`);
    return response.data;
  }

  static async cancelOrder(orderId: string): Promise<Order> {
    const response = await api.patch<Order>(`/orders/${orderId}/status`, {
      status: 'cancelled',
      note: 'Cancelled by customer',
    });
    return response.data;
  }
}

export class ReviewService {
  static async getProductReviews(
    productId: string,
    params?: {
      rating?: number;
      verified_only?: boolean;
      sort_by?: string;
      page?: number;
      limit?: number;
    }
  ): Promise<{
    reviews: Review[];
    total: number;
    page: number;
    total_pages: number;
    average_rating: number;
    rating_distribution: Record<string, number>;
  }> {
    const response = await api.get('/reviews', {
      params: { product_id: productId, ...params },
    });
    return response.data;
  }

  static async createReview(reviewData: {
    product_id: string;
    variant_id?: string;
    order_id?: string;
    rating: number;
    title: string;
    content: string;
    pros?: string[];
    cons?: string[];
  }): Promise<Review> {
    const response = await api.post<Review>('/reviews', reviewData);
    return response.data;
  }

  static async voteOnReview(
    reviewId: string,
    isHelpful: boolean
  ): Promise<void> {
    await api.post(`/reviews/${reviewId}/vote`, { is_helpful: isHelpful });
  }
}

export default api;