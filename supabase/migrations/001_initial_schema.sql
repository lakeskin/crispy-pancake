-- =============================================================================
-- SalikChat — Initial Database Schema
-- Run this in Supabase SQL Editor: https://app.supabase.com → SQL Editor
-- =============================================================================

-- ============================================
-- PROFILES (extends Supabase auth.users)
-- ============================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'mechanic', 'admin')),
    full_name TEXT NOT NULL DEFAULT '',
    phone TEXT,
    avatar_url TEXT,
    city TEXT,
    country TEXT DEFAULT 'AE',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- MECHANIC PROFILES
-- ============================================
CREATE TABLE IF NOT EXISTS public.mechanic_profiles (
    id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    specializations TEXT[] DEFAULT '{}',
    experience_years INTEGER DEFAULT 0,
    certification_docs TEXT[],
    verification_status TEXT DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    bio TEXT,
    hourly_rate DECIMAL(10,2),
    rating_avg DECIMAL(3,2) DEFAULT 0.00,
    rating_count INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT true,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES public.profiles(id)
);

-- ============================================
-- CAR ISSUES
-- ============================================
CREATE TABLE IF NOT EXISTS public.car_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES public.profiles(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    car_make TEXT NOT NULL,
    car_model TEXT NOT NULL,
    car_year INTEGER NOT NULL,
    car_mileage INTEGER,
    category TEXT NOT NULL
        CHECK (category IN ('engine', 'brakes', 'electrical', 'suspension', 'ac', 'transmission', 'body', 'other')),
    urgency TEXT DEFAULT 'normal'
        CHECK (urgency IN ('low', 'normal', 'urgent')),
    status TEXT DEFAULT 'open'
        CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    location_city TEXT,
    budget_range TEXT,
    is_public BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- ISSUE MEDIA
-- ============================================
CREATE TABLE IF NOT EXISTS public.issue_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES public.car_issues(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('audio', 'image', 'video')),
    storage_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    duration_seconds INTEGER,
    thumbnail_path TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- CONVERSATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES public.car_issues(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.profiles(id),
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'closed', 'archived')),
    last_message_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(issue_id, mechanic_id)
);

-- ============================================
-- MESSAGES
-- ============================================
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.profiles(id),
    content TEXT,
    message_type TEXT DEFAULT 'text'
        CHECK (message_type IN ('text', 'image', 'audio', 'video', 'file', 'system', 'diagnosis')),
    media_url TEXT,
    metadata JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- VIDEO CALL SESSIONS
-- ============================================
CREATE TABLE IF NOT EXISTS public.video_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id),
    initiated_by UUID NOT NULL REFERENCES public.profiles(id),
    livekit_room_name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'ended', 'missed', 'declined')),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- MECHANIC RESPONSES
-- ============================================
CREATE TABLE IF NOT EXISTS public.mechanic_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES public.car_issues(id) ON DELETE CASCADE,
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    initial_diagnosis TEXT NOT NULL,
    estimated_cost_min DECIMAL(10,2),
    estimated_cost_max DECIMAL(10,2),
    estimated_fix_time TEXT,
    confidence_level TEXT DEFAULT 'medium'
        CHECK (confidence_level IN ('low', 'medium', 'high')),
    needs_video_call BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(issue_id, mechanic_id)
);

-- ============================================
-- REVIEWS
-- ============================================
CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id),
    reviewer_id UUID NOT NULL REFERENCES public.profiles(id),
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    was_helpful BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(conversation_id, reviewer_id)
);

-- ============================================
-- TRANSACTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS public.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id),
    customer_id UUID NOT NULL REFERENCES public.profiles(id),
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    amount DECIMAL(10,2) NOT NULL,
    platform_fee DECIMAL(10,2) NOT NULL,
    mechanic_payout DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'AED',
    payment_type TEXT NOT NULL
        CHECK (payment_type IN ('consultation', 'video_call', 'tip')),
    payment_status TEXT DEFAULT 'pending'
        CHECK (payment_status IN ('pending', 'completed', 'refunded', 'failed')),
    stripe_payment_intent_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- NOTIFICATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id),
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_car_issues_customer ON public.car_issues(customer_id);
CREATE INDEX IF NOT EXISTS idx_car_issues_status ON public.car_issues(status);
CREATE INDEX IF NOT EXISTS idx_car_issues_category ON public.car_issues(category);
CREATE INDEX IF NOT EXISTS idx_car_issues_created ON public.car_issues(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON public.messages(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON public.conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_mechanic ON public.conversations(mechanic_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_mechanic_responses_issue ON public.mechanic_responses(issue_id);
CREATE INDEX IF NOT EXISTS idx_issue_media_issue ON public.issue_media(issue_id);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Profiles: users can read all, update own
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view profiles"
    ON public.profiles FOR SELECT
    USING (true);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Service role can insert profiles"
    ON public.profiles FOR INSERT
    WITH CHECK (true);

-- Mechanic Profiles
ALTER TABLE public.mechanic_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view mechanic profiles"
    ON public.mechanic_profiles FOR SELECT
    USING (true);

CREATE POLICY "Mechanics can update own mechanic profile"
    ON public.mechanic_profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Service role can insert mechanic profiles"
    ON public.mechanic_profiles FOR INSERT
    WITH CHECK (true);

-- Car Issues
ALTER TABLE public.car_issues ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public issues visible to all"
    ON public.car_issues FOR SELECT
    USING (is_public = true OR customer_id = auth.uid());

CREATE POLICY "Customers can create issues"
    ON public.car_issues FOR INSERT
    WITH CHECK (customer_id = auth.uid());

CREATE POLICY "Owners can update issues"
    ON public.car_issues FOR UPDATE
    USING (customer_id = auth.uid());

CREATE POLICY "Owners can delete issues"
    ON public.car_issues FOR DELETE
    USING (customer_id = auth.uid());

-- Issue Media
ALTER TABLE public.issue_media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view issue media"
    ON public.issue_media FOR SELECT
    USING (true);

CREATE POLICY "Issue owners can add media"
    ON public.issue_media FOR INSERT
    WITH CHECK (true);

-- Conversations
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view conversations"
    ON public.conversations FOR SELECT
    USING (customer_id = auth.uid() OR mechanic_id = auth.uid());

CREATE POLICY "Customers can create conversations"
    ON public.conversations FOR INSERT
    WITH CHECK (customer_id = auth.uid());

-- Messages
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view messages"
    ON public.messages FOR SELECT
    USING (
        conversation_id IN (
            SELECT id FROM public.conversations
            WHERE customer_id = auth.uid() OR mechanic_id = auth.uid()
        )
    );

CREATE POLICY "Participants can send messages"
    ON public.messages FOR INSERT
    WITH CHECK (sender_id = auth.uid());

CREATE POLICY "Recipients can mark messages read"
    ON public.messages FOR UPDATE
    USING (
        conversation_id IN (
            SELECT id FROM public.conversations
            WHERE customer_id = auth.uid() OR mechanic_id = auth.uid()
        )
    );

-- Mechanic Responses
ALTER TABLE public.mechanic_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view responses"
    ON public.mechanic_responses FOR SELECT
    USING (true);

CREATE POLICY "Mechanics can submit responses"
    ON public.mechanic_responses FOR INSERT
    WITH CHECK (mechanic_id = auth.uid());

-- Notifications
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own notifications"
    ON public.notifications FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Service role can create notifications"
    ON public.notifications FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can update own notifications"
    ON public.notifications FOR UPDATE
    USING (user_id = auth.uid());

-- Reviews
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view reviews"
    ON public.reviews FOR SELECT
    USING (true);

CREATE POLICY "Reviewers can create reviews"
    ON public.reviews FOR INSERT
    WITH CHECK (reviewer_id = auth.uid());

-- Video Calls
ALTER TABLE public.video_calls ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view video calls"
    ON public.video_calls FOR SELECT
    USING (true);

CREATE POLICY "Anyone authenticated can create video calls"
    ON public.video_calls FOR INSERT
    WITH CHECK (true);

-- Transactions
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view own transactions"
    ON public.transactions FOR SELECT
    USING (customer_id = auth.uid() OR mechanic_id = auth.uid());


-- ============================================
-- REALTIME — Enable for chat tables
-- ============================================

-- Enable realtime on messages table (for live chat)
ALTER PUBLICATION supabase_realtime ADD TABLE public.messages;

-- Enable realtime on notifications (for live notifications)
ALTER PUBLICATION supabase_realtime ADD TABLE public.notifications;

-- Enable realtime on conversations (for conversation list updates)
ALTER PUBLICATION supabase_realtime ADD TABLE public.conversations;

-- Enable realtime on car_issues (for live mechanic feed)
ALTER PUBLICATION supabase_realtime ADD TABLE public.car_issues;

-- Enable realtime on mechanic_responses (for live response notifications)
ALTER PUBLICATION supabase_realtime ADD TABLE public.mechanic_responses;


-- ============================================
-- TRIGGER: auto-update updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER car_issues_updated_at
    BEFORE UPDATE ON public.car_issues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================
-- TRIGGER: auto-create profile on signup
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, role, full_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'role', 'customer'),
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    )
    ON CONFLICT (id) DO NOTHING;

    -- If mechanic, also create mechanic_profiles row
    IF COALESCE(NEW.raw_user_meta_data->>'role', 'customer') = 'mechanic' THEN
        INSERT INTO public.mechanic_profiles (id)
        VALUES (NEW.id)
        ON CONFLICT (id) DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users insert
CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ============================================
-- STORAGE BUCKETS (run separately if needed)
-- ============================================
-- These need to be created via Supabase Dashboard or API:
-- 1. issue-media (public, 50MB limit)
-- 2. chat-media (private, 10MB limit)
-- 3. mechanic-docs (private, 10MB limit)
-- 4. avatars (public, 2MB limit)
