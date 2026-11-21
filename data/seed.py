"""
CareGrid AI — Database Seed Script
=====================================
Resets the database, creates default users, and populates synthetic data.

Can be run as:
    python -m data.seed
    python data/seed.py
"""

from __future__ import annotations

import sys
import os
import logging
from datetime import datetime

# ── Ensure the project root is on sys.path so imports work ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.constants import UserRole
from models.database import reset_db, get_db_session
from models.schema import User
from utils.auth import hash_password
from data.synthetic_data_generator import SyntheticDataGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Default users ───────────────────────────────────────────────
_DEFAULT_USERS: list[dict] = [
    {
        "username": "admin",
        "password": "admin123",
        "role": UserRole.DISTRICT_ADMIN,
        "full_name": "Dr. Amit Sharma",
        "email": "amit.sharma@caregrid.in",
        "facility_id": None,
    },
    {
        "username": "staff1",
        "password": "staff123",
        "role": UserRole.FACILITY_STAFF,
        "full_name": "Nurse Priya Verma",
        "email": "priya.verma@caregrid.in",
        "facility_id": 1,
    },
    {
        "username": "sysadmin",
        "password": "sysadmin123",
        "role": UserRole.SYSTEM_ADMIN,
        "full_name": "Rahul Mehta",
        "email": "rahul.mehta@caregrid.in",
        "facility_id": None,
    },
]


def _create_default_users() -> None:
    """Insert default system users with hashed passwords."""
    print("\n[*] Creating default users ...")
    with get_db_session() as session:
        for user_data in _DEFAULT_USERS:
            user = User(
                username=user_data["username"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                facility_id=user_data["facility_id"],
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            print(f"   [OK] {user_data['full_name']} ({user_data['username']} / {user_data['role'].value})")
    print("   [OK] All default users created.\n")


def seed() -> None:
    """
    Full seed pipeline:
        1. Reset DB (drop + recreate tables)
        2. Create default users
        3. Generate synthetic data
    """
    print("=" * 60)
    print("  CareGrid AI -- Database Seeder")
    print("=" * 60)

    # Step 1: Reset database
    print("\n[*] Resetting database (drop + recreate tables) ...")
    reset_db()
    print("   [OK] Database reset complete.")

    # Step 2: Create default users
    _create_default_users()

    # Step 3: Generate synthetic data
    generator = SyntheticDataGenerator()
    generator.generate()

    # Step 4: Ensure every facility has at least one staff user
    print("\n[*] Ensuring every facility has at least one staff member ...")
    with get_db_session() as session:
        from models.schema import Facility, User
        from config.constants import UserRole
        
        facilities = session.query(Facility).all()
        for f in facilities:
            # check if this facility already has a staff user
            existing = session.query(User).filter(
                User.facility_id == f.id,
                User.role == UserRole.FACILITY_STAFF
            ).first()
            if not existing:
                # create a default staff member
                safe_name = f.name.lower().replace(" ", "_")
                staff_username = f"staff_{safe_name}"
                new_staff = User(
                    username=staff_username,
                    password_hash=hash_password("staff123"),
                    role=UserRole.FACILITY_STAFF,
                    full_name=f"Staff for {f.name}",
                    email=f"staff.{safe_name}@caregrid.in",
                    facility_id=f.id,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(new_staff)
                print(f"   [OK] Auto-created staff '{staff_username}' for {f.name}")
        session.commit()

    print("\n" + "=" * 60)
    print("  [OK] Seeding complete! Database is ready.")
    print("=" * 60)
    print("\n  Default logins:")
    print("  " + "-" * 40)
    for u in _DEFAULT_USERS:
        print(f"  {u['username']:12s} / {u['password']:12s}  ({u['role'].value})")
    print("  " + "-" * 40 + "\n")


if __name__ == "__main__":
    seed()
