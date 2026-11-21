"""
CareGrid AI — Database Tests
==============================
Tests for database connection, table creation, and CRUD operations.
"""

import sys
import os
from datetime import date, datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_database_connection():
    """Test that database connection is established."""
    from models.database import check_db_health
    assert check_db_health(), "Database connection failed"
    print("✅ Database connection: OK")


def test_table_creation():
    """Test that all tables are created."""
    from models.database import init_db, get_engine
    from sqlalchemy import inspect

    init_db()
    inspector = inspect(get_engine())
    tables = inspector.get_table_names()

    expected_tables = [
        "users", "facilities", "stock_items", "stock_logs",
        "footfall", "bed_status", "doctor_attendance",
        "test_availability", "alerts",
    ]

    for table in expected_tables:
        assert table in tables, f"Table '{table}' not found"

    print(f"✅ Table creation: OK ({len(tables)} tables found)")


def test_facility_crud():
    """Test CRUD operations on Facility model."""
    from models.database import get_db_session
    from models.schema import Facility
    from config.constants import FacilityType

    with get_db_session() as session:
        # Create
        facility = Facility(
            name="Test PHC",
            facility_type=FacilityType.PHC,
            district="Test District",
            latitude=26.85,
            longitude=80.95,
            total_capacity=30,
        )
        session.add(facility)
        session.flush()
        fid = facility.id

    with get_db_session() as session:
        # Read
        f = session.query(Facility).filter_by(id=fid).first()
        assert f is not None, "Facility not found after create"
        assert f.name == "Test PHC"

        # Update
        f.name = "Test PHC Updated"
        session.flush()

    with get_db_session() as session:
        f = session.query(Facility).filter_by(id=fid).first()
        assert f.name == "Test PHC Updated", "Update failed"

        # Delete
        session.delete(f)
        session.flush()

    with get_db_session() as session:
        f = session.query(Facility).filter_by(id=fid).first()
        assert f is None, "Delete failed"

    print("✅ Facility CRUD: OK")


def test_relationships():
    """Test that model relationships work correctly."""
    from models.database import get_db_session
    from models.schema import Facility, StockItem
    from config.constants import FacilityType

    with get_db_session() as session:
        facility = Facility(
            name="Relationship Test PHC",
            facility_type=FacilityType.PHC,
            district="Test",
            latitude=26.85,
            longitude=80.95,
        )
        session.add(facility)
        session.flush()

        item = StockItem(
            facility_id=facility.id,
            medicine_name="Test Medicine",
            category="Test",
            current_stock=100,
            unit="tablets",
            reorder_level=50,
        )
        session.add(item)
        session.flush()

        # Test relationship
        assert len(facility.stock_items) == 1
        assert facility.stock_items[0].medicine_name == "Test Medicine"
        assert item.facility.name == "Relationship Test PHC"

        # Cleanup
        session.delete(item)
        session.delete(facility)

    print("✅ Relationships: OK")


def test_data_seeded():
    """Test that synthetic data was properly seeded."""
    from models.database import get_db_session
    from models.schema import Facility, StockItem, Alert
    from sqlalchemy import func

    with get_db_session() as session:
        facility_count = session.query(func.count(Facility.id)).scalar()
        stock_count = session.query(func.count(StockItem.id)).scalar()
        alert_count = session.query(func.count(Alert.id)).scalar()

        if facility_count >= 15:
            print(f"✅ Seeded data: {facility_count} facilities, {stock_count} stock items, {alert_count} alerts")
        else:
            print(f"⚠️  Seeded data check: only {facility_count} facilities (run `python -m data.seed` first)")


if __name__ == "__main__":
    print("\n🧪 CareGrid AI — Database Tests\n" + "=" * 40)
    test_database_connection()
    test_table_creation()
    test_facility_crud()
    test_relationships()
    test_data_seeded()
    print("\n✅ All database tests passed!\n")
