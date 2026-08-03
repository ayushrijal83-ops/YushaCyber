# Live Classroom Experience

## Layout

Desktop: 3-column grid (Video + Notes + Participants) with bottom bar (Chat + AI + Resources).
Mobile: Tab-based (Video | Chat | Notes | AI | Resources).

## Components

| Component | Features |
|---|---|
| Waiting Room | Countdown timer, class info, register button, pre-class resources |
| Live Header | 🔴 LIVE badge, title, instructor, elapsed timer, participant count, leave button |
| Video | Jitsi embed (iframe), fullscreen button, PiP-ready |
| Notes | Auto-save (1.5s debounce), localStorage, export to .md/.txt |
| Chat | Pinned instructor announcements, emoji-ready, auto-scroll |
| AI Mentor | CyberMentor sidebar, contextual to current class |
| Participants | Avatar, name, status (speaking/muted/offline) |
| Hand Raise | Toggle button, visual indicator |
| Resources | File list, open in new tab |

## Routes

| Route | Purpose |
|---|---|
| `/classroom/<slug>` | Student classroom view |
| `/instructor/classroom/<slug>` | Instructor classroom view |
| `/classes/<slug>/leave` | Leave + record attendance |

## Responsive

- Desktop (>900px): Full grid layout
- Mobile (<900px): Tab navigation
- Landscape supported
- prefers-reduced-motion respected

## Accessibility

- `aria-label` on all inputs and interactive elements
- `role` attributes on panels
- Keyboard navigable tabs
- Focus states on all interactive elements
- High contrast via CSS variables
