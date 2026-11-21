"""
CareGrid AI — Constants
========================
Healthcare-specific constants, enumerations, and reference data.
These values are used across the platform for consistency.
"""

from enum import Enum


# ============================================================
# COLOR PALETTE
# ============================================================

class Colors:
    """Healthcare theme color palette."""
    PRIMARY = "#2563EB"        # Blue — primary actions, headers
    PRIMARY_DARK = "#1E40AF"   # Dark blue — sidebar, deep accents
    PRIMARY_LIGHT = "#DBEAFE"  # Light blue — card backgrounds
    SUCCESS = "#22C55E"        # Green — healthy, available
    WARNING = "#F59E0B"        # Amber — caution, low stock
    DANGER = "#EF4444"         # Red — critical, alerts
    BACKGROUND = "#F8FAFC"     # Off-white — page background
    SURFACE = "#FFFFFF"        # White — card surfaces
    TEXT_PRIMARY = "#1E293B"   # Dark slate — body text
    TEXT_SECONDARY = "#64748B" # Slate — secondary text
    BORDER = "#E2E8F0"        # Light gray — borders


# ============================================================
# FACILITY TYPES
# ============================================================

class FacilityType(str, Enum):
    """Healthcare facility categories."""
    PHC = "PHC"  # Primary Health Centre
    CHC = "CHC"  # Community Health Centre


# ============================================================
# USER ROLES
# ============================================================

class UserRole(str, Enum):
    """Role-based access control roles."""
    DISTRICT_ADMIN = "District Administrator"
    FACILITY_STAFF = "Facility Staff"
    SYSTEM_ADMIN = "System Administrator"


# ============================================================
# ALERT TYPES & SEVERITY
# ============================================================

class AlertType(str, Enum):
    """Categories of system alerts."""
    LOW_STOCK = "Low Stock"
    STOCKOUT = "Stock Out"
    HIGH_ABSENTEEISM = "High Absenteeism"
    BED_OVERCROWDING = "Bed Overcrowding"
    EQUIPMENT_FAILURE = "Equipment Failure"
    DIAGNOSTIC_UNAVAILABLE = "Diagnostic Unavailable"
    HIGH_FOOTFALL = "High Footfall"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# ============================================================
# ATTENDANCE STATUS
# ============================================================

class AttendanceStatus(str, Enum):
    """Doctor attendance statuses."""
    PRESENT = "present"
    ABSENT = "absent"
    LEAVE = "leave"
    HALF_DAY = "half_day"


# ============================================================
# STOCK CHANGE TYPES
# ============================================================

class StockChangeType(str, Enum):
    """Types of stock inventory changes."""
    RECEIVED = "received"
    CONSUMED = "consumed"
    TRANSFERRED_IN = "transferred_in"
    TRANSFERRED_OUT = "transferred_out"
    EXPIRED = "expired"
    ADJUSTMENT = "adjustment"


# ============================================================
# WARD TYPES
# ============================================================

class WardType(str, Enum):
    """Hospital ward categories."""
    GENERAL = "General"
    ICU = "ICU"
    MATERNITY = "Maternity"
    PEDIATRIC = "Pediatric"
    EMERGENCY = "Emergency"


# ============================================================
# MEDICINE LIST
# ============================================================

MEDICINES: list[dict] = [
    {"name": "Paracetamol 500mg", "category": "Analgesic", "unit": "tablets", "reorder_level": 500},
    {"name": "Amoxicillin 250mg", "category": "Antibiotic", "unit": "capsules", "reorder_level": 300},
    {"name": "Metformin 500mg", "category": "Antidiabetic", "unit": "tablets", "reorder_level": 400},
    {"name": "Amlodipine 5mg", "category": "Antihypertensive", "unit": "tablets", "reorder_level": 350},
    {"name": "Omeprazole 20mg", "category": "Antacid", "unit": "capsules", "reorder_level": 300},
    {"name": "Ciprofloxacin 500mg", "category": "Antibiotic", "unit": "tablets", "reorder_level": 200},
    {"name": "Ibuprofen 400mg", "category": "Anti-inflammatory", "unit": "tablets", "reorder_level": 400},
    {"name": "Cetirizine 10mg", "category": "Antihistamine", "unit": "tablets", "reorder_level": 250},
    {"name": "Azithromycin 500mg", "category": "Antibiotic", "unit": "tablets", "reorder_level": 150},
    {"name": "ORS Packets", "category": "Rehydration", "unit": "packets", "reorder_level": 500},
    {"name": "Iron + Folic Acid", "category": "Supplement", "unit": "tablets", "reorder_level": 600},
    {"name": "Diclofenac 50mg", "category": "Anti-inflammatory", "unit": "tablets", "reorder_level": 300},
    {"name": "Ranitidine 150mg", "category": "Antacid", "unit": "tablets", "reorder_level": 250},
    {"name": "Salbutamol Inhaler", "category": "Bronchodilator", "unit": "inhalers", "reorder_level": 50},
    {"name": "Insulin (Regular)", "category": "Antidiabetic", "unit": "vials", "reorder_level": 30},
]


# ============================================================
# DEPARTMENTS
# ============================================================

DEPARTMENTS: list[str] = [
    "OPD",
    "IPD",
    "Emergency",
    "Maternity",
    "Pediatric",
    "Dental",
    "Ophthalmology",
    "Pathology",
]


# ============================================================
# DIAGNOSTIC TESTS
# ============================================================

DIAGNOSTIC_TESTS: list[dict] = [
    {"name": "Complete Blood Count (CBC)", "category": "Hematology"},
    {"name": "Blood Sugar (Fasting)", "category": "Biochemistry"},
    {"name": "Blood Sugar (PP)", "category": "Biochemistry"},
    {"name": "HbA1c", "category": "Biochemistry"},
    {"name": "Lipid Profile", "category": "Biochemistry"},
    {"name": "Liver Function Test (LFT)", "category": "Biochemistry"},
    {"name": "Kidney Function Test (KFT)", "category": "Biochemistry"},
    {"name": "Thyroid Profile (TSH)", "category": "Biochemistry"},
    {"name": "Urine Routine & Microscopy", "category": "Microbiology"},
    {"name": "Malaria Antigen Test", "category": "Microbiology"},
    {"name": "Dengue NS1 Antigen", "category": "Microbiology"},
    {"name": "HIV Rapid Test", "category": "Serology"},
    {"name": "Hepatitis B Surface Antigen", "category": "Serology"},
    {"name": "X-Ray (Chest)", "category": "Radiology"},
    {"name": "ECG", "category": "Cardiology"},
    {"name": "Ultrasound (Abdomen)", "category": "Radiology"},
]


# ============================================================
# FACILITY SEED DATA
# ============================================================

FACILITY_NAMES: list[dict] = [
    {"name": "PHC Rajpur", "type": FacilityType.PHC, "lat": 26.8800, "lon": 80.9100},
    {"name": "CHC Sadar", "type": FacilityType.CHC, "lat": 26.8500, "lon": 80.9500},
    {"name": "PHC Mohanlalganj", "type": FacilityType.PHC, "lat": 26.7500, "lon": 80.8800},
    {"name": "CHC Malihabad", "type": FacilityType.CHC, "lat": 26.9200, "lon": 80.7200},
    {"name": "PHC Bakshi Ka Talab", "type": FacilityType.PHC, "lat": 26.9100, "lon": 80.9400},
    {"name": "PHC Chinhat", "type": FacilityType.PHC, "lat": 26.8900, "lon": 81.0300},
    {"name": "CHC Kakori", "type": FacilityType.CHC, "lat": 26.8700, "lon": 80.7900},
    {"name": "PHC Gosainganj", "type": FacilityType.PHC, "lat": 26.7800, "lon": 80.8100},
    {"name": "PHC Itaunja", "type": FacilityType.PHC, "lat": 27.0200, "lon": 80.9000},
    {"name": "CHC Nagram", "type": FacilityType.CHC, "lat": 26.7200, "lon": 80.8500},
    {"name": "PHC Mal", "type": FacilityType.PHC, "lat": 26.8400, "lon": 81.0800},
    {"name": "PHC Sarojininagar", "type": FacilityType.PHC, "lat": 26.7900, "lon": 80.9200},
    {"name": "CHC Mohanlalganj Block", "type": FacilityType.CHC, "lat": 26.7600, "lon": 80.8300},
    {"name": "PHC Amaniganj", "type": FacilityType.PHC, "lat": 26.8300, "lon": 80.9700},
    {"name": "PHC Nilmatha", "type": FacilityType.PHC, "lat": 26.9000, "lon": 80.8600},
]


# ============================================================
# DOCTOR NAMES (for seeding)
# ============================================================

DOCTOR_NAMES: list[dict] = [
    {"name": "Dr. Priya Sharma", "specialization": "General Medicine"},
    {"name": "Dr. Rajesh Kumar", "specialization": "General Medicine"},
    {"name": "Dr. Anita Verma", "specialization": "Pediatrics"},
    {"name": "Dr. Suresh Patel", "specialization": "Orthopedics"},
    {"name": "Dr. Meena Singh", "specialization": "Gynecology"},
    {"name": "Dr. Arun Gupta", "specialization": "General Medicine"},
    {"name": "Dr. Kavita Mishra", "specialization": "Ophthalmology"},
    {"name": "Dr. Vikram Yadav", "specialization": "Dental"},
    {"name": "Dr. Sunita Tiwari", "specialization": "Pathology"},
    {"name": "Dr. Ramesh Chauhan", "specialization": "General Surgery"},
]


# ============================================================
# UI CONSTANTS
# ============================================================

SIDEBAR_WIDTH: int = 300
CHART_HEIGHT: int = 400
KPI_CARD_HEIGHT: int = 120
TABLE_PAGE_SIZE: int = 15

# Icons for navigation and status
ICONS: dict = {
    "dashboard": "📊",
    "facility": "🏥",
    "stock": "💊",
    "footfall": "👥",
    "beds": "🛏️",
    "attendance": "📋",
    "diagnostics": "🔬",
    "ai_insights": "🤖",
    "maps": "🗺️",
    "reports": "📄",
    "settings": "⚙️",
    "login": "🔐",
    "logout": "🚪",
    "alert": "🚨",
    "success": "✅",
    "warning": "⚠️",
    "danger": "🔴",
    "info": "ℹ️",
}
