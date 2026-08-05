# Live Classroom Foundation

## Architecture

```
app/live/
├── models.py      ← LiveClass, Enrollment, ClassResource
├── services.py    ← CRUD, enrollment (capacity), attendance
│                     (join/leave/duration), calendar, resources
├── providers.py   ← BaseProvider (abstract), JitsiProvider (default),
│                     ZoomProvider, GoogleMeetProvider, TeamsProvider
├── routes.py      ← Student + Instructor + API routes
└── __init__.py
```

## Database Tables

| Table | Key Fields |
|---|---|
| `live_classes` | title, slug, instructor_id, start/end_time, meeting_provider, meeting_url, capacity, status |
| `live_enrollments` | user_id, class_id, attendance_status, joined_at, left_at, duration |
| `live_class_resources` | class_id, title, resource_type, url, filename |

## Class Lifecycle

Draft → Scheduled → Live → Ended (or Cancelled → Archived)

## Provider System

```python
from app.live.providers import register_provider, BaseProvider

class CustomProvider(BaseProvider):
    name = "custom"
    def generate_url(self, room):
        return f"https://custom.example/{room}"

register_provider("custom", CustomProvider())
```

## Attendance

Automatic tracking: join time, leave time, duration. Present (≤10 min after start) vs Late (>10 min). Manual override via admin.

## Routes

| Route | Purpose |
|---|---|
| `/classes` | Browse upcoming |
| `/classes/<slug>` | Class detail + register |
| `/classes/calendar` | Calendar view |
| `/classes/my` | My enrollments |
| `/instructor/classes` | Instructor dashboard |
| `/instructor/classes/new` | Create class |
| `/api/classes` | JSON list |
| `/api/classes/register` | Enroll via API |
| `/api/classes/attendance` | Join/leave via API |

## Security

Meeting URLs only visible when class is live + student is enrolled. Only instructors can start/end their own classes. Admins have full access.
