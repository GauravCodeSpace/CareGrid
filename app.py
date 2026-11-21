"""
CareGrid AI — Main Application Entry Point
=============================================
Streamlit multi-page application with st.navigation for programmatic
page routing, authentication gating, and shared frame elements.

Run with:
    streamlit run app.py
"""

import streamlit as st
from pathlib import Path

from utils.translator import t
import pandas as pd

# ── Pandas Styler compatibility (pandas < 2.1 uses applymap, pandas >= 2.1 uses map) ──
if hasattr(pd, "io") and hasattr(pd.io, "formats") and hasattr(pd.io.formats, "style"):
    _styler = pd.io.formats.style.Styler
    if not hasattr(_styler, "applymap") and hasattr(_styler, "map"):
        _styler.applymap = _styler.map
    elif not hasattr(_styler, "map") and hasattr(_styler, "applymap"):
        _styler.map = _styler.applymap

# ── Page Configuration (must be first Streamlit command) ──
st.set_page_config(
    page_title="CareGrid AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "CareGrid AI — AI-Powered Healthcare Operations & Resource Management Platform v1.0.0",
    },
)


def _load_css() -> None:
    """Inject custom healthcare theme CSS."""
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _init_session_state() -> None:
    """Initialize session state variables with defaults."""
    defaults = {
        "authenticated": False,
        "user": None,
        "user_role": None,
        "user_facility_id": None,
        "language": "en",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _init_database() -> None:
    """Initialize database tables on first run."""
    try:
        from models.database import init_db
        init_db()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")


def _build_navigation() -> None:
    """Build navigation based on authentication state."""
    # ── Login Page (unauthenticated users) ──
    login_page = st.Page(
        "pages/1_Login.py",
        title="Login",
        icon="🔐",
    )

    # ── Authenticated Pages ──
    monitoring_pages = [
        st.Page("pages/2_Dashboard.py", title=t("nav.dashboard"), icon="📊", default=True),
        st.Page("pages/3_Facility.py", title=t("nav.facilities"), icon="🏥"),
    ]

    operations_pages = [
        st.Page("pages/4_Stock.py", title=t("nav.stock"), icon="💊"),
        st.Page("pages/5_Footfall.py", title=t("nav.footfall"), icon="👥"),
        st.Page("pages/6_Beds.py", title=t("nav.beds"), icon="🛏️"),
        st.Page("pages/7_Attendance.py", title=t("nav.attendance"), icon="📋"),
    ]

    intelligence_pages = [
        st.Page("pages/8_AI_Insights.py", title=t("nav.ai_insights", default="AI Insights"), icon="🤖"),
        st.Page("pages/9_Maps.py", title=t("nav.maps", default="Maps"), icon="🗺️"),
        st.Page("pages/10_Reports.py", title=t("nav.reports", default="Reports"), icon="📄"),
    ]

    from utils.auth import is_authenticated
    # ── Route based on auth state ──
    if not is_authenticated():
        pg = st.navigation([login_page], position="hidden")
    else:
        nav_dict = {
            "Monitoring": monitoring_pages,
            "Operations": operations_pages,
            "Intelligence": intelligence_pages,
        }
        
        # Only show Administration section to admins
        user_role = st.session_state.get("user_role")
        from config.constants import UserRole
        if user_role in [UserRole.SYSTEM_ADMIN.value, UserRole.DISTRICT_ADMIN.value, "System Administrator", "District Administrator"]:
            administration_pages = [
                st.Page("pages/11_Admin_Panel.py", title="Admin Panel", icon="🗄️"),
            ]
            nav_dict["Administration"] = administration_pages
        pg = st.navigation(nav_dict)

    return pg


def _render_sidebar() -> None:
    """Render shared sidebar elements for authenticated users."""
    if not st.session_state.get("authenticated"):
        return

    with st.sidebar:
        # ── Logo ──
        logo_path = Path(__file__).parent / "assets" / "logo.png"
        if logo_path.exists():
            # st.logo adds the logo to both expanded and collapsed sidebar states (Streamlit 1.35+)
            st.logo(str(logo_path), icon_image=str(logo_path))

        st.markdown(
            '<p style="color: rgba(255,255,255,0.6); font-size: 11px; '
            'letter-spacing: 1px; text-transform: uppercase; margin-top: 10px;">'
            "Healthcare Operations Platform</p>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── User Info ──
        user = st.session_state.get("user")
        if user:
            st.markdown(
                f"""
                <div style="padding: 12px 16px; background:blue;
                border-radius: 12px; margin-bottom: 16px;">
                    <div style="color: white; font-weight: 600; font-size: 14px;">
                        👤 {user.get('full_name', user.get('username', 'User'))}
                    </div>
                    <div style="color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 4px;">
                        {user.get('role', 'Staff')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Language Selector ──
        lang_options = {"English": "en", "हिन्दी": "hi"}
        current_lang = st.session_state.get("language", "en")
        current_lang_name = next(
            (k for k, v in lang_options.items() if v == current_lang), "English"
        )
        
        # Adding custom CSS to make the segmented control attractive
        st.markdown(
            """
            <style>
            div[data-testid="stSegmentedControl"] > div {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 4px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Using segmented_control for an attractive pill-style toggle (Streamlit 1.40+)
        if hasattr(st, "segmented_control"):
            selected_lang = st.segmented_control(
                "🌐 Language",
                options=list(lang_options.keys()),
                default=current_lang_name,
                selection_mode="single",
                key="sidebar_language_selector"
            )
            # If user unselects everything, fallback to current
            if not selected_lang:
                selected_lang = current_lang_name
        else:
            # Fallback for older versions
            selected_lang = st.radio(
                "🌐 Language",
                options=list(lang_options.keys()),
                index=list(lang_options.keys()).index(current_lang_name),
                horizontal=True,
                key="sidebar_language_selector",
            )
            
        st.session_state["language"] = lang_options[selected_lang]

        st.divider()

        # ── Quick Stats ──
        st.markdown(
            '<p style="color: rgba(255,255,255,0.5); font-size: 11px; '
            'text-transform: uppercase; letter-spacing: 1px;">Quick Stats</p>',
            unsafe_allow_html=True,
        )

        try:
            from services.dashboard_service import DashboardService

            stats = DashboardService.get_quick_stats()
            stat_col1, stat_col2 = st.columns(2)
            with stat_col1:
                st.markdown(
                    f"""<div style="text-align:center; padding:8px;
                    background:blue; border-radius:8px;">
                    <div style="font-size:20px; font-weight:700; color:white;">{stats.get('facilities', 0)}</div>
                    <div style="font-size:10px; color:rgba(255,255,255,0.5);">Facilities</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with stat_col2:
                st.markdown(
                    f"""<div style="text-align:center; padding:8px;
                    background:red; border-radius:8px;">
                    <div style="font-size:20px; font-weight:700; color:white;">{stats.get('active_alerts', 0)}</div>
                    <div style="font-size:10px; color:white;">Alerts</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        except Exception:
            pass  # Services not yet available during initial setup

        # ── Spacer + Logout ──
        st.markdown("<br>" * 3, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout_btn"):
            from utils.auth import logout_user
            logout_user(st.session_state)
            st.rerun()

        # ── Footer ──
        st.markdown(
            """
            <div style="position: fixed; bottom: 16px; left: 16px; right: 16px;
            text-align: center; padding: 8px;">
                <p style="color: rgba(255,255,255,0.3); font-size: 10px; margin: 0;">
                    CareGrid AI v1.0.0<br>
                    © 2026 District Health Administration
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    """Main application entry point."""
    # Step 1: Load custom CSS
    _load_css()

    # Step 2: Initialize session state
    _init_session_state()

    # Step 3: Initialize database
    _init_database()

    # Step 4: Build navigation and get selected page
    pg = _build_navigation()

    # Step 5: Render sidebar for authenticated users
    _render_sidebar()

    # Step 6: Run the selected page
    pg.run()


if __name__ == "__main__":
    main()
