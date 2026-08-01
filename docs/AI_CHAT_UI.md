# CyberMentor Chat Interface

## Architecture

```
app/templates/components/ai_chat.html  ← Jinja include (data bridge)
app/static/css/mentor.css              ← All chat styling
app/static/js/mentor.js                ← Chat logic, markdown, cyber formatting
```

The component is a self-contained include: `{% include "components/ai_chat.html" %}` placed before `</body>` on any authenticated page. The JS reads `data-mentor-*` attributes to get the student context, injects the floating button + slide-in panel, and handles all interaction.

## Component Structure

1. **Floating button** (`.mentor-fab`) — fixed bottom-right, pulse animation, hidden on auth pages
2. **Overlay** (`.mentor-overlay`) — click-to-close backdrop
3. **Panel** (`.mentor-panel`) — 420px slide-in, full-screen on mobile
4. **Header** — icon, title, online/offline status, model name, close button
5. **Context bar** — current lab, level, XP
6. **Messages** — user bubbles (indigo) + AI bubbles (surface) with markdown
7. **Suggested prompts** — 6 clickable chips when conversation is empty
8. **Input** — auto-resize textarea, send button, clear button

## Features

- **Markdown** — bold, italic, links, lists, code blocks, inline code
- **Code blocks** — language label, copy button, JetBrains Mono
- **Cyber tokens** — auto-highlighted IPs, ports, CVEs, hashes, file paths
- **Session persistence** — conversation survives page refresh (sessionStorage)
- **Health check** — green/red status dot, model name from `/api/ai/health`
- **Keyboard** — Enter sends, Shift+Enter newline, Escape closes
- **Responsive** — full-screen on mobile (<480px)
- **Theme** — dark default, light theme support via `[data-theme="light"]`
- **Reduced motion** — respects `prefers-reduced-motion`
- **XSS safe** — all user input escaped via DOM textContent

## Streaming (future)

Replace `fetch` with `EventSource` or `ReadableStream` and append tokens as they arrive. The message container already renders incrementally.

## Customization

- Colors via CSS variables (`--color-accent`, `--color-bg`, etc.)
- Suggested prompts array in `mentor.js`
- System prompt in `app/core/ai/prompts.py`
