/**
 * API service for StoryBoard AI
 * Handles all HTTP requests to the Flask backend
 */
import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { authStorage } from './authStorage';

// Types
export interface HealthCheckResponse {
  status: string;
  timestamp: string;
}

export interface ConfigResponse {
  models: Record<string, unknown>;
  image_models: Record<string, unknown>;
  video_models: Record<string, unknown>;
  prompt_variations: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface UploadResponse {
  success: boolean;
  filename: string;
  path: string;
}

export interface BalanceResponse {
  balance: number;
  tier: string;
}

export interface CreditPackage {
  id: string;
  name: string;
  credits: number;
  price: number;
  bonus_credits: number;
  stripe_price_id: string;
}

export interface Subscription {
  id: string;
  name: string;
  credits_per_month: number;
  price: number;
  interval: string;
  interval_count: number;
  trial_days: number;
  stripe_price_id: string;
}

export interface PackagesResponse {
  packages: CreditPackage[];
  subscriptions: Subscription[];
  currency: string;
  features: Record<string, unknown>;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

// Story outline types (Stage 1)
export interface StoryCharacter {
  name: string;
  description: string;
  personality: string;
}

export interface StoryPanelOutline {
  scene: string;
  caption: string;
  moment?: string;
}

export interface StoryOutline {
  title: string;
  character: StoryCharacter;
  panels: StoryPanelOutline[];
}

export interface OutlineRequest {
  idea: string;
  panel_count: number;
}

export interface OutlineProgress {
  type: 'status' | 'outline' | 'complete' | 'error';
  message?: string;
  title?: string;
  character?: StoryCharacter;
  panels?: StoryPanelOutline[];
}

export interface RegeneratePanelRequest {
  title: string;
  character: StoryCharacter;
  panels: StoryPanelOutline[];
  panel_index: number;
  feedback?: string;
}

// Legacy types (kept for compatibility)
export interface StoryPanel {
  scene: string;
  caption: string;
}

// Bracket variation types
export interface BracketInfo {
  original: string;
  variations: string[];
  selected: number;
}

export interface VariationRequest {
  prompt: string;
  num_variations?: number;
}

export interface VariationResponse {
  original_prompt: string;
  brackets: BracketInfo[];
  full_prompts: string[];
  message?: string;
}

// Full prompt variation types (new system)
export interface FullVariation {
  id: number;
  prompt: string;
  selected: boolean;
}

export interface FullVariationRequest {
  prompt: string;
  num_variations?: number;
  model?: string;
}

export interface FullVariationResponse {
  original_prompt: string;
  variations: FullVariation[];
}

export interface RegenerateVariationRequest {
  original_prompt: string;
  current_variation: string;
  feedback?: string;
  model?: string;
}

export interface RegenerateVariationResponse {
  new_variation: string;
}

export interface GenerationProgress {
  type: 'panel' | 'story' | 'complete' | 'error' | 'status';
  index?: number;
  url?: string;
  caption?: string;
  scene?: string;
  prompt?: string;  // Prompt used for this panel (Full Variations mode)
  panels?: StoryPanel[];
  title?: string;
  character?: StoryCharacter;
  error?: string;
  message?: string;
}

export interface StoryboardRequest {
  mode: 'story' | 'remix' | 'custom';
  panel_count: number;
  theme_id?: string;
  user_image?: string;
  custom_prompt?: string;
  custom_prompts?: string[];  // Array of prompts for Full Variations mode
  image_model?: string;  // Image model for Full Variations mode
  style?: string;
  // Generation mode
  generation_mode?: 'parallel' | 'sequential' | 'progressive';
  // Option 1: Pre-generated outline from /generate-outline
  outline?: StoryOutline;
  // Option 2: Custom story text (legacy)
  custom_story?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to all requests
api.interceptors.request.use(
  (config) => {
    const { accessToken } = authStorage.getTokens();
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const apiService = {
  // ============================================================================
  // HEALTH & CONFIG
  // ============================================================================

  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await api.get('/health');
    return response.data;
  },

  async getConfig(): Promise<ConfigResponse> {
    const response = await api.get('/config');
    return response.data;
  },

  // ============================================================================
  // IMAGE UPLOAD
  // ============================================================================

  async uploadImage(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('image', file);

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // ============================================================================
  // STORYBOARD GENERATION - STAGE 1: STORY OUTLINE
  // ============================================================================

  /**
   * Generate a story outline from user's idea
   * Stage 1 of the two-stage workflow
   */
  async generateOutline(
    request: OutlineRequest,
    onProgress: (data: OutlineProgress) => void
  ): Promise<void> {
    const { accessToken } = authStorage.getTokens();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/generate-outline`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onProgress(data);
          } catch {
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }
  },

  /**
   * Regenerate a single panel in the story outline (SSE streaming version)
   */
  async regeneratePanelStream(
    request: RegeneratePanelRequest,
    onProgress: (data: OutlineProgress) => void
  ): Promise<void> {
    const { accessToken } = authStorage.getTokens();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/regenerate-panel`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onProgress(data);
          } catch {
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }
  },

  /**
   * Regenerate a single panel - returns the new panel directly
   */
  async regeneratePanel(
    title: string,
    character: StoryCharacter,
    panels: StoryPanelOutline[],
    panelIndex: number,
    feedback?: string
  ): Promise<{ panel: StoryPanelOutline }> {
    return new Promise((resolve, reject) => {
      let result: StoryPanelOutline | null = null;
      
      this.regeneratePanelStream(
        { title, character, panels, panel_index: panelIndex, feedback },
        (data: OutlineProgress & { scene?: string; caption?: string; moment?: string; index?: number }) => {
          // The backend returns type: 'panel' with scene, caption, moment directly
          if (data.type === 'panel' as string && data.scene) {
            result = {
              scene: data.scene,
              caption: data.caption || '',
              moment: data.moment,
            };
          } else if (data.type === 'error') {
            reject(new Error(data.message || 'Regeneration failed'));
          }
        }
      ).then(() => {
        if (result) {
          resolve({ panel: result });
        } else {
          reject(new Error('No panel returned'));
        }
      }).catch(reject);
    });
  },

  // ============================================================================
  // STORYBOARD GENERATION - STAGE 2: IMAGE GENERATION
  // ============================================================================

  /**
   * Generate storyboard panels (Story/Remix/Simple/Pro modes)
   * Returns SSE stream with panel results
   */
  async generateStoryboard(
    request: StoryboardRequest,
    onProgress: (data: GenerationProgress) => void
  ): Promise<void> {
    const { accessToken } = authStorage.getTokens();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/generate-story`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onProgress(data);
          } catch {
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }
  },

  /**
   * Legacy: Generate images with streaming (for Pro mode compatibility)
   */
  async generateImagesStream(
    prompt: string,
    imagePath: string | null = null,
    models: string[] | null = null,
    numVariations = 3,
    onProgress: (data: unknown) => void,
    customPrompts: string[] | null = null,
    mode = 'image',
    videoSettings: Record<string, unknown> | null = null
  ): Promise<void> {
    const requestBody = {
      prompt,
      image_path: imagePath,
      models,
      num_variations: numVariations,
      mode,
      custom_prompts: customPrompts,
      video_settings: videoSettings,
    };

    const { accessToken } = authStorage.getTokens();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/generate-stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          onProgress(data);
        }
      }
    }
  },

  // ============================================================================
  // CREDITS API
  // ============================================================================

  async getCreditsBalance(): Promise<BalanceResponse> {
    const response = await api.get('/credits/balance');
    return response.data;
  },

  async getCreditPackages(): Promise<PackagesResponse> {
    const response = await api.get('/credits/packages');
    return response.data;
  },

  async validateCoupon(code: string, packageId: string | null = null, subscriptionId: string | null = null): Promise<{
    valid: boolean;
    discount_type?: string;
    discount_value?: number;
    message?: string;
  }> {
    const response = await api.post('/credits/validate-coupon', {
      code,
      package_id: packageId,
      subscription_id: subscriptionId,
    });
    return response.data;
  },

  async createPackageCheckout(packageId: string, couponCode: string | null = null): Promise<CheckoutResponse> {
    const response = await api.post('/credits/checkout/package', {
      package_id: packageId,
      coupon_code: couponCode,
    });
    return response.data;
  },

  async createSubscriptionCheckout(subscriptionId: string, couponCode: string | null = null): Promise<CheckoutResponse> {
    const response = await api.post('/credits/checkout/subscription', {
      subscription_id: subscriptionId,
      coupon_code: couponCode,
    });
    return response.data;
  },

  async verifyPayment(sessionId: string): Promise<{ success: boolean; credits_added?: number; new_balance?: number; error?: string }> {
    const response = await api.post('/credits/verify-payment', {
      session_id: sessionId,
    });
    return response.data;
  },

  // ============================================================================
  // BRACKET VARIATIONS API
  // ============================================================================

  /**
   * Generate creative variations for bracketed text in a prompt.
   * Used in Remix mode when users use [bracket] syntax.
   * 
   * Example: "A [dramatic] portrait in [cyberpunk] style"
   * Returns variations for each bracket plus full prompt combinations.
   */
  async generateVariations(request: VariationRequest): Promise<VariationResponse> {
    const response = await api.post('/generate-variations', {
      prompt: request.prompt,
      num_variations: request.num_variations || 4,
    });
    return response.data;
  },

  // ============================================================================
  // FULL PROMPT VARIATIONS API (Third Option)
  // ============================================================================

  /**
   * Generate N complete prompt variations from a base prompt.
   * Each variation is a fully-formed, ready-to-use prompt.
   * 
   * Example input: "make me wear cool old clothing on cool backgrounds"
   * Returns 7 (or N) complete, creative variations.
   */
  async generateFullVariations(request: FullVariationRequest): Promise<FullVariationResponse> {
    const response = await api.post('/generate-full-variations', {
      prompt: request.prompt,
      num_variations: request.num_variations || 7,
      model: request.model,
    });
    return response.data;
  },

  /**
   * Regenerate a single variation with optional feedback.
   * Used when user wants a fresh take on one specific variation.
   */
  async regenerateVariation(request: RegenerateVariationRequest): Promise<RegenerateVariationResponse> {
    const response = await api.post('/regenerate-variation', {
      original_prompt: request.original_prompt,
      current_variation: request.current_variation,
      feedback: request.feedback,
      model: request.model,
    });
    return response.data;
  },

  // ============================================================================
  // AUTH API (for reference - AuthContext handles these directly)
  // ============================================================================

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const response = await api.post('/auth/password-reset/request', { email });
    return response.data;
  },

  async updatePassword(newPassword: string, accessToken: string | null = null): Promise<{ success: boolean }> {
    const response = await api.post('/auth/password-reset/update', {
      new_password: newPassword,
      access_token: accessToken,
    });
    return response.data;
  },

  // ============================================================================
  // UNLOCK API (Credit Deduction)
  // ============================================================================

  /**
   * Unlock a generated story by deducting 1 credit.
   * Gives user access to HD, watermark-free downloads.
   */
  async unlockStory(storyId: string | null = null, panelCount: number = 4): Promise<{
    success: boolean;
    credits_deducted?: number;
    new_balance?: number;
    unlocked?: boolean;
    error?: string;
  }> {
    const response = await api.post('/unlock-story', {
      story_id: storyId,
      panel_count: panelCount,
    });
    return response.data;
  },

  /**
   * Unlock a single panel for download.
   * Cost: 1 credit per panel.
   */
  async unlockPanel(panelId: string | null = null, panelIndex: number = 0): Promise<{
    success: boolean;
    credits_deducted?: number;
    new_balance?: number;
    unlocked?: boolean;
    error?: string;
  }> {
    const response = await api.post('/unlock-panel', {
      panel_id: panelId,
      panel_index: panelIndex,
    });
    return response.data;
  },

  // ============================================================================
  // BILLING PORTAL (Subscription Management)
  // ============================================================================

  /**
   * Create a Stripe Billing Portal session.
   * Opens a portal where users can manage subscriptions and payment methods.
   */
  async createBillingPortal(returnUrl: string | null = null): Promise<{ portal_url: string }> {
    const response = await api.post('/credits/billing-portal', {
      return_url: returnUrl,
    });
    return response.data;
  },

  /**
   * Get user's active subscriptions
   */
  async getSubscriptions(): Promise<{ subscriptions: unknown[]; has_active: boolean }> {
    const response = await api.get('/credits/subscriptions');
    return response.data;
  },
};

export default apiService;
