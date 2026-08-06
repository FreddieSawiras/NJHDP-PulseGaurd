import os
import json
from urllib.parse import quote
import streamlit as st
import streamlit.components.v1 as components
import random
import time
import io
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from google import genai
from google.genai import errors as genai_errors

# --------------------------------------------------
# Safe secrets getter — st.secrets normally behaves like a dict, but if
# no secrets.toml exists at all (common on a fresh local checkout or a
# fresh deploy before secrets are added), some Streamlit versions raise
# instead of just returning the default from .get(). This wrapper makes
# every secrets lookup in the app crash-proof either way.
def _secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

# --------------------------------------------------
# Gemini model configuration
# Get a free API key from https://aistudio.google.com/apikey
#
# GEMINI_API_KEY_SOURCE tracks whether the key came from an environment
# variable or st.secrets (not surfaced in the UI — kept only in case
# it's useful for local debugging).
GEMINI_MODEL = (_secret("GEMINI_MODEL", "gemini-3.6-flash") or "").strip() or "gemini-3.6-flash"

_env_key = os.getenv("GEMINI_API_KEY")
_secrets_key = _secret("GEMINI_API_KEY", None)
if _env_key:
    GEMINI_API_KEY = _env_key.strip()
    GEMINI_API_KEY_SOURCE = "environment variable"
elif _secrets_key:
    GEMINI_API_KEY = _secrets_key.strip()
    GEMINI_API_KEY_SOURCE = "st.secrets"
else:
    GEMINI_API_KEY = None
    GEMINI_API_KEY_SOURCE = "not set"


# Scopes needed to call Vertex AI with a service account. Separate from
# AUTH_SCOPES (Sheets/Drive) below since Vertex needs cloud-platform access
# instead — same service account JSON, different scope grant.
VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _get_vertex_config():
    """Build (project, location, credentials) for Vertex AI from the same
    gcp_service_account secret already used for the Google Sheets
    integration, if one is configured. Returns None (never raises) if it
    can't be built, so callers can cleanly fall back to the API-key path.
    """
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except Exception:
        return None
    project = creds_dict.get("project_id")
    if not project:
        return None
    location = (_secret("GEMINI_VERTEX_LOCATION", "us-central1") or "us-central1").strip()
    try:
        from google.oauth2.service_account import Credentials as _SACredentials
        creds = _SACredentials.from_service_account_info(creds_dict, scopes=VERTEX_SCOPES)
    except Exception:
        return None
    return project, location, creds


@st.cache_resource
def get_gemini_client():
    """Create (once) and cache the Gemini client for the app's lifetime.

    Prefers Vertex AI, authenticated with the same Google service account
    already used for Sheets. That path uses a short-lived OAuth2 access
    token rather than an AI-Studio API key, which sidesteps the ongoing
    "AQ." key / ACCESS_TOKEN_TYPE_UNSUPPORTED issue entirely (it only
    affects generativelanguage.googleapis.com API-key auth, not Vertex's
    aiplatform.googleapis.com with OAuth2 credentials).

    Requires the service account to have the "Vertex AI User"
    (roles/aiplatform.user) IAM role on the project, and the Vertex AI
    API enabled on that project. Falls back to the plain API-key client
    (GEMINI_API_KEY) if Vertex can't be configured or fails to build —
    so nothing breaks for setups that only have an API key.
    """
    vertex_config = _get_vertex_config()
    if vertex_config is not None:
        project, location, creds = vertex_config
        try:
            return genai.Client(vertexai=True, project=project, location=location, credentials=creds)
        except Exception:
            pass  # fall through to the API-key client below

    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def _friendly_gemini_error(exc):
    """Turn raw Gemini API errors into something actionable instead of a
    dumped JSON blob. Special-cased for ACCESS_TOKEN_TYPE_UNSUPPORTED,
    which as of mid-2026 is a known, ongoing issue with newly-issued
    'AQ.' format API keys being rejected server-side by Google — not
    something fixable from the app's code. See:
    https://ai.google.dev/gemini-api/docs/api-key"""
    text = str(exc)
    if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in text:
        return (
            "Gemini rejected the request (401 ACCESS_TOKEN_TYPE_UNSUPPORTED). "
            "This is a known, currently-open issue on Google's side affecting "
            "newly issued 'AQ.' format API keys — it isn't something in this "
            "app's code. If gcp_service_account is set in secrets (used for "
            "Sheets), the app will now automatically use Vertex AI with that "
            "service account instead of the API key — just make sure it has "
            "the 'Vertex AI User' role and the Vertex AI API is enabled on "
            "the project. Otherwise, try restricting the key to 'Gemini API "
            "only' in AI Studio, or file a report at "
            "https://ai.google.dev/gemini-api/docs/api-key."
        )
    return text

# --------------------------------------------------
# Email alert configuration — used to proactively email the user when an
# anomaly is detected, instead of only surfacing it in-app. Uses plain
# SMTP (Gmail by default) instead of Twilio, since that needs zero
# compliance profile, zero ID verification, and zero cost.
#
# Setup (Gmail):
#   1. Turn on 2-Step Verification on the Gmail account you'll send from:
#      myaccount.google.com/security
#   2. Create an "App Password" at myaccount.google.com/apppasswords
#      (choose "Mail" as the app) — this gives you a 16-character code,
#      NOT your normal Gmail password.
#   3. Add to st.secrets:
#        ALERT_EMAIL_ADDRESS = "youraccount@gmail.com"
#        ALERT_EMAIL_APP_PASSWORD = "xxxxxxxxxxxxxxxx"
# Any other provider works too — just change ALERT_SMTP_HOST/PORT below.
# --------------------------------------------------
import smtplib
from email.mime.text import MIMEText

ALERT_EMAIL_ADDRESS = _secret("ALERT_EMAIL_ADDRESS", None)
ALERT_EMAIL_APP_PASSWORD = _secret("ALERT_EMAIL_APP_PASSWORD", None)
ALERT_SMTP_HOST = _secret("ALERT_SMTP_HOST", "smtp.gmail.com")
ALERT_SMTP_PORT = int(_secret("ALERT_SMTP_PORT", 587))


def email_alerts_configured():
    return bool(ALERT_EMAIL_ADDRESS and ALERT_EMAIL_APP_PASSWORD)


def send_sms_alert(to_email, message):
    """Send a proactive alert via email. Named send_sms_alert for
    continuity with the rest of the app, but it sends over SMTP email —
    no Twilio account, no compliance profile, no ID required."""
    if not email_alerts_configured():
        return False, "Email alerts aren't configured (missing secrets — see setup notes above)."
    if not to_email:
        return False, "No email address on file."
    try:
        msg = MIMEText(message[:5000])
        msg["Subject"] = "PulseGuard Alert"
        msg["From"] = ALERT_EMAIL_ADDRESS
        msg["To"] = to_email
        with smtplib.SMTP(ALERT_SMTP_HOST, ALERT_SMTP_PORT) as server:
            server.starttls()
            server.login(ALERT_EMAIL_ADDRESS, ALERT_EMAIL_APP_PASSWORD)
            server.sendmail(ALERT_EMAIL_ADDRESS, [to_email], msg.as_string())
        return True, None
    except Exception as exc:
        return False, str(exc)

# --------------------------------------------------
# Set up page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="PulseGuard — Heart Health Intelligence",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_URL = "https://plain-enam-prod-public.komododecks.com/202607/27/VZS1Q3WWHJ5eZyOEZXiM/image.png"

# ==========================================================
# GOOGLE SHEETS AUTH — username | password_hash | email | created_at
# ==========================================================
import hashlib
import gspread
from google.oauth2.service_account import Credentials

AUTH_SHEET_NAME = "PulseGuard_Users"
AUTH_WORKSHEET_NAME = "Sheet1"
AUTH_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_auth_worksheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=AUTH_SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(AUTH_SHEET_NAME)
    return sheet.worksheet(AUTH_WORKSHEET_NAME)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_all_users(worksheet):
    return {row["username"]: row for row in worksheet.get_all_records()}


def _create_user(worksheet, username, password, email=""):
    worksheet.append_row([
        username,
        _hash_password(password),
        email,
        datetime.now(ZoneInfo("America/New_York")).isoformat(),
    ])


def _verify_login(worksheet, username, password):
    user = _get_all_users(worksheet).get(username)
    return bool(user) and user["password_hash"] == _hash_password(password)


def _username_exists(worksheet, username):
    return username in _get_all_users(worksheet)


# ==========================================================
# GOOGLE SHEETS USER DATA — persists each user's dashboard data
# (BPM, HRV, steps, history, etc.) so it's the same on any device.
# Stored as one row per user in a second worksheet:
#   username | data_json | updated_at
# ==========================================================
USERDATA_WORKSHEET_NAME = "UserData"

# Which session_state keys count as "this user's data" and get
# saved/restored. UI-only state (current page, loader flags, etc.)
# is intentionally left out.
PERSIST_KEYS = [
    "heart_rate", "resting_hr", "hrv", "blood_pressure_variability",
    "heart_rate_recovery", "sleep_quality", "steps", "battery",
    "hydration_oz", "streak_days", "logged_symptoms", "meds_state",
    "patient_name", "patient_age", "selected_watch", "connected_since",
    "trend_data", "full_history", "activity_feed", "chat_history",
    "weekly_story", "alert_email", "sms_alerts_enabled", "emergency_contact_email",
    "symptom_risk_adjustment", "symptom_risk_note", "symptom_check_at",
    "is_subscribed",
]


@st.cache_resource
def get_userdata_worksheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=AUTH_SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(AUTH_SHEET_NAME)
    try:
        return sheet.worksheet(USERDATA_WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=USERDATA_WORKSHEET_NAME, rows=1000, cols=3)
        ws.append_row(["username", "data_json", "updated_at"])
        return ws


def _load_user_data(worksheet, username):
    """Return the saved dict of session data for this user, or None."""
    try:
        cell = worksheet.find(username, in_column=1)
    except gspread.exceptions.CellNotFound:
        return None
    if not cell:
        return None
    row = worksheet.row_values(cell.row)
    if len(row) < 2 or not row[1]:
        return None
    try:
        return json.loads(row[1])
    except (json.JSONDecodeError, TypeError):
        return None


def _save_user_data(worksheet, username, data: dict):
    """Upsert this user's row with their latest data as JSON."""
    payload = json.dumps(data, default=str)
    now = datetime.now(ZoneInfo("America/New_York")).isoformat()
    try:
        cell = worksheet.find(username, in_column=1)
    except gspread.exceptions.CellNotFound:
        cell = None
    if cell:
        worksheet.update(f"B{cell.row}:C{cell.row}", [[payload, now]])
    else:
        worksheet.append_row([username, payload, now])


# ==========================================================
# GOOGLE SHEETS SURVEY — feedback survey responses, one row per
# submission, in their own worksheet tab of the same spreadsheet:
#   username | q1_easy_to_use | q2_favorite_feature | q3_missing_feature |
#   q4_recommend | free_text | submitted_at
# ==========================================================
SURVEY_WORKSHEET_NAME = "Survey"
SURVEY_HEADER_ROW = [
    "username", "q1_easy_to_use", "q2_favorite_feature",
    "q3_missing_feature", "q4_recommend", "free_text", "submitted_at",
]


@st.cache_resource
def get_survey_worksheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=AUTH_SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(AUTH_SHEET_NAME)
    try:
        return sheet.worksheet(SURVEY_WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(
            title=SURVEY_WORKSHEET_NAME, rows=1000, cols=len(SURVEY_HEADER_ROW)
        )
        ws.append_row(SURVEY_HEADER_ROW)
        return ws


def _save_survey_response(worksheet, username, answers: dict, free_text: str):
    """Append one row for this survey submission. Multiple submissions
    per user are allowed (each is its own row)."""
    worksheet.append_row([
        username or "guest",
        answers.get("q1_easy_to_use", ""),
        answers.get("q2_favorite_feature", ""),
        answers.get("q3_missing_feature", ""),
        answers.get("q4_recommend", ""),
        free_text or "",
        datetime.now(ZoneInfo("America/New_York")).isoformat(),
    ])


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "auth_username" not in st.session_state:
    st.session_state.auth_username = None
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "survey_submitted" not in st.session_state:
    st.session_state.survey_submitted = False
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False


def render_login_gate():
    st.markdown("""
        <style>
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #071722 !important;
            }
            section[data-testid="stSidebar"], header[data-testid="stHeader"] { display: none !important; }
            .pg-login-wrap { max-width: 440px; margin: 6vh auto 0 auto; text-align: center; }
            .pg-login-logo { width: 56px; height: 56px; border-radius: 14px; margin-bottom: 14px;
                box-shadow: 0 24px 60px rgba(76, 155, 191,0.2); }
            .pg-login-title { font-family: Inter, sans-serif; font-size: 30px; font-weight: 800;
                color: #F4FBFF; letter-spacing: -0.01em; margin-bottom: 4px; }
            .pg-login-sub { font-family: Inter, sans-serif; color: #8FB0C1; margin-bottom: 28px; font-size: 14px; }

            /* Buttons and text inputs on this page render before the site's
               main CSS block (further down app.py) ever executes, since
               render_login_gate() calls st.stop() first. Re-declare the same
               dark styling here so Guest/Log in/Sign up buttons and the
               username/password boxes match the rest of the site instead of
               falling back to Streamlit's default white theme. */
            .stButton > button, div.stFormSubmitButton > button {
                border-radius: 12px !important;
                border: none !important;
                background: linear-gradient(135deg, rgba(14, 34, 48,0.92), rgba(11, 28, 40,0.92)) !important;
                color: #F4FBFF !important;
                font-weight: 600 !important;
                font-size: 13.5px !important;
                padding: 0.6rem 1.1rem !important;
                transition: transform 0.18s ease, box-shadow 0.18s ease !important;
                box-shadow: 0 6px 18px rgba(3, 17, 13,0.6) !important;
            }
            .stButton > button:hover, div.stFormSubmitButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 10px 26px rgba(76, 155, 191,0.18) !important;
            }
            input, textarea, select, .stTextInput>div>div>input {
                background: rgba(14, 34, 48, 0.78) !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                color: #F4FBFF !important;
                padding: 10px 12px !important;
                border-radius: 10px !important;
                outline: none !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
            }
            input::placeholder, textarea::placeholder { color: rgba(244, 251, 255,0.55) !important; }
            input:focus, textarea:focus, select:focus, .stTextInput>div>div>input:focus {
                box-shadow: 0 0 28px rgba(245, 158, 11,0.14), 0 0 8px rgba(76, 155, 191,0.08) !important;
                border-color: rgba(255, 107, 107,0.2) !important;
            }
            div[data-baseweb="input"],
            div[data-baseweb="select"] > div,
            div[data-testid="stTextInput"] > div > div,
            div[data-testid="stSelectbox"] > div > div {
                background-color: rgba(14, 34, 48, 0.78) !important;
                border: 1px solid rgba(255, 255, 255, 0.12) !important;
                border-radius: 10px !important;
                color: #EAF7F0 !important;
            }
            div[data-baseweb="input"] input,
            div[data-baseweb="select"] input {
                color: #EAF7F0 !important;
                background-color: transparent !important;
            }
            /* Tabs (Log in / Sign up) — match the lit-up pill treatment
               used for tabs and toggles elsewhere on the site. */
            div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
                background: rgba(255, 255, 255, 0.05) !important;
                padding: 6px !important;
                border-radius: 999px !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                gap: 4px !important;
                width: fit-content !important;
                margin: 0 auto !important;
            }
            div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
            div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
                display: none !important;
            }
            div[data-testid="stTabs"] button[data-baseweb="tab"] {
                border-radius: 999px !important;
                padding: 8px 22px !important;
                color: #DCECF4 !important;
                font-weight: 700 !important;
                font-size: 12.5px !important;
                text-transform: uppercase !important;
                letter-spacing: 0.06em !important;
                background: transparent !important;
                transition: all 0.25s ease !important;
                border: none !important;
            }
            div[data-testid="stTabs"] button[data-baseweb="tab"] p { color: inherit !important; }
            div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
                color: #4C9BBF !important;
                background: rgba(76, 155, 191, 0.08) !important;
            }
            div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
                background: rgba(76, 155, 191, 0.15) !important;
                color: #4C9BBF !important;
                box-shadow: 0 0 20px rgba(76, 155, 191, 0.15), inset 0 0 0 1px rgba(76, 155, 191, 0.3) !important;
            }
        </style>
        <div class="pg-login-wrap">
            <img src="{logo}" class="pg-login-logo" />
            <div class="pg-login-title">PulseGuard</div>
            <div class="pg-login-sub">Sign in to access your heart health dashboard</div>
        </div>
    """.replace("{logo}", LOGO_URL), unsafe_allow_html=True)

    # --------------------------------------------------
    # Guest mode: skip Google Sheets auth entirely so you can jump
    # straight into the dashboard without creating an account.
    # --------------------------------------------------
    gcol1, gcol2, gcol3 = st.columns([1, 1.3, 1])
    with gcol2:
        if st.button("👤 Continue as Guest", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.auth_username = "Guest"
            st.session_state.is_guest = True
            st.rerun()
        st.markdown(
            "<div style='text-align:center; color:#66807A; font-size:12px; margin:14px 0;'>"
            "or sign in below to save your data across visits</div>",
            unsafe_allow_html=True
        )

    try:
        worksheet = get_auth_worksheet()
    except Exception as e:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error(
                "Could not connect to the Google Sheet database. Check that "
                "st.secrets['gcp_service_account'] is configured and the sheet "
                "is shared with the service account."
            )
            st.exception(e)
        st.stop()

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            with st.form("pg_login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", use_container_width=True)
                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    elif _verify_login(worksheet, username, password):
                        st.session_state.logged_in = True
                        st.session_state.auth_username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_signup:
            with st.form("pg_signup_form"):
                new_username = st.text_input("Choose a username")
                new_email = st.text_input("Email (optional)")
                new_password = st.text_input("Choose a password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Sign up", use_container_width=True)
                if submitted:
                    if not new_username or not new_password:
                        st.error("Username and password are required.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif _username_exists(worksheet, new_username):
                        st.error("That username is already taken.")
                    else:
                        _create_user(worksheet, new_username, new_password, new_email)
                        st.success("Account created! You can now log in from the Log in tab.")

    st.stop()


if "boot_loader_shown" not in st.session_state:
    st.session_state.boot_loader_shown = False

if not st.session_state.boot_loader_shown:
    st.markdown(
        """
        <style>
        @keyframes pulseguardBootFadeOut {
            from { opacity: 1; visibility: visible; }
            to { opacity: 0; visibility: hidden; }
        }
        #pulseguard-boot-loader {
            position: fixed;
            inset: 0;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(7, 17, 13, 0.98);
            animation: pulseguardBootFadeOut 0.8s ease 5.2s forwards;
        }
        .pulseguard-boot-loader-inner {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .pulseguard-boot-loader-logo {
            width: 64px;
            height: 64px;
            border-radius: 18px;
            box-shadow: 0 24px 60px rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .pulseguard-boot-loader-text {
            color: #EAF7F0;
            font-family: Inter, sans-serif;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 0.02em;
            text-shadow: 0 0 18px rgba(16, 185, 129,0.15);
        }
        .pulseguard-boot-loader-subtext {
            color: #9AB0A5;
            font-family: Inter, sans-serif;
            font-size: 14px;
            margin-top: 6px;
        }
        </style>
        <div id="pulseguard-boot-loader">
            <div class="pulseguard-boot-loader-inner">
                <img src=\""""
        + LOGO_URL
        + """\" class="pulseguard-boot-loader-logo" />
                <div>
                    <div class="pulseguard-boot-loader-text">Welcome to PulseGuard</div>
                    <div class="pulseguard-boot-loader-subtext">Your road to a healthier heart starts here</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.session_state.boot_loader_shown = True

if not st.session_state.logged_in:
    render_login_gate()

# --------------------------------------------------
# Restore this user's saved data (BPM, HRV, history, etc.)
# so it carries over across devices/sessions. Runs once per
# session, right after login and before any defaults are set,
# so restored values aren't overwritten by fresh random defaults.
# Guests don't have an account to save to, so they always start fresh.
# --------------------------------------------------
if (
    st.session_state.logged_in
    and not st.session_state.is_guest
    and not st.session_state.get("user_data_loaded")
):
    try:
        _userdata_ws = get_userdata_worksheet()
        _saved_data = _load_user_data(_userdata_ws, st.session_state.auth_username)
        if _saved_data:
            for _k, _v in _saved_data.items():
                if _k in PERSIST_KEYS:
                    st.session_state[_k] = _v
    except Exception:
        # If the sheet is unreachable, fall back to fresh defaults
        # rather than blocking the user from using the app.
        pass
    st.session_state.user_data_loaded = True

loader_html = """
<style>
@keyframes pulseguardFadeOut {
    from { opacity: 1; visibility: visible; }
    to { opacity: 0; visibility: hidden; }
}
#pulseguard-loader {
    position: fixed;
    inset: 0;
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(7, 17, 13, 0.98);
    animation: pulseguardFadeOut 0.8s ease 4.3s forwards;
}
.pulseguard-loader-inner {
    display: flex;
    align-items: center;
    gap: 16px;
    transform: translate(0, 0) scale(1);
}
.pulseguard-loader-logo {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    box-shadow: 0 24px 60px rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(255,255,255,0.08);
}
.pulseguard-loader-text {
    color: #EAF7F0;
    font-family: Inter, sans-serif;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.02em;
    text-shadow: 0 0 18px rgba(16, 185, 129,0.15);
}
.pulseguard-loader-subtext {
    color: #9AB0A5;
    font-family: Inter, sans-serif;
    font-size: 14px;
    margin-top: 6px;
}
</style>
<div id="pulseguard-loader">
    <div class="pulseguard-loader-inner">
        <img src="{{LOGO_URL}}" class="pulseguard-loader-logo" />
        <div>
            <div class="pulseguard-loader-text">PulseGuard</div>
            <div class="pulseguard-loader-subtext">{{WELCOME_TEXT}}</div>
        </div>
    </div>
</div>
""".replace("{{LOGO_URL}}", LOGO_URL).replace(
    "{{WELCOME_TEXT}}",
    f"Welcome, {st.session_state.auth_username}!" if st.session_state.get("auth_username") else "Loading your heart intelligence..."
)

if "loader_shown" not in st.session_state:
    st.session_state.loader_shown = True

if st.session_state.loader_shown:
    st.markdown(loader_html, unsafe_allow_html=True)
    st.session_state.loader_shown = False

# --------------------------------------------------
# Safe HTML rendering patch
# --------------------------------------------------
_original_markdown = st.markdown

def _safe_markdown(body, *args, **kwargs):
    if kwargs.get("unsafe_allow_html") and isinstance(body, str):
        body = "\n".join(line.lstrip() for line in body.strip("\n").splitlines())
    return _original_markdown(body, *args, **kwargs)

st.markdown = _safe_markdown

# --------------------------------------------------
# Session state defaults
# --------------------------------------------------
_defaults = {
    "heart_rate": 72,
    "resting_hr": 61,
    "hrv": 55,
    "blood_pressure_variability": 5,
    "heart_rate_recovery": 27,
    "sleep_quality": 86,
    "steps": 6840,
    "battery": 87,
    "dark_mode": True,
    "autoplay": False,
    "scenario_idx": 0,
    "selected_watch": "⌚ Apple Watch",
    "hydration_oz": 48,
    "streak_days": 12,
    "logged_symptoms": [],
    "meds_state": {"BP Medication": True, "Omega-3": True, "Magnesium": False},
    "patient_name": "",
    "patient_age": 45,
    "weekly_story": None,
    "anomaly_alert_shown": False,
    "alert_email": "",
    "sms_alerts_enabled": False,
    "emergency_contact_email": "",
    "last_emergency_alert_date": None,
    "symptom_risk_adjustment": 0,
    "symptom_risk_note": None,
    "symptom_check_at": None,
    "last_sms_alert_date": None,
    "show_symptom_check": False,
}

for _key, _val in _defaults.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val


if "connected_since" not in st.session_state:
    fake_days_ago = random.randint(2, 45)
    st.session_state.connected_since = (
        datetime.now(ZoneInfo("America/New_York")) - timedelta(days=fake_days_ago)
    ).strftime("%B %d, %Y")

if "trend_data" not in st.session_state:
    st.session_state.trend_data = {
        "heart_rate": [random.randint(65, 85) for _ in range(6)],
        "sleep_quality": [random.randint(70, 95) for _ in range(6)],
        "steps": [random.randint(4000, 9000) for _ in range(6)],
    }

if "full_history" not in st.session_state:
    _history = {}
    for _i in range(30, 0, -1):
        _d = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=_i)).strftime("%Y-%m-%d")
        _history[_d] = {
            "heart_rate": random.randint(60, 105),
            "resting_hr": random.randint(50, 85),
            "hrv": random.randint(25, 85),
            "blood_pressure_variability": random.randint(1, 18),
            "heart_rate_recovery": random.randint(10, 38),
            "sleep_quality": random.randint(45, 98),
            "steps": random.randint(2000, 13000),
        }
    st.session_state.full_history = _history

if "activity_feed" not in st.session_state:
    st.session_state.activity_feed = [
        {"time": "10m ago", "event": "Telemetry synced from Apple Watch"},
        {"time": "1h ago", "event": "HRV baseline updated (+4 ms)"},
        {"time": "3h ago", "event": "Resting Heart Rate logged at 61 BPM"},
        {"time": "5h ago", "event": "Sleep analysis processed: 86% Quality"},
    ]

TIPS = [
    "💧 Staying hydrated helps regulate heart rate and blood pressure.",
    "😴 7-9 hours of consistent sleep supports a healthy heart rhythm.",
    "🚶 Even a 10-minute walk can improve circulation.",
    "🧂 Reducing sodium intake can help manage blood pressure over time.",
    "🧘 A few minutes of deep breathing can lower stress-related heart strain.",
    "🚭 Avoiding tobacco significantly reduces cardiovascular risk.",
    "🥗 A diet rich in fruits and vegetables supports long-term heart health.",
    "📅 Regular checkups help catch early warning signs.",
    "🏋️ Strength training a couple times a week supports cardiovascular fitness too.",
    "☕ Moderating caffeine can help reduce heart rate spikes for some people.",
]

if "tip_index" not in st.session_state:
    st.session_state.tip_index = datetime.now(ZoneInfo("America/New_York")).timetuple().tm_yday % len(TIPS)

# Clinical palette
UI_BG = "#071722"
UI_SURFACE = "#0E2230"
UI_SURFACE_ALT = "#133449"
TEXT_PRIMARY = "#F4FBFF"
TEXT_MUTED = "#8FB0C1"
UI_ACCENT = "#4C9BBF"
UI_ACCENT_DARK = "#2F7597"
HEART_PULSE = "#FF6B6B"
GOOD, WARN, DANGER = UI_ACCENT, "#F59E0B", "#EF4444"

SCENARIOS = [
    {
        "heart_rate": 68, "resting_hr": 58, "hrv": 72,
        "blood_pressure_variability": 4, "heart_rate_recovery": 30,
        "sleep_quality": 92, "steps": 11200, "battery": 91,
    },
    {
        "heart_rate": 104, "resting_hr": 79, "hrv": 28,
        "blood_pressure_variability": 16, "heart_rate_recovery": 14,
        "sleep_quality": 58, "steps": 3200, "battery": 46,
    },
    {
        "heart_rate": 88, "resting_hr": 70, "hrv": 38,
        "blood_pressure_variability": 9, "heart_rate_recovery": 18,
        "sleep_quality": 41, "steps": 5100, "battery": 63,
    },
]

WATCH_OPTIONS = {
    "⌚ Apple Watch": UI_ACCENT,
    "⌚ Samsung Galaxy Watch": "#F59E0B",
    "⌚ Google Pixel Watch": "#38BDF8",
    "⌚ Garmin": DANGER,
    "⌚ Fitbit": UI_ACCENT,
}

def hex_to_rgba(hex_color, alpha=0.2):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def score_color(score):
    if score >= 75:
        return GOOD
    elif score >= 50:
        return WARN
    else:
        return DANGER

def get_ai_system_prompt():
    return (
        "You are PulseGuard AI Assistant, a knowledgeable and empathetic health companion. "
        "Use only the available data from the user's current vitals and wearable telemetry. "
        "Provide clear, actionable guidance, but do not provide a medical diagnosis. "
        "Always remind the user that this is informational and that a clinician should confirm any clinical decisions. "
        "This is an ongoing conversation — do not re-introduce yourself or say hello again after the first message. "
        "Give complete answers; don't trail off mid-thought."
    )

def build_ai_context():
    score, _, _ = generate_health_summary(
        heart_rate=st.session_state.heart_rate,
        resting_hr=st.session_state.resting_hr,
        hrv=st.session_state.hrv,
        sleep_quality=st.session_state.sleep_quality,
        steps=st.session_state.steps,
        heart_rate_recovery=st.session_state.heart_rate_recovery,
        blood_pressure_variability=st.session_state.blood_pressure_variability,
    )
    trend_days = sorted(st.session_state.full_history.keys())[-7:]
    trend_summary = []
    for d in trend_days:
        day = st.session_state.full_history[d]
        trend_summary.append(
            f"{d}: HR {day['heart_rate']} BPM, RHR {day['resting_hr']} BPM, HRV {day['hrv']} ms, Sleep {day['sleep_quality']}%, Steps {day['steps']}"
        )

    return (
        "Current telemetry and trends:\n"
        f"- Heart rate: {st.session_state.heart_rate} BPM\n"
        f"- Resting heart rate: {st.session_state.resting_hr} BPM\n"
        f"- Heart rate variability (HRV): {st.session_state.hrv} ms\n"
        f"- Sleep quality: {st.session_state.sleep_quality}%\n"
        f"- Daily steps: {st.session_state.steps}\n"
        f"- Heart rate recovery: {st.session_state.heart_rate_recovery} BPM\n"
        f"- Blood pressure variability: {st.session_state.blood_pressure_variability} mmHg\n"
        f"- Computed heart score: {score}\n"
        "Recent 7-day trend summary:\n"
        + "\n".join(trend_summary)
    )

def get_ai_response(user_question, chat_history=None):
    system_prompt = get_ai_system_prompt()
    context = build_ai_context()

    client = get_gemini_client()
    if client is None:
        return (
            "Gemini is not configured. Please set GEMINI_API_KEY in your environment "
            "or Streamlit secrets to enable the Gemini Assistant."
        )

    # Build multi-turn contents so Gemini remembers the conversation instead
    # of treating every message as the first one.
    contents = []
    if chat_history:
        for role, content in chat_history:
            gemini_role = "user" if role == "user" else "model"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})

    # Attach the live telemetry context to the latest user turn so it always
    # has current numbers without repeating the full dump every message.
    contents.append(
        {"role": "user", "parts": [{"text": f"{context}\n\nUser question: {user_question}"}]}
    )

    base_config = {
        "system_instruction": system_prompt,
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }

    try:
        # Not every Gemini model version accepts thinking_config, so try with
        # it first (saves tokens for the visible answer) and fall back
        # cleanly to a plain request if the model rejects the field.
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config={**base_config, "thinking_config": {"thinking_budget": 0}},
            )
        except genai_errors.APIError as thinking_exc:
            if "INVALID_ARGUMENT" in str(thinking_exc) or getattr(thinking_exc, "code", None) == 400:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=base_config,
                )
            else:
                raise
        text = (response.text or "").strip()
        return text if text else "Gemini returned no response."
    except genai_errors.APIError as exc:
        return f"Gemini API request failed: {exc.message if hasattr(exc, 'message') else exc}"
    except Exception as exc:
        return f"Gemini request failed: {exc}"


def get_doctor_recommendation(score):
    """Translate the heart score into a plain-language doctor-visit
    recommendation, paired with the matching status color."""
    if score < 40:
        message = "Your heart score is quite low right now — we'd strongly recommend seeing a doctor as soon as you can. Download the PDF below and bring it with you."
    elif score < 50:
        message = "Your heart score suggests it's a good idea to see a doctor soon. Download the PDF below so they have your recent trends."
    elif score < 75:
        message = "Your heart score is in a borderline range — consider checking in with a doctor if this continues. Downloading the PDF below can help them see the full picture."
    else:
        message = "Your heart score looks strong right now, so a doctor visit isn't urgent. It's still good practice to download the PDF below and keep a record."
    return message, score_color(score)

# --------------------------------------------------
# Advanced Ultra-Premium CSS & Custom Theme Architecture
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --ui-bg: #071722;
    --ui-surface: #0E2230;
    --ui-surface-2: #133449;
    --ui-border: rgba(255,255,255,0.08);
    --text-primary: #F4FBFF;
    --text-muted: #8FB0C1;
    --accent: #4C9BBF;
    --accent-strong: #2F7597;
    --pulse: #FF6B6B;
    --warn: #F59E0B;
    --danger: #EF4444;
}

/* Base layout and typography */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--ui-bg) !important;
    background-image:
        radial-gradient(circle at 12% 12%, rgba(76, 155, 191, 0.12) 0%, transparent 38%),
        radial-gradient(circle at 88% 18%, rgba(255, 107, 107, 0.10) 0%, transparent 38%),
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px) !important;
    background-size: 100% 100%, 100% 100%, 28px 28px, 28px 28px !important;
    font-family: 'Inter', -apple-system, 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
}

/* Headings & hierarchy */
h1, h2, h3, .navbar-title, .glass-card h2, .glass-card h3 {
    font-family: 'Inter', 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text-primary) !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
}
h1 { font-size: 28px; }
h2 { font-size: 22px; }
h3 { font-size: 18px; }

/* Subtitles and captions */
.caption, .stCaption, .glass-card .caption { color: var(--text-muted) !important; font-weight:500 !important; }

section[data-testid="stSidebar"], [data-testid="collapsedControl"], header[data-testid="stHeader"] {
    display: none !important;
}

.stMainBlockContainer {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* Force Navigation Columns to Stretch Equally */
div[data-testid="stHorizontalBlock"]:has(button[key^="nav_"]) {
    display: flex !important;
    gap: 8px !important;
    width: 100% !important;
}

div[data-testid="stHorizontalBlock"]:has(button[key^="nav_"]) > div[data-testid="column"] {
    flex: 1 1 0px !important;
    min-width: 0 !important;
    width: auto !important;
}

div[data-testid="column"] button[key^="nav_"] {
    width: 100% !important;
    height: 46px !important;
    max-height: 46px !important;
    min-height: 46px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 8px !important;
    font-size: 12.5px !important;
    font-weight: 700 !important;
}

div[data-testid="column"] button[key^="nav_"] p {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    margin: 0 !important;
}

.glass-card {
    background: linear-gradient(180deg, rgba(14, 34, 48, 0.82), rgba(11, 28, 40, 0.74)) !important;
    backdrop-filter: blur(8px) saturate(120%) !important;
    -webkit-backdrop-filter: blur(8px) saturate(120%) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 18px !important;
    padding: 22px !important;
    box-shadow: 0 8px 30px rgba(2, 10, 16,0.55), inset 0 1px 0 rgba(255,255,255,0.02) !important;
    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.28s !important;
    position: relative;
    overflow: hidden;
}

/* Native Streamlit bordered container (st.container(border=True)) styled to
   match glass-card, so widgets that need real nesting (charts, radios, etc.)
   don't have to rely on the broken open/close-div markdown trick. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(14, 34, 48, 0.82), rgba(11, 28, 40, 0.74)) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 18px !important;
    box-shadow: 0 8px 30px rgba(2, 10, 16,0.55), inset 0 1px 0 rgba(255,255,255,0.02) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"],
div[data-testid="stRadio"],
div[role="radiogroup"],
div[role="radiogroup"] * {
    color: #D7EAE0 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"] label,
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] span,
div[data-testid="stRadio"] div[role="radiogroup"] label,
div[data-testid="stRadio"] div[role="radiogroup"] span,
div[data-testid="stRadio"] div[role="radiogroup"] button,
div[data-testid="stRadio"] button,
div[data-testid="stRadio"] button span,
div[data-testid="stRadio"] button div,
div[role="radiogroup"] label,
div[role="radiogroup"] span,
div[role="radiogroup"] button {
    color: #D7EAE0 !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

div[data-testid="stRadio"] label:hover,
div[data-testid="stRadio"] span:hover,
div[data-testid="stRadio"] button:hover,
div[role="radiogroup"] button:hover,
div[role="radiogroup"] label:hover,
div[role="radiogroup"] span:hover {
    color: var(--accent) !important;
}

div[data-testid="stRadio"] input:checked + label,
div[data-testid="stRadio"] input:checked + span,
div[data-testid="stRadio"] button[aria-checked="true"],
div[data-testid="stRadio"] button[aria-pressed="true"],
div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"],
div[role="radiogroup"] button[aria-checked="true"],
div[role="radiogroup"] button[aria-pressed="true"],
div[role="radiogroup"] label[aria-checked="true"] {
    color: var(--accent) !important;
}

/* "Lit up" selected state for the pill/tab-style radio toggles (Heart
   Dashboard's VITALS / 3D MODEL / ECG WAVEFORM, the 7-day/30-day trend
   toggle, etc.) so the active option glows the same way the active nav
   button and the login page's active tab do, instead of only changing
   text color. */
div[data-testid="stRadio"] button[aria-checked="true"],
div[data-testid="stRadio"] button[aria-pressed="true"],
div[role="radiogroup"] button[aria-checked="true"],
div[role="radiogroup"] button[aria-pressed="true"] {
    background: rgba(76, 155, 191, 0.16) !important;
    border: 1px solid rgba(76, 155, 191, 0.35) !important;
    border-radius: 999px !important;
    box-shadow: 0 0 20px rgba(76, 155, 191, 0.16), inset 0 0 0 1px rgba(76, 155, 191, 0.24) !important;
    transition: all 0.25s ease !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"],
div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] * {
    color: #D7EAE0 !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"],
div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"] * {
    color: var(--accent) !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"] {
    background: rgba(76, 155, 191, 0.16) !important;
    border-radius: 999px !important;
    box-shadow: 0 0 20px rgba(76, 155, 191, 0.16), inset 0 0 0 1px rgba(76, 155, 191, 0.24) !important;
    transition: all 0.25s ease !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] p {
    color: inherit !important;
}

.glass-card:hover {
    border-color: rgba(56, 189, 248,0.18) !important;
    box-shadow: 0 14px 40px rgba(7, 89, 133, 0.12), inset 0 1px 0 rgba(255,255,255,0.02) !important;
    transform: translateY(-4px) !important;
}

.metric-card-wrapper {
    background: rgba(13, 26, 20, 0.75);
    border-radius: 18px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    position: relative;
    transition: all 0.25s ease;
}

.metric-card-wrapper:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.2);
}

div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
    background: rgba(255, 255, 255, 0.05) !important;
    padding: 6px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    gap: 4px !important;
    width: fit-content !important;
}

div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
    display: none !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"] {
    border-radius: 999px !important;
    padding: 8px 22px !important;
    color: #D7EAE0 !important;
    font-weight: 700 !important;
    font-size: 12.5px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    background: transparent !important;
    transition: all 0.25s ease !important;
    border: none !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"] p {
    color: inherit !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    color: var(--accent) !important;
    background: rgba(76, 155, 191, 0.08) !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(76, 155, 191, 0.16) !important;
    color: var(--accent) !important;
    box-shadow: 0 0 20px rgba(76, 155, 191, 0.15), inset 0 0 0 1px rgba(76, 155, 191, 0.3) !important;
}

.heart-struct-card {
    background: rgba(14, 34, 48, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-left: 3px solid var(--accent);
    border-radius: 12px;
    padding: 14px 16px;
    height: 100%;
}
.heart-struct-title {
    color: var(--accent);
    font-weight: 800;
    font-size: 12.5px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.heart-struct-desc {
    color: #8FA69C;
    font-size: 12.5px;
    line-height: 1.5;
}

.metric-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8FA69C;
    margin-bottom: 6px;
}

.metric-value {
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #FFFFFF;
    font-family: 'Inter', 'Plus Jakarta Sans', sans-serif;
}

.top-navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 24px;
    background: rgba(14, 34, 48, 0.86);
    backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.navbar-title {
    font-size: 20px;
    font-weight: 800;
    background: linear-gradient(135deg, #FFFFFF 30%, #8FA69C 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
}

.pulse-dot {
    width: 8px;
    height: 8px;
    background-color: var(--pulse);
    border-radius: 50%;
    box-shadow: 0 0 12px var(--pulse);
    animation: pulseGlow 1.8s infinite;
}

@keyframes pulseGlow {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(255, 107, 107, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 107, 107, 0); }
}

.stButton > button {
    border-radius: 12px !important;
    border: none !important;
    background: linear-gradient(135deg, rgba(14, 34, 48,0.9), rgba(11, 28, 40,0.92)) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 0.6rem 1.1rem !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
    box-shadow: 0 6px 18px rgba(3, 17, 13,0.6) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 26px rgba(76, 155, 191,0.18) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent) 0%, var(--pulse) 100%) !important;
    color: #05131D !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 30px rgba(76, 155, 191,0.22) !important;
}

/* Base styles for global text inputs, select elements, containers */
input, textarea, select, .stTextInput>div>div>input, .stDateInput>div>div>input {
    background: rgba(13, 26, 20, 0.75) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #EAF7F0 !important;
    padding: 10px 12px !important;
    border-radius: 10px !important;
    outline: none !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
}

input::placeholder, textarea::placeholder {
    color: rgba(234, 247, 240,0.55) !important;
}

input:focus, textarea:focus, select:focus, .stTextInput>div>div>input:focus {
    box-shadow: 0 0 28px rgba(245, 158, 11,0.14), 0 0 8px rgba(16, 185, 129,0.08) !important;
    border-color: rgba(245, 158, 11,0.28) !important;
}

/* Universal Streamlit Input Box Styling Override (Fixes White Box Issue Globally) */
div[data-baseweb="input"], 
div[data-baseweb="select"] > div,
div[data-testid="stTextInput"] > div > div,
div[data-testid="stSelectbox"] > div > div {
    background-color: rgba(13, 26, 20, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    color: #EAF7F0 !important;
}

div[data-baseweb="input"] input, 
div[data-baseweb="select"] input {
    color: #EAF7F0 !important;
    background-color: transparent !important;
}

/* Chat input widget — Streamlit/BaseWeb wrap the textbox in several
   nested divs. Earlier we only styled two of those layers, which left
   an outer layer showing its default light-theme border/box-shadow as
   a white edge around the box. Reset every layer to transparent first,
   then explicitly re-apply the dark background only on the actual
   textbox wrapper (a more specific selector, so it still wins). */
div[data-testid="stChatInput"] *,
.stChatInput * {
    background-color: transparent !important;
    box-shadow: none !important;
    border-color: transparent !important;
}

div[data-testid="stChatInput"] div[data-baseweb="textarea"],
div[data-testid="stChatInput"] div[data-baseweb="input"],
div[data-testid="stChatInput"] div[data-baseweb="base-input"],
.stChatInput div[data-baseweb="textarea"],
.stChatInput div[data-baseweb="input"],
.stChatInput div[data-baseweb="base-input"] {
    background-color: rgba(13, 26, 20, 0.85) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
}

div[data-testid="stChatInput"] input,
div[data-testid="stChatInput"] textarea,
.stChatInput input,
.stChatInput textarea {
    background-color: transparent !important;
    border: none !important;
    color: #EAF7F0 !important;
}

div[data-testid="stChatInput"] div[data-baseweb="textarea"]:focus-within,
div[data-testid="stChatInput"] div[data-baseweb="input"]:focus-within {
    outline: none !important;
    box-shadow: none !important;
    border-color: rgba(76, 155, 191, 0.4) !important;
}

div[data-testid="stChatInput"] input::placeholder,
div[data-testid="stChatInput"] textarea::placeholder,
.stChatInput input::placeholder,
.stChatInput textarea::placeholder {
    color: rgba(234, 247, 240,0.55) !important;
}

/* The fixed footer bar that st.chat_input renders into defaults to
   Streamlit's light theme background, which shows up as a white strip
   (and white edge around the box itself) at the bottom of the AI
   Assistant tab. Force every wrapper level to match the app's dark
   background, and strip any default border/shadow on the footer. */
div[data-testid="stBottom"],
div[data-testid="stBottom"] *,
div[data-testid="stBottomBlockContainer"],
div[data-testid="stBottomBlockContainer"] *,
div[data-testid="stChatInputContainer"],
div[data-testid="stChatInputContainer"] *,
.stChatFloatingInputContainer,
.stChatFloatingInputContainer * {
    background: #071410 !important;
    background-color: #071410 !important;
    box-shadow: none !important;
    border-color: transparent !important;
}

div[data-testid="stBottom"] {
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Universal Streamlit Download Button Override */
div.stDownloadButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--pulse) 100%) !important;
    color: #05131D !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 0.6rem 1.1rem !important;
    box-shadow: 0 6px 30px rgba(56, 189, 248,0.25) !important;
    transition: all 0.2s ease !important;
}

div.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 35px rgba(76, 155, 191,0.28) !important;
}

.metric-title { color:#9AB0A5 !important; font-weight:700 !important; }
.metric-value, .vital-card-value { font-family: 'Inter', 'JetBrains Mono', monospace !important; }
.report-metric-value { font-family: 'Inter', 'JetBrains Mono', monospace !important; }

.progress-container {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    height: 10px;
    width: 100%;
    overflow: hidden;
    margin-top: 8px;
}
.progress-bar {
    height: 100%;
    border-radius: 10px;
    transition: width 0.4s ease;
}

.vital-card {
    background: linear-gradient(160deg, rgba(14, 26, 20, 0.85) 0%, rgba(10, 22, 17, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 20px 22px;
    height: 100%;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.vital-card:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.18);
}
.vital-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}
.vital-icon-badge {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
}
.vital-status-chip {
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 4px 10px;
    border-radius: 20px;
}
.vital-card-title {
    font-size: 12px;
    font-weight: 700;
    color: #8FA69C;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}
.vital-card-value {
    font-size: 26px;
    font-weight: 800;
    color: #FFFFFF;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 12px;
}
.vital-bar-track {
    width: 100%;
    height: 6px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.06);
    overflow: hidden;
    margin-bottom: 10px;
}
.vital-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.4s ease;
}
.vital-card-desc {
    font-size: 11.5px;
    color: #7A9088;
    line-height: 1.4;
}

.alert-banner {
    background: rgba(244, 63, 94, 0.15);
    border: 1px solid #F43F5E;
    border-radius: 16px;
    padding: 16px 20px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 0 25px rgba(244, 63, 94, 0.2);
}

.chat-bubble-user {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(245, 158, 11, 0.2));
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 18px 18px 2px 18px;
    padding: 14px 18px;
    color: #F0F7F2;
    margin-bottom: 12px;
    max-width: 80%;
    margin-left: auto;
}

.chat-bubble-ai {
    background: rgba(13, 26, 20, 0.8);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 18px 18px 18px 2px;
    padding: 14px 18px;
    color: #E2EDE6;
    margin-bottom: 12px;
    max-width: 85%;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

.trend-badge {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 12px;
    display: inline-block;
    margin-left: 6px;
}
.trend-up { background: rgba(76, 155, 191, 0.15); color: var(--accent); }
.trend-down { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
.trend-neutral { background: rgba(255, 255, 255, 0.1); color: var(--text-muted); }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def metric_status(kind, value):
    if kind == "heart_rate":
        if 60 <= value <= 100:
            return "Optimal", GOOD, 100
        elif 50 <= value < 60 or 100 < value <= 110:
            return "Elevated", WARN, 60
        else:
            return "Anomaly", DANGER, 30
    if kind == "resting_hr":
        if 50 <= value <= 80:
            return "Optimal", GOOD, 100
        elif 40 <= value < 50 or 80 < value <= 90:
            return "Elevated", WARN, 60
        else:
            return "High", DANGER, 30
    if kind == "hrv":
        if value >= 50:
            return "Optimal", GOOD, min(100, value)
        elif value >= 30:
            return "Moderate", WARN, 60
        else:
            return "Low Recovery", DANGER, 30
    if kind == "bp_variability":
        if value <= 10:
            return "Stable", GOOD, 100
        elif value <= 15:
            return "Moderate", WARN, 60
        else:
            return "High", DANGER, 30
    if kind == "recovery":
        if value >= 20:
            return "Optimal", GOOD, min(100, value * 2)
        elif value >= 15:
            return "Fair", WARN, 60
        else:
            return "Delayed", DANGER, 30
    if kind == "sleep":
        if value >= 80:
            return "Restful", GOOD, value
        elif value >= 60:
            return "Fair", WARN, value
        else:
            return "Restless", DANGER, value
    if kind == "steps":
        pct = min(100, value / 10000 * 100)
        if value >= 10000:
            return "Goal Met", GOOD, 100
        elif value >= 7500:
            return "Active", WARN, pct
        else:
            return "Below Goal", DANGER, pct
    return "Optimal", GOOD, 100

def render_metric_card(title, value_str, color, micro_insight="", trend_str="", trend_class="trend-neutral"):
    trend_html = f'<span class="trend-badge {trend_class}">{trend_str}</span>' if trend_str else ""
    st.markdown(
        f"""
        <div class="metric-card-wrapper" style="border-top: 3px solid {color};">
            <div class="metric-title">{title} {trend_html}</div>
            <div class="metric-value">{value_str}</div>
            <div style="font-size: 12px; color: #8FA69C; margin-top: 6px; line-height: 1.4;">
                {micro_insight}
            </div>
            <div style="position: absolute; top: 18px; right: 18px; width: 8px; height: 8px; border-radius: 50%; background: {color}; box-shadow: 0 0 10px {color};"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_vital_card(icon, title, value_str, status_label, color, pct, description):
    st.markdown(
        f"""
        <div class="vital-card">
            <div class="vital-card-top">
                <div class="vital-icon-badge" style="background:{hex_to_rgba(color, 0.14)}; border:1px solid {hex_to_rgba(color, 0.35)};">{icon}</div>
                <div class="vital-status-chip" style="background:{hex_to_rgba(color, 0.14)}; color:{color}; border:1px solid {hex_to_rgba(color, 0.35)};">{status_label}</div>
            </div>
            <div class="vital-card-title">{title}</div>
            <div class="vital-card-value">{value_str}</div>
            <div class="vital-bar-track"><div class="vital-bar-fill" style="width:{max(4, pct)}%; background:{color};"></div></div>
            <div class="vital-card-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_chips(items):
    html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">'
    for text, color in items:
        html += (
            f'<span style="background:{hex_to_rgba(color, 0.12)};'
            f'color:{color} !important;border:1px solid {hex_to_rgba(color, 0.3)};'
            f'padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600;">{text}</span>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_score_gauge(score):
    bar_color = score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'color': '#FFFFFF', 'size': 42, 'family': 'Plus Jakarta Sans'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': 'rgba(255,255,255,0.3)'},
            'bar': {'color': bar_color, 'thickness': 0.25},
            'bgcolor': "rgba(255,255,255,0.03)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 50], 'color': "rgba(244, 63, 94, 0.15)"},
                {'range': [50, 75], 'color': "rgba(251, 191, 36, 0.15)"},
                {'range': [75, 100], 'color': "rgba(16, 185, 129, 0.15)"},
            ],
        }
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True)

def render_ecg_animation(hr):
    html_code = f"""
    <div style="background: rgba(14, 34, 48, 0.86); border-radius: 16px; padding: 12px; border: 1px solid rgba(76, 155, 191, 0.24); box-shadow: inset 0 0 20px rgba(255, 107, 107,0.05);">
    <canvas id="ecgCanvas" width="900" height="130" style="width:100%; display:block;"></canvas>
    </div>
    <script>
    const canvas = document.getElementById("ecgCanvas");
    const ctx = canvas.getContext("2d");
    let offset = 0;
    const hr = {hr};
    const speedFactor = Math.max(0.4, hr / 70);

    function drawECG() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#FF6B6B";
        ctx.shadowBlur = 8;
        ctx.shadowColor = "#FF6B6B";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        const midY = canvas.height / 2;

        for (let x = 0; x < canvas.width; x++) {{
            const t = (x + offset) * 0.05 * speedFactor;
            let y = midY;
            const beatPos = t % 20;
            if (beatPos > 9 && beatPos < 9.5) y -= 12;
            else if (beatPos > 9.5 && beatPos < 10) y += 45;
            else if (beatPos > 10 && beatPos < 10.5) y -= 65;
            else if (beatPos > 10.5 && beatPos < 11) y += 18;
            else y += Math.sin(t) * 2;

            if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }}
        ctx.stroke();
        offset += 2.5 * speedFactor;
        requestAnimationFrame(drawECG);
    }}
    drawECG();
    </script>
    """
    components.html(html_code, height=155)

HEART_STRUCTURES = [
    {"title": "Aorta", "desc": "The main artery routing freshly oxygenated blood from the heart out to the rest of the body. Weakening or narrowing here (aneurysm or stenosis) can restrict blood flow to the whole body."},
    {"title": "Left Ventricle", "desc": "The heart's primary pumping chamber — thick, muscular, and responsible for sending blood to the entire body. Long-term high blood pressure or elevated heart rate can cause its walls to thicken (hypertrophy)."},
    {"title": "Right Atrium", "desc": "Receives deoxygenated blood returning from the body's veins before it's sent to the lungs. Irregular electrical signals starting here are a common trigger for atrial fibrillation."},
    {"title": "Coronary Artery", "desc": "Supplies oxygenated blood directly to the heart muscle itself, keeping the heart alive. Plaque buildup here (atherosclerosis) is the leading cause of heart attacks."},
    {"title": "Right Ventricle", "desc": "Pumps deoxygenated blood onward to the lungs via the pulmonary artery to be re-oxygenated. Chronic strain here can signal pulmonary hypertension or lung-related heart stress."},
    {"title": "SA Node", "desc": "The heart's natural pacemaker — a small cluster of cells that sets your resting heart rate. A sustained resting rate above 100 BPM (tachycardia) makes this node fire faster, forcing the heart to work harder than it should."},
    {"title": "Left Atrium", "desc": "Receives freshly oxygenated blood from the lungs before it moves to the left ventricle. It's especially vulnerable to atrial fibrillation, which raises stroke risk if untreated."},
    {"title": "Pulmonary Artery", "desc": "Carries deoxygenated blood from the right ventricle to the lungs. A blood clot lodging here (pulmonary embolism) is a medical emergency."},
    {"title": "Mitral Valve", "desc": "Controls blood flow between the left atrium and left ventricle. Its leaflets can leak (regurgitation) or stiffen and narrow (stenosis), both of which force the heart to work harder."},
    {"title": "Myocardium", "desc": "The thick muscular wall of the heart that does the actual pumping. Poor heart rate recovery after exertion often points to reduced cardiovascular fitness in this muscle."},
]

def render_heart_structure_reference():
    for row_start in range(0, len(HEART_STRUCTURES), 5):
        row_structs = HEART_STRUCTURES[row_start:row_start + 5]
        cols = st.columns(len(row_structs))
        for _col, _struct in zip(cols, row_structs):
            with _col:
                st.markdown(
                    f"""
                    <div class="heart-struct-card">
                        <div class="heart-struct-title">📍 {_struct['title']}</div>
                        <div class="heart-struct-desc">{_struct['desc']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

def render_3d_heart(hr=72, hrv=55, resting_hr=61, blood_pressure_variability=5, heart_rate_recovery=27):
    MODEL_URL = "https://cdn.jsdelivr.net/gh/FreddieSawiras/NJHDP-PulseGaurd@main/assets/scene.gltf"
    MODEL_URL_FALLBACK = "https://raw.githubusercontent.com/FreddieSawiras/NJHDP-PulseGaurd/main/assets/scene.gltf"

    # Pull live status/color for the data-tied hotspots so hovering them
    # reflects the person's actual current readings, not generic text.
    hr_label, hr_color, _ = metric_status("heart_rate", hr)
    hrv_label, hrv_color, _ = metric_status("hrv", hrv)
    bp_label, bp_color, _ = metric_status("bp_variability", blood_pressure_variability)
    recovery_label, recovery_color, _ = metric_status("recovery", heart_rate_recovery)

    if hr > 100:
        sa_node_desc = (
            f"Your natural pacemaker. Live reading: {hr} BPM ({hr_label}). Sustained rates above "
            f"100 BPM force the heart to work harder and, over time, can strain the heart muscle."
        )
    elif hr < 60:
        sa_node_desc = (
            f"Your natural pacemaker. Live reading: {hr} BPM ({hr_label}). Rates this low are normal for "
            f"very fit hearts, but if paired with dizziness they can signal the node is firing too slowly."
        )
    else:
        sa_node_desc = (
            f"Your natural pacemaker. Live reading: {hr} BPM ({hr_label}) — a healthy resting range that "
            f"keeps oxygen delivery efficient without overworking the heart."
        )

    if recovery_label in ("Fair", "Delayed"):
        myocardium_desc = (
            f"The thick muscular wall that does the actual pumping. Your heart rate recovery is "
            f"{heart_rate_recovery} BPM/min ({recovery_label}) — slower recovery after exertion can point "
            f"to reduced cardiovascular fitness in this muscle."
        )
    else:
        myocardium_desc = (
            f"The thick muscular wall that does the actual pumping. Your heart rate recovery of "
            f"{heart_rate_recovery} BPM/min ({recovery_label}) shows this muscle bouncing back efficiently after exertion."
        )

    def _js_color(hex_color):
        return "0x" + hex_color.lstrip("#")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body {{ margin: 0; height: 100%; overflow: hidden; background: transparent; font-family: 'Plus Jakarta Sans', sans-serif; }}
            #container {{ width: 100%; height: 100%; min-height: 500px; position: relative; }}
            #infoBox {{
                position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
                background: rgba(14, 34, 48, 0.86); backdrop-filter: blur(12px);
                border: 1px solid rgba(76, 155, 191, 0.25); border-radius: 14px;
                padding: 10px 20px; color: #FFFFFF; font-size: 12.5px; font-weight: 600;
                text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                pointer-events: none; transition: all 0.2s ease;
                z-index: 10; max-width: 85%;
            }}
            .part-tag {{ color: #4C9BBF; font-weight: 700; }}
            #loading {{
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                color: #4C9BBF; font-size: 13px; font-weight: 700; letter-spacing: 0.05em;
                z-index: 5; text-align: center; width: 80%;
            }}
            #hud {{
                position: absolute; top: 14px; left: 16px;
                color: rgba(255,255,255,0.6); font-size: 11px; font-weight: 700;
                letter-spacing: 0.04em; z-index: 10;
            }}
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    </head>
    <body>
        <div id="container">
            <div id="loading">⚡ LOADING 3D ANATOMICAL MODEL...</div>
            <div id="hud">HEART // INTERACTIVE MODEL</div>
            <div id="infoBox">💡 Drag to rotate • Scroll to zoom • Hover glowing nodes for details</div>
        </div>
        <script>
            const container = document.getElementById('container');
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0.3, 7.5);

            const renderer = new THREE.WebGLRenderer({{ antialias: false, alpha: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.06;
            controls.minDistance = 3;
            controls.maxDistance = 16;

            const ambientLight = new THREE.AmbientLight(0xffffff, 1.1);
            scene.add(ambientLight);

            const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
            keyLight.position.set(5, 8, 6);
            scene.add(keyLight);

            const rimLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
            rimLight.position.set(-6, 2, -4);
            scene.add(rimLight);

            const glowLight = new THREE.PointLight(0xff4d6d, 3, 25, 2);
            glowLight.position.set(-3, -2, 4);
            scene.add(glowLight);

            const fillLight = new THREE.PointLight(0x00e5ff, 1.2, 20);
            fillLight.position.set(3, 3, -3);
            scene.add(fillLight);

            const heartGroup = new THREE.Group();
            scene.add(heartGroup);

            let modelMesh = null;
            const hotspotMeshes = [];

            const hotspotFractions = [
                {{ fx: 0.50, fy: 0.92, fz: 0.55, title: "AORTA", desc: "Main artery routing oxygenated blood to systemic circulation. Narrowing or weakening here (aneurysm/stenosis) can restrict blood flow to the whole body.", color: 0x00e5ff }},
                {{ fx: 0.68, fy: 0.30, fz: 0.62, title: "LEFT VENTRICLE", desc: "Primary muscular pumping chamber sending blood to the body. Long-term high blood pressure can thicken its walls (hypertrophy).", color: 0x00e5ff }},
                {{ fx: 0.22, fy: 0.68, fz: 0.55, title: "RIGHT ATRIUM", desc: "Receives deoxygenated blood returning from systemic veins. A common origin point for atrial fibrillation.", color: 0x00e5ff }},
                {{ fx: 0.55, fy: 0.55, fz: 0.85, title: "CORONARY ARTERY", desc: "Supplies oxygenated blood directly to cardiac tissue. Plaque buildup here (atherosclerosis) is the leading cause of heart attacks.", color: 0x00e5ff }},
                {{ fx: 0.32, fy: 0.28, fz: 0.60, title: "RIGHT VENTRICLE", desc: "Pumps deoxygenated blood to the lungs via the pulmonary artery. Chronic strain here can signal pulmonary hypertension.", color: 0x00e5ff }},
                {{ fx: 0.25, fy: 0.82, fz: 0.50, title: "SA NODE (LIVE)", desc: "{sa_node_desc}", color: {_js_color(hr_color)} }},
                {{ fx: 0.65, fy: 0.72, fz: 0.42, title: "LEFT ATRIUM", desc: "Receives freshly oxygenated blood from the lungs. Especially vulnerable to atrial fibrillation, which raises stroke risk if untreated.", color: 0x00e5ff }},
                {{ fx: 0.42, fy: 0.88, fz: 0.38, title: "PULMONARY ARTERY", desc: "Carries deoxygenated blood to the lungs. A clot lodging here (pulmonary embolism) is a medical emergency.", color: 0x00e5ff }},
                {{ fx: 0.58, fy: 0.48, fz: 0.68, title: "MITRAL VALVE", desc: "Controls flow between left atrium and ventricle. Leaflets can leak (regurgitation) or narrow (stenosis), forcing the heart to work harder.", color: 0x00e5ff }},
                {{ fx: 0.50, fy: 0.10, fz: 0.60, title: "MYOCARDIUM (LIVE)", desc: "{myocardium_desc}", color: {_js_color(recovery_color)} }}
            ];

            function addHotspots(box) {{
                const hotspotGeo = new THREE.SphereGeometry(box.getSize(new THREE.Vector3()).length() * 0.02, 16, 16);

                hotspotFractions.forEach(data => {{
                    const pos = new THREE.Vector3(
                        THREE.MathUtils.lerp(box.min.x, box.max.x, data.fx),
                        THREE.MathUtils.lerp(box.min.y, box.max.y, data.fy),
                        THREE.MathUtils.lerp(box.min.z, box.max.z, data.fz)
                    );
                    const hotspotMat = new THREE.MeshBasicMaterial({{ color: data.color }});
                    const mesh = new THREE.Mesh(hotspotGeo, hotspotMat);
                    mesh.position.copy(pos);
                    mesh.userData = data;
                    heartGroup.add(mesh);
                    hotspotMeshes.push(mesh);

                    const ringSize = box.getSize(new THREE.Vector3()).length() * 0.03;
                    const ringGeo = new THREE.RingGeometry(ringSize, ringSize * 1.25, 24);
                    const ringMat = new THREE.MeshBasicMaterial({{ color: data.color, transparent: true, opacity: 0.5, side: THREE.DoubleSide }});
                    const ring = new THREE.Mesh(ringGeo, ringMat);
                    ring.position.copy(pos);
                    ring.lookAt(camera.position);
                    heartGroup.add(ring);
                    mesh.userData.ring = ring;
                }});
            }}

            function finishLoading() {{
                document.getElementById('loading').style.display = 'none';
            }}

            function buildFallbackHeart() {{
                const shape = new THREE.Shape();
                const x = 0, y = 0;
                shape.moveTo(x, y + 0.7);
                shape.bezierCurveTo(x, y + 1.1, x - 1.1, y + 1.3, x - 1.1, y + 0.55);
                shape.bezierCurveTo(x - 1.1, y - 0.15, x - 0.55, y - 0.85, x, y - 1.6);
                shape.bezierCurveTo(x + 0.55, y - 0.85, x + 1.1, y - 0.15, x + 1.1, y + 0.55);
                shape.bezierCurveTo(x + 1.1, y + 1.3, x, y + 1.1, x, y + 0.7);
                const geo = new THREE.ExtrudeGeometry(shape, {{
                    steps: 4, depth: 1.1, bevelEnabled: true, bevelThickness: 0.35,
                    bevelSize: 0.35, bevelOffset: 0, bevelSegments: 12, curveSegments: 24
                }});
                geo.center();
                geo.computeVertexNormals();
                const mat = new THREE.MeshStandardMaterial({{
                    color: 0xff6b6b, roughness: 0.35, metalness: 0.15,
                    emissive: 0x2a0b0f, emissiveIntensity: 0.35
                }});
                const mesh = new THREE.Mesh(geo, mat);
                mesh.rotation.x = Math.PI;
                heartGroup.add(mesh);
                modelMesh = mesh;
                const box = new THREE.Box3().setFromObject(mesh);
                addHotspots(box);
                finishLoading();
                document.getElementById('hud').innerText = "HEART // STYLIZED FALLBACK";
            }}

            const loader = new THREE.GLTFLoader();

            function onModelLoaded(gltf) {{
                const model = gltf.scene;
                const rawBox = new THREE.Box3().setFromObject(model);
                const center = rawBox.getCenter(new THREE.Vector3());
                const size = rawBox.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z) || 1;
                const scale = 3.4 / maxDim;

                model.position.sub(center);
                model.scale.setScalar(scale);

                model.traverse((child) => {{
                    if (child.isMesh) {{
                        if (child.material) {{
                            child.material.metalness = Math.min(child.material.metalness ?? 0.1, 0.2);
                            child.material.roughness = Math.max(child.material.roughness ?? 0.4, 0.35);
                        }}
                    }}
                }});

                heartGroup.add(model);
                modelMesh = model;

                const fittedBox = new THREE.Box3().setFromObject(model);
                addHotspots(fittedBox);
                finishLoading();
            }}

            loader.load(
                "{MODEL_URL}",
                onModelLoaded,
                undefined,
                function (primaryError) {{
                    console.warn("Could not load heart model from primary host, trying fallback host:", primaryError);
                    loader.load(
                        "{MODEL_URL_FALLBACK}",
                        onModelLoaded,
                        undefined,
                        function (fallbackError) {{
                            console.warn("Could not load heart model from fallback host either, using stylized shape:", fallbackError);
                            buildFallbackHeart();
                        }}
                    );
                }}
            );

            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const infoBox = document.getElementById('infoBox');
            const defaultInfo = infoBox.innerHTML;
            let isHoveringHotspot = false;

            function updatePointer(clientX, clientY) {{
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(hotspotMeshes);

                if (intersects.length > 0) {{
                    const data = intersects[0].object.userData;
                    infoBox.innerHTML = `<span class="part-tag">📍 ${{data.title}}:</span> ${{data.desc}}`;
                    container.style.cursor = 'pointer';
                    isHoveringHotspot = true;
                }} else {{
                    infoBox.innerHTML = defaultInfo;
                    container.style.cursor = 'default';
                    isHoveringHotspot = false;
                }}
            }}

            container.addEventListener('mousemove', (e) => updatePointer(e.clientX, e.clientY));
            container.addEventListener('touchmove', (e) => {{
                if (e.touches.length > 0) updatePointer(e.touches[0].clientX, e.touches[0].clientY);
            }}, {{ passive: true }});

            const clock = new THREE.Clock();
            const bpm = {hr};
            const beatFreq = Math.max(0.4, bpm / 60);

            function animate() {{
                requestAnimationFrame(animate);
                const t = clock.getElapsedTime() * beatFreq;

                const pulse = 1 + Math.sin(t * 4) * 0.035 + Math.max(0, Math.sin(t * 8)) * 0.02;
                heartGroup.scale.set(pulse, pulse, pulse);
                if (!isHoveringHotspot) {{
                    heartGroup.rotation.y += 0.0012;
                }}

                hotspotMeshes.forEach(m => {{
                    const s = 1 + Math.sin(t * 6 + m.position.x) * 0.25;
                    m.scale.set(s, s, s);
                    if (m.userData.ring) m.userData.ring.lookAt(camera.position);
                }});

                glowLight.intensity = 2.5 + Math.sin(t * 4) * 1.0;

                controls.update();
                renderer.render(scene, camera);
            }}
            animate();

            window.addEventListener('resize', () => {{
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=520)

def generate_health_summary(heart_rate=None, resting_hr=None, hrv=None,
                             sleep_quality=None, steps=None, heart_rate_recovery=None,
                             blood_pressure_variability=None, apply_symptom_adjustment=True):
    heart_rate = st.session_state.heart_rate if heart_rate is None else heart_rate
    resting_hr = st.session_state.resting_hr if resting_hr is None else resting_hr
    hrv = st.session_state.hrv if hrv is None else hrv
    sleep_quality = st.session_state.sleep_quality if sleep_quality is None else sleep_quality
    steps = st.session_state.steps if steps is None else steps
    heart_rate_recovery = st.session_state.heart_rate_recovery if heart_rate_recovery is None else heart_rate_recovery
    blood_pressure_variability = (
        st.session_state.blood_pressure_variability
        if blood_pressure_variability is None else blood_pressure_variability
    )

    positives = []
    concerns = []

    if 60 <= heart_rate <= 100:
        positives.append("Your heart rate is within the expected resting range.")
    else:
        concerns.append("Your heart rate is outside the expected resting range.")

    if 50 <= resting_hr <= 80:
        positives.append("Your resting heart rate looks healthy.")
    else:
        concerns.append("Your resting heart rate may be unusual.")

    if hrv >= 50:
        positives.append("Your heart rate variability is strong.")
    else:
        concerns.append("Your heart rate variability is lower than normal.")

    if blood_pressure_variability <= 10:
        positives.append("Your blood pressure variability is within a typical range.")
    else:
        concerns.append("Your blood pressure variability is higher than typical.")

    if sleep_quality >= 80:
        positives.append("Excellent sleep quality.")
    elif sleep_quality >= 60:
        concerns.append("Your sleep quality could improve.")
    else:
        concerns.append("Poor sleep quality detected.")

    if steps >= 10000:
        positives.append("You reached your daily activity goal.")
    elif steps >= 7500:
        positives.append("You stayed fairly active today.")
    else:
        concerns.append("Try increasing your daily activity.")

    if heart_rate_recovery >= 20:
        positives.append("Heart rate recovery looks healthy.")
    else:
        concerns.append("Heart rate recovery is slower than expected.")

    metric_scores = [
        metric_status("heart_rate", heart_rate)[2],
        metric_status("resting_hr", resting_hr)[2],
        metric_status("hrv", hrv)[2],
        metric_status("bp_variability", blood_pressure_variability)[2],
        metric_status("recovery", heart_rate_recovery)[2],
        metric_status("sleep", sleep_quality)[2],
        metric_status("steps", steps)[2],
    ]
    score = round(sum(metric_scores) / len(metric_scores))
    score = max(0, min(100, score))

    # Fold in the AI symptom-check adjustment (from "More Accurate Details")
    # for today's live score only — never for historical trend recomputation,
    # since that adjustment reflects how the person feels *right now*, not
    # on any given past day.
    if apply_symptom_adjustment:
        _sym_adj = st.session_state.get("symptom_risk_adjustment", 0) or 0
        if _sym_adj:
            score = max(0, min(100, score + _sym_adj))
            _sym_note = st.session_state.get("symptom_risk_note")
            if _sym_note:
                concerns = concerns + [f"Symptom check: {_sym_note}"]

    return score, positives, concerns

@st.cache_data(show_spinner=False)
def _get_score_trend_cached(history_snapshot, live_vitals, days):
    history = {date_key: dict(day_items) for date_key, day_items in history_snapshot}
    dates = sorted(history.keys())[-days:]
    trend = []
    for d in dates:
        day = history[d]
        day_score, _, _ = generate_health_summary(
            heart_rate=day["heart_rate"],
            resting_hr=day["resting_hr"],
            hrv=day["hrv"],
            sleep_quality=day["sleep_quality"],
            steps=day["steps"],
            heart_rate_recovery=day["heart_rate_recovery"],
            blood_pressure_variability=day["blood_pressure_variability"],
            apply_symptom_adjustment=False,
        )
        trend.append(day_score)
    trend.append(generate_health_summary()[0])  # today
    return trend


def get_score_trend(days=7):
    """Recompute the health score for each of the last `days` days from
    full_history, for the trend sparkline."""
    return _get_score_trend_cached(_history_snapshot(), _live_vitals_key(), days)

def get_biggest_driver():
    """Return (label, is_concern) for whichever tracked metric is furthest
    from its optimal range, or None if everything is currently optimal."""
    named_scores = [
        ("Heart rate", metric_status("heart_rate", st.session_state.heart_rate)[2]),
        ("Resting heart rate", metric_status("resting_hr", st.session_state.resting_hr)[2]),
        ("Heart rate variability", metric_status("hrv", st.session_state.hrv)[2]),
        ("Blood pressure variability", metric_status("bp_variability", st.session_state.blood_pressure_variability)[2]),
        ("Heart rate recovery", metric_status("recovery", st.session_state.heart_rate_recovery)[2]),
        ("Sleep quality", metric_status("sleep", st.session_state.sleep_quality)[2]),
        ("Daily steps", metric_status("steps", st.session_state.steps)[2]),
    ]
    worst_label, worst_score = min(named_scores, key=lambda pair: pair[1])
    if worst_score >= 100:
        return None
    return worst_label, True

def render_trend_sparkline(scores):
    """Render a small inline SVG sparkline for the score trend, as a single
    self-contained HTML block (avoids the Streamlit sibling-div nesting bug)."""
    if len(scores) < 2:
        st.caption("Not enough history yet to chart a trend.")
        return
    w, h, pad = 320, 46, 6
    lo, hi = min(scores), max(scores)
    span = max(1, hi - lo)
    step = (w - 2 * pad) / (len(scores) - 1)
    points = []
    for i, s in enumerate(scores):
        x = pad + i * step
        y = pad + (h - 2 * pad) * (1 - (s - lo) / span)
        points.append(f"{x:.1f},{y:.1f}")
    line_color = GOOD if scores[-1] >= scores[0] else DANGER
    last_x, last_y = points[-1].split(",")
    st.markdown(
        f"""
        <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display:block;">
            <polyline points="{' '.join(points)}" fill="none" stroke="{line_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="{last_x}" cy="{last_y}" r="3.5" fill="{line_color}"/>
        </svg>
        """,
        unsafe_allow_html=True,
    )

def generate_ai_insight(score, positives, concerns):
    if not concerns:
        return (
            "Based on today's readings, all monitored metrics fall within healthy ranges. "
            "Heart rate, HRV, sleep, and activity levels look consistent with good cardiovascular status. "
            "No specific action is indicated beyond continuing current habits and routine monitoring."
        )
    if score >= 90:
        tone = "overall cardiovascular indicators remain strong, though a few areas are worth noting: "
    elif score >= 75:
        tone = "cardiovascular indicators are generally acceptable, with some areas that could benefit from attention: "
    else:
        tone = "several cardiovascular indicators fall outside typical healthy ranges and may warrant closer review: "

    body = " ".join(concerns)
    closing = (
        " These observations are derived from wearable-device estimates, are not a diagnosis, "
        "and should be confirmed by a clinician with appropriate testing before any treatment decision."
    )
    return "Based on today's readings, " + tone + body + closing


# =====================================================
# AI INSIGHTS HELPERS (Weekly Story, Correlations,
# Heart Age / Trajectory, Anomaly Detection)
# =====================================================

def _history_snapshot():
    """Hashable snapshot of full_history, used as a cache key so cached
    functions below only recompute when the underlying data actually
    changes — not on every Streamlit rerun (tab switch, unrelated click)."""
    return tuple(sorted(
        (date_key, tuple(sorted(day.items())))
        for date_key, day in st.session_state.full_history.items()
    ))


def _live_vitals_key():
    """Hashable snapshot of today's live slider values, used alongside
    _history_snapshot() as a cache key for anything that also factors in
    today's current readings (heart age, score trend/projection)."""
    return (
        st.session_state.heart_rate,
        st.session_state.resting_hr,
        st.session_state.hrv,
        st.session_state.sleep_quality,
        st.session_state.steps,
        st.session_state.heart_rate_recovery,
        st.session_state.blood_pressure_variability,
    )


@st.cache_data(show_spinner=False)
def _history_dataframe_cached(history_snapshot):
    rows = []
    for date_key, day_items in history_snapshot:
        row = dict(day_items)
        row["date"] = date_key
        rows.append(row)
    return pd.DataFrame(rows)


def _history_dataframe():
    """Full telemetry history as a DataFrame, sorted by date, for stats work."""
    return _history_dataframe_cached(_history_snapshot())


def get_weekly_story():
    """Ask Gemini for a short narrative summary of the last 7 days. Cached
    in session_state so it's only regenerated when the user asks for it."""
    client = get_gemini_client()
    if client is None:
        return "Gemini is not configured, so the weekly story can't be generated right now."

    trend_days = sorted(st.session_state.full_history.keys())[-7:]
    lines = []
    for d in trend_days:
        day = st.session_state.full_history[d]
        lines.append(
            f"{d}: HR {day['heart_rate']} BPM, RHR {day['resting_hr']} BPM, HRV {day['hrv']} ms, "
            f"Sleep {day['sleep_quality']}%, Steps {day['steps']}"
        )
    prompt = (
        "Here is one user's last 7 days of wearable heart telemetry:\n" + "\n".join(lines) +
        "\n\nWrite a short (4-6 sentence) plain-language 'weekly story' that highlights the most "
        "notable pattern or change across the week (e.g. a dip tied to poor sleep, a recovery, a steady "
        "trend). Reference only the numbers given above. Be warm but not alarmist, and end with a brief "
        "reminder that this is informational, not a diagnosis. Keep the whole thing under 90 words so "
        "it comfortably finishes within the response budget — never cut a sentence off partway through."
    )
    try:
        # Thinking models spend part of max_output_tokens on invisible
        # reasoning before writing the visible answer, which is what was
        # cutting this off mid-sentence — turn thinking off (with a
        # fallback for model versions that reject the field) the same
        # way get_ai_response() already does.
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.7, "max_output_tokens": 3000, "thinking_config": {"thinking_budget": 0}},
            )
        except genai_errors.APIError as thinking_exc:
            if "INVALID_ARGUMENT" in str(thinking_exc) or getattr(thinking_exc, "code", None) == 400:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={"temperature": 0.7, "max_output_tokens": 3000},
                )
            else:
                raise

        text = (response.text or "").strip()

        # If we still hit MAX_TOKENS even with thinking off, double the
        # budget once and retry rather than returning a half-finished story.
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            finish_reason = None
        if finish_reason is not None and "MAX_TOKENS" in str(finish_reason):
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.7, "max_output_tokens": 6000},
            )
            text = (response.text or "").strip()

        return text or "Gemini returned no response."
    except Exception as exc:
        return f"Couldn't generate your weekly story right now: {_friendly_gemini_error(exc)}"


@st.cache_data(show_spinner=False)
def _compute_correlations_cached(history_snapshot, min_abs_corr):
    """Compute Pearson correlations between metric pairs across full_history
    and return the most notable ones as plain-language findings."""
    df = _history_dataframe_cached(history_snapshot)
    metrics = {
        "heart_rate": "Heart rate",
        "resting_hr": "Resting heart rate",
        "hrv": "HRV",
        "sleep_quality": "Sleep quality",
        "steps": "Daily steps",
        "heart_rate_recovery": "Heart rate recovery",
        "blood_pressure_variability": "Blood pressure variability",
    }
    if len(df) < 5:
        return []

    corr_matrix = df[list(metrics.keys())].corr(numeric_only=True)
    findings = []
    seen_pairs = set()
    keys = list(metrics.keys())
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pair = tuple(sorted((a, b)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            r = corr_matrix.loc[a, b]
            if pd.isna(r) or abs(r) < min_abs_corr:
                continue
            direction = "rise together" if r > 0 else "move in opposite directions"
            findings.append({
                "metric_a": metrics[a],
                "metric_b": metrics[b],
                "r": round(float(r), 2),
                "direction": direction,
            })
    findings.sort(key=lambda f: abs(f["r"]), reverse=True)
    return findings[:4]


def compute_correlations(min_abs_corr=0.3):
    return _compute_correlations_cached(_history_snapshot(), min_abs_corr)


def get_correlation_insight(findings):
    """Turn computed correlation numbers into plain-language sentences via
    Gemini, constrained to only the numbers we actually computed."""
    if not findings:
        return "Not enough history yet to detect reliable correlations — check back after a few more days of data."

    client = get_gemini_client()
    facts = "\n".join(
        f"- {f['metric_a']} and {f['metric_b']}: r = {f['r']} ({f['direction']})" for f in findings
    )
    if client is None:
        return "Here's what the numbers show (Gemini isn't configured to add narration):\n" + facts

    prompt = (
        "These are real, already-computed Pearson correlations from a user's health telemetry history. "
        "Do not invent or restate different numbers — only explain the ones given, in plain language, "
        "one short sentence per line:\n" + facts +
        "\n\nFor context, |r| above 0.7 is a strong relationship, 0.4-0.7 is moderate, 0.3-0.4 is weak. "
        "Keep it to 1 short sentence per correlation, no preamble, and make sure every sentence you "
        "start is finished — never cut one off partway through."
    )
    try:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.4, "max_output_tokens": 2500, "thinking_config": {"thinking_budget": 0}},
            )
        except genai_errors.APIError as thinking_exc:
            if "INVALID_ARGUMENT" in str(thinking_exc) or getattr(thinking_exc, "code", None) == 400:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={"temperature": 0.4, "max_output_tokens": 2500},
                )
            else:
                raise
        return (response.text or "").strip() or facts
    except Exception:
        return "Here's what the numbers show:\n" + facts


@st.cache_data(show_spinner=False)
def _compute_heart_age_cached(age, live_vitals, score):
    """Heuristic 'heart age' estimate: a healthier score shifts the estimate
    younger than the person's stated age, a lower score shifts it older.
    This is a simplified, non-clinical illustration, not a validated model."""
    offset = (score - 75) / 3.0  # each ~3 points above/below 75 shifts a year
    heart_age = age - offset
    heart_age = max(18, round(heart_age))
    return heart_age, score


def compute_heart_age(age):
    score, _, _ = generate_health_summary()
    return _compute_heart_age_cached(age, _live_vitals_key(), score)


@st.cache_data(show_spinner=False)
def _compute_score_projection_cached(history_snapshot, live_vitals, days_ahead):
    """Fit a simple linear trend to the last 30 days of health scores and
    project it forward. Returns (current_score, projected_score, slope_per_day)."""
    scores = _get_score_trend_cached(history_snapshot, live_vitals, 30)
    if len(scores) < 5:
        return scores[-1] if scores else 0, scores[-1] if scores else 0, 0.0
    x = list(range(len(scores)))
    slope, intercept = np.polyfit(x, scores, 1)
    projected_x = len(scores) - 1 + days_ahead
    projected = slope * projected_x + intercept
    projected = max(0, min(100, round(projected)))
    return scores[-1], projected, round(slope, 3)


def compute_score_projection(days_ahead=30):
    return _compute_score_projection_cached(_history_snapshot(), _live_vitals_key(), days_ahead)


def detect_anomalies(z_threshold=2.0):
    """Compare today's live slider values against the person's own 30-day
    baseline (mean/std) and flag anything that's a real outlier for them,
    rather than a generic fixed threshold."""
    df = _history_dataframe()
    if len(df) < 7:
        return []

    live_values = {
        "heart_rate": st.session_state.heart_rate,
        "resting_hr": st.session_state.resting_hr,
        "hrv": st.session_state.hrv,
        "sleep_quality": st.session_state.sleep_quality,
        "heart_rate_recovery": st.session_state.heart_rate_recovery,
        "blood_pressure_variability": st.session_state.blood_pressure_variability,
    }
    labels = {
        "heart_rate": "Heart rate",
        "resting_hr": "Resting heart rate",
        "hrv": "HRV",
        "sleep_quality": "Sleep quality",
        "heart_rate_recovery": "Heart rate recovery",
        "blood_pressure_variability": "Blood pressure variability",
    }
    anomalies = []
    for key, live_val in live_values.items():
        series = df[key]
        mean, std = series.mean(), series.std()
        if not std or pd.isna(std):
            continue
        z = (live_val - mean) / std
        if abs(z) >= z_threshold:
            anomalies.append({
                "metric": labels[key],
                "value": live_val,
                "baseline": round(mean, 1),
                "z": round(float(z), 2),
                "direction": "higher" if z > 0 else "lower",
            })
    return anomalies


def get_anomaly_alert_message(anomalies):
    """Phrase detected anomalies as a caring, plain-language heads-up,
    strictly using the computed values (no invented numbers)."""
    if not anomalies:
        return None
    facts = "\n".join(
        f"- {a['metric']}: currently {a['value']}, which is {a['direction']} than this person's own "
        f"typical baseline of {a['baseline']} (z-score {a['z']})" for a in anomalies
    )
    client = get_gemini_client()
    if client is None:
        return "Heads up — a couple of readings look off from your usual baseline:\n" + facts

    prompt = (
        "A wearable health app detected that these readings are unusual compared to this specific "
        "person's own historical baseline (not a generic medical threshold):\n" + facts +
        "\n\nWrite a brief (2-3 sentence), calm, non-alarmist heads-up message as the PulseGuard AI "
        "Assistant would say it at the start of a chat. Don't diagnose. Suggest they keep an eye on it "
        "and mention a clinician if it persists."
    )
    fallback = "Heads up — a couple of readings look off from your usual baseline:\n" + facts
    try:
        # Same fix as get_weekly_story()/get_symptom_risk_assessment(): thinking
        # models burn part of max_output_tokens on invisible reasoning before
        # writing the visible answer, which was cutting this off mid-sentence.
        # Turn thinking off (falling back for model versions that reject the
        # field), and retry once with a bigger budget if we still hit MAX_TOKENS.
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.6, "max_output_tokens": 1000, "thinking_config": {"thinking_budget": 0}},
            )
        except genai_errors.APIError as thinking_exc:
            if "INVALID_ARGUMENT" in str(thinking_exc) or getattr(thinking_exc, "code", None) == 400:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={"temperature": 0.6, "max_output_tokens": 1000},
                )
            else:
                raise

        text = (response.text or "").strip()
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            finish_reason = None
        if finish_reason is not None and "MAX_TOKENS" in str(finish_reason):
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.6, "max_output_tokens": 2000},
            )
            text = (response.text or "").strip()

        return text or fallback
    except Exception:
        return fallback


def get_symptom_risk_assessment(symptoms, extra_notes):
    """Send the user's reported symptoms + free-text notes, alongside their
    live telemetry, to Gemini and get back a risk-score adjustment plus a
    plain-language explanation. Returns (adjustment:int, explanation:str,
    error:str|None). Adjustment is negative (worse) or 0 — this only ever
    lowers today's score, it never raises it, since self-reported symptoms
    should never make a computed score look *better*."""
    client = get_gemini_client()
    if client is None:
        return 0, None, "Gemini isn't configured — set GEMINI_API_KEY in secrets."

    context = build_ai_context()
    symptom_text = ", ".join(symptoms) if symptoms else "None reported"

    prompt = (
        f"{context}\n\n"
        f"The person just completed a symptom check-in.\n"
        f"Reported symptoms: {symptom_text}\n"
        f"Additional details they typed: {extra_notes.strip() or 'None'}\n\n"
        "Based on this alongside their telemetry above, decide how much to lower "
        "today's heart risk score to reflect these self-reported symptoms (it should "
        "never increase the score). Respond with ONLY raw JSON, no markdown fences, "
        "in exactly this shape:\n"
        '{"adjustment": <integer from -30 to 0>, "explanation": <string, 2-3 sentences, '
        'plain language, calm, not alarmist, no diagnosis, mention seeing a clinician '
        'if symptoms are concerning>}'
    )

    try:
        # Same fix as get_weekly_story(): thinking models burn part of
        # max_output_tokens on invisible reasoning before writing the
        # visible answer, which was truncating the JSON mid-string
        # (surfacing as "Unterminated string" from json.loads). Turn
        # thinking off, with a fallback for model versions that reject
        # the field.
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.4, "max_output_tokens": 3000, "thinking_config": {"thinking_budget": 0}},
            )
        except genai_errors.APIError as thinking_exc:
            if "INVALID_ARGUMENT" in str(thinking_exc) or getattr(thinking_exc, "code", None) == 400:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={"temperature": 0.4, "max_output_tokens": 3000},
                )
            else:
                raise
        raw = (response.text or "").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        # If we still hit MAX_TOKENS even at 3000, double the budget once
        # and retry rather than failing outright — some prompts/models
        # eat more invisible reasoning tokens than others.
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            finish_reason = None
        if finish_reason is not None and "MAX_TOKENS" in str(finish_reason) and not raw.rstrip().endswith("}"):
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.4, "max_output_tokens": 6000},
            )
            raw = (response.text or "").strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as parse_exc:
            # Surface WHY it broke instead of just the parser error, so we
            # can tell truncation apart from genuinely malformed JSON.
            finish_reason = None
            try:
                finish_reason = response.candidates[0].finish_reason
            except Exception:
                pass
            diag = f"finish_reason={finish_reason}, {len(raw)} chars received: {raw[:120]!r}"
            return 0, None, f"Couldn't complete the assessment: {parse_exc} [{diag}]"
        adjustment = int(parsed.get("adjustment", 0))
        adjustment = max(-30, min(0, adjustment))
        explanation = str(parsed.get("explanation", "")).strip()
        return adjustment, explanation, None
    except (genai_errors.APIError, ValueError, TypeError, KeyError) as exc:
        return 0, None, f"Couldn't complete the assessment: {_friendly_gemini_error(exc)}"


def build_report_window(period_key, custom_start=None, custom_end=None):
    now = datetime.now(ZoneInfo("America/New_York"))
    today = now.date()

    if period_key == "24h":
        start_dt = datetime.combine(today, datetime.min.time(), tzinfo=ZoneInfo("America/New_York"))
        end_dt = datetime.combine(today, datetime.max.time(), tzinfo=ZoneInfo("America/New_York"))
        label = "Last 24 hours"
    elif period_key == "7d":
        start_dt = datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=ZoneInfo("America/New_York"))
        end_dt = datetime.combine(today, datetime.max.time(), tzinfo=ZoneInfo("America/New_York"))
        label = "Last 7 days"
    elif period_key == "30d":
        start_dt = datetime.combine(today - timedelta(days=29), datetime.min.time(), tzinfo=ZoneInfo("America/New_York"))
        end_dt = datetime.combine(today, datetime.max.time(), tzinfo=ZoneInfo("America/New_York"))
        label = "Last 30 days"
    elif period_key == "custom":
        custom_start = custom_start or today - timedelta(days=6)
        custom_end = custom_end or today
        start_dt = datetime.combine(custom_start, datetime.min.time(), tzinfo=ZoneInfo("America/New_York"))
        end_dt = datetime.combine(custom_end, datetime.max.time(), tzinfo=ZoneInfo("America/New_York"))
        label = f"{custom_start:%b %d, %Y} to {custom_end:%b %d, %Y}"
    else:
        start_dt = datetime.combine(today, datetime.min.time(), tzinfo=ZoneInfo("America/New_York"))
        end_dt = datetime.combine(today, datetime.max.time(), tzinfo=ZoneInfo("America/New_York"))
        label = "Last 24 hours"

    return start_dt, end_dt, label


def get_report_rows(start_dt, end_dt):
    rows = []
    for date_key in sorted(st.session_state.full_history.keys()):
        try:
            row_dt = datetime.strptime(date_key, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York"))
        except ValueError:
            continue
        if start_dt <= row_dt <= end_dt:
            values = st.session_state.full_history[date_key]
            rows.append({
                "date": row_dt.strftime("%b %d, %Y"),
                "heart_rate": values.get("heart_rate"),
                "resting_hr": values.get("resting_hr"),
                "hrv": values.get("hrv"),
                "bp": values.get("blood_pressure_variability"),
                "recovery": values.get("heart_rate_recovery"),
                "sleep_quality": values.get("sleep_quality"),
                "steps": values.get("steps"),
            })
    return rows


def summarize_report_rows(rows):
    if not rows:
        return {}

    metrics = {
        "heart_rate": [row["heart_rate"] for row in rows],
        "resting_hr": [row["resting_hr"] for row in rows],
        "hrv": [row["hrv"] for row in rows],
        "bp": [row["bp"] for row in rows],
        "recovery": [row["recovery"] for row in rows],
        "sleep_quality": [row["sleep_quality"] for row in rows],
        "steps": [row["steps"] for row in rows],
    }

    return {
        "avg_heart_rate": round(sum(metrics["heart_rate"]) / len(metrics["heart_rate"])),
        "avg_resting_hr": round(sum(metrics["resting_hr"]) / len(metrics["resting_hr"])),
        "avg_hrv": round(sum(metrics["hrv"]) / len(metrics["hrv"])),
        "avg_bp": round(sum(metrics["bp"]) / len(metrics["bp"])),
        "avg_recovery": round(sum(metrics["recovery"]) / len(metrics["recovery"])),
        "avg_sleep": round(sum(metrics["sleep_quality"]) / len(metrics["sleep_quality"])),
        "avg_steps": round(sum(metrics["steps"]) / len(metrics["steps"])),
        "max_steps": max(metrics["steps"]),
        "min_steps": min(metrics["steps"]),
    }


# ==========================================================
# SHAREABLE STORY CARD — a vertical PNG (Instagram-story shaped)
# with the person's heart score, styled to match the app so it
# looks good posted straight to a story or feed.
# ==========================================================
def _story_font(size, bold=False):
    """Best-effort font loader — tries a few common bundled TrueType
    fonts, then falls back to Pillow's own built-in font. Pillow's
    load_default() *without* a size argument always renders as a tiny
    fixed ~10px bitmap regardless of the requested size — that's what
    was making every label look like a dot. Passing size= (supported
    since Pillow 10.1) gives a scalable version of that same built-in
    font, so text is always legible even on a server with zero of the
    TrueType font files below actually installed."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    # matplotlib bundles DejaVu Sans internally and is present in most
    # data-science environments even when not imported directly — worth
    # a shot before falling back to Pillow's built-in font.
    try:
        import matplotlib
        mpl_font = os.path.join(
            matplotlib.get_data_path(), "fonts", "ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        )
        if os.path.exists(mpl_font):
            return ImageFont.truetype(mpl_font, size)
    except Exception:
        pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Ancient Pillow without size-aware load_default — better a
        # readable-if-imperfect font than a silent crash.
        return ImageFont.load_default()


def _lerp_color(c1, c2, t):
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _draw_centered_text(draw, xy, text, font, fill):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((x - w / 2, y - h / 2 - bbox[1]), text, font=font, fill=fill)


def _rounded_rect_alpha(size, radius, fill):
    """A rounded rectangle on its own transparent layer, so it can be
    alpha-composited onto the background for a soft glass-card look."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=fill)
    return layer


def _draw_heart_icon(draw, cx, cy_visual_center, size, fill):
    """Draw a filled heart as actual shapes (two lobes + a point) instead
    of the U+2665 text glyph — the PNG export's fallback font doesn't
    include that glyph and was rendering it as a missing-character box."""
    r = size * 0.28
    top = cy_visual_center - r * 1.55
    draw.ellipse([cx - 2 * r, top, cx, top + 2 * r], fill=fill)
    draw.ellipse([cx, top, cx + 2 * r, top + 2 * r], fill=fill)
    draw.polygon(
        [(cx - 2 * r, top + r * 1.1), (cx + 2 * r, top + r * 1.1), (cx, top + r * 3.2)],
        fill=fill
    )


def generate_share_card(score, resting_hr, hrv, sleep_quality, streak_days,
                         patient_name="", trend_word="steady"):
    """Build a 1080x1920 (Instagram-story-shaped) PNG summarizing the
    person's heart score and a few headline stats, in PulseGuard's
    cyan/purple dark theme. Returns raw PNG bytes."""
    W, H = 1080, 1920
    CYAN = (16, 185, 129)
    PURPLE = (245, 158, 11)
    BG_TOP = (10, 22, 17)
    BG_BOTTOM = (5, 10, 20)
    TEXT = (234, 247, 240)
    MUTED = (138, 153, 173)

    # Vertical gradient background
    bg = Image.new("RGB", (W, H))
    grad = np.linspace(0, 1, H)[:, None]
    top = np.array(BG_TOP)
    bottom = np.array(BG_BOTTOM)
    rows = (top + (bottom - top) * grad).astype(np.uint8)
    bg_arr = np.repeat(rows[:, None, :], W, axis=1)
    bg = Image.fromarray(bg_arr, "RGB").convert("RGBA")

    # Soft glow blobs behind the ring, echoing the app's radial accents
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([W * 0.5 - 420, 560, W * 0.5 + 420, 1400], fill=(16, 185, 129, 40))
    glow_draw.ellipse([W * 0.5 - 300, 620, W * 0.5 + 300, 1340], fill=(245, 158, 11, 35))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    bg = Image.alpha_composite(bg, glow)

    draw = ImageDraw.Draw(bg)

    # Header wordmark
    draw.ellipse([W / 2 - 34, 96, W / 2 + 34, 164], fill=(16, 185, 129, 255))
    _draw_heart_icon(draw, W / 2, 130, 60, (5, 16, 32))
    _draw_centered_text(draw, (W / 2, 220), "PulseGuard", _story_font(56, bold=True), TEXT)
    _draw_centered_text(draw, (W / 2, 270), "HEART HEALTH INTELLIGENCE", _story_font(22, bold=True), MUTED)

    # Score ring — segmented arc, colour interpolated cyan -> purple so
    # it reads as a smooth gradient stroke despite PIL not supporting
    # gradient strokes natively.
    ring_cx, ring_cy, ring_r = W / 2, 980, 300
    thickness = 34
    bbox = [ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r]
    draw.arc(bbox, start=-90, end=270, fill=(255, 255, 255, 30), width=thickness)

    sweep = max(1, round(360 * (score / 100)))
    steps = max(sweep, 1)
    for i in range(steps):
        a0 = -90 + i
        a1 = a0 + 1.2
        t = i / max(steps - 1, 1)
        color = _lerp_color(CYAN, PURPLE, t)
        draw.arc(bbox, start=a0, end=a1, fill=color + (255,), width=thickness)

    _draw_centered_text(draw, (ring_cx, ring_cy - 30), str(score), _story_font(150, bold=True), (255, 255, 255))
    _draw_centered_text(draw, (ring_cx, ring_cy + 70), "/ 100", _story_font(40, bold=True), MUTED)
    _draw_centered_text(draw, (ring_cx, ring_cy + 150), "HEART SCORE", _story_font(28, bold=True), CYAN)

    if patient_name:
        _draw_centered_text(draw, (ring_cx, ring_cy + 210), f"{patient_name}'s cardiovascular snapshot", _story_font(24), MUTED)

    trend_labels = {
        "improving": ("Trending up this month", (16, 185, 129)),
        "declining": ("Keep an eye on this month", (244, 63, 94)),
        "steady": ("Holding steady this month", (251, 191, 36)),
    }
    trend_text, trend_color = trend_labels.get(trend_word, trend_labels["steady"])
    _draw_centered_text(draw, (ring_cx, ring_cy + ring_r + 55), trend_text, _story_font(26, bold=True), trend_color)

    # Stat chips
    stats = [
        ("RESTING HR", f"{resting_hr} bpm"),
        ("HRV", f"{hrv} ms"),
        ("SLEEP", f"{sleep_quality}%"),
        ("STREAK", f"{streak_days}d"),
    ]
    chip_w, chip_h, gap = 228, 150, 24
    total_w = chip_w * 4 + gap * 3
    start_x = (W - total_w) / 2
    chip_y = 1420
    bg_rgba = bg
    for i, (label, value) in enumerate(stats):
        cx0 = start_x + i * (chip_w + gap)
        card = _rounded_rect_alpha((chip_w, chip_h), 22, (255, 255, 255, 18))
        bg_rgba.alpha_composite(card, (round(cx0), chip_y))
        draw = ImageDraw.Draw(bg_rgba)
        _draw_centered_text(draw, (cx0 + chip_w / 2, chip_y + 50), value, _story_font(34, bold=True), (255, 255, 255))
        _draw_centered_text(draw, (cx0 + chip_w / 2, chip_y + 105), label, _story_font(18, bold=True), MUTED)

    # Footer
    draw = ImageDraw.Draw(bg_rgba)
    _draw_centered_text(draw, (W / 2, 1720), "Track your own heart health with PulseGuard", _story_font(26, bold=True), TEXT)
    _draw_centered_text(draw, (W / 2, 1760), "Informational only - not a medical diagnosis", _story_font(20), MUTED)

    out = io.BytesIO()
    bg_rgba.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def generate_doctor_report_pdf(rows, period_label, patient_name=""):
    pdf = _PulseGuardPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    content_width = pdf.w - pdf.l_margin - pdf.r_margin
    generated_on = datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")
    summary = summarize_report_rows(rows)

    pdf.set_fill_color(8, 20, 15)
    pdf.rect(0, 0, pdf.w, 32, style="F")
    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(content_width, 10, _pdf_safe("PulseGuard Cardiology Report"), ln=True)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(content_width, 6, _pdf_safe("Prepared for clinical review"), ln=True)
    pdf.set_y(36)
    pdf.set_text_color(20, 20, 20)

    # Connecting patient_name explicitly from parameter or session state
    actual_name = patient_name.strip()
    meta_label = actual_name if actual_name else "Not provided"
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Patient / User: {meta_label}"))
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Report Period: {period_label}"), ln=True)
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Generated On: {generated_on}"))
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Device: {st.session_state.selected_watch}"), ln=True)
    pdf.ln(4)

    _pdf_section_header(pdf, "Period Summary", content_width)
    pdf.set_font("Helvetica", "", 10.5)
    summary_rows = [
        ("Average Heart Rate", f"{summary.get('avg_heart_rate', 'n/a')} BPM"),
        ("Average Resting HR", f"{summary.get('avg_resting_hr', 'n/a')} BPM"),
        ("Average HRV", f"{summary.get('avg_hrv', 'n/a')} ms"),
        ("Average BP Variability", f"{summary.get('avg_bp', 'n/a')} mmHg"),
        ("Average Recovery", f"{summary.get('avg_recovery', 'n/a')} BPM"),
        ("Average Sleep Quality", f"{summary.get('avg_sleep', 'n/a')}%"),
        ("Average Daily Steps", f"{summary.get('avg_steps', 'n/a'):,}"),
        ("Highest Steps", f"{summary.get('max_steps', 'n/a'):,}"),
    ]
    label_width = 95
    value_width = content_width - label_width
    for i, (label, value) in enumerate(summary_rows):
        fill = (245, 245, 245) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(225, 225, 225)
        pdf.cell(label_width, 8, "  " + _pdf_safe(label), border="B", fill=True)
        pdf.cell(value_width, 8, _pdf_safe(value), border="B", fill=True, ln=True)
    pdf.ln(5)

    _pdf_section_header(pdf, "Daily Telemetry Log", content_width)
    pdf.set_font("Helvetica", "", 9.5)
    if not rows:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 6, _pdf_safe("No telemetry entries were available for the selected window."))
    else:
        for row in rows:
            pdf.set_x(pdf.l_margin)
            entry_text = (
                f"{row['date']} — HR {row['heart_rate']} BPM | Resting HR {row['resting_hr']} BPM | "
                f"HRV {row['hrv']} ms | BP var {row['bp']} mmHg | Recovery {row['recovery']} BPM | "
                f"Sleep {row['sleep_quality']}% | Steps {row['steps']:,}"
            )
            pdf.multi_cell(content_width, 6, _pdf_safe(entry_text))
            pdf.ln(1)

    return bytes(pdf.output())


def _pdf_safe(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

class _PulseGuardPDF(FPDF):
    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, _pdf_safe(f"PulseGuard Health Report  |  Page {self.page_no()}"), align="C")

def _pdf_section_header(pdf, text, content_width, rgb=(13, 26, 20)):
    pdf.set_fill_color(*rgb)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(content_width, 9, "  " + _pdf_safe(text), border=0, fill=True, ln=True)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(2)

def generate_pdf_report(score, positives, concerns, ai_insight, heart_rate, resting_hr, hrv,
                         bp, recovery, sleep_quality, steps, battery, last_sync, watch_name,
                         period_label="Today", patient_name=""):
    pdf = _PulseGuardPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    content_width = pdf.w - pdf.l_margin - pdf.r_margin
    generated_on = datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")

    pdf.set_fill_color(8, 20, 15)
    pdf.rect(0, 0, pdf.w, 32, style="F")
    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(content_width, 10, _pdf_safe("PulseGuard Cardiovascular Telemetry Export"), ln=True)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(content_width, 6, _pdf_safe("New Jersey Heart Disease Prevention (NJHDP)"), ln=True)
    pdf.set_y(36)
    pdf.set_text_color(20, 20, 20)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    actual_name = patient_name.strip()
    meta_label = actual_name if actual_name else "Not provided"
    
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Patient / User: {meta_label}"))
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Report Period: {period_label}"), ln=True)
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Report Generated: {generated_on} ({last_sync} ET)"))
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Data Source Device: {watch_name}"), ln=True)
    pdf.ln(3)

    if score >= 90:
        score_rgb = (0, 180, 200)
        score_word = "Good"
    elif score >= 75:
        score_rgb = (191, 144, 0)
        score_word = "Fair"
    else:
        score_rgb = (244, 63, 94)
        score_word = "Needs Attention"

    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(*score_rgb)
    pdf.set_line_width(0.6)
    pdf.rect(pdf.l_margin, pdf.get_y(), content_width, 20, style="DF")
    pdf.set_xy(pdf.l_margin + 4, pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*score_rgb)
    pdf.cell(content_width - 8, 10, _pdf_safe(f"Heart Health Score: {score}/100  ({score_word})"))
    pdf.ln(20)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(4)

    _pdf_section_header(pdf, f"Telemetry Readings — {period_label}", content_width)
    pdf.set_font("Helvetica", "", 10.5)

    rows = [
        ("Heart Rate", f"{heart_rate} BPM"),
        ("Resting Heart Rate", f"{resting_hr} BPM"),
        ("Heart Rate Variability", f"{hrv} ms"),
        ("Blood Pressure Variability", f"{bp} mmHg"),
        ("Heart Rate Recovery", f"{recovery} BPM"),
        ("Sleep Quality", f"{sleep_quality}%"),
        ("Daily Steps", f"{steps:,}"),
        ("Logged Context", ", ".join(st.session_state.logged_symptoms) if st.session_state.logged_symptoms else "None reported"),
    ]
    label_width = 95
    value_width = content_width - label_width
    for i, (label, value) in enumerate(rows):
        fill = (245, 245, 245) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(225, 225, 225)
        pdf.cell(label_width, 8, "  " + _pdf_safe(label), border="B", fill=True)
        pdf.cell(value_width, 8, _pdf_safe(value), border="B", fill=True, ln=True)
    pdf.ln(5)

    if positives:
        _pdf_section_header(pdf, "Favorable Findings", content_width, rgb=(0, 150, 170))
        pdf.set_font("Helvetica", "", 10.5)
        for p in positives:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_width, 6, _pdf_safe(f"-  {p}"))
        pdf.ln(2)

    if concerns:
        _pdf_section_header(pdf, "Findings Warranting Follow-Up", content_width, rgb=(244, 63, 94))
        pdf.set_font("Helvetica", "", 10.5)
        for c in concerns:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_width, 6, _pdf_safe(f"-  {c}"))
        pdf.ln(2)

    _pdf_section_header(pdf, "Summary for Clinical Review", content_width)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_x(pdf.l_margin)
    clinical_intro = (
        f"The following automated summary is derived from consumer wearable-device estimates "
        f"over the selected reporting period ({period_label}). It is intended to support, not "
        f"replace, clinical judgment."
    )
    pdf.multi_cell(content_width, 6, _pdf_safe(clinical_intro))
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(content_width, 6, _pdf_safe(ai_insight))
    pdf.ln(4)

    return bytes(pdf.output())

def animate_score(final_score):
    c = score_color(final_score)
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; padding:32px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#8FA69C;">Overall Vital Status</div>
            <div style="font-size:56px; font-weight:800; color:{c}; margin:8px 0; text-shadow:0 0 30px {hex_to_rgba(c, 0.4)};">
                {final_score}<span style="font-size:24px; color:#8FA69C;">/100</span>
            </div>
            <div style="display:inline-block; padding:4px 16px; border-radius:20px; background:{hex_to_rgba(c,0.15)}; color:{c}; font-weight:600; font-size:13px; border:1px solid {hex_to_rgba(c,0.3)};">
                {"EXCELLENT" if final_score>=80 else ("STABLE" if final_score>=60 else "ATTENTION REQUIRED")}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------------
# Top Floating Modern Navigation Header
# --------------------------------------------------
NAV_ITEMS = [
    "🏠 Home",
    "❤️ Heart Health",
    "⌚ Smartwatch",
    "📈 Health Summary",
    "🤖 AI Assistant",
    "🧠 AI Insights",
    "⚙️ Settings",
    "📝 Survey",
    "ℹ️ About"
]

if "current_page" not in st.session_state:
    st.session_state.current_page = NAV_ITEMS[0]

if "heart_dashboard_tab" not in st.session_state:
    st.session_state.heart_dashboard_tab = "📊 VITALS"

if "health_summary_scroll_target" not in st.session_state:
    st.session_state.health_summary_scroll_target = None


def render_alert_settings():
    """Notification settings: proactive email alerts + emergency contact.
    Lives on the Settings page (moved out of Device & Controls, which is
    for simulating the wearable device rather than account preferences)."""
    st.subheader("📧 Proactive Email Alerts")
    st.caption(
        "PulseGuard will email you when it detects a reading that's unusual for "
        "*your* own baseline — it doesn't wait for you to open the app."
    )
    with st.form("alert_settings_form"):
        sms_col1, sms_col2 = st.columns([2, 1])
        with sms_col1:
            _alert_email_input = st.text_input(
                "Email address to send alerts to",
                value=st.session_state.alert_email,
            )
        with sms_col2:
            _sms_enabled_input = st.checkbox(
                "Enable email alerts", value=st.session_state.sms_alerts_enabled
            )

        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        st.caption(
            "🚨 **Emergency contact** — someone PulseGuard can notify if you need help "
            "or your score drops low (a family member, friend, or caregiver)."
        )
        _emergency_email_input = st.text_input(
            "Emergency contact's email address",
            value=st.session_state.emergency_contact_email,
            placeholder="e.g. mom@example.com",
        )

        _alert_submitted = st.form_submit_button("💾 Submit", use_container_width=True)

    if _alert_submitted:
        _alert_email_input = _alert_email_input.strip()
        _emergency_email_input = _emergency_email_input.strip()
        if _sms_enabled_input and not _alert_email_input:
            st.session_state.alert_settings_status = ("error", "Enter an email address before enabling alerts.")
        else:
            st.session_state.alert_email = _alert_email_input
            st.session_state.sms_alerts_enabled = _sms_enabled_input
            st.session_state.emergency_contact_email = _emergency_email_input
            _saved_msgs = []
            if _sms_enabled_input:
                _saved_msgs.append(f"you'll get email alerts at {_alert_email_input}")
            else:
                _saved_msgs.append("email alerts are turned off")
            if _emergency_email_input:
                _saved_msgs.append(f"emergency contact set to {_emergency_email_input}")
            st.session_state.alert_settings_status = ("success", "Saved! " + "; ".join(_saved_msgs) + ".")

    _alert_status = st.session_state.get("alert_settings_status")
    if _alert_status:
        _status_kind, _status_msg = _alert_status
        getattr(st, _status_kind)(_status_msg)

    if st.session_state.sms_alerts_enabled and not email_alerts_configured():
        st.warning(
            "Email alerts are turned on, but the sending account isn't configured yet "
            "on the backend (needs ALERT_EMAIL_ADDRESS and ALERT_EMAIL_APP_PASSWORD in "
            "st.secrets — see the setup comment near the top of app.py)."
        )

    if st.session_state.emergency_contact_email:
        st.caption(
            f"✅ {st.session_state.emergency_contact_email} will be emailed automatically "
            "whenever PulseGuard detects your score has dropped — no extra action needed."
        )


SUBSCRIPTION_PRICE_STR = "$7.99/mo"


def render_subscription_paywall(feature_name):
    """Mock paywall shown in place of a gated AI feature. This is a
    front-end sample only — the 'card form' below does not talk to a
    real payment processor. It exists so you can see how the upsell
    and checkout flow would look and feel before wiring up real
    billing (e.g. Stripe Checkout / Billing)."""
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; padding:40px 24px;">
            <div style="font-size:40px;">🔒</div>
            <h2 style="margin:8px 0 4px 0;">{feature_name} is a Premium Feature</h2>
            <p style="color:#8FA69C; max-width:520px; margin:0 auto;">
                Unlock the AI Assistant chat and AI Insights (weekly story, correlation
                explorer, heart age & trajectory) with PulseGuard Premium.
            </p>
            <div style="font-size:32px; font-weight:800; color:#10B981; margin-top:16px;">
                {SUBSCRIPTION_PRICE_STR}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    _pw_col1, _pw_col2 = st.columns([1, 1])
    with _pw_col1:
        st.markdown(
            """
            <div class="glass-card">
                <h4 style="margin-top:0;">✅ What's included</h4>
                <p style="color:#C9E0D2;">
                🤖 Unlimited AI Assistant chat<br>
                🧠 Weekly AI-generated health story<br>
                🔗 Correlation explorer<br>
                📈 Heart age & 30-day trajectory<br>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with _pw_col2:
        st.markdown("<h4 style='margin-top:0;'>💳 Payment (sample only)</h4>", unsafe_allow_html=True)
        st.caption("This is a demo checkout UI — no real card is charged and nothing is sent anywhere.")
        with st.form("mock_subscribe_form"):
            st.text_input("Name on card", placeholder="Jane Doe", key="mock_card_name")
            st.text_input("Card number", placeholder="4242 4242 4242 4242", key="mock_card_number", max_chars=19)
            _exp_col, _cvc_col = st.columns(2)
            with _exp_col:
                st.text_input("Expiry", placeholder="MM/YY", key="mock_card_exp", max_chars=5)
            with _cvc_col:
                st.text_input("CVC", placeholder="123", key="mock_card_cvc", max_chars=4, type="password")
            _subscribe_clicked = st.form_submit_button(
                f"🔓 Subscribe — {SUBSCRIPTION_PRICE_STR}", use_container_width=True
            )
        if _subscribe_clicked:
            st.session_state.is_subscribed = True
            st.success("Subscribed! (Sample flow — no real payment was processed.)")
            st.rerun()

    st.caption(
        "In production this card form would be replaced with a real payment "
        "provider's hosted checkout (e.g. Stripe Checkout/Elements) — PulseGuard "
        "should never collect or store raw card numbers itself."
    )


def ai_features_unlocked():
    # Guests get a preview of the paywall too, but subscribing as a guest
    # won't persist since guest sessions aren't saved to the sheet.
    return st.session_state.is_subscribed


page = st.session_state.current_page

# --------------------------------------------------
# Live Data Sliders — instantiated BEFORE the nav bar / logout button below.
# Those buttons can call st.rerun() mid-script; if these sliders were defined
# AFTER them, a run that ends early via st.rerun() (before ever reaching the
# sliders) appears to Streamlit as "these widgets weren't on this run," which
# was clearing their session_state value back to default every time you
# switched tabs. Defining them first guarantees they're always instantiated
# before any rerun can fire, so their value never gets treated as stale.
# --------------------------------------------------
_devctrl_col, _boot_logout_col = st.columns([8.6, 1.4])
with _boot_logout_col:
    if st.button(f"🔓 Log out ({st.session_state.auth_username})", use_container_width=True, key="logout_top"):
        st.session_state.logged_in = False
        st.session_state.auth_username = None
        st.session_state.is_guest = False
        # Clear the "already loaded" flag and the actual data values so
        # the next login (even in this same browser tab/session) always
        # re-fetches fresh data from the sheet instead of reusing whatever
        # happens to still be sitting in session_state — otherwise a
        # second account logging in on the same tab could briefly see
        # the previous account's leftover data, or fall back to defaults.
        st.session_state.user_data_loaded = False
        for _k in PERSIST_KEYS:
            st.session_state.pop(_k, None)
        st.rerun()

with _devctrl_col:
    _devctrl_expander = st.expander("⚙️ Device & Controls", expanded=False)
with _devctrl_expander:
    st.caption("Customize live parameters or test automated simulation profiles.")
    device_col, action_col = st.columns([2, 1])
    with device_col:
        st.subheader("⌚ Select Wearable Interface")
        st.session_state.selected_watch = st.selectbox(
            "Simulated device",
            list(WATCH_OPTIONS.keys()),
            index=list(WATCH_OPTIONS.keys()).index(st.session_state.selected_watch)
        )
        watch_plain_name = " ".join(st.session_state.selected_watch.split(" ")[1:])
    with action_col:
        st.subheader("🎲 Controls")

        def _simulate_new_reading():
            st.session_state.heart_rate = random.randint(55, 130)
            st.session_state.resting_hr = random.randint(45, 90)
            st.session_state.hrv = random.randint(15, 90)
            st.session_state.blood_pressure_variability = random.randint(0, 20)
            st.session_state.heart_rate_recovery = random.randint(5, 40)
            st.session_state.sleep_quality = random.randint(30, 100)
            st.session_state.steps = random.randint(500, 15000)
            st.session_state.battery = random.randint(10, 100)

        st.button("🎲 Simulate New Reading", use_container_width=True, on_click=_simulate_new_reading)

        st.session_state.autoplay = st.checkbox(
            "▶️ Auto-Play Demo Scenarios",
            value=st.session_state.autoplay
        )

    st.markdown("---")

    # Apply any externally-set reading (e.g. from the camera scan) now,
    # before the sliders below are instantiated.
    if st.session_state.get("pending_camera_bpm") is not None:
        st.session_state.heart_rate = st.session_state.pending_camera_bpm
        st.session_state.pending_camera_bpm = None

    slider_row1 = st.columns(4)
    with slider_row1[0]:
        heart_rate = st.slider("❤️ Heart Rate (BPM)", 30, 180, key="heart_rate")
    with slider_row1[1]:
        resting_hr = st.slider("💓 Resting HR (BPM)", 30, 130, key="resting_hr")
    with slider_row1[2]:
        hrv = st.slider("📊 HRV (ms)", 0, 150, key="hrv")
    with slider_row1[3]:
        blood_pressure_variability = st.slider("🩺 BP Var (mmHg)", 0, 40, key="blood_pressure_variability")

    slider_row2 = st.columns(4)
    with slider_row2[0]:
        heart_rate_recovery = st.slider("🏃 Recovery (BPM)", 0, 60, key="heart_rate_recovery")
    with slider_row2[1]:
        sleep_quality = st.slider("😴 Sleep Quality (%)", 0, 100, key="sleep_quality")
    with slider_row2[2]:
        steps = st.slider("👟 Daily Steps", 0, 20000, step=100, key="steps")
    with slider_row2[3]:
        battery = st.slider("🔋 Watch Battery (%)", 0, 100, key="battery")

watch_connected = True
last_sync = datetime.now(ZoneInfo("America/New_York")).strftime("%I:%M %p")

# --------------------------------------------------
# Proactive email alert — runs on every app load/rerun (not just when the
# person opens the AI Assistant tab), so PulseGuard reaches out on its own
# the moment it sees something unusual, throttled to one email per day per
# account. Note: this only fires while the app is actually running — a
# true always-on watcher (emailing even while nobody has the app open)
# would need a separate scheduled job (cron / cloud function) hitting this
# same detect_anomalies() + send_sms_alert() logic outside of Streamlit.
# --------------------------------------------------
if st.session_state.sms_alerts_enabled and st.session_state.alert_email:
    _today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    if st.session_state.get("last_sms_alert_date") != _today_str:
        _sms_anomalies = detect_anomalies()
        if _sms_anomalies:
            _sms_msg = get_anomaly_alert_message(_sms_anomalies)
            if _sms_msg:
                _sent, _err = send_sms_alert(
                    st.session_state.alert_email,
                    f"PulseGuard alert: {_sms_msg}",
                )
                if _sent:
                    st.session_state.last_sms_alert_date = _today_str

# --------------------------------------------------
# Emergency contact alert — fires automatically (no button press) whenever
# the person's score has dropped, independent of and throttled separately
# from the alert above (once per day), the same way it's checked on every
# app load/rerun.
# --------------------------------------------------
if st.session_state.emergency_contact_email:
    _today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    if st.session_state.get("last_emergency_alert_date") != _today_str:
        _ec_anomalies = detect_anomalies()
        _ec_score, _, _ = generate_health_summary()
        if _ec_anomalies or _ec_score < 60:
            _who = st.session_state.patient_name.strip() or st.session_state.auth_username or "This user"
            _ec_message = (
                f"{_who} needs help, or their PulseGuard heart score is low "
                f"({_ec_score}/100). Please check up on them, or call for medical "
                f"help if this seems urgent."
            )
            _ec_sent, _ec_err = send_sms_alert(
                st.session_state.emergency_contact_email,
                _ec_message,
            )
            if _ec_sent:
                st.session_state.last_emergency_alert_date = _today_str

# Application Layout Header
st.markdown(
    f"""
    <div class="top-navbar">
        <div class="navbar-brand">
            <img src="{LOGO_URL}" width="38" style="border-radius:10px; filter: drop-shadow(0 0 8px rgba(16, 185, 129,0.4));">
            <div>
                <div class="navbar-title">PulseGuard</div>
            </div>
            <div style="display:flex; align-items:center; gap:6px; background:rgba(255, 107, 107, 0.12); border:1px solid rgba(255, 107, 107, 0.24); padding:4px 12px; border-radius:20px; margin-left:12px;">
                <div class="pulse-dot"></div>
                <span style="font-size:11px; font-weight:700; color:#FF6B6B; letter-spacing:0.05em;">LIVE MONITORING</span>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="font-size:12px; color:#8FA69C; font-family:'JetBrains Mono', monospace;">
                {datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y")}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Pill Navigation Bar
st.markdown(
    """
    <style>
    /* Bigger top nav pills (Home / Heart Health / Smartwatch / etc.) */
    .st-key-main_nav_bar .stButton > button {
        font-size: 26px !important;
        font-weight: 800 !important;
        padding: 1.4rem 1rem !important;
        min-height: 78px !important;
        line-height: 1.25 !important;
        white-space: normal !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
_nav_bar = st.container(key="main_nav_bar")
with _nav_bar:
    _nav_cols = st.columns(len(NAV_ITEMS))
    for _col, _item in zip(_nav_cols, NAV_ITEMS):
        with _col:
            _is_active = st.session_state.current_page == _item
            if st.button(_item, key=f"nav_{_item}", use_container_width=True,
                         type="primary" if _is_active else "secondary"):
                st.session_state.current_page = _item
                st.rerun()

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# =====================================================
# HOME PAGE
# =====================================================
if page == "🏠 Home":

    _today_score, _today_positives, _today_concerns = generate_health_summary()
    _score_color = score_color(_today_score)

    current_hour = datetime.now(ZoneInfo("America/New_York")).hour
    time_greeting = "Good morning" if current_hour < 12 else ("Good afternoon" if current_hour < 18 else "Good evening")

    st.markdown(
        f"""
        <div class="glass-card" style="padding:28px; background: linear-gradient(135deg, rgba(13, 26, 20, 0.95) 0%, rgba(8, 20, 15, 0.98) 100%);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;">
                <div>
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                        <span style="font-size:28px; font-weight:800; color:#FFFFFF;">{time_greeting}! 👋</span>
                        <div style="display:flex; align-items:center; gap:8px; background:rgba(255, 107, 107, 0.12); border:1px solid rgba(255, 107, 107, 0.24); padding:4px 14px; border-radius:20px;">
                            <div class="pulse-dot"></div>
                            <span style="font-size:12px; font-weight:700; color:#FF6B6B; letter-spacing:0.04em;">LIVE {st.session_state.heart_rate} BPM</span>
                        </div>
                    </div>
                    <div style="font-size:18px; font-weight:600; color:#E2EDE6;">
                        Your heart health is looking steady and resilient today.
                    </div>
                    <div style="font-size:13px; color:#8FA69C; margin-top:6px;">
                        Continuous telemetry streaming from {st.session_state.selected_watch} • Synced {last_sync}
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:16px;">
                    <div style="background:{hex_to_rgba(_score_color, 0.12)}; border:1px solid {hex_to_rgba(_score_color, 0.35)}; padding:12px 20px; border-radius:18px; text-align:center;">
                        <div style="font-size:11px; font-weight:700; color:#8FA69C; text-transform:uppercase; letter-spacing:0.06em;">Vital Score</div>
                        <div style="font-size:28px; font-weight:800; color:{_score_color}; font-family:'Plus Jakarta Sans';">{_today_score}<span style="font-size:14px; color:#8FA69C;">/100</span></div>
                    </div>
                    <div style="background:rgba(251, 191, 36, 0.1); border:1px solid rgba(251, 191, 36, 0.3); padding:12px 20px; border-radius:18px; text-align:center;">
                        <div style="font-size:11px; font-weight:700; color:#8FA69C; text-transform:uppercase; letter-spacing:0.06em;">Active Streak</div>
                        <div style="font-size:28px; font-weight:800; color:#FBBF24;">🔥 {st.session_state.streak_days} <span style="font-size:14px; color:#8FA69C;">Days</span></div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    focus_insight = "Your HRV dipped slightly below average today. A brief 10-minute walk or controlled breathing exercise will promote parasympathetic recovery."
    if st.session_state.hrv >= 60:
        focus_insight = "Your HRV is exceptional today! Your body is fully recovered and primed for optimal physical performance."
    elif st.session_state.resting_hr > 75:
        focus_insight = "Resting heart rate is elevated. Ensure hydration levels are met and limit afternoon caffeine intake."

    st.markdown(
        f"""
        <div class="glass-card" style="border-left: 5px solid #4C9BBF; padding:26px 30px;">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:18px;">
                    <div style="font-size:34px; background:rgba(16, 185, 129,0.12); padding:14px; border-radius:16px;">🎯</div>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#4C9BBF; text-transform:uppercase; letter-spacing:0.08em;">Today's Mission</div>
                        <div style="font-size:19px; color:#F0F7F2; font-weight:600; margin-top:4px;">{focus_insight}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:12px; font-weight:700; color:#8FA69C; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:10px;'>⚡ Quick Actions</div>", unsafe_allow_html=True)
    qa_cols = st.columns(6)
    with qa_cols[0]:
        def _simulate_quick_vitals():
            st.session_state.heart_rate = random.randint(55, 130)
            st.session_state.resting_hr = random.randint(45, 90)
            st.session_state.hrv = random.randint(15, 90)
            st.session_state.steps = random.randint(1000, 14000)
            st.session_state.activity_feed.insert(0, {"time": "Just now", "event": "Simulated new telemetry sync"})

        st.button("🎲 Simulate New Vitals", use_container_width=True, on_click=_simulate_quick_vitals)
    with qa_cols[1]:
        if st.button("📋 Download Clinical Report", use_container_width=True):
            st.session_state.current_page = "📈 Health Summary"
            st.session_state.health_summary_scroll_target = "doctor_report"
            st.rerun()
    with qa_cols[2]:
        if st.button("🤖 Ask AI Assistant", use_container_width=True):
            st.session_state.current_page = "🤖 AI Assistant"
            st.rerun()
    with qa_cols[3]:
        if st.button("🫀 Open 3D Heart Model", use_container_width=True):
            st.session_state.current_page = "❤️ Heart Health"
            st.session_state.heart_dashboard_tab = "🫀 3D MODEL"
            st.rerun()
    with qa_cols[4]:
        if st.button("🗞️ Weekly Story", use_container_width=True):
            st.session_state.current_page = "🧠 AI Insights"
            st.rerun()
    with qa_cols[5]:
        if st.button("🩺 More Accurate Details", use_container_width=True, type="primary" if st.session_state.symptom_risk_adjustment else "secondary"):
            st.session_state.show_symptom_check = not st.session_state.show_symptom_check

    st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # Symptom check-in — sends how the person actually feels right now
    # (not just wearable numbers) to Gemini alongside their live telemetry,
    # and lets it pull today's Vital Score down to reflect it.
    # --------------------------------------------------
    if st.session_state.show_symptom_check:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:14px; font-weight:800; color:var(--accent); text-transform:uppercase; "
                "letter-spacing:0.06em; margin-bottom:4px;'>🩺 Symptom Check-In</div>"
                "<div style='font-size:13px; color:#8FA69C; margin-bottom:14px;'>"
                "Tell us how you're actually feeling and we'll factor it into your Vital Score, "
                "on top of your wearable readings.</div>",
                unsafe_allow_html=True,
            )
            symptom_options = [
                "Chest pain or pressure", "Shortness of breath", "Dizziness or lightheadedness",
                "Heart palpitations / racing heart", "Unusual fatigue", "Nausea",
                "Swelling in legs or ankles", "Cold sweats",
            ]
            picked_symptoms = st.multiselect("Symptoms you're experiencing right now", symptom_options)
            extra_notes = st.text_area(
                "Anything else worth mentioning? (when it started, how severe, what you were doing, etc.)",
                height=90,
            )
            sc_col1, sc_col2 = st.columns([1, 1])
            with sc_col1:
                submit_check = st.button("Update Risk Score", use_container_width=True, type="primary")
            with sc_col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_symptom_check = False
                    st.rerun()

            if submit_check:
                if not picked_symptoms and not extra_notes.strip():
                    st.warning("Select at least one symptom or add a note before updating your score.")
                else:
                    with st.spinner("Analyzing your symptoms alongside your telemetry..."):
                        adjustment, explanation, error = get_symptom_risk_assessment(picked_symptoms, extra_notes)
                    if error and adjustment == 0 and explanation is None:
                        st.error(error)
                    else:
                        st.session_state.symptom_risk_adjustment = adjustment
                        st.session_state.symptom_risk_note = explanation
                        st.session_state.symptom_check_at = datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %I:%M %p")
                        st.session_state.activity_feed.insert(0, {
                            "time": "Just now",
                            "event": f"Symptom check-in completed (score adjusted {adjustment:+d})" if adjustment else "Symptom check-in completed",
                        })
                        st.success(f"Heart risk score updated. {('Adjustment: ' + str(adjustment) + ' points.') if adjustment else 'No adjustment needed based on what you reported.'}")
                        if explanation:
                            st.info(explanation)
                        st.session_state.show_symptom_check = False
                        st.rerun()

    if st.session_state.symptom_risk_adjustment and not st.session_state.show_symptom_check:
        st.markdown(
            f"""
            <div class="glass-card" style="border-left: 4px solid {WARN}; padding:14px 22px; margin-bottom:16px;">
                <div style="font-size:12px; font-weight:800; color:{WARN}; text-transform:uppercase; letter-spacing:0.06em;">
                    🩺 Symptom Check-In Applied ({st.session_state.symptom_check_at})
                </div>
                <div style="font-size:13px; color:#E2EDE6; margin-top:4px;">{st.session_state.symptom_risk_note or ''}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='font-size:12px; font-weight:700; color:#8FA69C; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px;'>📊 Core Telemetry Metrics</div>", unsafe_allow_html=True)
    
    hr_status, hr_color, _ = metric_status("heart_rate", heart_rate)
    rhr_status, rhr_color, _ = metric_status("resting_hr", resting_hr)
    hrv_status, hrv_color, _ = metric_status("hrv", hrv)
    bp_status, bp_color, _ = metric_status("bp_variability", blood_pressure_variability)

    stat_cols = st.columns(4)
    with stat_cols[0]:
        render_metric_card("Heart Rate", f"{heart_rate} BPM", hr_color, "Better than 74% of peers", "↑ +2 vs avg", "trend-up")
    with stat_cols[1]:
        render_metric_card("Resting HR", f"{resting_hr} BPM", rhr_color, "Optimal resting baseline", "↓ -1 vs avg", "trend-neutral")
    with stat_cols[2]:
        render_metric_card("HRV Recovery", f"{hrv} ms", hrv_color, "Autonomic nervous balance", "↑ +5 ms", "trend-up")
    with stat_cols[3]:
        render_metric_card("BP Variability", f"{blood_pressure_variability} mmHg", bp_color, "Vascular resistance marker", "Stable", "trend-neutral")

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    col_timeline, col_habits = st.columns([1, 1])

    with col_timeline:
        st.markdown('<div class="glass-card" style="padding:22px;">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; font-weight:800; color:#4C9BBF; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:14px;'>🕒 Live Telemetry Activity Feed</div>", unsafe_allow_html=True)
        
        feed_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
        for item in st.session_state.activity_feed[:4]:
            feed_html += f"""
            <div style='display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:8px;'>
                <div style='display:flex; align-items:center; gap:10px;'>
                    <div style='width:6px; height:6px; border-radius:50%; background:#4C9BBF;'></div>
                    <span style='font-size:13px; color:#F0F7F2; font-weight:500;'>{item['event']}</span>
                </div>
                <span style='font-size:11px; color:#8FA69C; font-family:"JetBrains Mono";'>{item['time']}</span>
            </div>
            """
        feed_html += "</div>"
        st.markdown(feed_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_habits:
        st.markdown('<div class="glass-card" style="padding:22px;">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; font-weight:800; color:#F59E0B; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:14px;'>🎯 Goal Rings & Habit Progress</div>", unsafe_allow_html=True)

        step_pct = min(100, int((steps / 10000) * 100))
        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px;'><span>👟 Step Goal ({steps:,} / 10,000)</span><span style='color:#4C9BBF; font-weight:700;'>{step_pct}%</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{step_pct}%; background:#4C9BBF;'></div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px;'><span>😴 Sleep Quality Target</span><span style='color:#F59E0B; font-weight:700;'>{sleep_quality}%</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{sleep_quality}%; background:#F59E0B;'></div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        hyd_pct = min(100, int((st.session_state.hydration_oz / 64) * 100))
        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px;'><span>💧 Hydration Goal ({st.session_state.hydration_oz} / 64 oz)</span><span style='color:#38BDF8; font-weight:700;'>{hyd_pct}%</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{hyd_pct}%; background:#38BDF8;'></div></div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# HEART DASHBOARD PAGE
# =====================================================
elif page == "❤️ Heart Health":

    st.markdown("<h2 style='font-weight:800;'>❤️ Cardiovascular Analytics</h2>", unsafe_allow_html=True)
    st.caption("Deep-dive metrics evaluating real-time heart rate dynamics and autonomic recovery.")
    st.markdown("---")

    heart_dashboard_tabs = ["📊 VITALS", "🫀 3D MODEL", "💓 ECG WAVEFORM"]
    current_section = st.radio(
        "",
        heart_dashboard_tabs,
        index=heart_dashboard_tabs.index(st.session_state.heart_dashboard_tab),
        horizontal=True,
        label_visibility="collapsed",
        key="heart_dashboard_tab",
    )
    st.markdown("<div style='margin-bottom:18px;'></div>", unsafe_allow_html=True)

    if current_section == "📊 VITALS":
        st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            status, color, pct = metric_status("heart_rate", heart_rate)
            render_vital_card("❤️", "Heart Rate", f"{heart_rate} BPM", status, color, pct,
                               "Normal resting range: 60–100 BPM")
        with col2:
            status, color, pct = metric_status("resting_hr", resting_hr)
            render_vital_card("🌙", "Resting Heart Rate", f"{resting_hr} BPM", status, color, pct,
                               "Healthy baseline: 50–80 BPM")
        with col3:
            status, color, pct = metric_status("hrv", hrv)
            render_vital_card("📶", "Heart Rate Variability", f"{hrv} ms", status, color, pct,
                               "Higher values indicate stronger recovery")

        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        col4, col5, col6 = st.columns(3)
        with col4:
            status, color, pct = metric_status("bp_variability", blood_pressure_variability)
            render_vital_card("🩸", "Blood Pressure Variability", f"{blood_pressure_variability} mmHg", status, color, pct,
                               "Stable range: below 10 mmHg")
        with col5:
            status, color, pct = metric_status("recovery", heart_rate_recovery)
            render_vital_card("🔄", "Heart Rate Recovery", f"{heart_rate_recovery} BPM", status, color, pct,
                               "Drop within 1 min post-exertion: 20+ BPM is optimal")
        with col6:
            status, color, pct = metric_status("sleep", sleep_quality)
            render_vital_card("😴", "Sleep Quality", f"{sleep_quality}%", status, color, pct,
                               "Restful sleep target: 80%+ quality score")

    elif current_section == "🫀 3D MODEL":
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🫀 Interactive 3D Anatomical Heart")
        st.caption("Drag to rotate, scroll to zoom, hover the glowing nodes to explore key structures. Nodes marked LIVE reflect your current readings.")
        render_3d_heart(
            hr=heart_rate,
            hrv=hrv,
            resting_hr=resting_hr,
            blood_pressure_variability=blood_pressure_variability,
            heart_rate_recovery=heart_rate_recovery,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        render_heart_structure_reference()

    else:
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("💓 Simulated Real-Time Waveform (ECG)")
        render_ecg_animation(heart_rate)
        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# SMARTWATCH CONNECTION PAGE
# =====================================================
elif page == "⌚ Smartwatch":

    st.markdown("<h2 style='font-weight:800;'>⌚ Connected Wearable Device</h2>", unsafe_allow_html=True)
    st.caption("Interface and telemetry streaming settings for paired devices.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="glass-card" style="border-left: 4px solid #4C9BBF;">
                <div style="font-size:12px; font-weight:700; color:#8FB0C1; text-transform:uppercase;">Connected Device</div>
                <div style="font-size:28px; font-weight:800; color:#FFFFFF; margin:8px 0;">{watch_plain_name}</div>
                <div style="display:flex; gap:16px; margin-top:16px;">
                    <div><span style="color:#8FB0C1; font-size:12px;">Battery:</span> <strong style="color:#4C9BBF;">{battery}%</strong></div>
                    <div><span style="color:#8FB0C1; font-size:12px;">Last Sync:</span> <strong>{last_sync}</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Supported Ecosystems")
        st.write("⚡ Apple HealthKit • WHOOP • Oura Ring • Garmin Connect • Google Fit")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
    st.markdown("<h3>📷 No Watch? Scan Your Pulse With Your Camera</h3>", unsafe_allow_html=True)
    st.caption(
        "Uses your webcam to detect tiny color changes in your face caused by blood flow (a technique "
        "called remote photoplethysmography). Works best in steady, bright light while holding still."
    )

    components.html(
        """
        <div style="font-family: Inter, sans-serif; color: #EAF7F0; max-width: 480px;">
            <div style="position:relative; width:320px; height:240px; border-radius:12px; overflow:hidden;
                        background:#000; border:1px solid rgba(255,255,255,0.1);">
                <video id="pg-video" autoplay playsinline muted
                    style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);"></video>
                <div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
                            pointer-events:none;">
                    <div style="width:130px; height:170px; border:2px dashed rgba(16, 185, 129,0.6); border-radius:50%;"></div>
                </div>
            </div>
            <canvas id="pg-canvas" width="64" height="64" style="display:none;"></canvas>

            <div style="margin-top:12px; display:flex; align-items:center; gap:10px;">
                <button id="pg-start-btn" style="background:#4C9BBF; color:#071722; border:none; padding:10px 18px;
                    border-radius:8px; font-weight:700; cursor:pointer;">▶ Start 20s Scan</button>
                <div id="pg-status" style="font-size:13px; color:#8FB0C1;">Camera not started yet.</div>
            </div>

            <div style="margin-top:10px; height:6px; width:320px; background:rgba(255,255,255,0.08); border-radius:4px; overflow:hidden;">
                <div id="pg-progress" style="height:100%; width:0%; background:#4C9BBF; transition:width 0.2s linear;"></div>
            </div>

            <div id="pg-result" style="margin-top:16px; font-size:15px;"></div>
        </div>

        <script>
        (function() {
            const startBtn = document.getElementById('pg-start-btn');
            const status = document.getElementById('pg-status');
            const progress = document.getElementById('pg-progress');
            const resultBox = document.getElementById('pg-result');
            const video = document.getElementById('pg-video');
            const canvas = document.getElementById('pg-canvas');
            const ctx = canvas.getContext('2d');

            const SCAN_MS = 20000;
            const SAMPLE_INTERVAL_MS = 66; // ~15 fps

            startBtn.addEventListener('click', async function() {
                resultBox.innerHTML = '';
                startBtn.disabled = true;
                startBtn.style.opacity = 0.6;
                status.textContent = 'Requesting camera permission...';

                let stream;
                try {
                    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
                } catch (err) {
                    status.textContent = 'Camera access was blocked or unavailable: ' + err.message;
                    startBtn.disabled = false;
                    startBtn.style.opacity = 1;
                    return;
                }
                video.srcObject = stream;
                status.textContent = 'Hold still and keep your face steady...';

                const samples = [];
                const startTime = Date.now();

                const sampleTimer = setInterval(function() {
                    const elapsed = Date.now() - startTime;
                    progress.style.width = Math.min(100, (elapsed / SCAN_MS) * 100) + '%';

                    try {
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const frame = ctx.getImageData(16, 16, 32, 32).data; // central region only
                        let sum = 0, count = 0;
                        for (let i = 0; i < frame.length; i += 4) {
                            sum += frame[i + 1]; // green channel
                            count++;
                        }
                        samples.push({ t: elapsed / 1000, v: sum / count });
                    } catch (e) { /* frame not ready yet, skip */ }

                    if (elapsed >= SCAN_MS) {
                        clearInterval(sampleTimer);
                        stream.getTracks().forEach(t => t.stop());
                        finishScan(samples);
                    }
                }, SAMPLE_INTERVAL_MS);
            });

            function finishScan(samples) {
                status.textContent = 'Processing your scan...';
                progress.style.width = '100%';

                if (samples.length < 30) {
                    status.textContent = 'Scan too short or camera too slow — try again.';
                    startBtn.disabled = false;
                    startBtn.style.opacity = 1;
                    return;
                }

                const values = samples.map(s => s.v);

                // Detrend: subtract a ~1.5s moving average to remove slow lighting drift.
                const winLong = Math.max(3, Math.round(1.5 * 1000 / SAMPLE_INTERVAL_MS));
                const detrended = values.map((v, i) => {
                    const start = Math.max(0, i - winLong);
                    const window = values.slice(start, i + 1);
                    const avg = window.reduce((a, b) => a + b, 0) / window.length;
                    return v - avg;
                });

                // Light smoothing to reduce single-frame noise.
                const smoothed = detrended.map((v, i) => {
                    const a = detrended[Math.max(0, i - 1)];
                    const b = detrended[Math.min(detrended.length - 1, i + 1)];
                    return (a + v + b) / 3;
                });

                // Peak detection with a minimum spacing so we don't count noise as
                // multiple beats (human heart rate physically can't exceed ~220bpm).
                const minSpacingSec = 60 / 220;
                const peakTimes = [];
                for (let i = 2; i < smoothed.length - 2; i++) {
                    if (smoothed[i] > smoothed[i - 1] && smoothed[i] > smoothed[i + 1] && smoothed[i] > 0.5) {
                        const t = samples[i].t;
                        if (peakTimes.length === 0 || t - peakTimes[peakTimes.length - 1] >= minSpacingSec) {
                            peakTimes.push(t);
                        }
                    }
                }

                if (peakTimes.length < 4) {
                    resultBox.innerHTML = '<div style="color:#FB7185;">Couldn\\'t get a clear reading. ' +
                        'Try again with brighter, steady lighting and stay still.</div>';
                    status.textContent = 'Scan complete — low signal quality.';
                    startBtn.disabled = false;
                    startBtn.style.opacity = 1;
                    return;
                }

                const intervals = [];
                for (let i = 1; i < peakTimes.length; i++) {
                    intervals.push(peakTimes[i] - peakTimes[i - 1]);
                }
                const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
                let bpm = Math.round(60 / avgInterval);
                bpm = Math.max(40, Math.min(180, bpm));

                status.textContent = 'Scan complete.';
                resultBox.innerHTML =
                    '<div style="font-size:34px; font-weight:800; color:#FF6B6B;">' + bpm + ' BPM</div>' +
                    '<div style="color:#8FB0C1; font-size:13px; margin-top:4px;">Detected from ' + peakTimes.length +
                    ' pulses over 20 seconds. Type this number into the field below to apply it to your dashboard.</div>';

                startBtn.disabled = false;
                startBtn.style.opacity = 1;
                startBtn.textContent = '▶ Scan Again';
            }
        })();
        </script>
        """,
        height=420,
    )

    st.caption(
        "A browser-based widget can't write directly into the app's backend, so once you see your BPM "
        "above, enter it here and confirm to apply it."
    )
    scan_col1, scan_col2 = st.columns([1, 1])
    with scan_col1:
        scanned_bpm = st.number_input("Detected BPM from scan", min_value=40, max_value=180, value=st.session_state.heart_rate, key="camera_scan_bpm")
    with scan_col2:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        if st.button("✅ Apply to My Dashboard", use_container_width=True):
            st.session_state.pending_camera_bpm = int(scanned_bpm)
            st.session_state.camera_apply_confirm = int(scanned_bpm)
            st.session_state.activity_feed.insert(0, {
                "time": "just now",
                "event": f"Heart rate updated to {int(scanned_bpm)} BPM via camera scan"
            })
            st.rerun()

    if st.session_state.get("camera_apply_confirm"):
        st.success(f"Applied — your heart rate is now set to {st.session_state.camera_apply_confirm} BPM. Current session_state.heart_rate is now {st.session_state.heart_rate}.")
        st.session_state.camera_apply_confirm = None

# =====================================================
# HEALTH SUMMARY PAGE
# =====================================================
elif page == "📈 Health Summary":

    st.markdown("<h2 style='font-weight:800;'>📈 Daily Health Summary & Analytics</h2>", unsafe_allow_html=True)
    st.markdown("---")

    score, positives, concerns = generate_health_summary()

    # Trend strip: 7/30-day score sparkline with a range toggle.
    with st.container(border=True):
        trend_label_col, trend_range_col = st.columns([2, 1])
        with trend_range_col:
            trend_range = st.radio(
                "Trend range", ["7d", "30d"], horizontal=True,
                label_visibility="collapsed", key="score_trend_range",
            )
        trend_days = 7 if trend_range == "7d" else 30
        trend_scores = get_score_trend(days=trend_days)
        trend_delta = trend_scores[-1] - trend_scores[0]
        delta_color = GOOD if trend_delta >= 0 else DANGER
        delta_sign = "+" if trend_delta >= 0 else ""
        with trend_label_col:
            st.markdown(
                f"""
                <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#8FA69C;">Score trend, last {trend_range}</div>
                <div style="font-size:14px; color:{delta_color}; margin-top:2px;">{delta_sign}{trend_delta} vs {trend_range} ago</div>
                """,
                unsafe_allow_html=True,
            )
        render_trend_sparkline(trend_scores)

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    gauge_col, anim_col = st.columns([1, 1])
    with gauge_col:
        with st.container(border=True):
            render_score_gauge(score)
    with anim_col:
        animate_score(score)

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # Biggest-driver callout.
    driver = get_biggest_driver()
    with st.container(border=True):
        if driver:
            driver_label, _ = driver
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:18px;">⚡</span>
                    <span style="font-size:14px; color:#EAF7F0;">{driver_label} is the biggest drag on today's score.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:18px;">✨</span>
                    <span style="font-size:14px; color:#EAF7F0;">Every tracked metric is in a healthy range today.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("🧠 PulseGuard AI Clinical Summary")
        ai_insight = generate_ai_insight(score, positives, concerns)
        st.write(ai_insight)

    if positives:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        st.write("### ✅ Favorable Parameters")
        render_chips([(p, GOOD) for p in positives])

    if concerns:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        st.write("### ⚠ Areas Requiring Attention")
        render_chips([(c, DANGER) for c in concerns])

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown('<div id="health_summary_report"></div>', unsafe_allow_html=True)
    
    # Custom styling applied to the Doctor Report section to override Streamlit defaults
    st.markdown(
        """
        <style>
        /* Report card theme matching overall glass style */
        .st-key-report_card { color: #EAF9F0 !important; }
        .st-key-report_card .report-metric-value { color: #FFFFFF !important; font-weight:800; font-size:36px; opacity:1 !important; text-shadow: 0 2px 10px rgba(0,0,0,0.6); }
        .st-key-report_card .report-metric-label { color:#9AB0A5 !important; font-size:12px; margin-top:6px; }

        /* Direct native input overrides to enforce dark background & match UI scheme */
        .st-key-report_card input[type="text"],
        .st-key-report_card div[data-baseweb="select"] > div,
        .st-key-report_card div[data-baseweb="input"] > div,
        .st-key-report_card .stTextInput input,
        .st-key-report_card .stSelectbox [data-baseweb="select"] {
            background-color: rgba(13, 26, 20, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            color: #EAF7F0 !important;
            border-radius: 10px !important;
        }

        /* Download Button Styling - Dark Primary Gradient */
        .st-key-report_card button[kind="primary"],
        .st-key-report_card div.stDownloadButton > button {
            background: linear-gradient(135deg, #10B981 0%, #F59E0B 100%) !important;
            color: #050F0B !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            border: none !important;
            box-shadow: 0 6px 30px rgba(56, 189, 248,0.25) !important;
            transition: all 0.2s ease !important;
        }
        .st-key-report_card button[kind="primary"]:hover,
        .st-key-report_card div.stDownloadButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 35px rgba(16, 185, 129,0.4) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    report_card = st.container(border=True, key="report_card")
    with report_card:
        rec_message, rec_color = get_doctor_recommendation(score)
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px; padding-bottom:16px; margin-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.08);">
                <span style="font-size:22px;">🩺</span>
                <span style="font-size:14px; color:{rec_color}; font-weight:600; line-height:1.5;">{rec_message}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.subheader("🩺 Download Doctor Report")
        st.caption("Choose a reporting window and export a PDF summary for your clinician.")

        # Render Patient Name above the Report Window selector and save to session_state
        patient_name = st.text_input(
            "Patient name",
            value=st.session_state.get("patient_name", ""),
            placeholder="Enter patient or user name",
        )

        st.session_state.patient_name = patient_name

        period_key = st.selectbox(
            "Report window",
            ["24h", "7d", "30d", "custom"],
            format_func=lambda option: {
                "24h": "Last 24 hours",
                "7d": "Last 7 days",
                "30d": "Last 30 days",
                "custom": "Custom date range",
            }[option],
            index=1,
        )

        if period_key == "custom":
            custom_start_col, custom_end_col = st.columns(2)
            with custom_start_col:
                start_date = st.date_input("Start date", value=datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=6))
            with custom_end_col:
                end_date = st.date_input("End date", value=datetime.now(ZoneInfo("America/New_York")).date())
            if end_date < start_date:
                st.warning("End date must be after the start date.")
                report_ready = False
            else:
                report_ready = True
        else:
            start_date = None
            end_date = None
            report_ready = True

        if report_ready:
            start_dt, end_dt, period_label = build_report_window(period_key, start_date, end_date)
            report_rows = get_report_rows(start_dt, end_dt)
            summary = summarize_report_rows(report_rows)

            if report_rows:
                st.write(f"Selected range: {period_label} • {len(report_rows)} daily entries")
                mcols = st.columns(4)
                labels = ["Avg Heart Rate", "Avg Sleep", "Avg Steps", "Peak Steps"]
                values = [
                    f"{summary.get('avg_heart_rate', 'n/a')} BPM",
                    f"{summary.get('avg_sleep', 'n/a')}%",
                    f"{summary.get('avg_steps', 'n/a'):,}",
                    f"{summary.get('max_steps', 'n/a'):,}",
                ]
                for col, lab, val in zip(mcols, labels, values):
                    with col:
                        st.markdown(
                            f"""
                            <div style='text-align:left; padding:12px 8px;'>
                                <div class='report-metric-value'>{val}</div>
                                <div class='report-metric-label'>{lab}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
            else:
                st.info("No telemetry history is available for the selected range.")

            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

            # Generate the PDF via an explicit button click. Clicking a normal
            # button always forces any pending text_input edits (like patient
            # name) to sync to the backend first, so the PDF is guaranteed to
            # be built with the latest typed value instead of a stale one.
            if st.button("📝 Generate Report", use_container_width=True):
                st.session_state.doctor_report_pdf_bytes = generate_doctor_report_pdf(
                    report_rows, period_label, patient_name=patient_name
                )
                st.session_state.doctor_report_period_key = period_key

            if st.session_state.get("doctor_report_pdf_bytes"):
                downloaded = st.download_button(
                    label="⬇️ Download PDF for Doctor",
                    data=st.session_state.doctor_report_pdf_bytes,
                    file_name=f"pulseguard_{st.session_state.get('doctor_report_period_key', period_key)}_{datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

                st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                doctor_email = st.text_input("📧 Doctor's email", placeholder="doctor@clinic.com", key="doctor_email_input")
                if doctor_email:
                    subject = quote(f"PulseGuard Heart Health Report — {period_label}")
                    body = quote(
                        "Hi,\n\nI'm sharing my PulseGuard heart health report with you. I've attached the "
                        "PDF I downloaded from the app — you'll need to attach it manually since browsers "
                        "don't allow apps to auto-attach files to an email for security reasons.\n\nThanks!"
                    )
                    gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(doctor_email)}&su={subject}&body={body}"
                    st.link_button("📧 Open Gmail to Send to Doctor", gmail_url, use_container_width=True)
                    st.caption(
                        "This opens Gmail with your doctor's email, subject, and a note already filled in — "
                        "just attach the PDF you downloaded above before hitting send. Browsers can't auto-attach "
                        "files to an email link, so that one step has to stay manual."
                    )

                # Once downloaded, clear it so the button disappears — the person
                # has to press Generate Report again (with whatever name/window
                # they currently have set) before they can download again.
                if downloaded:
                    st.session_state.doctor_report_pdf_bytes = None
                    st.rerun()
            else:
                st.caption("Click **Generate Report** to build the PDF before downloading.")

    if st.session_state.health_summary_scroll_target == "doctor_report":
        components.html(
            "<script>setTimeout(()=>{const parent = window.parent || window; const el = parent.document.getElementById('health_summary_report'); if(el){el.scrollIntoView({behavior:'smooth', block:'start'});}}, 250);</script>",
            height=1,
        )
        st.session_state.health_summary_scroll_target = None

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("📲 Share Your Heart Score")
        st.caption("Generate a story-shaped card of today's score to post on Instagram, Snapchat, or anywhere else.")

        if st.button("✨ Generate Share Card", use_container_width=True):
            _current_proj, _projected_score, _slope = compute_score_projection(days_ahead=30)
            _trend_word = "improving" if _slope > 0.05 else "declining" if _slope < -0.05 else "steady"
            st.session_state.share_card_png_bytes = generate_share_card(
                score=score,
                resting_hr=st.session_state.resting_hr,
                hrv=st.session_state.hrv,
                sleep_quality=st.session_state.sleep_quality,
                streak_days=st.session_state.streak_days,
                patient_name=st.session_state.patient_name,
                trend_word=_trend_word,
            )

        if st.session_state.get("share_card_png_bytes"):
            preview_col, _spacer_col = st.columns([1, 1])
            with preview_col:
                st.image(st.session_state.share_card_png_bytes, use_container_width=True)
            st.download_button(
                label="⬇️ Download Story Card (PNG)",
                data=st.session_state.share_card_png_bytes,
                file_name=f"pulseguard_heart_score_{datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d')}.png",
                mime="image/png",
                use_container_width=True,
            )
            st.caption(
                "Sized for Instagram/Snapchat Stories (1080×1920, PNG) — a PNG shares cleanly on social "
                "apps, unlike a PDF which most platforms won't render as an image. Just save it and post "
                "like any other photo."
            )
        else:
            st.caption("Click **Generate Share Card** to build a story-ready image of today's heart score.")


# =====================================================
# AI CHAT ASSISTANT PAGE
# =====================================================
elif page == "🤖 AI Assistant":

    st.markdown("<h2 style='font-weight:800;'>🤖 PulseGuard AI Assistant</h2>", unsafe_allow_html=True)
    st.caption("Ask questions about your telemetry, resting trends, or HRV values.")
    st.markdown("---")

    if not ai_features_unlocked():
        render_subscription_paywall("The AI Assistant")
    else:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                ("assistant", "Hello! I am your PulseGuard AI companion. How can I help analyze your cardiovascular metrics today?")
            ]

        # Proactively flag anything unusual compared to this person's own
        # baseline, once per session, instead of waiting for them to ask.
        if not st.session_state.anomaly_alert_shown:
            st.session_state.anomaly_alert_shown = True
            anomalies = detect_anomalies()
            if anomalies:
                alert_msg = get_anomaly_alert_message(anomalies)
                if alert_msg:
                    st.session_state.chat_history.append(("assistant", alert_msg))

        for role, content in st.session_state.chat_history:
            if role == "user":
                st.markdown(f'<div class="chat-bubble-user">{content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bubble-ai">🤖 <strong>PulseGuard AI:</strong><br>{content}</div>', unsafe_allow_html=True)

        user_question = st.chat_input("Ask a question about your heart health...")
        if user_question:
            with st.spinner("Analyzing your telemetry and preparing a response..."):
                # Pass everything said so far (before this new message) so Gemini
                # has real conversation memory instead of starting fresh each time.
                assistant_response = get_ai_response(user_question, st.session_state.chat_history)
            st.session_state.chat_history.append(("user", user_question))
            st.session_state.chat_history.append(("assistant", assistant_response))
            st.rerun()

# =====================================================
# AI INSIGHTS PAGE (Weekly Story, Correlation Explorer,
# Heart Age / Predictive Trajectory)
# =====================================================
elif page == "🧠 AI Insights":

    st.markdown("<h2 style='font-weight:800;'>🧠 AI Insights</h2>", unsafe_allow_html=True)
    st.caption("Deeper, personalized patterns pulled from your history — powered by Gemini.")
    st.markdown("---")

    if not ai_features_unlocked():
        render_subscription_paywall("AI Insights")
    else:
        # --- Weekly Story ---
        st.markdown("<h3>🗞️ Your Weekly Story</h3>", unsafe_allow_html=True)
        if st.button("✨ Generate My Weekly Story"):
            with st.spinner("Reading through your last 7 days..."):
                st.session_state.weekly_story = get_weekly_story()
        if st.session_state.weekly_story:
            st.markdown(
                f'<div class="glass-card"><p style="color:#C9E0D2;">{st.session_state.weekly_story}</p></div>',
                unsafe_allow_html=True
            )
        else:
            st.caption("Click the button above for a plain-language recap of your week.")

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # --- Correlation Explorer ---
        st.markdown("<h3>🔗 Correlation Explorer</h3>", unsafe_allow_html=True)
        findings = compute_correlations()
        insight_text = get_correlation_insight(findings)
        st.markdown(
            f'<div class="glass-card"><p style="color:#C9E0D2; white-space:pre-line;">{insight_text}</p></div>',
            unsafe_allow_html=True
        )

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # --- Heart Age & Predictive Trajectory ---
        st.markdown("<h3>📈 Heart Age & Trajectory</h3>", unsafe_allow_html=True)
        age_col, _ = st.columns([1, 2])
        with age_col:
            patient_age = st.number_input("Your age", min_value=18, max_value=100, key="patient_age")

        heart_age, current_score = compute_heart_age(patient_age)
        current_proj, projected_score, slope = compute_score_projection(days_ahead=30)

        hcol1, hcol2 = st.columns(2)
        with hcol1:
            age_diff = patient_age - heart_age
            age_note = (
                f"{age_diff} years younger than your age" if age_diff > 0
                else f"{-age_diff} years older than your age" if age_diff < 0
                else "right in line with your age"
            )
            st.markdown(
                f"""
                <div class="glass-card">
                    <h4 style="margin-top:0;">❤️ Estimated Heart Age</h4>
                    <div style="font-size:38px; font-weight:800; color:var(--accent);">{heart_age}</div>
                    <p style="color:#8FA69C;">Based on today's score, your heart is trending {age_note}.
                    This is a simplified, non-clinical illustration — not a medical measurement.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with hcol2:
            trend_word = "improving" if slope > 0.05 else "declining" if slope < -0.05 else "holding steady"
            st.markdown(
                f"""
                <div class="glass-card">
                    <h4 style="margin-top:0;">🔮 30-Day Projection</h4>
                    <div style="font-size:38px; font-weight:800; color:var(--accent);">{projected_score}/100</div>
                    <p style="color:#8FA69C;">If your last 30 days continue at the same pace, your heart score
                    is {trend_word} (currently {current_proj}/100). This is a simple trend projection, not a forecast guarantee.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        trend_scores = get_score_trend(days=30)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=trend_scores, mode="lines", name="Last 30 days", line=dict(color=UI_ACCENT, width=2)))
        fig.add_trace(go.Scatter(
            x=[len(trend_scores) - 1, len(trend_scores) - 1 + 30],
            y=[trend_scores[-1], projected_score],
            mode="lines", name="Projected", line=dict(color="#FB7185", width=2, dash="dash")
        ))
        fig.update_layout(
            height=280, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8FA69C"), showlegend=True,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", range=[0, 100]),
        )
        st.plotly_chart(fig, use_container_width=True)

# =====================================================
# SETTINGS PAGE (notifications: proactive alerts + emergency contact)
# =====================================================
elif page == "⚙️ Settings":

    st.markdown("<h2 style='font-weight:800;'>⚙️ Settings</h2>", unsafe_allow_html=True)
    st.caption("Account notification preferences.")
    st.markdown("---")

    render_alert_settings()

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("💳 Subscription")
    if st.session_state.is_subscribed:
        st.success(f"You're subscribed to PulseGuard Premium ({SUBSCRIPTION_PRICE_STR}) — AI features are unlocked.")
        if st.button("Cancel subscription (sample)"):
            st.session_state.is_subscribed = False
            st.rerun()
    else:
        st.caption("Unlock the AI Assistant and AI Insights with PulseGuard Premium.")
        render_subscription_paywall("PulseGuard Premium")

# =====================================================
# SURVEY PAGE (feedback survey → its own Google Sheet tab)
# =====================================================
elif page == "📝 Survey":

    st.markdown("<h2 style='font-weight:800;'>📝 Help Us Improve PulseGuard</h2>", unsafe_allow_html=True)
    st.caption("A couple of quick questions, plus a spot to tell us anything else.")
    st.markdown("---")

    if st.session_state.survey_submitted:
        st.success("Thanks — your feedback has been recorded! 💙")
        if st.button("Submit another response"):
            st.session_state.survey_submitted = False
            st.rerun()
    else:
        with st.form("pulseguard_survey_form"):
            q1 = st.radio(
                "1. How easy is PulseGuard to use?",
                ["Very easy", "Somewhat easy", "Neutral", "Somewhat difficult", "Very difficult"],
                index=None,
            )
            q2 = st.radio(
                "2. Which feature do you use the most?",
                ["Heart rate scanner", "AI Assistant", "AI Insights",
                 "Health Summary / reports", "Smartwatch simulation", "Alerts"],
                index=None,
            )
            q3 = st.radio(
                "3. Is there a feature you feel is missing?",
                ["No, it has everything I need", "Yes, I'll describe it below",
                 "Not sure yet"],
                index=None,
            )
            q4 = st.radio(
                "4. How likely are you to recommend PulseGuard to a friend or family member?",
                ["Very likely", "Likely", "Neutral", "Unlikely", "Very unlikely"],
                index=None,
            )
            free_text = st.text_area(
                "Anything else you think would make PulseGuard better?",
                placeholder="Type anything on your mind — new features, bugs, confusing bits, praise...",
                height=120,
            )
            survey_submit = st.form_submit_button("📨 Submit Feedback", use_container_width=True)

        if survey_submit:
            if not (q1 and q2 and q3 and q4):
                st.error("Please answer all four questions before submitting.")
            else:
                try:
                    _survey_ws = get_survey_worksheet()
                    _save_survey_response(
                        _survey_ws,
                        st.session_state.auth_username,
                        {
                            "q1_easy_to_use": q1,
                            "q2_favorite_feature": q2,
                            "q3_missing_feature": q3,
                            "q4_recommend": q4,
                        },
                        free_text,
                    )
                    st.session_state.survey_submitted = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Couldn't save your feedback right now: {exc}")

# =====================================================
# ABOUT PAGE
# =====================================================
elif page == "ℹ️ About":

    st.markdown("<h2 style='font-weight:800;'>ℹ️ About PulseGuard</h2>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown(
        """
        <div class="glass-card">
            <h3>Who We Are</h3>
            <p style="color:#8FA69C;">
                PulseGuard is developed in coordination with New Jersey Heart Disease Prevention (NJHDP),
                an initiative focused on reducing preventable cardiovascular disease through early, accessible
                insight. We build tools that turn everyday wearable data into something people can actually
                act on, rather than raw numbers that sit unread in an app.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="glass-card">
                <h3>🎯 Our Mission</h3>
                <p style="color:#8FA69C;">
                    Heart disease remains one of the leading causes of preventable death, and much of the
                    risk builds quietly over years before it's ever diagnosed. PulseGuard exists to close
                    that gap — surfacing trends in heart rate, HRV, resting heart rate, and sleep so problems
                    can be caught and discussed with a clinician long before they become emergencies.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="glass-card">
                <h3>🌱 Our Goals</h3>
                <p style="color:#8FA69C;">
                    We're working toward wearable-driven insights that are genuinely understandable —
                    not just data dashboards, but clear, actionable guidance. Longer term, we want PulseGuard
                    to help lower the age at which cardiovascular risk is first caught, and to make that kind
                    of early insight available to anyone with a smartwatch, not just people who already see
                    a cardiologist regularly.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="glass-card">
            <h3>⚠️ A Note on What This Is</h3>
            <p style="color:#8FA69C;">
                PulseGuard is an informational and educational tool. It is not a diagnostic device and does
                not replace a doctor. Always talk to a clinician about any concerning symptoms or before
                making changes to your care based on what you see here.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------------
# Footer & Autoplay Logic
# --------------------------------------------------
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; padding:24px; color:#8FA69C; font-size:12px; border-top:1px solid rgba(255,255,255,0.05);">
        PulseGuard Health Telemetry • Version 2.0 Actionable Dashboard<br>
        New Jersey Heart Disease Prevention (NJHDP)
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Autosave user data (BPM, HRV, history, etc.) back to their
# account so it's there next time they log in on any device.
# Skipped for guests, and skipped if nothing actually changed
# since the last save (avoids hammering the Sheet on every rerun).
# --------------------------------------------------
if st.session_state.logged_in and not st.session_state.is_guest:
    _current_data = {k: st.session_state.get(k) for k in PERSIST_KEYS if k in st.session_state}
    _current_data_str = json.dumps(_current_data, default=str, sort_keys=True)
    if st.session_state.get("_last_saved_data_str") != _current_data_str:
        try:
            _userdata_ws = get_userdata_worksheet()
            _save_user_data(_userdata_ws, st.session_state.auth_username, _current_data)
            st.session_state._last_saved_data_str = _current_data_str
        except Exception:
            # Don't crash the app if the save fails; user just won't
            # get this run's changes persisted until the next save.
            pass

if st.session_state.autoplay:
    time.sleep(3)
    idx = st.session_state.scenario_idx % len(SCENARIOS)
    scenario = SCENARIOS[idx]
    for _k, _v in scenario.items():
        st.session_state[_k] = _v
    st.session_state.scenario_idx = idx + 1
    st.rerun()