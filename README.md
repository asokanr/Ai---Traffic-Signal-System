# 🚦 Smart AI-Based Traffic Signal Control System

A full-stack intelligent traffic management system built with **Django** and **YOLOv8** that uses real-time AI-powered vehicle detection to dynamically optimize traffic signal timings. Features a modern dark-themed dashboard with live camera analysis, emergency vehicle management, heatmap visualization, and multi-junction control.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-green?logo=django&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple?logo=pytorch&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.7-red?logo=opencv&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Endpoints](#-api-endpoints)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### 🤖 AI-Powered Traffic Analysis
- **YOLOv8 Vehicle Detection** — Real-time object detection for cars, trucks, buses, motorcycles, and bicycles
- **Video Upload Analysis** — Upload traffic footage for batch processing and detailed vehicle count reports
- **Live Camera Feed** — Browser-based live camera streaming with periodic AI-powered frame analysis
- **Smart Signal Timing** — Auto-calculated green/yellow/red timings based on detected traffic density per lane

### 🖥️ Interactive Dashboard
- **Real-Time Monitoring** — Live traffic signal states with animated indicators for all 4 directions (N/S/E/W)
- **Traffic Simulation** — Built-in traffic simulator with configurable vehicle generation rates
- **Dark Glassmorphism UI** — Premium modern interface with neon accents, gradients, and micro-animations

### 🚨 Emergency Management
- **SOS Alert System** — Priority emergency vehicle detection and signal override
- **Emergency Logging** — Full audit trail of emergency events with timestamps

### 📊 Analytics & Visualization
- **Traffic Heatmap** — Geographic density visualization across junctions
- **Statistical Dashboard** — Historical charts, peak-hour analysis, and vehicle breakdown by type
- **PDF Reports** — Downloadable traffic analysis reports via ReportLab

### 🔧 Admin & Control
- **Multi-Junction Management** — Monitor and control multiple intersections simultaneously
- **Manual Signal Override** — Admin-level manual control for emergency situations
- **Remote Timing Configuration** — Adjust signal durations remotely per direction
- **User Authentication** — Secure login/registration with role-based access

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Browser)                     │
│  Dashboard │ AI Analysis │ Heatmap │ Emergency │ Admin   │
│  HTML/CSS/JS │ Chart.js │ getUserMedia API               │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API / AJAX
┌──────────────────────▼──────────────────────────────────┐
│                  Django Backend                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Views   │  │  Serializers │  │  REST Framework   │  │
│  └────┬─────┘  └──────────────┘  └───────────────────┘  │
│       │                                                  │
│  ┌────▼──────────────────────────────────────────────┐  │
│  │              Business Logic Layer                  │  │
│  │  ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │  │
│  │  │ YOLOv8       │ │ Traffic    │ │ Emergency   │ │  │
│  │  │ Detector     │ │ Engine     │ │ Manager     │ │  │
│  │  └──────────────┘ └────────────┘ └─────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
│       │                                                  │
│  ┌────▼─────────────────────────────────────────────┐   │
│  │           SQLite Database (Models)                │   │
│  │  Junction │ TrafficSignal │ TrafficLog │ VideoAn. │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer        | Technology                                        |
| ------------ | ------------------------------------------------- |
| **Backend**  | Django 4.2, Django REST Framework, Gunicorn        |
| **AI/ML**    | YOLOv8 (Ultralytics), OpenCV, NumPy               |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Chart.js          |
| **Database** | SQLite (default), easily switchable to PostgreSQL  |
| **Auth**     | Django Allauth, PyJWT                              |
| **Reports**  | ReportLab (PDF generation)                         |
| **Camera**   | Browser getUserMedia API + backend frame analysis  |

---

## 🖼️ Screenshots

> Add your screenshots here after running the project:
> - Dashboard with live signal monitoring
> - AI Analysis page (Upload & Live modes)
> - Traffic heatmap visualization
> - Emergency management panel

---

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git
- Webcam (optional — for live camera features)

### Step-by-Step Setup

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/smart-traffic-signal-control.git
cd smart-traffic-signal-control
```

**2. Create a virtual environment**
```bash
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Apply database migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

**5. Create a superuser (admin access)**
```bash
python manage.py createsuperuser
```

**6. Run the development server**
```bash
python manage.py runserver
```

**7. Open in browser**
```
http://127.0.0.1:8000/api/dashboard/
```

> **Note:** The YOLOv8 model (`yolov8n.pt`) will auto-download on first AI analysis use if not already present.

---

## 📖 Usage

### Dashboard
Navigate to `http://127.0.0.1:8000/api/dashboard/` after login. The sidebar provides access to all modules:

| Icon | Module | Description |
|------|--------|-------------|
| 📊 | Dashboard | Real-time signal monitoring & control |
| 🚨 | Emergency | SOS alerts & emergency overrides |
| 🔀 | Multi-Junction | Control multiple intersections |
| 🗺️ | Heatmap | Traffic density visualization |
| 📈 | Statistics | Historical analytics & charts |
| 🌍 | Environment | Environmental sensor monitoring |
| 📜 | History | Signal change audit log |
| ⚙️ | Admin | System configuration & user management |
| 🧠 | AI Analysis | YOLO-based traffic detection |

### AI Analysis — Upload Mode
1. Go to **AI Analysis** → **Upload** tab
2. Drag & drop or click to upload a traffic video (MP4, AVI, MOV, WebM)
3. Wait for YOLO processing (progress bar shows status)
4. View results: vehicle counts, density classification, lane-wise signal timings

### AI Analysis — Live Mode
1. Go to **AI Analysis** → **Live** tab
2. Click **Check Camera** to verify webcam connectivity
3. Allow browser camera permission when prompted
4. Click **Start Stream** — your camera feed appears in real-time
5. AI analyses frames every 3 seconds and updates traffic statistics live

---

## 🔌 API Endpoints

### REST API (ViewSets)
| Endpoint | Description |
|----------|-------------|
| `GET /api/signals/` | List all traffic signals |
| `GET /api/junctions/` | List all junctions |
| `GET /api/analytics/` | Traffic analytics data |
| `GET /api/emergency/` | Emergency events |
| `GET /api/heatmap/` | Heatmap density data |
| `GET /api/alerts/` | System alerts |
| `GET /api/pollution/` | Environmental data |

### AI Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai-analysis/upload/` | POST | Upload video for YOLO analysis |
| `/api/ai-analysis/camera-check/` | GET | Check webcam availability |
| `/api/ai-analysis/analyze-frame/` | POST | Analyze a single JPEG frame |
| `/api/ai-analysis/live-feed/` | GET | MJPEG stream (server-side) |
| `/api/ai-analysis/live-snapshot/` | GET | Current traffic snapshot |
| `/api/ai-analysis/history/` | GET | Past analysis records |

### Dashboard
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/` | GET | Main dashboard page |
| `/api/dashboard/data/` | GET | Dashboard JSON data |
| `/api/dashboard/analytics/` | GET | Analytics page |

---

## 📁 Project Structure

```
traffic_signal_project/
├── accounts/                   # User authentication (login/signup)
│   └── templates/accounts/     # Auth templates
├── signal_app/                 # Core application
│   ├── logic/                  # Business logic modules
│   │   ├── yolo_detector.py    # YOLOv8 vehicle detection engine
│   │   ├── traffic_engine.py   # Signal timing algorithms
│   │   └── emergency_manager.py# Emergency vehicle handling
│   ├── management/commands/    # Django management commands
│   │   └── simulate_traffic.py # Traffic simulation command
│   ├── migrations/             # Database migrations
│   ├── models.py               # Database models (Junction, Signal, VideoAnalysis)
│   ├── views.py                # API views & page controllers
│   ├── serializers.py          # DRF serializers
│   ├── urls.py                 # URL routing
│   ├── admin.py                # Django admin configuration
│   └── reports.py              # PDF report generation
├── static/
│   ├── css/                    # Stylesheets
│   │   ├── dashboard_style.css # Main dashboard styles
│   │   ├── ai_analysis.css     # AI analysis module styles
│   │   └── ...                 # Other CSS files
│   └── js/                     # JavaScript modules
│       ├── dashboard_logic.js  # Dashboard controller
│       ├── ai_analysis.js      # AI analysis (Upload + Live)
│       ├── simulator.js        # Traffic simulation
│       ├── emergency.js        # Emergency management
│       ├── heatmap.js          # Heatmap visualization
│       └── ...                 # Other JS modules
├── templates/
│   ├── dashboard.html          # Main SPA dashboard template
│   └── analytics.html          # Analytics page
├── traffic_signal_project/     # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── requirements.txt            # Python dependencies
├── manage.py                   # Django CLI
└── yolov8n.pt                  # YOLOv8 nano model weights
```

---

## 🗃️ Database Models

| Model | Description |
|-------|-------------|
| `Junction` | Traffic intersection with location data |
| `TrafficSignal` | Individual signal (direction, state, timings) |
| `TrafficLog` | Historical signal state change records |
| `EmergencyLog` | Emergency vehicle event tracking |
| `VehicleTypeCount` | Vehicle classification counts per signal |
| `VideoAnalysis` | AI analysis results (upload/live mode) |
| `AdminActionLog` | Admin activity audit trail |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Your Name**

- GitHub: [@your-username](https://github.com/your-username)

---

<p align="center">
  Built with ❤️ using Django & YOLOv8
</p>
