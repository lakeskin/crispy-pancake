# SalikChat — Development Phases

> **Version**: 1.0
> **Date**: February 2026
> **Estimated Total Timeline**: 12-16 weeks (solo developer with AI assistance)

---

## 📋 TABLE OF CONTENTS

1. [Phase 0 — Project Setup & Foundation](#phase-0--project-setup--foundation-week-1)
2. [Phase 1 — MVP Core](#phase-1--mvp-core-weeks-2-5)
3. [Phase 2 — Chat & Real-Time](#phase-2--chat--real-time-weeks-6-8)
4. [Phase 3 — Video Calls & Media](#phase-3--video-calls--media-weeks-9-10)
5. [Phase 4 — Payments & Reviews](#phase-4--payments--reviews-weeks-11-12)
6. [Phase 5 — Admin Panel & Polish](#phase-5--admin-panel--polish-weeks-13-14)
7. [Phase 6 — Launch & Growth](#phase-6--launch--growth-weeks-15-16)
8. [Future Phases](#future-phases)
9. [Risk Register](#risk-register)
10. [Definition of Done](#definition-of-done)

---

## Phase 0 — Project Setup & Foundation (Week 1)

**Goal**: Set up the monorepo, configure all services, deploy empty shells to verify the pipeline works end-to-end.

### Tasks

| # | Task | Details |
|---|---|---|
| 0.1 | **Monorepo structure** | Create folder structure per architecture rules: `apps/`, `shared/`, `deploymentTools/` |
| 0.2 | **Backend scaffolding** | FastAPI project with `pyproject.toml`, health check endpoint, CORS config, YAML-based config loader |
| 0.3 | **Frontend scaffolding** | Next.js 15 + Tailwind CSS + shadcn/ui. Landing page shell with responsive layout |
| 0.4 | **Supabase project** | Create Supabase project. Run SQL migrations for all tables from DESIGN.md. Enable RLS. Set up storage buckets |
| 0.5 | **Auth integration** | Supabase Auth: email/password + Google OAuth. JWT validation middleware in FastAPI |
| 0.6 | **Infisical setup** | Create Infisical project with `dev` / `staging` / `prod` environments. Wire up to FastAPI + Next.js |
| 0.7 | **Deployment pipeline** | Deploy FastAPI to Railway. Deploy Next.js to Vercel. Verify both can talk to Supabase |
| 0.8 | **Config system** | Create `config.yaml` with all configurable values. Build config loader utility in `shared/` |

### Deliverable
- Deployed (empty) frontend at `salik.chat` (or staging subdomain)
- Deployed (empty) backend at `api.salik.chat`
- Both authenticated against Supabase
- CI/CD pipeline working

### Tech Checklist
```
☐ FastAPI running locally with hot reload
☐ Next.js running locally with hot reload
☐ Supabase tables created (all from DESIGN.md)
☐ RLS policies enabled
☐ Storage buckets created (issue-media, chat-media, mechanic-docs, avatars)
☐ Infisical secrets loaded into dev environment
☐ Railway deploy successful
☐ Vercel deploy successful
☐ Health check: GET /api/health returns 200
```

---

## Phase 1 — MVP Core (Weeks 2-5)

**Goal**: Car owners can post issues with car details. Mechanics can browse and respond. No chat yet — just the issue board and responses.

### Week 2: Auth & User Profiles

| # | Task | Details |
|---|---|---|
| 1.1 | **Sign-up page** | Email/password + Google. Role selection: "I need help with my car" / "I am a mechanic" |
| 1.2 | **Profile setup flow** | Customer: name, city, phone. Mechanic: name, city, specializations, experience, bio, hourly rate |
| 1.3 | **Profile page** | View/edit profile. Avatar upload to Supabase Storage |
| 1.4 | **Auth middleware** | Protected routes in Next.js. JWT validation in FastAPI. Role-based guards |
| 1.5 | **Telemetry setup** | Basic event tracking: signups, logins, page views (shared/telemetry module) |

### Week 3: Issue Posting

| # | Task | Details |
|---|---|---|
| 1.6 | **Issue creation form** | Multi-step form: Basic info → Car details → Media upload → Review & Submit |
| 1.7 | **Car make/model selector** | Searchable dropdown with common makes/models (from YAML config) |
| 1.8 | **Media upload (basic)** | Upload images to Supabase Storage. File type validation. Progress indicator |
| 1.9 | **Audio recording** | In-browser audio recorder (MediaRecorder API). "Hold to record" on mobile. Waveform playback |
| 1.10 | **Issue detail page** | Full issue view with all media, car details, description. Audio player. Image gallery |

### Week 4: Mechanic Feed & Responses

| # | Task | Details |
|---|---|---|
| 1.11 | **Mechanic issue feed** | List of open issues. Filters: category, urgency, location, budget. Pagination |
| 1.12 | **Issue detail (mechanic view)** | Same as customer view + "Respond" CTA |
| 1.13 | **Response submission form** | Initial diagnosis, cost estimate (min/max), fix time, confidence level, video call suggestion |
| 1.14 | **Response list (customer view)** | Customer sees all mechanic responses on their issue. Mechanic name, rating, diagnosis, cost |
| 1.15 | **FastAPI CRUD endpoints** | All issue + response endpoints from DESIGN.md. Input validation with Pydantic |

### Week 5: Dashboards & Navigation

| # | Task | Details |
|---|---|---|
| 1.16 | **Customer dashboard** | "My Issues" list with status badges. Quick stats: open issues, total responses |
| 1.17 | **Mechanic dashboard** | "My Responses" list. Quick stats: active conversations, this month's earnings, rating |
| 1.18 | **Navigation & layout** | Responsive sidebar/bottom nav. Role-appropriate menu items. Notification bell (placeholder) |
| 1.19 | **Landing page** | Hero section, how-it-works, testimonials (placeholder), CTA. Mobile-responsive |
| 1.20 | **Error handling** | Global error boundaries (React). FastAPI exception handlers. User-friendly error messages |

### Phase 1 Deliverable
- Car owners can sign up, post issues with audio/photos, and see mechanic responses
- Mechanics can sign up, browse issues, and submit diagnoses
- Both have dashboards showing their activity
- **No chat, no video calls, no payments** — just the issue marketplace

### Phase 1 Success Criteria
```
☐ End-to-end: Customer posts issue → Mechanic sees it → Mechanic responds → Customer sees response
☐ Audio recording works on mobile Chrome and Safari
☐ Image upload with preview and delete
☐ Mechanic feed loads in under 2 seconds
☐ All API endpoints have input validation
☐ RLS prevents cross-user data access
```

---

## Phase 2 — Chat & Real-Time (Weeks 6-8)

**Goal**: Customers and mechanics can chat in real-time. The issue board updates live when new issues/responses appear.

### Week 6: Chat Foundation

| # | Task | Details |
|---|---|---|
| 2.1 | **Conversation creation** | When customer clicks "Chat" on a mechanic response, create conversation row. Redirect to chat |
| 2.2 | **Chat UI component** | Message list, text input, send button. Auto-scroll. Timestamps. Sender avatars |
| 2.3 | **Supabase Realtime subscription** | Subscribe to new messages in conversation. Messages appear instantly without refresh |
| 2.4 | **Message persistence** | All messages stored in `messages` table. Paginated history on scroll-up |
| 2.5 | **Conversation list** | Left sidebar (desktop) / separate page (mobile) showing all active conversations |

### Week 7: Chat Enhancements

| # | Task | Details |
|---|---|---|
| 2.6 | **Image sharing in chat** | Upload/paste image → appears inline in chat |
| 2.7 | **Audio messages in chat** | Record & send voice clips within chat. Waveform playback |
| 2.8 | **Read receipts** | Double-check marks when message is read. Update `is_read` field |
| 2.9 | **Typing indicators** | Supabase Realtime broadcast. "Ahmed is typing..." ephemeral indicator |
| 2.10 | **Online/offline status** | Supabase Presence. Green dot on online users. "Last seen 5 min ago" |

### Week 8: Real-Time Feed & Notifications (In-App)

| # | Task | Details |
|---|---|---|
| 2.11 | **Live issue feed** | New issues appear in mechanic feed without refresh (Supabase Realtime on `car_issues`) |
| 2.12 | **Live response notifications** | Customer gets in-app notification when mechanic responds |
| 2.13 | **Unread message badges** | Red badge on conversation list. Badge on notification bell |
| 2.14 | **Notification dropdown** | Click bell → see recent notifications. Mark as read. Click to navigate |
| 2.15 | **System messages** | "Conversation started", "Mechanic joined", "Issue marked as resolved" |

### Phase 2 Deliverable
- Full real-time chat between customers and mechanics
- Typing indicators, read receipts, online status
- In-app notifications for all key events
- Live-updating issue feed

### Phase 2 Success Criteria
```
☐ Messages appear in < 500ms for both parties
☐ Chat works on mobile (responsive layout)
☐ Image/audio sharing in chat works
☐ Typing indicator shows/hides correctly
☐ Unread counts update in real-time
☐ 0 messages lost (verify with test: send 100 messages rapidly)
```

---

## Phase 3 — Video Calls & Media (Weeks 9-10)

**Goal**: Mechanics can conduct live video/voice consultations with customers. Full media pipeline for issue uploads.

### Week 9: Video Calls

| # | Task | Details |
|---|---|---|
| 3.1 | **LiveKit setup** | Deploy LiveKit server (Cloud or self-hosted). Configure Python SDK in FastAPI |
| 3.2 | **Token generation endpoint** | `POST /api/calls/create` — generates LiveKit room + participant tokens |
| 3.3 | **Video call UI** | Full-screen video call component using `@livekit/components-react`. Camera/mic toggles, hang up |
| 3.4 | **Call initiation flow** | "Request Video Call" button in chat → notification to other party → accept/decline |
| 3.5 | **Call end & logging** | On disconnect → record duration. System message in chat: "Video call ended (12 min)" |

### Week 10: Advanced Media & Call Features

| # | Task | Details |
|---|---|---|
| 3.6 | **Video upload for issues** | Upload video files (up to 50MB). Auto-generate thumbnail. Video player in issue detail |
| 3.7 | **Screen share in calls** | Mechanic can share screen (to show repair instructions). Built into LiveKit SDK |
| 3.8 | **Voice-only calls** | Option to start audio-only call (lower bandwidth). Toggle video on/off mid-call |
| 3.9 | **Call quality indicators** | Connection quality badge. Auto-switch to audio-only on poor connection |
| 3.10 | **Missed call handling** | If no answer in 30 seconds → mark as "missed". System message. Retry option |

### Phase 3 Deliverable
- 1-on-1 video/voice calls between customers and mechanics
- Call UI with camera/mic/screen controls
- Videos uploadable as issue media
- Call duration logged and displayed

### Phase 3 Success Criteria
```
☐ Video call connects in < 5 seconds
☐ Call works on Chrome, Safari, Firefox (desktop + mobile)
☐ Audio quality sufficient to hear engine sounds clearly
☐ Screen sharing works
☐ Call session persists if one party briefly disconnects (reconnect within 15s)
```

---

## Phase 4 — Payments & Reviews (Weeks 11-12)

**Goal**: Mechanics can charge for video consultations. Customers can pay and review mechanics.

### Week 11: Payments

| # | Task | Details |
|---|---|---|
| 4.1 | **Stripe integration** | Stripe Connect for marketplace payments. Mechanic onboarding (bank account) |
| 4.2 | **Payment flow** | Customer pays before video call. Amount = mechanic's rate x estimated time. Stripe Checkout |
| 4.3 | **Platform fee** | 15% commission deducted. Remaining 85% → mechanic's Stripe Connect account |
| 4.4 | **Transaction records** | Log all transactions. Customer sees payment history. Mechanic sees earnings |
| 4.5 | **Refund handling** | Admin can issue refunds via dispute resolution. Stripe refund API |

### Week 12: Reviews & Ratings

| # | Task | Details |
|---|---|---|
| 4.6 | **Review prompt** | After issue resolved or conversation closed → prompt customer to rate (1-5 stars + comment) |
| 4.7 | **Review UI** | Star rating component. Optional text comment. "Was this helpful?" toggle |
| 4.8 | **Mechanic rating calculation** | Update `rating_avg` and `rating_count` on mechanic profile. Display on all mechanic cards |
| 4.9 | **Review display** | Mechanic profile shows all reviews. Sorted by recent. Summary stats |
| 4.10 | **Mechanic earnings dashboard** | Monthly earnings chart. Transaction list. Pending payouts. Stripe dashboard link |

### Phase 4 Deliverable
- Stripe-powered payments for video consultations
- 15% platform commission
- Customer reviews and mechanic ratings
- Earnings dashboard for mechanics

### Phase 4 Success Criteria
```
☐ Payment flow works end-to-end in Stripe test mode
☐ Mechanic receives payout (test mode)
☐ Refund works from admin panel
☐ Rating correctly updates mechanic average
☐ Reviews display on mechanic profile
```

---

## Phase 5 — Admin Panel & Polish (Weeks 13-14)

**Goal**: Full admin panel for platform management. UI/UX polish. Performance optimization.

### Week 13: Admin Panel

| # | Task | Details |
|---|---|---|
| 5.1 | **Admin authentication** | Admin-only route group with middleware. Separate login or role-based |
| 5.2 | **Dashboard analytics** | Total users, active issues, messages today, revenue this month, avg response time |
| 5.3 | **Mechanic verification queue** | List pending mechanics. View uploaded documents. Approve/reject with notes |
| 5.4 | **User management** | Search users. View profile & activity. Suspend/ban with reason. Reactivate |
| 5.5 | **Dispute resolution** | View disputes. Read full chat transcript. Issue refunds. Warn/ban users |

### Week 14: Polish & Optimization

| # | Task | Details |
|---|---|---|
| 5.6 | **Mobile responsiveness audit** | Test every page on iOS Safari, Android Chrome. Fix layout issues |
| 5.7 | **Loading states** | Skeleton loaders on all data-fetching pages. Optimistic UI for chat |
| 5.8 | **SEO & Meta tags** | Landing page SEO. Open Graph tags. Structured data for issue pages |
| 5.9 | **Performance optimization** | Image optimization (Next.js Image). Lazy loading. Bundle analysis. DB query optimization |
| 5.10 | **Accessibility** | Keyboard navigation. Screen reader labels. Color contrast compliance. Focus management |
| 5.11 | **Error monitoring** | Sentry integration (frontend + backend). Error alerting |
| 5.12 | **Rate limiting** | Implement rate limits per DESIGN.md spec. FastAPI middleware |

### Phase 5 Deliverable
- Fully functional admin panel
- Polished, mobile-first UI
- Performance budget met (< 3s first load)
- Error monitoring active

### Phase 5 Success Criteria
```
☐ Admin can verify a mechanic end-to-end
☐ Admin can suspend a user and they can't log in
☐ Lighthouse score > 90 on landing page
☐ No layout shift on mobile
☐ Sentry capturing errors in production
```

---

## Phase 6 — Launch & Growth (Weeks 15-16)

**Goal**: Beta launch. Onboard first users. Gather feedback. Iterate.

### Week 15: Pre-Launch

| # | Task | Details |
|---|---|---|
| 6.1 | **Beta testing** | Invite 10 car owners + 5 mechanics for closed beta. Provide feedback form |
| 6.2 | **Bug fixes from beta** | Priority fixes based on beta feedback |
| 6.3 | **Content & copy** | Professional landing page copy. FAQ page. Terms of Service. Privacy Policy |
| 6.4 | **Email notifications** | Key emails: welcome, mechanic verified, new response, payment receipt (via Resend) |
| 6.5 | **Production environment** | Switch to production Supabase. Production Stripe. Production LiveKit. Infisical prod env |

### Week 16: Launch

| # | Task | Details |
|---|---|---|
| 6.6 | **Public launch** | Open registrations. Announce on social media |
| 6.7 | **Monitoring** | Watch error rates, response times, user signups. Daily check on Sentry + Supabase dashboard |
| 6.8 | **User feedback channel** | In-app feedback button. Feedback Supabase table or Typeform |
| 6.9 | **Analytics dashboard** | PostHog or Plausible for user behavior analytics |
| 6.10 | **First iteration** | Based on week 1 feedback: quick fixes, UX improvements, feature requests |

### Phase 6 Deliverable
- App live and accepting real users
- Monitoring and alerting active
- Feedback loop established
- First iteration shipped

---

## Future Phases

### Phase 7 — AI Features (Post-Launch)
| Feature | Description |
|---|---|
| **AI Pre-Diagnosis** | User describes issue → AI gives preliminary diagnosis before mechanic responds. Uses GPT-4o or similar via FastAPI |
| **Audio Analysis** | AI analyzes engine audio recordings to suggest possible issues. Help mechanics prioritize |
| **Smart Matching** | AI matches issues to mechanics based on specialization, rating, availability, location |
| **Chat Summarization** | After conversation ends, AI summarizes the diagnosis for the customer's records |

### Phase 8 — Mobile App
| Feature | Description |
|---|---|
| **React Native / Expo** | Native mobile app sharing business logic with web. Better camera/audio access |
| **Push Notifications** | FCM/APNs for real-time push. Critical for video call invitations |
| **Offline Support** | Cache recent conversations. Queue messages when offline |

### Phase 9 — Marketplace Expansion
| Feature | Description |
|---|---|
| **Mechanic Shop Profiles** | Shops (not just individuals) can register. Multiple mechanics under one shop |
| **Booking System** | Book in-person appointments at mechanic shops directly from the app |
| **Parts Marketplace** | Mechanics recommend parts. Affiliate links or integrated purchase |
| **Insurance Integration** | Connect with car insurance for covered repairs |

### Phase 10 — Geographic Expansion
| Feature | Description |
|---|---|
| **Multi-language** | Arabic + English (RTL support in Next.js) |
| **Multi-currency** | AED, SAR, USD, EUR |
| **Regional mechanics** | Expand beyond UAE to GCC, then globally |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Low mechanic supply at launch** | High | High | Pre-recruit 20+ mechanics before launch. Offer free premium for first 3 months |
| **Poor audio quality for engine sounds** | Medium | Medium | Provide recording tips. Test on 10+ devices. Allow high-quality audio upload |
| **Supabase Realtime latency** | Medium | Low | Supabase handles this well. Fallback: polling every 2s |
| **LiveKit connection issues** | Medium | Medium | Graceful fallback to audio-only. Retry logic. Connection quality indicator |
| **Stripe onboarding friction** | Medium | Medium | Clear instructions for mechanics. Support chat for onboarding issues |
| **Scope creep** | High | High | Strict MVP-first approach. No feature goes into a phase unless predecessor is done |
| **Security breach** | Critical | Low | RLS on all tables. JWT validation. Rate limiting. Infisical for secrets. Sentry for monitoring |

---

## Definition of Done

A feature is **done** when:

1. **Code works** — Feature performs as described in DESIGN.md
2. **Config-driven** — All configurable values are in YAML (per instruction rules)
3. **Shared modules used** — Auth, telemetry, storage use shared utilities (per instruction rules)
4. **No hardcoded secrets** — All secrets in Infisical
5. **RLS enabled** — Database access scoped to authorized users
6. **Mobile responsive** — Works on 375px+ screens
7. **Error handled** — Graceful error states, no blank screens
8. **Tested** — Manual testing on Chrome + Safari (desktop + mobile)
9. **Deployed** — Running on staging environment before merge to production

---

## Quick Start for Development

```bash
# 1. Clone the repo
git clone <repo-url> && cd SalikChat

# 2. Load secrets
infisical run --env=dev -- echo "Secrets loaded"

# 3. Start backend
cd apps/backend
pip install -r requirements.txt
infisical run --env=dev -- uvicorn main:app --reload

# 4. Start frontend
cd apps/frontend
npm install
infisical run --env=dev -- npm run dev

# 5. Open browser
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs (Swagger)
# Supabase: https://app.supabase.com/project/<your-project>
```

---

*End of Development Phases Document*
