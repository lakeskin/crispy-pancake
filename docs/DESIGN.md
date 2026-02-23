# SalikChat — Design Document

> **Version**: 1.0
> **Date**: February 2026
> **Project**: SalikChat — Connect Car Owners with Mechanics

---

## 📋 TABLE OF CONTENTS

1. [Vision & Problem Statement](#1-vision--problem-statement)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [User Roles](#4-user-roles)
5. [Database Schema](#5-database-schema)
6. [Customer (Car Owner) Flow](#6-customer-car-owner-flow)
7. [Mechanic Flow](#7-mechanic-flow)
8. [Admin Flow](#8-admin-flow)
9. [Real-Time Chat System](#9-real-time-chat-system)
10. [Video Call System](#10-video-call-system)
11. [File Upload System](#11-file-upload-system)
12. [Notifications](#12-notifications)
13. [Monetization Model](#13-monetization-model)
14. [API Endpoints Overview](#14-api-endpoints-overview)
15. [Security Considerations](#15-security-considerations)

---

## 1. Vision & Problem Statement

### The Problem
Car owners hear a strange noise, see a warning light, or notice unusual behavior — and they have **no idea** if it's a $50 fix or a $5,000 engine rebuild. Their options today:
- Drive to a mechanic and wait hours for a diagnosis (often overcharged)
- Google symptoms and get unreliable forum answers
- Call a friend who "knows about cars"

### The Solution — SalikChat
A platform where **car owners post their car issue** (with audio recordings of engine sounds, photos, or videos) and **verified mechanics respond** with a quick diagnosis, cost estimate, and advice — all through **real-time chat** and optional **video calls**.

### Core Value Proposition
| For Car Owners | For Mechanics |
|---|---|
| Get a fast, affordable diagnosis without leaving home | Earn money from expertise during downtime |
| Upload engine sounds, photos, videos for accurate help | Build reputation and attract local customers |
| Choose from multiple mechanics and compare opinions | Low barrier to entry — just a phone and knowledge |

---

## 2. Tech Stack

### Why This Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | **Python FastAPI** | You know Python. FastAPI is the fastest Python framework with async support, auto-generated docs, and WebSocket support |
| **Frontend** | **Next.js 15 (React 19)** + **Tailwind CSS** + **shadcn/ui** | Best React framework in 2026. SSR for SEO (important for landing pages). shadcn/ui gives polished components out of the box |
| **Database** | **Supabase (PostgreSQL)** | Handles DB + Auth + Storage + Realtime all-in-one. Postgres is rock-solid. Free tier is generous |
| **Auth** | **Supabase Auth** | Email/password, Google, phone OTP — built-in. Row Level Security in Postgres |
| **Real-Time Chat** | **Supabase Realtime** | Zero extra services. Subscribe to DB changes in real-time. Messages are just rows in a table |
| **Video Calls** | **LiveKit** (open-source WebRTC) | Free, open-source, self-hostable. Has Python SDK (backend) + React SDK (frontend). Production-grade |
| **File Storage** | **Supabase Storage** | Integrated with auth. Upload audio/images/videos directly. CDN included |
| **Deployment** | **Vercel** (frontend) + **Railway** (backend) | Zero-config deploys. Railway runs Python/Docker natively |
| **Secrets** | **Infisical** | Per your architecture rules — env-centric secret management |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Car Owner   │  │   Mechanic   │  │   Admin Dashboard    │  │
│  │  (Next.js)   │  │   (Next.js)  │  │     (Next.js)        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼──────────────────┼────────────────────┼───────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     NEXT.JS API LAYER                           │
│              (SSR, API Routes, Auth Middleware)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   FastAPI    │  │   Supabase   │  │   LiveKit    │
│   Backend    │  │  (DB/Auth/   │  │  (Video/     │
│  (Business   │  │   Storage/   │  │   Voice      │
│   Logic)     │  │   Realtime)  │  │   Calls)     │
└──────┬───────┘  └──────┬───────┘  └──────────────┘
       │                 │
       ▼                 ▼
┌─────────────────────────────┐
│     PostgreSQL (Supabase)   │
│  ┌────────┐ ┌────────────┐  │
│  │ Tables │ │  Storage   │  │
│  │  & RLS │ │  Buckets   │  │
│  └────────┘ └────────────┘  │
└─────────────────────────────┘
```

---

## 3. Architecture Overview

### Data Flow

```
Car Owner posts issue ──► FastAPI validates & saves to Supabase DB
                          ──► Supabase Realtime notifies mechanics
                          ──► Mechanic sees new issue in feed

Mechanic sends message ──► Supabase Realtime (insert row)
                          ──► Car Owner sees message instantly

Video Call request ──► FastAPI creates LiveKit room token
                      ──► Both parties join via LiveKit React SDK
```

### Key Design Decisions

1. **Supabase as the backbone** — One service replaces 4 (DB, Auth, Storage, Realtime). Less infrastructure, less cost, less complexity.

2. **FastAPI for business logic only** — Auth is handled by Supabase. Storage is handled by Supabase. FastAPI handles: issue matching, payment logic, mechanic verification, video call token generation, and any AI-powered features (future).

3. **Next.js handles both car owner and mechanic UIs** — One codebase, role-based rendering. Admin is a separate route group with middleware protection.

4. **LiveKit over Daily.co / Twilio** — Open-source, self-hostable, free to start, and has first-class Python + React SDKs. Perfect for 1-on-1 diagnostic calls.

---

## 4. User Roles

### 4.1 Customer (Car Owner)
- **Can**: Sign up, post issues, upload media, chat with mechanics, request video calls, rate mechanics, pay for consultations
- **Cannot**: Access mechanic dashboard, verify other mechanics, access admin panel

### 4.2 Mechanic
- **Can**: Browse issues, respond to issues, chat with customers, conduct video calls, set pricing & availability, view earnings
- **Cannot**: Access admin panel, verify themselves, modify platform settings
- **Must**: Complete verification process before accepting paid jobs

### 4.3 Admin
- **Can**: Verify mechanics (review documents), manage users, view platform analytics, handle disputes, manage payouts, configure platform settings
- **Cannot**: Impersonate users for chat (audit trail required)

---

## 5. Database Schema

### Core Tables

```sql
-- ============================================
-- USERS (extends Supabase auth.users)
-- ============================================
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('customer', 'mechanic', 'admin')),
    full_name TEXT NOT NULL,
    phone TEXT,
    avatar_url TEXT,
    city TEXT,
    country TEXT DEFAULT 'AE',  -- UAE default
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- MECHANIC PROFILES (extra mechanic info)
-- ============================================
CREATE TABLE public.mechanic_profiles (
    id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    specializations TEXT[] DEFAULT '{}',       -- e.g. {'engine', 'electrical', 'brakes'}
    experience_years INTEGER DEFAULT 0,
    certification_docs TEXT[],                  -- URLs in Supabase Storage
    verification_status TEXT DEFAULT 'pending'  -- 'pending', 'verified', 'rejected'
        CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    bio TEXT,
    hourly_rate DECIMAL(10,2),                  -- for video consultations
    rating_avg DECIMAL(3,2) DEFAULT 0.00,
    rating_count INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT true,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES public.profiles(id)
);

-- ============================================
-- CAR ISSUES (the core post)
-- ============================================
CREATE TABLE public.car_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES public.profiles(id),
    title TEXT NOT NULL,                         -- "Strange noise when braking"
    description TEXT NOT NULL,                   -- detailed description
    car_make TEXT NOT NULL,                      -- "Toyota"
    car_model TEXT NOT NULL,                     -- "Camry"
    car_year INTEGER NOT NULL,                   -- 2022
    car_mileage INTEGER,                         -- 85000 km
    category TEXT NOT NULL                       -- 'engine', 'brakes', 'electrical', 'suspension', 'ac', 'transmission', 'other'
        CHECK (category IN ('engine', 'brakes', 'electrical', 'suspension', 'ac', 'transmission', 'body', 'other')),
    urgency TEXT DEFAULT 'normal'                -- 'low', 'normal', 'urgent'
        CHECK (urgency IN ('low', 'normal', 'urgent')),
    status TEXT DEFAULT 'open'                   -- 'open', 'in_progress', 'resolved', 'closed'
        CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    location_city TEXT,
    budget_range TEXT,                           -- 'under_50', '50_200', '200_500', 'above_500', 'not_sure'
    is_public BOOLEAN DEFAULT true,             -- visible in mechanic feed
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- ISSUE MEDIA (audio, photos, videos)
-- ============================================
CREATE TABLE public.issue_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES public.car_issues(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('audio', 'image', 'video')),
    storage_path TEXT NOT NULL,                  -- Supabase Storage path
    file_name TEXT NOT NULL,
    file_size INTEGER,                           -- bytes
    duration_seconds INTEGER,                    -- for audio/video
    thumbnail_path TEXT,                         -- for video thumbnails
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- CONVERSATIONS (1 issue can have multiple mechanic conversations)
-- ============================================
CREATE TABLE public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES public.car_issues(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.profiles(id),
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'closed', 'archived')),
    last_message_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(issue_id, mechanic_id)               -- one conversation per mechanic per issue
);

-- ============================================
-- MESSAGES (chat messages within a conversation)
-- ============================================
CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.profiles(id),
    content TEXT,                                 -- text message
    message_type TEXT DEFAULT 'text'
        CHECK (message_type IN ('text', 'image', 'audio', 'video', 'file', 'system', 'diagnosis')),
    media_url TEXT,                               -- for media messages
    metadata JSONB DEFAULT '{}',                  -- flexible: diagnosis details, call summary, etc.
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- VIDEO CALL SESSIONS
-- ============================================
CREATE TABLE public.video_calls (
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
-- MECHANIC RESPONSES (initial response to an issue)
-- ============================================
CREATE TABLE public.mechanic_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES public.car_issues(id) ON DELETE CASCADE,
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    initial_diagnosis TEXT NOT NULL,              -- "Sounds like worn brake pads"
    estimated_cost_min DECIMAL(10,2),
    estimated_cost_max DECIMAL(10,2),
    estimated_fix_time TEXT,                      -- "1-2 hours"
    confidence_level TEXT DEFAULT 'medium'
        CHECK (confidence_level IN ('low', 'medium', 'high')),
    needs_video_call BOOLEAN DEFAULT false,       -- mechanic suggests video call
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(issue_id, mechanic_id)
);

-- ============================================
-- REVIEWS & RATINGS
-- ============================================
CREATE TABLE public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id),
    reviewer_id UUID NOT NULL REFERENCES public.profiles(id),    -- the customer
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    was_helpful BOOLEAN,                          -- "Did this diagnosis help?"
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(conversation_id, reviewer_id)
);

-- ============================================
-- PAYMENTS / TRANSACTIONS
-- ============================================
CREATE TABLE public.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id),
    customer_id UUID NOT NULL REFERENCES public.profiles(id),
    mechanic_id UUID NOT NULL REFERENCES public.profiles(id),
    amount DECIMAL(10,2) NOT NULL,
    platform_fee DECIMAL(10,2) NOT NULL,          -- SalikChat's cut
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
CREATE TABLE public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id),
    type TEXT NOT NULL,                            -- 'new_response', 'new_message', 'call_request', 'review', 'verification'
    title TEXT NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}',                       -- action payload (issue_id, conversation_id, etc.)
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- INDEXES for performance
-- ============================================
CREATE INDEX idx_car_issues_customer ON public.car_issues(customer_id);
CREATE INDEX idx_car_issues_status ON public.car_issues(status);
CREATE INDEX idx_car_issues_category ON public.car_issues(category);
CREATE INDEX idx_car_issues_created ON public.car_issues(created_at DESC);
CREATE INDEX idx_messages_conversation ON public.messages(conversation_id);
CREATE INDEX idx_messages_created ON public.messages(created_at);
CREATE INDEX idx_conversations_customer ON public.conversations(customer_id);
CREATE INDEX idx_conversations_mechanic ON public.conversations(mechanic_id);
CREATE INDEX idx_notifications_user ON public.notifications(user_id, is_read);
CREATE INDEX idx_mechanic_responses_issue ON public.mechanic_responses(issue_id);
```

---

## 6. Customer (Car Owner) Flow

### 6.1 Onboarding

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Landing     │────►│  Sign Up     │────►│  Basic       │────►│  Dashboard   │
│  Page        │     │  (Email/     │     │  Profile     │     │  (Empty)     │
│              │     │   Google/    │     │  (Name,      │     │              │
│  "Get a      │     │   Phone)    │     │   City)      │     │  "Post Your  │
│   Diagnosis" │     │              │     │              │     │   First      │
│              │     │              │     │              │     │   Issue"     │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### 6.2 Posting an Issue

```
Step 1: Basic Info
┌─────────────────────────────────────────┐
│  What's wrong with your car?            │
│  ┌───────────────────────────────────┐  │
│  │ Title: "Grinding noise when I     │  │
│  │         brake at low speed"       │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ Description: "For the past week,  │  │
│  │ I hear a metal grinding sound..." │  │
│  └───────────────────────────────────┘  │
│  Category: [Brakes ▼]                   │
│  Urgency:  ○ Low  ● Normal  ○ Urgent   │
└─────────────────────────────────────────┘

Step 2: Car Details
┌─────────────────────────────────────────┐
│  Tell us about your car                 │
│  Make:    [Toyota ▼]                    │
│  Model:   [Camry ▼]                    │
│  Year:    [2022 ▼]                     │
│  Mileage: [85,000 km]                  │
│  Budget:  [Not sure ▼]                 │
└─────────────────────────────────────────┘

Step 3: Upload Media (Optional but encouraged)
┌─────────────────────────────────────────┐
│  Help mechanics diagnose faster         │
│                                         │
│  🎙️ [Record Engine Sound]              │
│     OR drag & drop audio file           │
│                                         │
│  📸 [Upload Photos]                    │
│     Dashboard lights, damage, parts     │
│                                         │
│  🎥 [Upload Video]                     │
│     Show the issue in action            │
│                                         │
│  ┌─────┐ ┌─────┐ ┌─────┐              │
│  │ 🔊  │ │ 📸  │ │ 📸  │  3 files     │
│  │audio│ │img1 │ │img2 │  uploaded     │
│  └─────┘ └─────┘ └─────┘              │
└─────────────────────────────────────────┘

Step 4: Review & Post
┌─────────────────────────────────────────┐
│  ✅ Your issue is live!                 │
│                                         │
│  Mechanics in your area will be         │
│  notified. You'll get responses         │
│  within minutes.                        │
│                                         │
│  [View My Issue]  [Post Another]        │
└─────────────────────────────────────────┘
```

### 6.3 Receiving Responses & Chatting

```
Customer Dashboard → My Issues → "Grinding noise when braking"

┌─────────────────────────────────────────────────────┐
│  3 Mechanics Responded                               │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ ⭐ 4.8  Ahmed K. — Verified Brake Specialist   │  │
│  │ "Sounds like worn brake pads. Estimate:         │  │
│  │  AED 150-300. Fix time: 1 hour."               │  │
│  │ Confidence: HIGH     [💬 Chat]  [📞 Call]      │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ ⭐ 4.2  Omar S. — General Mechanic             │  │
│  │ "Could be brake pads or rotors. Need to see    │  │
│  │  video. AED 200-500."                          │  │
│  │ Confidence: MEDIUM   [💬 Chat]  [📞 Call]      │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ ⭐ 3.9  Sara M. — Auto Electrician             │  │
│  │ "Wants video call to hear the sound live.       │  │
│  │  AED 25 for 15-min call."                      │  │
│  │ Confidence: LOW      [💬 Chat]  [📞 Call]      │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 6.4 Chat Experience

```
┌─────────────────────────────────────────────────────┐
│  Chat with Ahmed K.  ⭐ 4.8  ● Online              │
│  Re: Grinding noise when braking                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Ahmed: Hi! I listened to your audio clip.           │
│  That's definitely the brake pad wear indicator.     │
│  14:30                                               │
│                                                      │
│                    You: Is it safe to drive on? │
│                                           14:31 │
│                                                      │
│  Ahmed: For a few days, yes. But don't delay —       │
│  if the metal reaches the rotor, it'll cost 3x more. │
│  14:32                                               │
│                                                      │
│  Ahmed: Want me to give you a shop recommendation    │
│  in your area?                                       │
│  14:32                                               │
│                                                      │
│           [📷 Photo] [🎙️ Voice] [📞 Video Call]    │
│  ┌─────────────────────────────────────┐ [Send ►]   │
│  │ Type a message...                   │             │
│  └─────────────────────────────────────┘             │
└─────────────────────────────────────────────────────┘
```

### 6.5 After Resolution

```
┌─────────────────────────────────────────┐
│  Issue Resolved! 🎉                     │
│                                         │
│  How was your experience with Ahmed K.? │
│                                         │
│  ⭐⭐⭐⭐⭐ (tap to rate)              │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ "Very helpful! Accurate diagnosis │  │
│  │  saved me a lot of money."        │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Was this diagnosis helpful?            │
│  [👍 Yes]   [👎 No]                    │
│                                         │
│  [Submit Review]                        │
└─────────────────────────────────────────┘
```

### Customer Flow Summary

```
Sign Up → Post Issue (+ media) → Receive Mechanic Responses
  → Chat with Mechanic → (Optional Video Call)
  → Get Diagnosis → Rate & Review → Mark Resolved
```

---

## 7. Mechanic Flow

### 7.1 Onboarding & Verification

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Sign Up     │────►│  Mechanic    │────►│  Upload      │────►│  Pending     │
│  (Choose     │     │  Profile     │     │  Docs        │     │  Verification│
│   "I am a   │     │  - Bio       │     │  - License   │     │              │
│    Mechanic")│     │  - Specialty │     │  - Certs     │     │  "Admin will │
│              │     │  - Rate      │     │  - ID        │     │   review in  │
│              │     │  - Exp Years │     │              │     │   24 hours"  │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
                                                              ┌──────────────┐
                                                              │  ✅ Verified  │
                                                              │  Dashboard   │
                                                              │  Unlocked    │
                                                              └──────────────┘
```

### 7.2 Browsing & Responding to Issues

```
Mechanic Dashboard → Issue Feed

┌─────────────────────────────────────────────────────────────┐
│  🔧 Open Issues in Your Area                 [Filter ▼]     │
│                                                              │
│  Filters: Category | Urgency | Budget | Distance             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🔴 URGENT  "Car won't start — clicking sound"         │  │
│  │ Toyota Camry 2022 · 85K km · Engine · Dubai            │  │
│  │ 📎 1 audio, 2 photos  ·  Posted 5 min ago             │  │
│  │ Budget: AED 200-500   ·  0 responses yet               │  │
│  │ [View Details & Respond]                                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🟡 NORMAL  "AC blowing warm air"                       │  │
│  │ Nissan Patrol 2020 · 120K km · AC · Abu Dhabi          │  │
│  │ 📎 1 video  ·  Posted 20 min ago                       │  │
│  │ Budget: Under AED 50   ·  2 responses                  │  │
│  │ [View Details & Respond]                                │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Submitting a Response

```
┌─────────────────────────────────────────────────────┐
│  Respond to: "Grinding noise when braking"          │
│                                                      │
│  Your Initial Diagnosis:                             │
│  ┌───────────────────────────────────────────────┐  │
│  │ "Based on the audio, this sounds like worn    │  │
│  │  brake pads making contact with the rotor..." │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  Estimated Cost:  Min [150] AED  Max [300] AED      │
│  Estimated Time:  [1-2 hours ▼]                     │
│  Confidence:      ○ Low  ○ Medium  ● High           │
│                                                      │
│  ☐ I'd recommend a video call for better diagnosis  │
│                                                      │
│  [Submit Response]                                   │
└─────────────────────────────────────────────────────┘
```

### 7.4 Mechanic Dashboard

```
┌─────────────────────────────────────────────────────┐
│  🔧 My Dashboard                                    │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Active   │ │ This     │ │ Rating   │            │
│  │ Chats: 5 │ │ Month:   │ │ ⭐ 4.8   │            │
│  │          │ │ AED 1,250│ │ (47 rev) │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│                                                      │
│  📨 Active Conversations          [View All]        │
│  ├── Ahmad R. — Brake noise       ● 2 unread        │
│  ├── Fatima A. — Engine light     ● 1 unread        │
│  └── Mohammed S. — AC issue       ✓ up to date      │
│                                                      │
│  ⚙️ My Availability: [🟢 Available]                │
│  💰 Hourly Rate: AED 50/hr  [Edit]                 │
└─────────────────────────────────────────────────────┘
```

### Mechanic Flow Summary

```
Sign Up → Complete Profile → Upload Docs → Await Verification
  → Browse Issues → Submit Response → Chat with Customer
  → (Optional Video Call) → Get Rated → Earn Money
```

---

## 8. Admin Flow

### 8.1 Admin Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  🛡️ SalikChat Admin Panel                                   │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Users    │ │ Active   │ │ Pending  │ │ Revenue  │       │
│  │ 1,247   │ │ Issues   │ │ Verif.   │ │ AED      │       │
│  │         │ │ 89       │ │ 12       │ │ 15,340   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  📊 Platform Analytics                                       │
│  ├── Issues posted today: 23                                 │
│  ├── Messages sent today: 458                                │
│  ├── Video calls today: 7                                    │
│  ├── Avg response time: 8 min                                │
│  └── Customer satisfaction: 4.6/5                            │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Mechanic Verification

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Mechanic Verification Queue (12 pending)                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Ahmed Al-Kareem                                       │  │
│  │  Applied: Feb 20, 2026                                 │  │
│  │  Specialty: Engine & Transmission                      │  │
│  │  Experience: 8 years                                   │  │
│  │  Location: Dubai, Al Quoz                              │  │
│  │                                                        │  │
│  │  📄 Documents:                                         │  │
│  │  ├── [View] Trade License — Al Kareem Auto Repair      │  │
│  │  ├── [View] ASE Certification — Engine Repair          │  │
│  │  └── [View] Emirates ID                                │  │
│  │                                                        │  │
│  │  [✅ Approve]  [❌ Reject]  [💬 Request More Info]     │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 User Management

```
┌─────────────────────────────────────────────────────────────┐
│  👥 User Management        [Search: ____________] [Filter]   │
│                                                              │
│  Name          │ Role     │ Status   │ Joined    │ Actions  │
│  ─────────────┼──────────┼──────────┼───────────┼──────────│
│  Ahmad R.     │ Customer │ Active   │ Jan 2026  │ [⋮]      │
│  Ahmed K.     │ Mechanic │ Verified │ Dec 2025  │ [⋮]      │
│  Sara M.      │ Mechanic │ Pending  │ Feb 2026  │ [⋮]      │
│  Omar S.      │ Customer │ Banned   │ Nov 2025  │ [⋮]      │
│                                                              │
│  Actions: View Profile | View Activity | Suspend | Ban      │
└─────────────────────────────────────────────────────────────┘
```

### 8.4 Dispute Resolution

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Dispute #1042                                           │
│                                                              │
│  Customer: Ahmad R.                                          │
│  Mechanic: Omar S.                                           │
│  Issue: "Mechanic said it would cost AED 200 but the shop   │
│          charged me AED 800"                                 │
│                                                              │
│  📜 Chat History: [View Full Transcript]                     │
│  📞 Call Records: 1 video call (12 min)                      │
│                                                              │
│  Admin Notes:                                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  [Refund Customer]  [Warn Mechanic]  [Dismiss]  [Escalate]  │
└─────────────────────────────────────────────────────────────┘
```

### Admin Flow Summary

```
Login → Dashboard Overview → Verify Mechanics (approve/reject docs)
  → Manage Users (suspend/ban) → Handle Disputes (view chat history)
  → View Analytics → Configure Platform Settings → Manage Payouts
```

---

## 9. Real-Time Chat System

### Technology: Supabase Realtime

The chat system is built entirely on **Supabase Realtime subscriptions**. Messages are rows in the `messages` table. When a new row is inserted, Supabase broadcasts it to all subscribers of that conversation.

### How It Works

```
1. Customer opens conversation → Frontend subscribes to:
   supabase.channel('conversation:abc123')
     .on('postgres_changes', { table: 'messages', filter: 'conversation_id=eq.abc123' })
     .subscribe()

2. Mechanic sends a message → Frontend inserts row:
   supabase.from('messages').insert({ conversation_id, sender_id, content })

3. Supabase auto-broadcasts the change → Customer's subscription fires
   → New message appears instantly (no polling)

4. Read receipts → When customer scrolls to message:
   supabase.from('messages').update({ is_read: true }).eq('id', msg.id)
```

### Chat Features

| Feature | Implementation |
|---|---|
| Text messages | Row insert in `messages` table |
| Image/audio/video in chat | Upload to Supabase Storage → store URL in `media_url` |
| Read receipts | `is_read` boolean on message row |
| Typing indicators | Supabase Realtime broadcast (ephemeral, not stored) |
| Online/offline status | Supabase Presence (built-in) |
| Unread count | `SELECT COUNT(*) FROM messages WHERE is_read = false AND conversation_id = X` |
| Message history | Paginated query on `messages` table |

### Why Supabase Realtime (not Socket.io / Pusher)

1. **Zero extra infrastructure** — no WebSocket server to deploy & scale
2. **Messages are persisted automatically** — they're just DB rows
3. **Row Level Security** — only conversation participants can read/write
4. **Built-in presence** — online/offline indicators for free
5. **Works with your existing Postgres** — no data sync needed

---

## 10. Video Call System

### Technology: LiveKit (Open-Source WebRTC)

LiveKit is a free, open-source WebRTC platform with:
- **Python SDK** (`livekit-server-sdk`) for token generation on FastAPI
- **React SDK** (`@livekit/components-react`) for the call UI
- **Cloud option** (LiveKit Cloud) for zero-infra, or **self-host** on any VPS

### Video Call Flow

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│ Customer │       │ FastAPI  │       │ LiveKit  │
│ (React)  │       │ Backend  │       │ Server   │
└────┬─────┘       └────┬─────┘       └────┬─────┘
     │                   │                   │
     │ 1. Click "Video   │                   │
     │    Call" button    │                   │
     │──────────────────►│                   │
     │                   │ 2. Create room    │
     │                   │    + generate     │
     │                   │    tokens         │
     │                   │──────────────────►│
     │                   │                   │
     │                   │◄──────────────────│
     │ 3. Return tokens  │   Room created    │
     │◄──────────────────│                   │
     │                   │                   │
     │ 4. Join room with │                   │
     │    LiveKit React  │                   │
     │    SDK            │                   │
     │──────────────────────────────────────►│
     │                   │                   │
     │     5. Video/Audio streaming          │
     │◄─────────────────────────────────────►│
     │                   │                   │
```

### FastAPI Token Generation

```python
from livekit import api

async def create_video_call(conversation_id: str, user_id: str):
    """Generate LiveKit room token for a video call."""
    room_name = f"salik-{conversation_id}"

    token = api.AccessToken(
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    token.with_identity(user_id)
    token.with_name(user_display_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
    ))

    return {
        "token": token.to_jwt(),
        "room_name": room_name,
        "livekit_url": os.getenv("LIVEKIT_URL"),
    }
```

### Frontend (React + LiveKit)

```tsx
import { LiveKitRoom, VideoConference } from "@livekit/components-react";

function VideoCall({ token, roomName, livekitUrl }) {
  return (
    <LiveKitRoom
      serverUrl={livekitUrl}
      token={token}
      connect={true}
    >
      <VideoConference />
    </LiveKitRoom>
  );
}
```

---

## 11. File Upload System

### Supabase Storage Buckets

| Bucket | Purpose | Access |
|---|---|---|
| `issue-media` | Audio, photos, videos for car issues | Public read (issue owner + mechanics), authenticated write |
| `chat-media` | Files shared in chat | Conversation participants only (RLS) |
| `mechanic-docs` | Verification documents | Admin + mechanic owner only |
| `avatars` | Profile pictures | Public read, owner write |

### Upload Flow

```
1. User selects file (audio/image/video)
2. Frontend validates: file type, size limits (audio: 10MB, image: 5MB, video: 50MB)
3. Frontend uploads to Supabase Storage:
   supabase.storage.from('issue-media').upload(path, file)
4. Returns public URL
5. URL stored in issue_media table (for issues) or messages.media_url (for chat)
```

### Audio Recording (In-Browser)

```
- Use MediaRecorder API to record engine sounds directly in the browser
- "Hold to record" UX for mobile
- Auto-compress to WebM/Opus format
- Max 60 seconds per recording
- Waveform visualization during playback
```

---

## 12. Notifications

### Notification Triggers

| Event | Who Gets Notified | Channel |
|---|---|---|
| New mechanic response to issue | Customer | Push + In-app |
| New chat message | Recipient | Push + In-app |
| Video call request | Recipient | Push + In-app + Sound |
| Issue posted in specialty area | Relevant mechanics | In-app |
| Mechanic verified | Mechanic | Email + In-app |
| New review received | Mechanic | In-app |
| Payment received | Mechanic | Email + In-app |

### Implementation

- **In-app**: Supabase Realtime subscription on `notifications` table
- **Push (future)**: Web Push API via service worker
- **Email (future)**: Resend or SendGrid via FastAPI

---

## 13. Monetization Model

### Phase 1 — MVP (Free)
- Free for all users during launch
- Goal: build user base and validate idea

### Phase 2 — Freemium
| What | Price |
|---|---|
| Post an issue | Free |
| Receive mechanic responses | Free |
| Chat with mechanics | Free (first 3 per issue) |
| Video call with mechanic | **AED 25-50** (set by mechanic) |
| Featured issue (priority visibility) | **AED 10** |

### Platform Revenue
- **15% commission** on all paid video consultations
- **Featured listing fees** from mechanics (future)
- **Subscription tier** for mechanics (unlimited responses per month) (future)

---

## 14. API Endpoints Overview

### Auth (Supabase handles directly)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register user (Supabase) |
| POST | `/auth/login` | Login (Supabase) |
| POST | `/auth/logout` | Logout (Supabase) |
| GET | `/auth/user` | Get current user (Supabase) |

### Issues (FastAPI)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/issues` | Create new car issue |
| GET | `/api/issues` | List issues (with filters) |
| GET | `/api/issues/{id}` | Get issue details |
| PATCH | `/api/issues/{id}` | Update issue status |
| DELETE | `/api/issues/{id}` | Delete issue (owner only) |
| POST | `/api/issues/{id}/media` | Upload media to issue |

### Mechanic Responses (FastAPI)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/issues/{id}/responses` | Submit response to issue |
| GET | `/api/issues/{id}/responses` | List responses for issue |

### Conversations & Chat (FastAPI + Supabase)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/conversations` | Start conversation |
| GET | `/api/conversations` | List my conversations |
| GET | `/api/conversations/{id}/messages` | Get message history |
| POST | `/api/conversations/{id}/messages` | Send message (also via Supabase client) |

### Video Calls (FastAPI)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/calls/create` | Create LiveKit room, return tokens |
| POST | `/api/calls/{id}/end` | End call, record duration |

### Mechanic Management (FastAPI)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/mechanics` | List verified mechanics |
| GET | `/api/mechanics/{id}` | Mechanic public profile |
| PATCH | `/api/mechanics/{id}` | Update my mechanic profile |
| POST | `/api/mechanics/{id}/verify` | Admin: verify mechanic |

### Reviews (FastAPI)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/reviews` | Submit review |
| GET | `/api/mechanics/{id}/reviews` | Get mechanic reviews |

### Admin (FastAPI)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/stats` | Platform analytics |
| GET | `/api/admin/verification-queue` | Pending mechanic verifications |
| GET | `/api/admin/users` | User management |
| POST | `/api/admin/users/{id}/suspend` | Suspend user |
| GET | `/api/admin/disputes` | List disputes |

---

## 15. Security Considerations

### Authentication & Authorization
- **Supabase Auth** handles token issuance (JWT)
- **Row Level Security (RLS)** on all tables — users can only access their own data
- **FastAPI middleware** validates Supabase JWT on every request
- **Role-based access**: customer, mechanic, admin — enforced at DB and API level

### Data Protection
- All media uploads are scoped to authenticated users
- Mechanic verification documents are in a **private bucket** (admin-only access)
- Chat messages are only accessible by conversation participants (RLS)
- Video call tokens are short-lived (1 hour expiry)

### Rate Limiting
- Issue posting: 5 per hour per user
- Message sending: 60 per minute per user
- File uploads: 20 per hour per user
- API calls: 100 per minute per IP

### Secrets Management
- All API keys, DB credentials, LiveKit secrets → **Infisical**
- Zero .env files in Git
- Environment-specific configs: dev, staging, prod

---

*End of Design Document*
