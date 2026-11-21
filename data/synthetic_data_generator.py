"""
CareGrid AI — Synthetic Data Generator
=========================================
Generates 90 days of realistic healthcare operational data for 15 facilities
in the Lucknow district.  Data is deterministic (numpy seed 42) so every run
produces the same dataset.

Injected Scenarios:
    0. PHC Rajpur        → critically low Paracetamol (CRITICAL alert)
    1. CHC Sadar         → 40 % doctor absenteeism   (WARNING alert)
    2. PHC Mohanlalganj  → bed overcrowding >92 %     (CRITICAL alert)
    3. CHC Malihabad     → 5 diagnostic tests down    (WARNING alert)

Usage:
    from data.synthetic_data_generator import SyntheticDataGenerator
    SyntheticDataGenerator().generate()
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np

from config.constants import (
    DEPARTMENTS,
    DIAGNOSTIC_TESTS,
    DOCTOR_NAMES,
    FACILITY_NAMES,
    MEDICINES,
    AlertSeverity,
    AlertType,
    AttendanceStatus,
    FacilityType,
    StockChangeType,
    WardType,
)
from models.database import get_db_session
from models.schema import (
    Alert,
    BedStatus,
    DoctorAttendance,
    Facility,
    Footfall,
    StockItem,
    StockLog,
    TestAvailability,
)

logger = logging.getLogger(__name__)

# ── Ward configuration: ward_type → total_beds ──────────────────
_WARD_BEDS: dict[WardType, int] = {
    WardType.GENERAL: 30,
    WardType.ICU: 10,
    WardType.MATERNITY: 15,
    WardType.PEDIATRIC: 10,
    WardType.EMERGENCY: 8,
}

# ── Department footfall ranges: department → (min, max) ─────────
_DEPT_FOOTFALL: dict[str, tuple[int, int]] = {
    "OPD": (20, 80),
    "IPD": (5, 20),
    "Emergency": (2, 15),
    "Maternity": (3, 12),
    "Pediatric": (4, 18),
    "Dental": (2, 10),
    "Ophthalmology": (2, 8),
    "Pathology": (5, 25),
}

# ── Time-span ───────────────────────────────────────────────────
_DATA_DAYS: int = 90


class SyntheticDataGenerator:
    """
    Populates the database with deterministic synthetic healthcare data.

    Attributes:
        rng: Seeded numpy random generator for reproducibility.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self._today: date = date.today()
        self._start_date: date = self._today - timedelta(days=_DATA_DAYS - 1)

    # ================================================================
    # PUBLIC ENTRY POINT
    # ================================================================

    def generate(self) -> None:
        """
        Run the full data-generation pipeline inside a single DB session.
        """
        print("[*] Starting synthetic data generation ...")
        with get_db_session() as session:
            # 1. Create facilities
            facilities = self._create_facilities(session)
            print(f"   [OK] {len(facilities)} facilities created")

            # 2. Per-facility data
            for idx, fac in enumerate(facilities):
                self._generate_stock(session, fac, idx)
                self._generate_footfall(session, fac)
                self._generate_beds(session, fac, idx)
                self._generate_attendance(session, fac, idx)
                self._generate_diagnostics(session, fac, idx)
                print(f"   [OK] Facility {idx + 1}/{len(facilities)}: {fac.name}")

            # 3. Inject alert scenarios
            self._inject_scenarios(session, facilities)
            print("   [OK] Alert scenarios injected")

        print("[OK] Synthetic data generation complete!")

    # ================================================================
    # FACILITIES
    # ================================================================

    def _create_facilities(self, session) -> list[Facility]:
        facilities: list[Facility] = []
        for info in FACILITY_NAMES:
            total_cap = sum(_WARD_BEDS.values())
            fac = Facility(
                name=info["name"],
                facility_type=info["type"],
                district="Lucknow",
                address=f'{info["name"]}, Lucknow, Uttar Pradesh',
                latitude=info["lat"],
                longitude=info["lon"],
                phone=f"+91-522-{self.rng.integers(2000000, 2999999)}",
                total_capacity=total_cap,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(fac)
            facilities.append(fac)
        session.flush()  # Populate IDs
        return facilities

    # ================================================================
    # STOCK
    # ================================================================

    def _generate_stock(self, session, fac: Facility, fac_idx: int) -> None:
        for med in MEDICINES:
            initial_stock = int(self.rng.integers(500, 3001))
            stock_item = StockItem(
                facility_id=fac.id,
                medicine_name=med["name"],
                category=med["category"],
                current_stock=initial_stock,
                unit=med["unit"],
                reorder_level=med["reorder_level"],
                last_restocked=datetime.combine(
                    self._today - timedelta(days=int(self.rng.integers(1, 30))),
                    datetime.min.time(),
                ),
            )
            session.add(stock_item)
            session.flush()

            # Daily consumption logs for 90 days
            remaining = initial_stock
            for day_offset in range(_DATA_DAYS):
                log_date = self._start_date + timedelta(days=day_offset)
                weekday = log_date.weekday()
                # Reduce consumption on weekends
                if weekday >= 5:
                    daily = int(self.rng.integers(5, 40))
                else:
                    daily = int(self.rng.integers(10, 81))

                daily = min(daily, max(remaining, 0))
                remaining -= daily

                log = StockLog(
                    stock_item_id=stock_item.id,
                    facility_id=fac.id,
                    quantity_change=-daily,
                    change_type=StockChangeType.CONSUMED,
                    timestamp=datetime.combine(log_date, datetime.min.time())
                    + timedelta(hours=int(self.rng.integers(8, 18))),
                    notes=f"Daily consumption for {med['name']}",
                )
                session.add(log)

                # Periodic restocking every ~20 days
                if day_offset > 0 and day_offset % 20 == 0:
                    restock_qty = int(self.rng.integers(300, 1001))
                    remaining += restock_qty
                    restock_log = StockLog(
                        stock_item_id=stock_item.id,
                        facility_id=fac.id,
                        quantity_change=restock_qty,
                        change_type=StockChangeType.RECEIVED,
                        timestamp=datetime.combine(log_date, datetime.min.time())
                        + timedelta(hours=int(self.rng.integers(9, 12))),
                        notes=f"Restocking {med['name']}",
                    )
                    session.add(restock_log)

            # Update current stock to final remaining (clamped ≥ 0)
            stock_item.current_stock = max(remaining, 0)

    # ================================================================
    # FOOTFALL
    # ================================================================

    def _generate_footfall(self, session, fac: Facility) -> None:
        for day_offset in range(_DATA_DAYS):
            log_date = self._start_date + timedelta(days=day_offset)
            weekday = log_date.weekday()
            weekend_factor = 0.5 if weekday >= 5 else 1.0

            for dept in DEPARTMENTS:
                lo, hi = _DEPT_FOOTFALL.get(dept, (5, 20))
                base_count = int(self.rng.integers(lo, hi + 1))
                count = max(1, int(base_count * weekend_factor))

                # Map department to OPD/IPD/Emergency counters
                opd = count if dept == "OPD" else 0
                ipd = count if dept == "IPD" else 0
                emg = count if dept == "Emergency" else 0

                ff = Footfall(
                    facility_id=fac.id,
                    date=log_date,
                    department=dept,
                    patient_count=count,
                    opd_count=opd,
                    ipd_count=ipd,
                    emergency_count=emg,
                )
                session.add(ff)

    # ================================================================
    # BED STATUS
    # ================================================================

    def _generate_beds(self, session, fac: Facility, fac_idx: int) -> None:
        for day_offset in range(_DATA_DAYS):
            log_date = self._start_date + timedelta(days=day_offset)

            for ward_type, total_beds in _WARD_BEDS.items():
                # Default occupancy 50-80%
                min_occ = int(total_beds * 0.5)
                max_occ = int(total_beds * 0.8)
                occupied = int(self.rng.integers(min_occ, max_occ + 1))
                available = total_beds - occupied

                bs = BedStatus(
                    facility_id=fac.id,
                    ward_type=ward_type,
                    total_beds=total_beds,
                    occupied_beds=occupied,
                    available_beds=available,
                    date=log_date,
                    updated_at=datetime.combine(log_date, datetime.min.time())
                    + timedelta(hours=8),
                )
                session.add(bs)

    # ================================================================
    # DOCTOR ATTENDANCE
    # ================================================================

    def _generate_attendance(self, session, fac: Facility, fac_idx: int) -> None:
        # Assign 3-4 doctors per facility
        num_doctors = int(self.rng.integers(3, 5))
        doc_indices = self.rng.choice(len(DOCTOR_NAMES), size=num_doctors, replace=False)
        assigned_doctors = [DOCTOR_NAMES[i] for i in doc_indices]

        for day_offset in range(_DATA_DAYS):
            log_date = self._start_date + timedelta(days=day_offset)
            weekday = log_date.weekday()

            for doc in assigned_doctors:
                if weekday == 6:  # Sunday — everyone off
                    status = AttendanceStatus.LEAVE
                    check_in: Optional[str] = None
                    check_out: Optional[str] = None
                else:
                    roll = float(self.rng.random())
                    if roll < 0.78:
                        status = AttendanceStatus.PRESENT
                        ci_hour = int(self.rng.integers(8, 10))
                        co_hour = int(self.rng.integers(16, 19))
                        check_in = f"{ci_hour:02d}:00"
                        check_out = f"{co_hour:02d}:00"
                    elif roll < 0.88:
                        status = AttendanceStatus.HALF_DAY
                        check_in = "09:00"
                        check_out = "13:00"
                    elif roll < 0.94:
                        status = AttendanceStatus.LEAVE
                        check_in = None
                        check_out = None
                    else:
                        status = AttendanceStatus.ABSENT
                        check_in = None
                        check_out = None

                att = DoctorAttendance(
                    facility_id=fac.id,
                    doctor_name=doc["name"],
                    specialization=doc["specialization"],
                    date=log_date,
                    status=status,
                    check_in=check_in,
                    check_out=check_out,
                )
                session.add(att)

    # ================================================================
    # DIAGNOSTIC TEST AVAILABILITY
    # ================================================================

    def _generate_diagnostics(self, session, fac: Facility, fac_idx: int) -> None:
        for test in DIAGNOSTIC_TESTS:
            ta = TestAvailability(
                facility_id=fac.id,
                test_name=test["name"],
                category=test["category"],
                is_available=True,
                last_checked=datetime.combine(self._today, datetime.min.time())
                - timedelta(hours=int(self.rng.integers(1, 48))),
                equipment_status="operational",
                notes=None,
            )
            session.add(ta)

    # ================================================================
    # SCENARIO INJECTION
    # ================================================================

    def _inject_scenarios(self, session, facilities: list[Facility]) -> None:
        """
        Inject predefined anomaly scenarios into the first four facilities
        so the AI and dashboards have interesting data to surface.
        """
        self._scenario_low_stock(session, facilities[0])
        self._scenario_high_absenteeism(session, facilities[1])
        self._scenario_bed_overcrowding(session, facilities[2])
        self._scenario_diagnostic_failure(session, facilities[3])

    # ── Scenario 0: Critically low Paracetamol at PHC Rajpur ────

    def _scenario_low_stock(self, session, fac: Facility) -> None:
        item: Optional[StockItem] = (
            session.query(StockItem)
            .filter(
                StockItem.facility_id == fac.id,
                StockItem.medicine_name == "Paracetamol 500mg",
            )
            .first()
        )
        if item:
            item.current_stock = 30  # Well below reorder_level 500

        session.add(
            Alert(
                facility_id=fac.id,
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.CRITICAL,
                message=(
                    f"CRITICAL: Paracetamol 500mg stock at {fac.name} is critically low "
                    f"(30 tablets remaining, reorder level 500). Immediate restocking required."
                ),
                is_resolved=False,
                created_at=datetime.utcnow(),
            )
        )
        logger.info("Scenario: low stock injected for %s", fac.name)

    # ── Scenario 1: High absenteeism at CHC Sadar ──────────────

    def _scenario_high_absenteeism(self, session, fac: Facility) -> None:
        # Set 40% of attendance records in the last 30 days to absent
        recent_cutoff = self._today - timedelta(days=30)
        records = (
            session.query(DoctorAttendance)
            .filter(
                DoctorAttendance.facility_id == fac.id,
                DoctorAttendance.date >= recent_cutoff,
            )
            .all()
        )
        num_to_flip = int(len(records) * 0.40)
        indices = self.rng.choice(len(records), size=min(num_to_flip, len(records)), replace=False)
        for i in indices:
            records[int(i)].status = AttendanceStatus.ABSENT
            records[int(i)].check_in = None
            records[int(i)].check_out = None

        session.add(
            Alert(
                facility_id=fac.id,
                alert_type=AlertType.HIGH_ABSENTEEISM,
                severity=AlertSeverity.WARNING,
                message=(
                    f"WARNING: Doctor absenteeism at {fac.name} has reached ~40% over the "
                    f"last 30 days. Patient care may be impacted. Please review staffing."
                ),
                is_resolved=False,
                created_at=datetime.utcnow(),
            )
        )
        logger.info("Scenario: high absenteeism injected for %s", fac.name)

    # ── Scenario 2: Bed overcrowding at PHC Mohanlalganj ────────

    def _scenario_bed_overcrowding(self, session, fac: Facility) -> None:
        # Set last 14 days of General and ICU to >92% occupancy
        recent_cutoff = self._today - timedelta(days=14)
        beds = (
            session.query(BedStatus)
            .filter(
                BedStatus.facility_id == fac.id,
                BedStatus.date >= recent_cutoff,
                BedStatus.ward_type.in_([WardType.GENERAL, WardType.ICU]),
            )
            .all()
        )
        for bed in beds:
            # Set occupancy to 93-98%
            target_pct = float(self.rng.uniform(0.93, 0.99))
            bed.occupied_beds = min(
                int(bed.total_beds * target_pct), bed.total_beds
            )
            bed.available_beds = bed.total_beds - bed.occupied_beds

        session.add(
            Alert(
                facility_id=fac.id,
                alert_type=AlertType.BED_OVERCROWDING,
                severity=AlertSeverity.CRITICAL,
                message=(
                    f"CRITICAL: Bed occupancy at {fac.name} exceeds 92% in General "
                    f"and ICU wards for the past 14 days. Patient diversion recommended."
                ),
                is_resolved=False,
                created_at=datetime.utcnow(),
            )
        )
        logger.info("Scenario: bed overcrowding injected for %s", fac.name)

    # ── Scenario 3: Diagnostic failures at CHC Malihabad ────────

    def _scenario_diagnostic_failure(self, session, fac: Facility) -> None:
        tests = (
            session.query(TestAvailability)
            .filter(TestAvailability.facility_id == fac.id)
            .all()
        )
        # Pick 5 tests to disable
        if len(tests) >= 5:
            chosen_indices = self.rng.choice(len(tests), size=5, replace=False)
            failed_names: list[str] = []
            for i in chosen_indices:
                tests[int(i)].is_available = False
                tests[int(i)].equipment_status = "out_of_order"
                tests[int(i)].notes = "Equipment malfunction — service requested."
                failed_names.append(tests[int(i)].test_name)

            session.add(
                Alert(
                    facility_id=fac.id,
                    alert_type=AlertType.EQUIPMENT_FAILURE,
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"WARNING: {len(failed_names)} diagnostic tests unavailable at "
                        f"{fac.name} due to equipment failure: "
                        f"{', '.join(failed_names[:3])}{'…' if len(failed_names) > 3 else ''}. "
                        f"Patients may need referral."
                    ),
                    is_resolved=False,
                    created_at=datetime.utcnow(),
                )
            )
        logger.info("Scenario: diagnostic failure injected for %s", fac.name)
