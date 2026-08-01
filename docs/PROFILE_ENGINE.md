# Universal Profile Engine

## Architecture

```
app/core/profile/
├── __init__.py      ← Public API exports
├── types.py         ← ProfileData, ProfileStatistics, ActivityItem,
│                       PrivacySettings, ShareData, SocialLinks, Visibility
├── models.py        ← ORM bridge: profile_from_user, profile_from_dict
├── engine.py        ← compute_statistics, recent_activity
├── privacy.py       ← get_privacy, is_visible, filter_sections
├── statistics.py    ← stats_to_display (formatted for UI)
└── services.py      ← Public API: get_profile, update_profile,
                        profile_statistics, get_activity, share_link,
                        profile_summary
```

## Profile Lifecycle

1. User signs up → default ProfileData created
2. User edits profile → `update_profile(user, {bio, country, ...})`
3. Public page loads → `profile_summary(user)` returns all sections
4. Privacy controls → hidden sections filtered out
5. Share → `share_link(user, base_url)` returns OG metadata

## Privacy Model

Three visibility levels: public, friends (future), private.
Per-section toggles: achievements, certificates, statistics,
activity, streak. Private profiles return only `{"visibility": "private"}`.

## Usage

```python
from app.core.profile import (
    get_profile, update_profile, profile_summary, share_link)

profile = get_profile(user)
profile = update_profile(user, {"bio": "Security researcher"})
summary = profile_summary(user)  # all sections, privacy-filtered
share = share_link(user, "https://yushacyber.com")
```

## Extension Guide

Add a new profile section by adding a field to `ProfileData`,
computing it in `engine.py`, and including it in `profile_summary`.
Add a privacy toggle in `PrivacySettings.section_visible()`.
