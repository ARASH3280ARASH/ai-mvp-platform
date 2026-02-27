# Whilber-AI — Freemium Model Roadmap
**Date:** 2026-02-23
**Version:** 1.0

---

## 1. Plan Tiers Overview

| | **Free (رایگان)** | **Pro (حرفه‌ای)** | **Premium (ویژه)** | **Enterprise (سازمانی)** |
|---|---|---|---|---|
| **Price** | 0 | 199,000 T/month | 499,000 T/month | 1,490,000 T/month |
| **Target** | New users exploring | Active traders | Serious/full-time traders | Teams, fund managers |
| **Strategies** | 32 (Original) | 72 (Original + Phase 1) | 184+ (All) | 184+ (All) |
| **Symbols** | 7 (Forex Major) | 30 (Forex + Metals + Indices) | 55+ (All incl. Crypto) | 55+ (All) |
| **Timeframes** | 3 (H1, H4, D1) | 5 (M15, M30, H1, H4, D1) | 7 (All: M1-D1) | 7 (All) |
| **Daily Analyses** | 5 | 50 | Unlimited | Unlimited |
| **Multi-Symbol** | No | 3 symbols at once | 10 symbols at once | Unlimited |
| **Alerts** | 2 active | 15 active | 50 active | Unlimited |
| **Alert Channels** | Desktop only | Desktop + Email | Desktop + Email + Telegram | All + API Webhook |
| **Alert Types** | Signal only | Signal + Price | All 12 types | All + Custom |
| **Strategy Builder** | View only | 3 saved strategies | 20 saved strategies | Unlimited |
| **MQL Export** | No | MQL5 only | MQL4 + MQL5 | MQL4 + MQL5 + Batch |
| **Backtest** | No | Last 30 days | Full history | Full + Optimization |
| **Risk Manager** | Basic calculator | 3 presets + 2 trailing | All 6 trailing + all partial | All + custom profiles |
| **Journal** | 10 entries/month | 100 entries/month | Unlimited | Unlimited + Team view |
| **Track Record** | Top 5 strategies | Top 20 + Export CSV | Full + CSV + HTML reports | Full + API export |
| **Performance** | Summary only | Full dashboard | Full + History | Full + Multi-account |
| **Heatmap** | No | View only | Full + export | Full + API |
| **Robot Store** | Browse only | Browse + 2 downloads/month | Unlimited downloads | Unlimited + Priority |
| **Robot Reviews** | Read only | Read + Write | Read + Write | All + Moderate |
| **Telegram Bot** | No | Alerts only | Full (alerts + signals) | Full + Custom bot |
| **Data Retention** | 7 days | 90 days | 1 year | Unlimited |
| **Support** | Community | Email (48h) | Email (12h) + Telegram | Priority (2h) + Phone |

---

## 2. Feature-by-Feature Restriction Details

### 2.1 Strategy Analysis (Dashboard)

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Available strategies | 32 original | 72 (+ Phase 1) | 184+ (all) | 184+ (all) |
| Symbols accessible | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD | + Metals, Indices, minor FX | + All Crypto | All |
| Timeframes | H1, H4, D1 | + M15, M30 | + M1, M5 | All |
| Analyses per day | 5 | 50 | Unlimited | Unlimited |
| Multi-symbol analysis | No | Up to 3 | Up to 10 | Unlimited |
| Confidence threshold shown | > 60% only | Full | Full | Full |
| Strategy detail (reasons) | Summary only | Full reasons | Full + Farsi detail | Full |
| Cache refresh rate | 120 sec | 60 sec | 30 sec | 15 sec |

**Upsell trigger:** After 5th analysis, show: "به پلن حرفه‌ای ارتقا دهید و روزانه ۵۰ تحلیل انجام دهید!"

### 2.2 Alerts System

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Max active alerts | 2 | 15 | 50 | Unlimited |
| Alert types | Signal Change only | + Price Above/Below, Confidence | All 12 types | All + Custom |
| Delivery channels | Desktop popup | + Email | + Telegram | + Webhook |
| Custom templates | No | 3 templates | 10 templates | Unlimited |
| Alert history retention | 3 days | 30 days | 180 days | Unlimited |
| Rate limit | 5/hour | 20/hour | 100/hour | 200/hour |
| Strategy-specific alerts | No | Yes (for unlocked strategies) | Yes (all) | Yes (all) |

**Upsell trigger:** When creating 3rd alert: "با پلن حرفه‌ای تا ۱۵ هشدار فعال داشته باشید و از تلگرام اطلاع‌رسانی بگیرید!"

### 2.3 Strategy Builder

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Access | View demos only | Full editor | Full editor | Full editor |
| Saved strategies | 0 | 3 | 20 | Unlimited |
| Indicators available | 5 basic (SMA, EMA, RSI, MACD, BB) | 12 indicators | All 20+ | All |
| Conditions per strategy | - | 4 max | 10 max | Unlimited |
| Time filters | No | Basic (session) | Full (time + day + session) | Full |
| MQL Export | No | MQL5 only | MQL4 + MQL5 | Both + Batch export |
| Backtest | No | 30 days history | Full history | Full + Optimization |

**Upsell trigger:** On builder page for free users: "با خرید پلن حرفه‌ای استراتژی اختصاصی خود را بسازید!"

### 2.4 Risk Manager

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Position calculator | Yes (basic) | Yes (full) | Yes (full) | Yes (full) |
| Risk presets | 1 (Conservative) | 3 presets | All + Custom | All + Team profiles |
| Trailing methods | None | Fixed + ATR | All 4 methods | All |
| Partial close | None | 1 level | All 3 levels | All + Custom |
| Break-even | No | Yes | Yes | Yes |
| Live trade monitoring | No | 2 positions | 10 positions | Unlimited |
| Profit-taking methods | None | 2 methods | All 6 methods | All |
| Saved profiles | 0 | 3 | 10 | Unlimited |

**Upsell trigger:** When clicking locked trailing method: "مدیریت حرفه‌ای معاملات با تریلینگ ATR — فقط در پلن حرفه‌ای!"

### 2.5 Trading Journal

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Entries per month | 10 | 100 | Unlimited | Unlimited |
| Emotions tracking | 3 emotions | All 7 | All 7 | All 7 |
| Tags | 3 basic tags | All 11 | All 11 | All + Custom |
| Star rating | Yes | Yes | Yes | Yes |
| Daily notes | No | Yes | Yes | Yes |
| Performance analytics | No | Basic (win/loss) | Full analytics | Full + AI insight |
| Export | No | CSV | CSV + PDF | All formats |

**Upsell trigger:** After 10th entry: "ظرفیت ژورنال رایگان تمام شد! با ارتقا به حرفه‌ای ماهانه ۱۰۰ ثبت داشته باشید."

### 2.6 Track Record

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Strategy ranking view | Top 5 only | Top 20 | Full ranking | Full |
| Trade history | Last 10 trades | Last 100 trades | Full history | Full |
| Equity curve | No | Yes (30 days) | Full | Full |
| Heatmap | No | View only | Full + export | Full + API |
| Export CSV | No | Yes | Yes | Yes |
| Export HTML report | No | No | Yes | Yes |
| Filter options | Symbol only | Symbol + TF | All filters | All |

**Upsell trigger:** Below top 5: "برای مشاهده رتبه‌بندی کامل ۱۸۴ استراتژی، پلن حرفه‌ای را فعال کنید."

### 2.7 Live Performance

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Account summary | Balance only | Full metrics | Full | Full + Multi-account |
| Open positions | Count only | Full details | Full + Events | Full |
| History | No | 30 days | Full | Full |
| Drawdown analysis | No | Yes | Yes | Yes |
| Auto-refresh rate | 120 sec | 30 sec | 10 sec | 5 sec |

### 2.8 Robot Store

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Browse robots | Yes | Yes | Yes | Yes |
| View details | Yes | Yes | Yes | Yes |
| Downloads per month | 0 | 2 | Unlimited | Unlimited |
| Write reviews | No | Yes | Yes | Yes |
| Rating | No | Yes | Yes | Yes |
| Featured access | No | No | Priority | Priority |

**Upsell trigger:** On download button for free: "برای دانلود ربات‌ها پلن حرفه‌ای را فعال کنید."

### 2.9 Telegram Integration

| Restriction | Free | Pro | Premium | Enterprise |
|---|---|---|---|---|
| Bot access | No | Alerts only | Full (signals + alerts) | Full + Custom |
| Signal notifications | No | Filtered | All | All |
| Commands | No | Basic | Full | Full |

---

## 3. Authentication & Anti-Abuse System

### 3.1 Login Methods (Required for all plans)

```
Phase 1: Email + OTP (One-Time Password)
- User enters email
- 6-digit code sent to email
- Code valid for 5 minutes
- Rate limit: 3 attempts per 10 minutes

Phase 2: SMS + OTP (optional, for paid users)
- Iranian mobile number verification
- SMS via Kavenegar/Melipayamak API
- More secure, prevents disposable emails

Phase 3: Telegram Login (optional)
- Link Telegram account to Whilber account
- Login via Telegram bot deeplink
```

### 3.2 Anti-Abuse Measures

| Measure | Implementation |
|---|---|
| **One account per email** | Unique email constraint in DB |
| **One account per phone** | Unique phone constraint (Phase 2) |
| **Disposable email block** | Block known disposable email domains (mailinator, guerrilla, etc.) |
| **Device fingerprint** | Browser fingerprint hash stored per user, flag multi-account from same device |
| **IP rate limiting** | Max 3 registrations per IP per day |
| **Session management** | Max 2 concurrent sessions per account |
| **Trial abuse** | Track used-trial emails, no second free trial |
| **Admin controls** | Admin can manually verify, block, or flag accounts |

### 3.3 User Table Extensions

```sql
ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free';
ALTER TABLE users ADD COLUMN plan_expires_at TEXT;
ALTER TABLE users ADD COLUMN phone TEXT UNIQUE;
ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN device_fingerprint TEXT;
ALTER TABLE users ADD COLUMN daily_analyses INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN daily_analyses_date TEXT;
ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN concurrent_sessions INTEGER DEFAULT 0;
```

---

## 4. Admin Panel Controls

### 4.1 New Admin Tab: "Plans & Subscriptions"

```
Stats Row:
- Total Free users
- Total Pro users
- Total Premium users
- Total Enterprise users
- Monthly revenue
- Churn rate

User Plan Management Table:
- Username | Email | Phone | Plan | Expires | Status | Actions
- Actions: Change Plan | Extend | Revoke | Gift Trial

Plan Configuration:
- Edit plan prices
- Edit feature limits per plan
- Enable/disable specific features
- Set trial period (default 7 days)
- Promotional discount codes

Revenue Dashboard:
- Monthly subscriptions chart
- Plan distribution pie chart
- Upgrade/downgrade tracking
```

### 4.2 Admin Plan Override

- Admin can manually set any user to any plan
- Admin can grant "gift" Pro/Premium for X days
- Admin can create discount codes (e.g., WELCOME50 = 50% off first month)
- Admin can view per-user usage stats (analyses count, alerts count, etc.)

---

## 5. Upsell & Upgrade Messaging Strategy

### 5.1 Where to Show Messages

| Page | Trigger | Message Type |
|---|---|---|
| **Landing (/)** | Always | Pricing section with plan comparison |
| **Dashboard** | Daily limit reached | Modal: "Upgrade for unlimited analyses" |
| **Dashboard** | Locked symbol clicked | Inline: "This symbol requires Pro plan" |
| **Dashboard** | Locked timeframe | Inline: "M1/M5 available in Premium" |
| **Alerts** | Alert limit reached | Banner: "Upgrade for more alerts" |
| **Alerts** | Telegram channel locked | Tooltip: "Telegram alerts in Premium" |
| **Builder** | Open page (free user) | Overlay: "Strategy Builder requires Pro" |
| **Builder** | Export locked | Button disabled + tooltip |
| **Risk Manager** | Locked trailing method | Lock icon + upsell text |
| **Journal** | Monthly limit reached | Modal: "Upgrade for more entries" |
| **Track Record** | Below fold (rank 6+) | Blur + "See all with Pro" |
| **Performance** | Locked metrics | Blur + upgrade prompt |
| **Robots** | Download button (free) | Modal: "Downloads require Pro" |
| **Services** | Always | Updated pricing cards |
| **Guide** | Always | Feature comparison by plan |

### 5.2 Upsell Component Design

```
Locked Feature Overlay:
- Semi-transparent blur over locked content
- Lock icon (🔒)
- Farsi text explaining what's locked
- "Upgrade" CTA button (gradient, prominent)
- "Compare Plans" link

Limit Reached Modal:
- Dark modal with plan comparison
- Current usage shown (e.g., "5/5 analyses used")
- Next plan benefits highlighted
- "Upgrade Now" primary button
- "Maybe Later" dismiss button

Inline Lock Badge:
- Small 🔒 icon next to locked items
- Tooltip on hover: "Available in {plan_name}"
- Click opens upgrade modal
```

### 5.3 Notification Messages (Farsi)

```
Daily limit:     "شما به سقف تحلیل روزانه رسیده‌اید. برای تحلیل نامحدود پلن خود را ارتقا دهید."
Symbol locked:   "نماد {symbol} در پلن {plan_name} قابل دسترسی است."
Feature locked:  "این قابلیت در پلن {plan_name} فعال می‌شود."
Trial ending:    "دوره آزمایشی شما {days} روز دیگر به پایان می‌رسد. همین الان ارتقا دهید!"
Trial ended:     "دوره آزمایشی شما به پایان رسید. برای ادامه استفاده پلنی انتخاب کنید."
Upgrade success: "تبریک! پلن {plan_name} فعال شد. از امکانات جدید لذت ببرید! 🎉"
```

---

## 6. Payment Integration Options (Iran-Compatible)

| Gateway | Type | Notes |
|---|---|---|
| **ZarinPal** | Online payment | Most popular in Iran, supports subscription |
| **IDPay** | Online payment | Good API, subscription support |
| **Pay.ir** | Online payment | Simple integration |
| **Crypto (USDT)** | Manual/auto | For international users |
| **Manual transfer** | Bank transfer | Admin verifies + activates |

### Payment Flow:
```
1. User selects plan on /services or upgrade modal
2. Redirected to payment gateway
3. After payment → callback to /api/payment/verify
4. Server verifies payment → activates plan
5. User redirected to dashboard with success message
6. Receipt stored in DB + emailed to user
```

---

## 7. Implementation Phases (Roadmap)

### Phase A — Foundation (Week 1-2)
1. Extend user DB schema (plan, phone, verification fields)
2. Build email OTP authentication system
3. Create `plan_manager.py` — plan checking, quota tracking
4. Add middleware to check plan on every API request
5. Create `/api/user/plan` endpoint

### Phase B — Backend Restrictions (Week 2-3)
1. Add plan checks to analysis endpoints (symbol/TF/strategy filtering)
2. Add daily analysis counter + reset logic
3. Add plan checks to alerts (max alerts, types, channels)
4. Add plan checks to builder (save limit, indicator access)
5. Add plan checks to journal, track record, risk manager
6. Add plan checks to robot downloads

### Phase C — Frontend Upgrade (Week 3-4)
1. Build upgrade modal component (reusable across pages)
2. Build lock overlay component
3. Add plan checks to dashboard (locked symbols/TFs show lock)
4. Add plan checks to all 17 pages
5. Create `/pricing` page with plan comparison table
6. Update landing.html, services.html with pricing

### Phase D — Admin & Payment (Week 4-5)
1. Build admin "Plans" tab (stats, user management, codes)
2. Integrate ZarinPal payment gateway
3. Build payment verification flow
4. Build subscription renewal/expiry logic
5. Build discount code system

### Phase E — Anti-Abuse & Polish (Week 5-6)
1. Add SMS verification (Phase 2 auth)
2. Add device fingerprinting
3. Add disposable email blocking
4. Add IP rate limiting for registration
5. Add session management (max 2 concurrent)
6. Comprehensive testing
7. Upsell message tuning based on analytics

---

## 8. Revenue Projections (Example)

| Scenario | Free | Pro (199K T) | Premium (499K T) | Enterprise (1.49M T) | Monthly Revenue |
|---|---|---|---|---|---|
| Conservative (100 users) | 70 | 20 | 8 | 2 | ~10.9M T |
| Moderate (500 users) | 350 | 100 | 40 | 10 | ~49.8M T |
| Optimistic (2000 users) | 1400 | 400 | 150 | 50 | ~228M T |

Typical freemium conversion: 5-10% free→paid. With good upsell: 15-20%.

---

## 9. Key Decisions Needed from You

1. **Pricing:** Are the proposed prices (199K / 499K / 1.49M Toman/month) appropriate for your market?
2. **Trial period:** 7-day free Pro trial for new signups? Or no trial?
3. **Annual discount:** Offer 2 months free for yearly payment?
4. **Payment gateway:** ZarinPal, IDPay, or both?
5. **SMS provider:** Kavenegar or Melipayamak for OTP?
6. **Crypto payments:** Support USDT for international users?
7. **Discount codes:** Enable promo codes from launch?
8. **Grandfathering:** Existing users get free Pro for X months?

---

*This document is a recommendation. No code changes have been made. Awaiting your decision on plans and priorities before implementation begins.*
