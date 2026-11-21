"""
CareGrid AI - Admin Service
===========================
Provides operations for the Admin Panel to read/write all database tables
using Pandas DataFrames, specifically tailored for Streamlit's data_editor.
Supports transition from synthetic data to real manual data entry.
"""

import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, date

from models.database import get_db_session
from models.schema import (
    User, Facility, StockItem, StockLog, Footfall,
    BedStatus, DoctorAttendance, TestAvailability, Alert
)
from config.constants import (
    UserRole, FacilityType, AlertType, AlertSeverity,
    AttendanceStatus, StockChangeType, WardType
)

class AdminService:
    # Mapping table names to their SQLAlchemy models
    TABLE_MAP = {
        "Users": User,
        "Facilities": Facility,
        "Stock Inventory": StockItem,
        "Daily Footfall": Footfall,
        "Bed Status": BedStatus,
        "Doctor Attendance": DoctorAttendance,
        "Diagnostic Tests": TestAvailability,
        "System Alerts": Alert
    }

    # Helper mapping for fields that need Enum conversion
    ENUM_MAP = {
        "role": UserRole,
        "facility_type": FacilityType,
        "alert_type": AlertType,
        "severity": AlertSeverity,
        "status": AttendanceStatus,
        "change_type": StockChangeType,
        "ward_type": WardType
    }

    @classmethod
    def get_table_data(cls, table_name: str) -> pd.DataFrame:
        """Fetch all records from a table as a pandas DataFrame."""
        model = cls.TABLE_MAP.get(table_name)
        if not model:
            raise ValueError(f"Unknown table: {table_name}")
            
        with get_db_session() as session:
            records = session.query(model).all()
            
            data = []
            for r in records:
                row_dict = {c.name: getattr(r, c.name) for c in model.__table__.columns}
                
                # Convert values to strings for UI editability
                for key, val in row_dict.items():
                    # Handle Enums
                    if hasattr(val, "value"):
                        row_dict[key] = val.value
                    # Handle Dates and Datetimes
                    elif isinstance(val, (datetime, date)):
                        row_dict[key] = val.isoformat()
                        
                data.append(row_dict)
                
            return pd.DataFrame(data)

    @classmethod
    def _coerce_value(cls, col_name: str, val: Any, target_type: Any) -> Any:
        """Helper to convert UI types (strings/timestamps) to database types."""
        if val is None or pd.isna(val):
            return None
        # Guard against empty strings from data_editor — treat as None
        if isinstance(val, str) and val.strip() == "":
            return None
            
        # 1. Handle Enums
        if col_name in cls.ENUM_MAP:
            try:
                return cls.ENUM_MAP[col_name](val)
            except ValueError:
                # Fallback to direct value if it matches the DB format
                return val

        # 2. Handle Date/Datetime
        if str(target_type) == "Date":
            if isinstance(val, str):
                return datetime.strptime(val.split("T")[0], "%Y-%m-%d").date()
            elif isinstance(val, (datetime, date)):
                return val.date() if isinstance(val, datetime) else val
            elif hasattr(val, "to_pydatetime"):
                return val.to_pydatetime().date()
                
        elif str(target_type) == "DateTime":
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except ValueError:
                    return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            elif isinstance(val, (datetime, date)):
                return datetime.combine(val, datetime.min.time()) if isinstance(val, date) else val
            elif hasattr(val, "to_pydatetime"):
                return val.to_pydatetime()
                
        # 3. Handle Boolean
        elif str(target_type) == "Boolean":
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes")
            return bool(val)
            
        # 4. Handle Numeric
        elif str(target_type) == "Integer":
            return int(val)
        elif str(target_type) == "Float":
            return float(val)

        return val

    @classmethod
    def apply_changes(cls, table_name: str, changes: Dict[str, Any], original_df: pd.DataFrame) -> None:
        """
        Apply changes from Streamlit's data_editor back to the SQLite database.
        """
        model = cls.TABLE_MAP.get(table_name)
        if not model:
            raise ValueError(f"Unknown table: {table_name}")

        # Get column types from model table columns
        col_types = {c.name: c.type for c in model.__table__.columns}

        with get_db_session() as session:
            # 1. Process Updates
            edited_rows = changes.get("edited_rows", {})
            for idx, updates in edited_rows.items():
                record_id = int(original_df.iloc[int(idx)]["id"])
                record = session.query(model).get(record_id)
                if record:
                    for col, val in updates.items():
                        # Auto-encrypt plaintext password entered by Admin
                        if table_name == "Users" and col == "password_hash":
                            is_already_hashed = isinstance(val, str) and val.startswith("$2") and len(val) == 60
                            if not is_already_hashed:
                                from utils.auth import hash_password
                                val = hash_password(str(val))
                                
                        coerced_val = cls._coerce_value(col, val, col_types.get(col))
                        setattr(record, col, coerced_val)

            # 2. Process Deletions
            deleted_rows = changes.get("deleted_rows", [])
            for idx in deleted_rows:
                record_id = int(original_df.iloc[int(idx)]["id"])
                record = session.query(model).get(record_id)
                if record:
                    session.delete(record)

            # 3. Process Additions
            added_rows = changes.get("added_rows", [])
            for row in added_rows:
                # Remove primary key 'id' to let SQLite auto-increment
                if "id" in row:
                    del row["id"]
                    
                # Auto-populate sensible defaults if left empty
                if table_name == "Users":
                    if not row.get("is_active"): row["is_active"] = True
                    if not row.get("created_at"): row["created_at"] = datetime.utcnow()
                elif table_name == "Facilities":
                    if not row.get("is_active"): row["is_active"] = True
                    if not row.get("created_at"): row["created_at"] = datetime.utcnow()
                    if not row.get("district"): row["district"] = "Lucknow"
                    if not row.get("latitude"): row["latitude"] = 26.85  # Lucknow default
                    if not row.get("longitude"): row["longitude"] = 80.95  # Lucknow default
                    if not row.get("total_capacity"): row["total_capacity"] = 50
                elif table_name == "Stock Inventory":
                    if not row.get("current_stock"): row["current_stock"] = 0
                    if not row.get("reorder_level"): row["reorder_level"] = 100
                    if not row.get("unit"): row["unit"] = "tablets"
                elif table_name == "Daily Footfall":
                    if not row.get("date"): row["date"] = date.today()
                    if not row.get("patient_count"): row["patient_count"] = 0
                elif table_name == "Bed Status":
                    if not row.get("date"): row["date"] = date.today()
                    if not row.get("total_beds"): row["total_beds"] = 30
                    if not row.get("updated_at"): row["updated_at"] = datetime.utcnow()
                elif table_name == "Doctor Attendance":
                    if not row.get("date"): row["date"] = date.today()
                    if not row.get("status"): row["status"] = "present"
                elif table_name == "Diagnostic Tests":
                    if not row.get("is_available"): row["is_available"] = True
                    if not row.get("last_checked"): row["last_checked"] = datetime.utcnow()
                    if not row.get("equipment_status"): row["equipment_status"] = "operational"
                elif table_name == "System Alerts":
                    if not row.get("is_resolved"): row["is_resolved"] = False
                    if not row.get("created_at"): row["created_at"] = datetime.utcnow()

                processed_row = {}
                for col, val in row.items():
                    # Auto-encrypt plaintext password entered by Admin
                    if table_name == "Users" and col == "password_hash":
                        is_already_hashed = isinstance(val, str) and val.startswith("$2") and len(val) == 60
                        if not is_already_hashed:
                            from utils.auth import hash_password
                            val = hash_password(str(val))
                            
                    processed_row[col] = cls._coerce_value(col, val, col_types.get(col))
                
                new_record = model(**processed_row)
                session.add(new_record)
