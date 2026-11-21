# CareGrid AI

> **AI-Powered Intelligent Healthcare Operations & Resource Management Platform**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red?style=flat)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Overview

CareGrid AI is an enterprise-grade district healthcare monitoring platform that enables **District Health Administrators** to monitor all Primary Health Centres (PHCs) and Community Health Centres (CHCs) from one centralized dashboard.

The platform provides real-time monitoring, AI-powered forecasting, explainable recommendations, and comprehensive analytics — all designed to look and function like a production government healthcare system.

> ⚠️ **This is NOT a patient diagnosis system.** It focuses on healthcare **operations and resource management**.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📊 **Dashboard** | Real-time KPIs, facility health table, alert feed |
| 💊 **Stock Monitoring** | Medicine inventory, low-stock alerts, consumption history |
| 👥 **Patient Footfall** | Daily/weekly/monthly analytics with department breakdown |
| 🛏️ **Bed Availability** | Ward-wise occupancy, heatmaps, trend analysis |
| 📋 **Doctor Attendance** | Calendar heatmaps, monthly percentages, absenteeism trends |
| 🤖 **AI Insights** | Stock-out prediction, demand forecasting, redistribution, risk scoring |
| 🗺️ **Facility Maps** | Interactive Folium map with status markers and routes |
| 📄 **Reports** | CSV and PDF export with professional formatting |
| 🌐 **Multilingual** | English and Hindi support (static + dynamic translation) |
| 🔐 **Authentication** | Role-based access control (Admin, Staff, System Admin) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Presentation Layer            │
│        (Streamlit Pages + CSS)          │
├─────────────────────────────────────────┤
│            Services Layer               │
│   (Dashboard, Stock, AI, Reports...)    │
├─────────────────────────────────────────┤
│          Business Logic Layer           │
│  (Forecasting, Risk, Redistribution)   │
├─────────────────────────────────────────┤
│           Database Layer                │
│      (SQLAlchemy ORM + SQLite)          │
├─────────────────────────────────────────┤
│              Storage                    │
│          (SQLite / PostgreSQL)          │
└─────────────────────────────────────────┘
```

**Clean Architecture enforced:** Business logic is NEVER written inside Streamlit pages.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | Python 3.10+ |
| Database | SQLAlchemy ORM + SQLite (PostgreSQL-compatible) |
| AI/ML | Scikit-learn, Linear Regression, NumPy, Pandas |
| Visualization | Plotly |
| Maps | Folium + streamlit-folium |
| Translation | deep-translator |
| PDF Export | fpdf2 |
| Auth | Session-based (bcrypt password hashing) |

---

## 📁 Folder Structure

```
CareGrid-AI/
├── app.py                          # Streamlit entry point
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
├── README.md
│
├── assets/                         # Static assets
│   ├── logo.png
│   ├── banner.png
│   └── styles.css                  # Healthcare theme CSS
│
├── config/                         # Configuration
│   ├── settings.py                 # Centralized settings
│   └── constants.py                # Healthcare constants & enums
│
├── data/                           # Data layer
│   ├── seed.py                     # Database seeder
│   └── synthetic_data_generator.py # Realistic 90-day data
│
├── models/                         # Business logic & ORM
│   ├── database.py                 # Engine, session, Base
│   ├── schema.py                   # 9 ORM models
│   ├── forecasting.py              # Linear Regression forecaster
│   ├── risk_scoring.py             # Weighted risk scorer
│   ├── redistribution.py           # Medicine redistribution engine
│   └── analytics.py                # Trend detection utilities
│
├── services/                       # Service layer
│   ├── auth_service.py             # Authentication
│   ├── dashboard_service.py        # Dashboard aggregations
│   ├── stock_service.py            # Stock management
│   ├── attendance_service.py       # Attendance analytics
│   ├── ai_service.py               # AI orchestration
│   ├── map_service.py              # Map data provider
│   └── report_service.py           # Report generation & export
│
├── pages/                          # Streamlit pages
│   ├── 1_Login.py
│   ├── 2_Dashboard.py
│   ├── 3_Facility.py
│   ├── 4_Stock.py
│   ├── 5_Footfall.py
│   ├── 6_Beds.py
│   ├── 7_Attendance.py
│   ├── 8_AI_Insights.py
│   ├── 9_Maps.py
│   └── 10_Reports.py
│
├── utils/                          # Utilities
│   ├── auth.py                     # Password hashing, session mgmt
│   ├── charts.py                   # Reusable Plotly chart factory
│   ├── db.py                       # Database shortcuts
│   ├── geo.py                      # Haversine, nearest facility
│   ├── helper.py                   # Formatting, HTML generators
│   └── translator.py               # i18n utility
│
├── locales/                        # Translations
│   ├── en.json                     # English (100+ keys)
│   └── hi.json                     # Hindi
│
├── tests/                          # Test suite
└── docs/                           # Documentation
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/caregrid-ai.git
cd caregrid-ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# 5. Seed the database (creates tables + 90 days of synthetic data)
python -m data.seed

# 6. Launch the application
streamlit run app.py
```

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| District Administrator | `admin` | `admin123` |
| Facility Staff | `staff1` | `staff123` |
| System Administrator | `sysadmin` | `sysadmin123` |

---

## 🤖 AI Modules

### Stock-Out Prediction
```
Days Remaining = Current Stock / Average Daily Consumption (30-day avg)
```
- **Critical**: < 3 days remaining
- **Warning**: < 7 days remaining

### Demand Forecasting
- **Algorithm**: Linear Regression (scikit-learn)
- **Features**: day_of_week, day_of_month, month, trend
- **Output**: 14-day forecast with ±1σ confidence intervals

### Redistribution Engine
- Identifies **surplus** (stock > 2× reorder level) and **deficit** (stock < reorder level) facilities
- Matches using **Haversine distance** minimization
- Generates transfer recommendations with quantity, route, and confidence

### Risk Scoring
- **Weighted composite**: Stock (30%) + Attendance (25%) + Beds (25%) + Diagnostics (20%)
- Scale: 0 (healthy) → 100 (critical)
- Every recommendation includes: **Reason**, **Confidence**, **Suggested Action**

---

## 🗄️ Database Schema

9 models with full foreign key relationships:

- **User** — RBAC with 3 roles
- **Facility** — PHC/CHC with geolocation
- **StockItem** — Medicine inventory
- **StockLog** — Stock change audit trail
- **Footfall** — Daily patient counts by department
- **BedStatus** — Ward-wise bed occupancy
- **DoctorAttendance** — Daily attendance records
- **TestAvailability** — Diagnostic test status
- **Alert** — System alerts with severity levels

---

## 🧪 Synthetic Data

The seeder generates realistic 90-day data for **15 facilities** with injected scenarios:

| Facility | Scenario |
|----------|----------|
| PHC Rajpur | Critically low Paracetamol stock |
| CHC Sadar | High doctor absenteeism (40%) |
| PHC Mohanlalganj | Overcrowded beds (>92% occupancy) |
| CHC Malihabad | Multiple unavailable diagnostic tests |

---

## 🌐 Deployment

### Local Development
```bash
streamlit run app.py
```

### Production (Docker)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m data.seed
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
```

### PostgreSQL Migration
Update `.env`:
```
DATABASE_URL=postgresql://user:password@host:5432/caregrid
```
No code changes needed — SQLAlchemy handles dialect switching.

---

## 🔮 Future Scope

- [ ] Real-time data feeds via API integration
- [ ] SMS/Email alert notifications
- [ ] Mobile-responsive PWA
- [ ] Advanced ML models (XGBoost, Prophet)
- [ ] Role-based page access restrictions
- [ ] Audit logging
- [ ] Multi-district support
- [ ] Integration with government health APIs (ABDM/NHA)

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">
  <strong>CareGrid AI</strong> — Built for District Health Administration<br>
  <sub>© 2026 District Health Administration</sub>
</div>
