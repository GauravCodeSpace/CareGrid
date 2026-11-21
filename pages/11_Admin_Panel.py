"""
CareGrid AI — Admin Panel
==========================
Manage system databases, facilities, users, and staffing allocations.
Restricted to System Administrators and District Administrators.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from sqlalchemy import func

from utils.auth import require_auth
from services.admin_service import AdminService
from models.database import get_db_session
from models.schema import Facility, User, DoctorAttendance
from config.constants import UserRole, AttendanceStatus, FacilityType

# ── Role guard ──
if not require_auth():
    st.stop()

user_role = st.session_state.get("user_role", "")
if user_role not in ["System Administrator", "District Administrator"]:
    st.error("🚫 Access Denied: This page is restricted to Administrators.")
    st.stop()

# ── Page Header & Readability CSS ──
st.html("""
<h1 style="color: #000000 !important; font-weight: 800; font-size: 2.2rem; margin-bottom: 0.2rem; font-family: 'Inter', sans-serif;">
    🗄️ Database Management
</h1>
<p style="color: #000000 !important; font-size: 1rem; margin-bottom: 1.5rem; font-family: 'Inter', sans-serif; font-weight: 500;">
    Directly manage system database tables, manage facility staffing, and assign doctors.
</p>

<style>
    /* Styling segmented control for admin page to look premium */
    div[data-testid="stSegmentedControl"] > div {
        background-color: #f1f5f9;
        border-radius: 12px;
        padding: 6px;
        border: 1px solid #cbd5e1;
    }
    
    /* Disable all shadows, animations, and transitions on st.tabs and stSegmentedControl */
    div[data-testid="stTabBar"] button,
    div[data-testid="stTabBar"] button *,
    div[data-testid="stTabBar"] button:hover,
    div[data-testid="stTabBar"] button:hover *,
    div[data-testid="stTabBar"] button:focus,
    div[data-testid="stTabBar"] button:focus *,
    div[data-testid="stTabBar"] button:active,
    div[data-testid="stTabBar"] button:active *,
    div[data-testid="stSegmentedControl"] button,
    div[data-testid="stSegmentedControl"] button *,
    div[data-testid="stSegmentedControl"] button:hover,
    div[data-testid="stSegmentedControl"] button:hover *,
    div[data-testid="stSegmentedControl"] button:focus,
    div[data-testid="stSegmentedControl"] button:focus *,
    div[data-testid="stSegmentedControl"] button:active,
    div[data-testid="stSegmentedControl"] button:active * {
        transition: none !important;
        box-shadow: none !important;
        transform: none !important;
    }

    /* Style active tab text color to match theme */
    div[data-testid="stTabBar"] button[aria-selected="true"],
    div[data-testid="stTabBar"] button[aria-selected="true"] * {
        color: #ef4444 !important;
        font-weight: 700 !important;
        background-color: transparent !important;
    }

    /* Style inactive tabs and tab hover text/backgrounds (make them flat and static) */
    div[data-testid="stTabBar"] button[aria-selected="false"],
    div[data-testid="stTabBar"] button[aria-selected="false"] *,
    div[data-testid="stTabBar"] button[aria-selected="false"]:hover,
    div[data-testid="stTabBar"] button[aria-selected="false"]:hover *,
    div[data-testid="stTabBar"] button[aria-selected="true"]:hover,
    div[data-testid="stTabBar"] button[aria-selected="true"]:hover * {
        color: #475569 !important;
        background-color: transparent !important;
    }
    
    /* Strict styling for unselected buttons (all states) */
    div[data-testid="stSegmentedControl"] button[aria-checked="false"],
    div[data-testid="stSegmentedControl"] button[aria-checked="false"] *,
    div[data-testid="stSegmentedControl"] button[aria-checked="false"]:hover,
    div[data-testid="stSegmentedControl"] button[aria-checked="false"]:hover *,
    div[data-testid="stSegmentedControl"] button[aria-checked="false"]:focus,
    div[data-testid="stSegmentedControl"] button[aria-checked="false"]:focus *,
    div[data-testid="stSegmentedControl"] button[aria-checked="false"]:active,
    div[data-testid="stSegmentedControl"] button[aria-checked="false"]:active * {
        background-color: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }
    
    /* Strict styling for selected buttons (all states - matching pink/red accent) */
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button[aria-checked="true"]:hover,
    div[data-testid="stSegmentedControl"] button[aria-checked="true"]:hover *,
    div[data-testid="stSegmentedControl"] button[aria-checked="true"]:focus,
    div[data-testid="stSegmentedControl"] button[aria-checked="true"]:focus *,
    div[data-testid="stSegmentedControl"] button[aria-checked="true"]:active,
    div[data-testid="stSegmentedControl"] button[aria-checked="true"]:active * {
        background-color: #fee2e2 !important;
        color: #ef4444 !important;
        border: 1.5px solid #ef4444 !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        font-size: 13px !important;
    }
    
    /* Ensure that double-clicking to edit cells in st.data_editor uses dark visible text */
    .glide-data-grid-portal input,
    .glide-data-grid-portal textarea,
    .glide-data-grid-portal * {
        color: #000000 !important;
        background-color: #ffffff !important;
        font-weight: 500 !important;
    }
</style>
""")

# ── Switch Tabs ──
if user_role == "System Administrator":
    tab_db, tab_staff = st.tabs(["🗄️ Database Table Editor", "👥 Staffing & Doctor Management"])
else:
    # District Administrator only gets Staffing tab
    tab_staff_list = st.tabs(["👥 Staffing & Doctor Management"])
    tab_staff = tab_staff_list[0]
    tab_db = None

# ============================================================
# TAB 1: DATABASE TABLE EDITOR
# ============================================================
if tab_db is not None:
    with tab_db:
        # ── Select Table as Pill Buttons (Segmented Control) ──
        table_options = list(AdminService.TABLE_MAP.keys())

        selected_table = st.segmented_control(
            "Select Table to Edit:",
            options=table_options,
            default="Users",
            selection_mode="single",
            key="admin_table_selector"
        )

        if not selected_table:
            selected_table = "Users"

        st.divider()

        st.html(f"""
        <h3 style="color: #000000 !important; font-weight: 700; margin-top: 1rem; margin-bottom: 1rem; font-family: 'Inter', sans-serif;">
            Editing Table: {selected_table}
        </h3>
        """)

        # ── Load Data ──
        try:
            df = AdminService.get_table_data(selected_table)
        except Exception as e:
            st.error(f"Error loading table: {e}")
            st.stop()

        # ── Edit Table ──
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key=f"editor_{selected_table}"
        )

        # ── Save Button ──
        if st.button("💾 Save Table Changes", use_container_width=True):
            try:
                # The diff dict (edited_rows, added_rows, deleted_rows) is in session_state,
                # NOT in the return value of st.data_editor (which is the full DataFrame).
                editor_key = f"editor_{selected_table}"
                change_dict = st.session_state.get(editor_key, {})
                AdminService.apply_changes(selected_table, change_dict, df)
                st.success("Changes saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving changes: {e}")


# ============================================================
# TAB 2: STAFFING & DOCTOR MANAGEMENT
# ============================================================
with tab_staff:
    st.html("<h3 style='color: #000000; font-weight: 700;'>👥 Staffing Overview by Facility</h3>")

    # Load summary data from database
    with get_db_session() as session:
        facilities = session.query(Facility).filter(Facility.is_active == True).all()
        facility_map = {f.name: f.id for f in facilities}
        
        summary_rows = []
        for fac in facilities:
            # count staff users
            staff_count = session.query(func.count(User.id)).filter(
                User.facility_id == fac.id,
                User.role == UserRole.FACILITY_STAFF
            ).scalar() or 0
            
            # count unique doctors in doctor_attendance
            doc_count = session.query(func.count(func.distinct(DoctorAttendance.doctor_name))).filter(
                DoctorAttendance.facility_id == fac.id
            ).scalar() or 0
            
            summary_rows.append({
                "Facility Name": fac.name,
                "Type": fac.facility_type.value,
                "Registered Staff (Users)": staff_count,
                "Active Doctors": doc_count,
                "District": fac.district
            })
            
    # Check for facilities with 0 staff
    missing_staff_facs = [row["Facility Name"] for row in summary_rows if row["Registered Staff (Users)"] == 0]
    if missing_staff_facs:
        st.warning(
            f"⚠️ **Attention Admin:** The following facilities have **0 registered staff**: "
            f"{', '.join(missing_staff_facs)}. "
            f"Please register at least one staff user for each facility below so they can log doctor attendance!"
        )
    else:
        st.success("✅ **Perfect Staffing:** All facilities have at least one registered staff member assigned.")

    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.html("<h3 style='color: #000000; font-weight: 700;'>✍️ Quick Registration & Allocations</h3>")
    
    col_add_fac, col_add_staff, col_add_doc = st.columns(3, gap="medium")
    
    # ── Form 0: Add New Facility ──
    with col_add_fac:
        with st.container(border=True):
            st.html("<h4 style='color: #000000; font-weight: 700; margin: 0 0 10px 0; font-family: sans-serif;'>🏥 Register New Facility</h4>")
            with st.form("quick_facility_form", clear_on_submit=True):
                fac_name = st.text_input("Facility Name", placeholder="e.g. PHC Bakshi Ka Talab")
                fac_type = st.selectbox("Facility Type", options=["PHC", "CHC"])
                fac_district = st.text_input("District", value="Lucknow")
                fac_address = st.text_input("Address", placeholder="e.g. Sitapur Road, Lucknow")
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    fac_lat = st.number_input("Latitude", value=26.8500, format="%.4f")
                with col_lon:
                    fac_lon = st.number_input("Longitude", value=80.9500, format="%.4f")
                fac_capacity = st.number_input("Bed Capacity", value=50, min_value=5, max_value=500, step=5)
                fac_phone = st.text_input("Phone (Optional)", placeholder="+91 522-XXXXXXX")
                
                submitted_fac = st.form_submit_button("🏥 Register Facility")
                
                if submitted_fac:
                    if not fac_name or not fac_name.strip():
                        st.error("Please enter a facility name.")
                    else:
                        try:
                            with get_db_session() as session:
                                existing = session.query(Facility).filter(Facility.name == fac_name.strip()).first()
                                if existing:
                                    st.error("A facility with this name already exists!")
                                else:
                                    new_facility = Facility(
                                        name=fac_name.strip(),
                                        facility_type=FacilityType(fac_type),
                                        district=fac_district.strip() or "Lucknow",
                                        address=fac_address.strip() or None,
                                        latitude=float(fac_lat),
                                        longitude=float(fac_lon),
                                        phone=fac_phone.strip() or None,
                                        total_capacity=int(fac_capacity),
                                        is_active=True,
                                        created_at=datetime.utcnow(),
                                    )
                                    session.add(new_facility)
                                    session.commit()
                                    st.success(f"Registered facility '{fac_name}' successfully!")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error registering facility: {e}")

    # ── Form 1: Add New Staff User ──
    with col_add_staff:
        with st.container(border=True):
            st.html("<h4 style='color: #000000; font-weight: 700; margin: 0 0 10px 0; font-family: sans-serif;'>👤 Register New Staff Member</h4>")
            with st.form("quick_staff_form", clear_on_submit=True):
                staff_name = st.text_input("Staff Full Name", placeholder="e.g. Nurse Kiran Devi")
                staff_username = st.text_input("Username (For login)", placeholder="e.g. kiran_phc")
                staff_password = st.text_input("Password", type="password", placeholder="Set password")
                staff_fac_name = st.selectbox("Assign Facility", options=list(facility_map.keys()))
                
                submitted_staff = st.form_submit_button("👤 Register Staff User")
                
                if submitted_staff:
                    if not staff_name or not staff_username or not staff_password:
                        st.error("Please fill all staff user details.")
                    else:
                        try:
                            from utils.auth import hash_password
                            with get_db_session() as session:
                                # check if username exists
                                existing = session.query(User).filter(User.username == staff_username).first()
                                if existing:
                                    st.error("Username already exists!")
                                else:
                                    new_user = User(
                                        username=staff_username,
                                        password_hash=hash_password(staff_password),
                                        role=UserRole.FACILITY_STAFF,
                                        full_name=staff_name,
                                        facility_id=facility_map[staff_fac_name],
                                        is_active=True,
                                        created_at=datetime.utcnow()
                                    )
                                    session.add(new_user)
                                    session.commit()
                                    st.success(f"Registered staff {staff_name} for {staff_fac_name} successfully!")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error adding staff: {e}")

    # ── Form 2: Register Doctor ──
    with col_add_doc:
        with st.container(border=True):
            st.html("<h4 style='color: #000000; font-weight: 700; margin: 0 0 10px 0; font-family: sans-serif;'>👨‍⚕️ Register New Doctor</h4>")
            with st.form("quick_doc_form", clear_on_submit=True):
                doc_name = st.text_input("Doctor Name", placeholder="e.g. Dr. Satish Kumar")
                doc_spec = st.text_input("Specialization", placeholder="e.g. Pediatrics")
                doc_fac_name = st.selectbox("Assign Facility", options=list(facility_map.keys()))
                
                submitted_doc = st.form_submit_button("👨‍⚕️ Register Doctor")
                
                if submitted_doc:
                    if not doc_name or not doc_spec:
                        st.error("Please fill doctor name and specialization.")
                    else:
                        try:
                            with get_db_session() as session:
                                # Register doctor by writing a baseline attendance record for today
                                new_att = DoctorAttendance(
                                    facility_id=facility_map[doc_fac_name],
                                    doctor_name=doc_name,
                                    specialization=doc_spec,
                                    date=date.today(),
                                    status=AttendanceStatus.PRESENT
                                )
                                session.add(new_att)
                                session.commit()
                                st.success(f"Registered {doc_name} ({doc_spec}) at {doc_fac_name} successfully!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error registering doctor: {e}")
