# design.md — Desktop App UI/UX Design (Spatial UI)

> Scope: Week 1–2 desktop app. "Spatial UI" = layered depth (background → surface → floating cards),
> generous spacing, soft glow/blur, consistent 8px grid. Framework: **React + Vite** (web dashboard). Tokens below become CSS variables.

## 1. Design Principles
1. **Calm, not noisy** — app focus ke liye hai, khud distraction nahi banna chahiye.
2. **Depth through layers** — 3 layers: Base (L0), Surface (L1), Floating (L2).
3. **One primary action per screen.**
4. **Data first** — numbers bade, labels chhote.
5. **Privacy visible** — tracking status hamesha dikhe (green dot).

## 2. Design Tokens

### Colors (Dark theme default)
| Token | Hex | Use |
|---|---|---|
| `--bg-base` | `#0B0D12` | Window background (L0) |
| `--bg-surface` | `#141821` | Sidebar, panels (L1) |
| `--bg-card` | `#1B2130` | Floating cards (L2) |
| `--border` | `#262D3F` | 1px card borders |
| `--text-primary` | `#EAEEF7` | Headings, numbers |
| `--text-secondary` | `#8C97B2` | Labels |
| `--accent` | `#6C7BFF` | Primary buttons, active nav |
| `--accent-glow` | `rgba(108,123,255,0.25)` | Glow behind active elements |
| `--focus` | `#34D399` | Focus / tracking active |
| `--warn` | `#FBBF24` | Idle / warnings |
| `--danger` | `#F87171` | Errors, distraction |

Light theme: invert base to `#F5F7FB`, surface `#FFFFFF`, card `#FFFFFF` + shadow.

### Typography
- Font: **Inter** (fallback: Segoe UI)
- Display number: 40px / 700
- H1: 24px / 600, H2: 18px / 600
- Body: 14px / 400, Caption: 12px / 400

### Spacing & Shape
- Grid: 8px. Scale: 4, 8, 16, 24, 32, 48
- Card radius: 16px, Button radius: 10px, Input radius: 10px
- Card shadow: `0 8px 24px rgba(0,0,0,0.35)`
- Window min size: 1000×640

### Depth Layers
```
L2  Floating cards  (shadow + 1px border + subtle top highlight)
L1  Sidebar / panels (flat, slightly lighter)
L0  Base background  (gradient: #0B0D12 → #10131C)
```

## 3. App Window Layout (Main)

```
┌──────────────────────────────────────────────────────────────────┐
│  ● Tracking ON            Attention Platform         ☾  👤 Sajal │ ← Top bar (56px)
├───────────┬──────────────────────────────────────────────────────┤
│           │  Good evening, Sajal                                 │
│  ◉ Today  │                                                      │
│  ◷ Focus  │  ┌────────────┐ ┌────────────┐ ┌────────────┐        │
│  ▤ Apps   │  │ Screen Time│ │ Focus Time │ │ Task Switch│        │
│  ⚑ Goals  │  │  5h 42m    │ │  2h 10m    │ │    148     │        │
│  ⚙ Settings│ │  ▲ 12%     │ │  Goal 3h   │ │  ▼ 8%      │        │
│           │  └────────────┘ └────────────┘ └────────────┘        │
│           │                                                      │
│           │  ┌──────────────────────────┐ ┌──────────────────┐   │
│           │  │ Today's Timeline         │ │ Top Apps         │   │
│           │  │ ▇▇░░▇▇▇░░▇▇▇▇░░▇         │ │ VS Code   2h 5m  │   │
│           │  │ 9am     12pm      6pm    │ │ Chrome    1h 40m │   │
│           │  └──────────────────────────┘ │ WhatsApp  32m    │   │
│           │                               └──────────────────┘   │
│  Sidebar  │                          [ ▶ Start Focus Session ]   │
│  (220px)  │                                                      │
└───────────┴──────────────────────────────────────────────────────┘
```

## 4. Screens

### 4.1 Splash / Login
```
┌─────────────────────────────────┐
│      (soft glow orb behind)     │
│         ◎  Attention            │
│     Take back your focus        │
│                                 │
│   ┌───────────────────────┐     │
│   │ Email                 │     │
│   └───────────────────────┘     │
│   ┌───────────────────────┐     │
│   │ Password          👁  │     │
│   └───────────────────────┘     │
│   [        Login          ]     │
│   New here? Create account      │
└─────────────────────────────────┘
```
- Window: 420×560, centered, frameless card with L2 depth.
- Errors inline below field in `--danger`.

### 4.2 Register
Fields: Name, Email, Password, Confirm Password. Password strength bar (4 segments).

### 4.3 Onboarding (Goal Configuration) — 3 steps
1. **Daily focus goal** — slider 1–8 hrs (default 3h).
2. **Idle threshold** — 1 / 2 / 5 min.
3. **Privacy** — toggle "Store window titles" (default OFF), consent text, [Start tracking].

### 4.4 Today (Dashboard)
- 3 stat cards (Screen Time, Focus Time, Task Switches), each with trend arrow.
- Timeline bar chart (hourly, color-coded: focus=green, active=accent, idle=grey).
- Top Apps list (icon, name, duration, mini progress bar).
- Floating CTA bottom-right: **Start Focus Session**.

### 4.5 Focus Session
```
        ┌───────────────────────┐
        │        ◯ 24:31        │   ← circular progress ring (accent→focus gradient)
        │     Deep work · 25m   │
        │   Switches: 3         │
        │  [ Pause ]  [ Stop ]  │
        └───────────────────────┘
```
- Choose duration chips: 15 / 25 / 45 / 60 / Custom.
- Optional label ("Studying DSA").
- Mini mode: 220×90 always-on-top floating widget showing only timer.

### 4.6 Apps (Usage)
Table: App | Total time | Sessions | Switches-in. Sort + date range filter (Today / 7d / 30d).

### 4.7 Goals
List of goal cards with progress ring: "3h focus/day", "<150 switches/day". [+ New Goal] modal.

### 4.8 Settings
- Account (name, email, change password)
- Tracking (pause/resume, idle threshold, store titles toggle, ignore-list apps)
- General (theme, start with Windows, minimize to tray)
- Data (Export my data, Delete my data)
- About / Logs

## 5. System Tray
Icon states: 🟢 tracking, 🟡 idle, ⚪ paused, 🔴 error/offline.
Menu: Open Dashboard · Start/Stop Focus · Pause Tracking (15m/1h/until I resume) · Quit.

## 6. Components
| Component | Spec |
|---|---|
| Button primary | bg accent, text white, h40, hover glow, press scale 0.98 |
| Button secondary | transparent, 1px border, hover bg-card |
| Stat card | 16px padding, label 12px, value 40px, trend chip |
| Input | h44, border, focus ring 2px accent |
| Toggle | 40×22, accent when ON |
| Toast | bottom-center, 3s, L2 depth |
| Empty state | icon + one line + one action |

## 7. Motion
- Page transition: 180ms fade + 8px slide.
- Card hover: translateY(-2px), shadow grows, 150ms ease-out.
- Numbers count up on load (400ms).
- Respect "reduce motion" setting.

## 8. States to design
Loading (skeleton shimmer), Empty (no data yet), Offline (yellow banner "Saving locally, will sync"), Error (red banner + Retry).

## 9. Accessibility
Contrast ≥ 4.5:1, full keyboard navigation (Tab order), visible focus ring, min click target 32px.
