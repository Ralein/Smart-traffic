# Smart Traffic Signal Management System

Real-time adaptive traffic signal control system with a live dashboard.

## Setup & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Features

- 6 traffic signals with live countdown timers
- Adaptive green time based on vehicle density
- Real-time dashboard with auto-refresh
- Vehicle count trend charts
- Interactive map with signal markers
- Manual override controls
- Emergency vehicle priority mode
- Browser geolocation support

## API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/signals` | GET | All signal data |
| `/signal/<id>` | GET | Single signal |
| `/override` | POST | Override vehicle count |
| `/simulate` | GET | Regenerate counts |
| `/history/<id>` | GET | Historical data |
| `/emergency` | POST | Toggle emergency mode |

## Tech Stack

- **Backend:** Python, Flask, SQLite
- **Frontend:** HTML, Tailwind CSS, Chart.js, Leaflet.js, Lucide Icons
