# Real-Time Classroom Engine

## Architecture

```
app/live/realtime/
├── rooms.py          ← Room join/leave/members/count
├── presence.py       ← Online/offline/idle tracking (120s timeout)
├── chat.py           ← In-memory chat (100 msg history), send/delete
├── polls.py          ← Create/vote/results/close polls
├── announcements.py  ← Broadcast/pin/unpin announcements
├── handraise.py      ← Raise/lower/queue/call-on/clear
├── heartbeat.py      ← 30s keepalive, 120s timeout detection
├── events.py         ← Event log (student_joined, poll_opened, etc.)
├── socket.py         ← SocketIO integration (optional, activates if installed)
└── services.py       ← Public API: join/leave, chat, presence, hand raise,
                         polls, announcements, timeline, classroom_state
```

## Two modes

**With Flask-SocketIO:** `socket.py` registers event handlers that call the
same service functions. Events broadcast to rooms in real time.

**Without SocketIO (default):** REST API endpoints poll `/api/classroom/<slug>/state`
every few seconds. Same data, just polled instead of pushed.

## REST API (polling)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/classroom/<slug>/join` | POST | Join room |
| `/api/classroom/<slug>/leave` | POST | Leave room |
| `/api/classroom/<slug>/chat` | GET/POST | Send + history |
| `/api/classroom/<slug>/presence` | GET | Online users |
| `/api/classroom/<slug>/heartbeat` | POST | Keepalive |
| `/api/classroom/<slug>/hand` | GET/POST | Raise/lower/queue |
| `/api/classroom/<slug>/poll` | POST | Create poll |
| `/api/classroom/<slug>/poll/vote` | POST | Vote |
| `/api/classroom/<slug>/announcements` | GET | Get announcements |
| `/api/classroom/<slug>/timeline` | GET | Event log |
| `/api/classroom/<slug>/state` | GET | Full classroom state |

## AI Integration

`classroom_state(slug)` returns everything CyberMentor needs:
members, presence, active polls, pinned announcements, recent chat,
and recent events. Pass to the AI context engine for contextual answers.
