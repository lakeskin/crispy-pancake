/* ---- TypeScript interfaces for SalikChat ---- */

export interface User {
  id: string;
  email: string;
  role: "customer" | "mechanic" | "admin";
  full_name: string;
  avatar_url?: string | null;
  phone?: string | null;
  city?: string | null;
  country?: string;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
}

export interface MechanicProfile {
  id: string;
  specializations: string[];
  experience_years: number;
  bio?: string | null;
  hourly_rate?: number | null;
  rating_avg: number;
  rating_count: number;
  is_available: boolean;
  verification_status: "pending" | "verified" | "rejected";
  certification_docs?: string[];
}

export interface Profile extends User {
  mechanic_profile?: MechanicProfile;
  created_at: string;
  updated_at: string;
}

export interface IssueMedia {
  id: string;
  issue_id: string;
  media_type: "audio" | "image" | "video";
  storage_path: string;
  file_name: string;
  file_size?: number;
  duration_seconds?: number;
  thumbnail_path?: string;
  created_at: string;
}

export interface CarIssue {
  id: string;
  customer_id: string;
  title: string;
  description: string;
  car_make: string;
  car_model: string;
  car_year: number;
  car_mileage?: number;
  category: string;
  urgency: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  location_city?: string;
  budget_range?: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  issue_media?: IssueMedia[];
  profiles?: { full_name: string; avatar_url?: string; city?: string };
  response_count?: number;
}

export interface MechanicResponse {
  id: string;
  issue_id: string;
  mechanic_id: string;
  initial_diagnosis: string;
  estimated_cost_min?: number;
  estimated_cost_max?: number;
  estimated_fix_time?: string;
  confidence_level: "low" | "medium" | "high";
  needs_video_call: boolean;
  created_at: string;
  profiles?: { full_name: string; avatar_url?: string };
  mechanic_profiles?: {
    rating_avg: number;
    rating_count: number;
    specializations: string[];
    experience_years?: number;
    verification_status: string;
  };
}

export interface Conversation {
  id: string;
  issue_id: string;
  customer_id: string;
  mechanic_id: string;
  status: "active" | "closed" | "archived";
  last_message_at: string;
  created_at: string;
  updated_at: string;
  car_issues?: Partial<CarIssue>;
  profiles?: { full_name: string; avatar_url?: string };
  unread_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  content?: string;
  message_type: "text" | "image" | "audio" | "video" | "file" | "system" | "diagnosis";
  media_url?: string;
  metadata?: Record<string, unknown>;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
  profiles?: { full_name: string; avatar_url?: string };
}

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body?: string;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface ConfigCategory {
  id: string;
  label: string;
  icon: string;
}

export interface ConfigUrgency {
  id: string;
  label: string;
  color: string;
}

export interface ConfigBudget {
  id: string;
  label: string;
}
