"""
CareGrid AI — Login Page
==========================
Professional login page with glass-card styling, logo,
authentication, and demo credentials hint.
"""

import streamlit as st
from pathlib import Path

# ── Service imports ──
try:
    from services.auth_service import AuthService
    _AUTH_SERVICE_AVAILABLE = True
except ImportError:
    _AUTH_SERVICE_AVAILABLE = False

try:
    from utils.auth import login_user, is_authenticated
    _AUTH_UTILS_AVAILABLE = True
except ImportError:
    _AUTH_UTILS_AVAILABLE = False

try:
    from utils.translator import t
except ImportError:
    def t(key: str, **kwargs) -> str:
        return key

# ── Redirect if already authenticated ──
if st.session_state.get("authenticated"):
    st.switch_page("pages/2_Dashboard.py")

def _fallback_authenticate(username: str, password: str) -> dict | None:
    """Fallback authentication when AuthService is unavailable."""
    demo_users = {
        "admin": {
            "password": "admin123",
            "username": "admin",
            "full_name": "District Administrator",
            "role": "District Administrator",
            "facility_id": None,
        },
        "staff": {
            "password": "staff123",
            "username": "staff",
            "full_name": "Facility Staff",
            "role": "Facility Staff",
            "facility_id": 1,
        },
    }
    user = demo_users.get(username)
    if user and user["password"] == password:
        return {k: v for k, v in user.items() if k != "password"}
    return None

def _do_login(username: str, password: str) -> bool:
    """Attempt login via AuthService or fallback."""
    user_data = None

    if _AUTH_SERVICE_AVAILABLE:
        try:
            user_data = AuthService.authenticate(username, password)
        except Exception:
            user_data = _fallback_authenticate(username, password)
    else:
        user_data = _fallback_authenticate(username, password)

    if user_data:
        if _AUTH_UTILS_AVAILABLE:
            login_user(st.session_state, user_data)
        else:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_data
            st.session_state["user_role"] = user_data.get("role")
            st.session_state["user_facility_id"] = user_data.get("facility_id")
        return True
    return False

# ---------------------------------------------------------------------------
# GLOBAL CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Completely hide Streamlit headers */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppHeader"] { display: none !important; }
    header { display: none !important; }

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        background: #f1f5f9;
        font-family: 'Inter', sans-serif !important;
    }

    /* Main Container setup */
    [data-testid="stAppViewBlockContainer"] {
        padding: 4rem 2rem !important;
        max-width: 1100px !important;
        margin: auto !important;
    }

    /* Left Brand Card */
    .brand-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0284c7 100%);
        color: white;
        border-radius: 24px;
        padding: 3rem 2.5rem;
        height: 100%;
        min-height: 500px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }

    .brand-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 2rem;
    }

    .brand-logo-icon {
        font-size: 1.8rem;
        background: rgba(255, 255, 255, 0.12);
        padding: 6px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .brand-name {
        font-size: 1.4rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .brand-name span {
        color: #38bdf8;
    }

    .brand-subtitle {
        font-size: 0.8rem;
        color: #93c5fd;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.25;
        margin-bottom: 1rem;
    }

    .hero-title span {
        color: #38bdf8;
    }

    .hero-description {
        font-size: 0.9rem;
        color: #cbd5e1;
        line-height: 1.6;
        margin-bottom: 2rem;
    }

    /* Features list */
    .feature-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 1.2rem;
    }

    .feature-icon {
        font-size: 1.2rem;
        background: rgba(255, 255, 255, 0.12);
        padding: 6px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 32px;
    }

    .feature-content {
        display: flex;
        flex-direction: column;
    }

    .feature-title {
        font-weight: 700;
        font-size: 0.9rem;
    }

    .feature-text {
        font-size: 0.75rem;
        color: #cbd5e1;
    }

    .illustration {
        margin-top: 1.5rem;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px dashed rgba(255, 255, 255, 0.2);
        text-align: center;
        padding: 1.5rem;
    }
    
    .illustration-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    .illustration-cap {
        font-size: 0.8rem;
        color: #93c5fd;
    }

    /* Right Login Form (stForm styling) */
    div[data-testid="stForm"] {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 24px !important;
        padding: 2.5rem !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02) !important;
    }

    .login-header-section {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 2rem;
    }

    .login-welcome-row {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .login-welcome-icon {
        font-size: 1.8rem;
        background: #eff6ff;
        padding: 6px 12px;
        border-radius: 12px;
        color: #2563eb;
    }

    .login-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a;
    }

    .login-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 0.25rem;
    }

    .lang-pill {
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: #475569;
        font-weight: 500;
        background: #f8fafc;
    }

    /* Custom Form Labels */
    .field-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: #334155;
        margin-bottom: 0.5rem;
        margin-top: 1.2rem;
    }

    /* Inputs styling */
    div[data-testid="stTextInput"] input {
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 10px 14px !important;
        font-size: 0.9rem !important;
        background: #f8fafc !important;
        color: #0f172a !important; /* Force input text to be dark and visible */
        transition: all 0.2s !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #2563eb !important;
        background: white !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
        color: #0f172a !important;
    }

    /* Submit Button styling */
    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 10px 0 !important;
        border: none !important;
        width: 100% !important;
        transition: all 0.2s !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2) !important;
        margin-top: 1rem;
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3) !important;
    }

    /* Secondary button styling */
    .admin-btn-container div[data-testid="stButton"] button {
        background: #eff6ff !important;
        color: #1d4ed8 !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        padding: 10px 0 !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }

    .admin-btn-container div[data-testid="stButton"] button:hover {
        background: #dbeafe !important;
    }

    .divider {
        display: flex;
        align-items: center;
        text-align: center;
        color: #94a3b8;
        font-size: 0.75rem;
        margin: 1.2rem 0;
    }

    .divider::before, .divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid #e2e8f0;
    }

    .divider:not(:empty)::before { margin-right: .5em; }
    .divider:not(:empty)::after { margin-left: .5em; }

    /* Credentials and badges */
    .demo-creds {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px;
        font-size: 0.75rem;
        color: #334155; /* Darker grey for better accessibility and readability */
        text-align: center;
        margin-top: 1.2rem;
    }

    .demo-creds strong {
        color: #0f172a;
    }

    .secure-badge {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-size: 0.75rem;
        color: #059669;
        background: #ecfdf5;
        padding: 8px 12px;
        border-radius: 10px;
        margin-top: 1rem;
        font-weight: 600;
        border: 1px solid #a7f3d0;
    }
</style>
""", unsafe_allow_html=True)

# ── Split layout using native Streamlit columns ──
col1, col2 = st.columns([6, 6], gap="large")

with col1:
    st.html(f"""
    <div class="brand-card">
        <div>
            <div class="brand-header">
                <div class="brand-logo-icon">🏥</div>
                <div>
                    <div class="brand-name">CareGrid <span>AI</span></div>
                    <div class="brand-subtitle">Intelligent Healthcare Management</div>
                </div>
            </div>
            
            <div class="hero-title">Smarter Insights.<br>Stronger <span>Healthcare.</span></div>
            <div class="hero-description">
                CareGrid AI empowers administrators to monitor, analyze and optimize 
                healthcare operations across all PHCs & CHCs in real-time.
            </div>
            
            <div class="feature-item">
                <div class="feature-icon">📈</div>
                <div class="feature-content">
                    <div class="feature-title">Real-time Monitoring</div>
                    <div class="feature-text">Live data from all facilities</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">💊</div>
                <div class="feature-content">
                    <div class="feature-title">Stock Intelligence</div>
                    <div class="feature-text">Predict, prevent & optimize</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🤖</div>
                <div class="feature-content">
                    <div class="feature-title">AI-Powered Insights</div>
                    <div class="feature-text">Smart recommendations</div>
                </div>
            </div>
        </div>
        
        <div class="illustration">
            <div class="illustration-icon">🏥</div>
            <div class="illustration-cap">Primary Health Centre Network</div>
        </div>
    </div>
    """)

with col2:
    with st.form("login_form", clear_on_submit=False):
        # Card Header
        st.html(f"""
        <div class="login-header-section">
            <div class="login-welcome-row">
                <div class="login-welcome-icon">🛡️</div>
                <div>
                    <div class="login-title">{t("auth.title", default="Welcome Back!")}</div>
                    <div class="login-subtitle">{t("auth.subtitle", default="Sign in to your CareGrid AI account")}</div>
                </div>
            </div>
        </div>
        """)

        # Username Input
        st.html(f'<div class="field-label">{t("auth.username", default="Username")}</div>')
        username = st.text_input(
            t("auth.username", default="Username"),
            placeholder="Enter your username",
            label_visibility="collapsed",
        )

        # Password Input
        st.html(f'<div class="field-label">{t("auth.password", default="Password")}</div>')
        password = st.text_input(
            t("auth.password", default="Password"),
            type="password",
            placeholder="Enter your password",
            label_visibility="collapsed",
        )

        # Submit
        submitted = st.form_submit_button("➜  " + t("auth.login_button", default="Sign In"), use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                with st.spinner("Authenticating..."):
                    if _do_login(username, password):
                        st.success(t("auth.login_success", default="Login successful! Redirecting..."))
                        st.rerun()
                    else:
                        st.error(t("auth.login_failed", default="Invalid username or password. Please try again."))

    st.html(f"""
    <div class="demo-creds">
        <div style="margin-bottom: 4px;"><strong>Demo Credentials</strong></div>
        <span><strong>Admin:</strong> admin / admin123 &nbsp;|&nbsp; <strong>Staff:</strong> staff / staff123</span>
    </div>
    
    <div class="secure-badge">
        <span>🛡️ Secure • Reliable • Intelligent</span>
    </div>
    """)