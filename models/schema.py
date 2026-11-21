"""
CareGrid AI — ORM Schema
==========================
SQLAlchemy 2.0+ ORM models for the healthcare operations platform.
All models are PostgreSQL-compatible while using SQLite in development.

Models:
    - User              : System users with role-based access
    - Facility          : PHC/CHC healthcare facilities
    - StockItem         : Medicine inventory items
    - StockLog          : Stock change audit trail
    - Footfall          : Daily patient footfall records
    - BedStatus         : Ward-wise bed occupancy
    - DoctorAttendance  : Doctor attendance records
    - TestAvailability  : Diagnostic test availability
    - Alert             : System alerts and notifications
"""


from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.constants import (
    AlertSeverity,
    AlertType,
    AttendanceStatus,
    FacilityType,
    StockChangeType,
    UserRole,
    WardType,
)
from models.database import Base


# ============================================================
# USER MODEL
# ============================================================

class User(Base):
    """
    System user with role-based access control.
    Roles: District Administrator, Facility Staff, System Administrator.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    facility_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    facility: Mapped[Optional["Facility"]] = relationship(
        "Facility", back_populates="staff"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# ============================================================
# FACILITY MODEL
# ============================================================

class Facility(Base):
    """
    Healthcare facility (PHC or CHC) in the district.
    Contains location data for map visualization.
    """
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    facility_type: Mapped[FacilityType] = mapped_column(
        SAEnum(FacilityType), nullable=False
    )
    district: Mapped[str] = mapped_column(String(100), default="Lucknow", nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    total_capacity: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    staff: Mapped[List["User"]] = relationship(
        "User", back_populates="facility", cascade="all, delete-orphan"
    )
    stock_items: Mapped[List["StockItem"]] = relationship(
        "StockItem", back_populates="facility", cascade="all, delete-orphan"
    )
    stock_logs: Mapped[List["StockLog"]] = relationship(
        "StockLog", back_populates="facility", cascade="all, delete-orphan"
    )
    footfall_records: Mapped[List["Footfall"]] = relationship(
        "Footfall", back_populates="facility", cascade="all, delete-orphan"
    )
    bed_statuses: Mapped[List["BedStatus"]] = relationship(
        "BedStatus", back_populates="facility", cascade="all, delete-orphan"
    )
    doctor_attendance: Mapped[List["DoctorAttendance"]] = relationship(
        "DoctorAttendance", back_populates="facility", cascade="all, delete-orphan"
    )
    test_availability: Mapped[List["TestAvailability"]] = relationship(
        "TestAvailability", back_populates="facility", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="facility", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Facility(id={self.id}, name='{self.name}', type='{self.facility_type}')>"


# ============================================================
# STOCK ITEM MODEL
# ============================================================

class StockItem(Base):
    """
    Medicine inventory item at a facility.
    Tracks current stock level and reorder threshold.
    """
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="tablets", nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    last_restocked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    facility: Mapped["Facility"] = relationship("Facility", back_populates="stock_items")
    logs: Mapped[List["StockLog"]] = relationship(
        "StockLog", back_populates="stock_item", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<StockItem(id={self.id}, medicine='{self.medicine_name}', "
            f"stock={self.current_stock})>"
        )


# ============================================================
# STOCK LOG MODEL
# ============================================================

class StockLog(Base):
    """
    Audit trail for stock changes (received, consumed, transferred, expired).
    """
    __tablename__ = "stock_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stock_items.id"), nullable=False, index=True
    )
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[StockChangeType] = mapped_column(
        SAEnum(StockChangeType), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    stock_item: Mapped["StockItem"] = relationship("StockItem", back_populates="logs")
    facility: Mapped["Facility"] = relationship("Facility", back_populates="stock_logs")

    def __repr__(self) -> str:
        return (
            f"<StockLog(id={self.id}, item_id={self.stock_item_id}, "
            f"change={self.quantity_change}, type='{self.change_type}')>"
        )


# ============================================================
# FOOTFALL MODEL
# ============================================================

class Footfall(Base):
    """
    Daily patient footfall by department at a facility.
    Tracks OPD, IPD, emergency, and department-wise counts.
    """
    __tablename__ = "footfall"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    patient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opd_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ipd_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emergency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    facility: Mapped["Facility"] = relationship(
        "Facility", back_populates="footfall_records"
    )

    def __repr__(self) -> str:
        return (
            f"<Footfall(id={self.id}, facility_id={self.facility_id}, "
            f"date={self.date}, patients={self.patient_count})>"
        )


# ============================================================
# BED STATUS MODEL
# ============================================================

class BedStatus(Base):
    """
    Ward-wise bed occupancy snapshot for a facility.
    Wards: General, ICU, Maternity, Pediatric, Emergency.
    """
    __tablename__ = "bed_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    ward_type: Mapped[WardType] = mapped_column(SAEnum(WardType), nullable=False)
    total_beds: Mapped[int] = mapped_column(Integer, nullable=False)
    occupied_beds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_beds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    facility: Mapped["Facility"] = relationship(
        "Facility", back_populates="bed_statuses"
    )

    def __repr__(self) -> str:
        return (
            f"<BedStatus(id={self.id}, facility_id={self.facility_id}, "
            f"ward='{self.ward_type}', occupied={self.occupied_beds}/{self.total_beds})>"
        )


# ============================================================
# DOCTOR ATTENDANCE MODEL
# ============================================================

class DoctorAttendance(Base):
    """
    Daily attendance record for each doctor at a facility.
    """
    __tablename__ = "doctor_attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    doctor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus), nullable=False
    )
    check_in: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    check_out: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Relationships
    facility: Mapped["Facility"] = relationship(
        "Facility", back_populates="doctor_attendance"
    )

    def __repr__(self) -> str:
        return (
            f"<DoctorAttendance(id={self.id}, doctor='{self.doctor_name}', "
            f"date={self.date}, status='{self.status}')>"
        )


# ============================================================
# TEST AVAILABILITY MODEL
# ============================================================

class TestAvailability(Base):
    """
    Diagnostic test availability at a facility.
    Tracks equipment status and availability over time.
    """
    __tablename__ = "test_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    equipment_status: Mapped[str] = mapped_column(
        String(50), default="operational", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    facility: Mapped["Facility"] = relationship(
        "Facility", back_populates="test_availability"
    )

    def __repr__(self) -> str:
        return (
            f"<TestAvailability(id={self.id}, test='{self.test_name}', "
            f"available={self.is_available})>"
        )


# ============================================================
# ALERT MODEL
# ============================================================

class Alert(Base):
    """
    System alerts and notifications for health anomalies.
    Generated by AI analysis or threshold breaches.
    """
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facilities.id"), nullable=False, index=True
    )
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(AlertSeverity), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    facility: Mapped["Facility"] = relationship("Facility", back_populates="alerts")

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, type='{self.alert_type}', "
            f"severity='{self.severity}', resolved={self.is_resolved})>"
        )
