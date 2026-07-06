# YushaCyber — Landing Page

A cybersecurity learning platform landing page built with Flask, HTML, CSS, and vanilla JavaScript.

## Run locally

```bash
pip install -r requirements.txt
cd app
python app.py
```

Then open http://127.0.0.1:5000

## Structure

```
app/
├── app.py                  # Flask entry point (single index route)
├── templates/
│   └── index.html          # Landing page (semantic HTML)
└── static/
    ├── css/style.css       # Dark theme, responsive, hover animations
    └── js/main.js          # Nav toggle, terminal typing, counters, reveals
```

## Features

- Fixed navigation with mobile hamburger menu
- Hero with animated terminal window and typed command sequence
- Count-up statistics triggered on scroll
- Roadmap, Daily Challenge, CTF Arena, and Featured Courses sections
- Smooth scrolling, scroll-reveal, and subtle hover animations
- Respects prefers-reduced-motion; visible keyboard focus states
