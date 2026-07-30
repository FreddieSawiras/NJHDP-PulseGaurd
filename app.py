import os
import json
import urllib.request
import urllib.error
import streamlit as st
import streamlit.components.v1 as components
import random
import time
import io
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------
# Gemini model configuration
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-1.5-mini")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY", None)

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
    background: rgba(7, 18, 26, 0.98);
    animation: pulseguardFadeOut 0.8s ease 1.5s forwards;
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
    box-shadow: 0 24px 60px rgba(0, 229, 255, 0.2);
    border: 1px solid rgba(255,255,255,0.08);
}
.pulseguard-loader-text {
    color: #E6F3FA;
    font-family: Inter, sans-serif;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.02em;
    text-shadow: 0 0 18px rgba(0,229,255,0.15);
}
.pulseguard-loader-subtext {
    color: #9fb0c0;
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
            <div class="pulseguard-loader-subtext">Loading your heart intelligence...</div>
        </div>
    </div>
</div>
""".replace("{{LOGO_URL}}", LOGO_URL)

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
    "⌚ Apple Watch": "#00E5FF",
    "⌚ Samsung Galaxy Watch": "#7C5CFF",
    "⌚ Google Pixel Watch": "#4F8BFF",
    "⌚ Garmin": "#FF4D6D",
    "⌚ Fitbit": "#00E5FF",
}

# Color Constants
GOOD, WARN, DANGER = "#00E5FF", "#FFB703", "#FF4D6D"

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
        "Always remind the user that this is informational and that a clinician should confirm any clinical decisions."
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

def get_ai_response(user_question):
    system_prompt = get_ai_system_prompt()
    context = build_ai_context()
    if not GEMINI_API_KEY:
        return (
            "Gemini is not configured. Please set GOOGLE_API_KEY in your environment "
            "or Streamlit secrets to enable the Gemini Assistant."
        )

    prompt = (
        f"{system_prompt}\n\n{context}\n\nUser question: {user_question}\nAssistant:")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta2/models/{GEMINI_MODEL}:generateText?key={GEMINI_API_KEY}"
    )
    body = {
        "prompt": {"text": prompt},
        "temperature": 0.7,
        "maxOutputTokens": 512,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        if "candidates" in data and data["candidates"]:
            return data["candidates"][0].get("output", "").strip()
        return "Gemini returned no response."
    except urllib.error.HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8")
            error_json = json.loads(error_body)
            message = error_json.get("error", {}).get("message", error_body)
        except Exception:
            message = exc.reason
        return f"Gemini API request failed: {message}"
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

/* Base layout and typography */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #07121a !important;
    background-image:
        radial-gradient(circle at 12% 12%, rgba(0,229,255,0.04) 0%, transparent 38%),
        radial-gradient(circle at 88% 18%, rgba(124,92,255,0.05) 0%, transparent 38%),
        linear-gradient(rgba(255,255,255,0.01) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.01) 1px, transparent 1px) !important;
    background-size: 100% 100%, 100% 100%, 28px 28px, 28px 28px !important;
    font-family: 'Inter', -apple-system, 'Plus Jakarta Sans', sans-serif !important;
    color: #E6F3FA !important;
    -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
}

/* Headings & hierarchy */
h1, h2, h3, .navbar-title, .glass-card h2, .glass-card h3 {
    font-family: 'Inter', 'Plus Jakarta Sans', sans-serif !important;
    color: #E6F3FA !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
}
h1 { font-size: 28px; }
h2 { font-size: 22px; }
h3 { font-size: 18px; }

/* Subtitles and captions */
.caption, .stCaption, .glass-card .caption { color: #9fb0c0 !important; font-weight:500 !important; }

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
    background: linear-gradient(180deg, rgba(8,18,30,0.64), rgba(10,20,34,0.56)) !important;
    backdrop-filter: blur(14px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(14px) saturate(140%) !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
    border-radius: 18px !important;
    padding: 22px !important;
    box-shadow: 0 8px 30px rgba(2,8,20,0.6), inset 0 1px 0 rgba(255,255,255,0.02) !important;
    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.28s !important;
    position: relative;
    overflow: hidden;
}

/* Native Streamlit bordered container (st.container(border=True)) styled to
   match glass-card, so widgets that need real nesting (charts, radios, etc.)
   don't have to rely on the broken open/close-div markdown trick. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(8,18,30,0.64), rgba(10,20,34,0.56)) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 18px !important;
    box-shadow: 0 8px 30px rgba(2,8,20,0.6), inset 0 1px 0 rgba(255,255,255,0.02) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"],
div[data-testid="stRadio"],
div[role="radiogroup"],
div[role="radiogroup"] * {
    color: #D7E1EC !important;
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
    color: #D7E1EC !important;
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
    color: #00E5FF !important;
}

div[data-testid="stRadio"] input:checked + label,
div[data-testid="stRadio"] input:checked + span,
div[data-testid="stRadio"] button[aria-checked="true"],
div[data-testid="stRadio"] button[aria-pressed="true"],
div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"],
div[role="radiogroup"] button[aria-checked="true"],
div[role="radiogroup"] button[aria-pressed="true"],
div[role="radiogroup"] label[aria-checked="true"] {
    color: #00E5FF !important;
}

div[data-testid="stRadio"] button[aria-checked="true"],
div[data-testid="stRadio"] button[aria-pressed="true"],
div[role="radiogroup"] button[aria-checked="true"],
div[role="radiogroup"] button[aria-pressed="true"] {
    background: rgba(0, 229, 255, 0.1) !important;
    border-color: rgba(0, 229, 255, 0.2) !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"],
div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] * {
    color: #D7E1EC !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"],
div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"] * {
    color: #00E5FF !important;
}

div[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] p {
    color: inherit !important;
}

.glass-card:hover {
    border-color: rgba(79,139,255,0.18) !important;
    box-shadow: 0 14px 40px rgba(0, 88, 140, 0.12), inset 0 1px 0 rgba(255,255,255,0.02) !important;
    transform: translateY(-4px) !important;
}

.metric-card-wrapper {
    background: rgba(13, 23, 40, 0.75);
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
    color: #D7E1EC !important;
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
    color: #00E5FF !important;
    background: rgba(0, 229, 255, 0.08) !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(0, 229, 255, 0.15) !important;
    color: #00E5FF !important;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.15), inset 0 0 0 1px rgba(0, 229, 255, 0.3) !important;
}

.heart-struct-card {
    background: rgba(13, 23, 40, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-left: 3px solid #00E5FF;
    border-radius: 12px;
    padding: 14px 16px;
    height: 100%;
}
.heart-struct-title {
    color: #00E5FF;
    font-weight: 800;
    font-size: 12.5px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.heart-struct-desc {
    color: #8A99AD;
    font-size: 12.5px;
    line-height: 1.5;
}

.metric-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8A99AD;
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
    background: rgba(13, 23, 40, 0.85);
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
    background: linear-gradient(135deg, #FFFFFF 30%, #8A99AD 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
}

.pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #00E5FF;
    border-radius: 50%;
    box-shadow: 0 0 12px #00E5FF;
    animation: pulseGlow 1.8s infinite;
}

@keyframes pulseGlow {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(0, 229, 255, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 229, 255, 0); }
}

.stButton > button {
    border-radius: 12px !important;
    border: none !important;
    background: linear-gradient(135deg, rgba(6,30,54,0.8), rgba(10,18,34,0.8)) !important;
    color: #DDEFF7 !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 0.6rem 1.1rem !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
    box-shadow: 0 6px 18px rgba(3,18,35,0.6) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 26px rgba(0,120,200,0.18) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00E5FF 0%, #7C5CFF 100%) !important;
    color: #051022 !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 30px rgba(79,139,255,0.25) !important;
}

/* Base styles for global text inputs, select elements, containers */
input, textarea, select, .stTextInput>div>div>input, .stDateInput>div>div>input {
    background: rgba(13, 23, 40, 0.75) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #E6F3FA !important;
    padding: 10px 12px !important;
    border-radius: 10px !important;
    outline: none !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
}

input::placeholder, textarea::placeholder {
    color: rgba(230,243,250,0.55) !important;
}

input:focus, textarea:focus, select:focus, .stTextInput>div>div>input:focus {
    box-shadow: 0 0 28px rgba(124,92,255,0.14), 0 0 8px rgba(0,229,255,0.08) !important;
    border-color: rgba(124,92,255,0.28) !important;
}

/* Universal Streamlit Input Box Styling Override (Fixes White Box Issue Globally) */
div[data-baseweb="input"], 
div[data-baseweb="select"] > div,
div[data-testid="stTextInput"] > div > div,
div[data-testid="stSelectbox"] > div > div {
    background-color: rgba(13, 23, 40, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    color: #E6F3FA !important;
}

div[data-baseweb="input"] input, 
div[data-baseweb="select"] input {
    color: #E6F3FA !important;
    background-color: transparent !important;
}

div[data-testid="stChatInput"] input,
div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] div[data-baseweb="input"] > div,
div[data-testid="stChatInput"] div[data-baseweb="textarea"] > div,
.stChatInput input,
.stChatInput textarea,
.stChatInput div[data-baseweb="input"] > div,
.stChatInput div[data-baseweb="textarea"] > div {
    background-color: rgba(13, 23, 40, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #E6F3FA !important;
    border-radius: 10px !important;
}

div[data-testid="stChatInput"] input::placeholder,
div[data-testid="stChatInput"] textarea::placeholder,
.stChatInput input::placeholder,
.stChatInput textarea::placeholder {
    color: rgba(230,243,250,0.55) !important;
}

/* Universal Streamlit Download Button Override */
div.stDownloadButton > button {
    background: linear-gradient(135deg, #00E5FF 0%, #7C5CFF 100%) !important;
    color: #051022 !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 0.6rem 1.1rem !important;
    box-shadow: 0 6px 30px rgba(79,139,255,0.25) !important;
    transition: all 0.2s ease !important;
}

div.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 35px rgba(0,229,255,0.4) !important;
}

.metric-title { color:#9fb0c0 !important; font-weight:700 !important; }
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
    background: linear-gradient(160deg, rgba(17, 28, 46, 0.85) 0%, rgba(10, 18, 32, 0.9) 100%);
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
    color: #8A99AD;
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
    color: #6E7C91;
    line-height: 1.4;
}

.alert-banner {
    background: rgba(255, 77, 109, 0.15);
    border: 1px solid #FF4D6D;
    border-radius: 16px;
    padding: 16px 20px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 0 25px rgba(255, 77, 109, 0.2);
}

.chat-bubble-user {
    background: linear-gradient(135deg, rgba(79, 139, 255, 0.2), rgba(124, 92, 255, 0.2));
    border: 1px solid rgba(124, 92, 255, 0.3);
    border-radius: 18px 18px 2px 18px;
    padding: 14px 18px;
    color: #F0F4F8;
    margin-bottom: 12px;
    max-width: 80%;
    margin-left: auto;
}

.chat-bubble-ai {
    background: rgba(13, 23, 40, 0.8);
    border: 1px solid rgba(0, 229, 255, 0.2);
    border-radius: 18px 18px 18px 2px;
    padding: 14px 18px;
    color: #E2E8F0;
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
.trend-up { background: rgba(0, 229, 255, 0.15); color: #00E5FF; }
.trend-down { background: rgba(255, 77, 109, 0.15); color: #FF4D6D; }
.trend-neutral { background: rgba(255, 255, 255, 0.1); color: #8A99AD; }
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
            <div style="font-size: 12px; color: #8A99AD; margin-top: 6px; line-height: 1.4;">
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
                {'range': [0, 50], 'color': "rgba(255, 77, 109, 0.15)"},
                {'range': [50, 75], 'color': "rgba(255, 183, 3, 0.15)"},
                {'range': [75, 100], 'color': "rgba(0, 229, 255, 0.15)"},
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
    <div style="background: rgba(8, 17, 31, 0.9); border-radius: 16px; padding: 12px; border: 1px solid rgba(0, 229, 255, 0.2); box-shadow: inset 0 0 20px rgba(0,229,255,0.05);">
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
        ctx.strokeStyle = "#00E5FF";
        ctx.shadowBlur = 8;
        ctx.shadowColor = "#00E5FF";
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
                background: rgba(8, 17, 31, 0.85); backdrop-filter: blur(12px);
                border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 14px;
                padding: 10px 20px; color: #FFFFFF; font-size: 12.5px; font-weight: 600;
                text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                pointer-events: none; transition: all 0.2s ease;
                z-index: 10; max-width: 85%;
            }}
            .part-tag {{ color: #00E5FF; font-weight: 700; }}
            #loading {{
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                color: #00E5FF; font-size: 13px; font-weight: 700; letter-spacing: 0.05em;
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

            const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
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
                const mat = new THREE.MeshPhysicalMaterial({{
                    color: 0xb5121b, roughness: 0.35, metalness: 0.05,
                    clearcoat: 0.6, clearcoatRoughness: 0.3, sheen: 1.0,
                    sheenColor: new THREE.Color(0xff4d6d), emissive: 0x2a0508, emissiveIntensity: 0.4
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
            loader.load(
                "{MODEL_URL}",
                function (gltf) {{
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
                }},
                undefined,
                function (error) {{
                    console.warn("Could not load heart.glb, using fallback shape:", error);
                    buildFallbackHeart();
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

            window.addEventListener('mousemove', (e) => updatePointer(e.clientX, e.clientY));
            window.addEventListener('touchmove', (e) => {{
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
                             blood_pressure_variability=None):
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
    return score, positives, concerns

def get_score_trend(days=7):
    """Recompute the health score for each of the last `days` days from
    full_history, for the trend sparkline."""
    dates = sorted(st.session_state.full_history.keys())[-days:]
    trend = []
    for d in dates:
        day = st.session_state.full_history[d]
        day_score, _, _ = generate_health_summary(
            heart_rate=day["heart_rate"],
            resting_hr=day["resting_hr"],
            hrv=day["hrv"],
            sleep_quality=day["sleep_quality"],
            steps=day["steps"],
            heart_rate_recovery=day["heart_rate_recovery"],
            blood_pressure_variability=day["blood_pressure_variability"],
        )
        trend.append(day_score)
    trend.append(generate_health_summary()[0])  # today
    return trend

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


def generate_doctor_report_pdf(rows, period_label, patient_name=""):
    pdf = _PulseGuardPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    content_width = pdf.w - pdf.l_margin - pdf.r_margin
    generated_on = datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")
    summary = summarize_report_rows(rows)

    pdf.set_fill_color(8, 17, 31)
    pdf.rect(0, 0, pdf.w, 32, style="F")
    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 229, 255)
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

def _pdf_section_header(pdf, text, content_width, rgb=(13, 23, 40)):
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

    pdf.set_fill_color(8, 17, 31)
    pdf.rect(0, 0, pdf.w, 32, style="F")
    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 229, 255)
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
        score_rgb = (255, 77, 109)
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
        _pdf_section_header(pdf, "Findings Warranting Follow-Up", content_width, rgb=(255, 77, 109))
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
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#8A99AD;">Overall Vital Status</div>
            <div style="font-size:56px; font-weight:800; color:{c}; margin:8px 0; text-shadow:0 0 30px {hex_to_rgba(c, 0.4)};">
                {final_score}<span style="font-size:24px; color:#8A99AD;">/100</span>
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
    "❤️ Heart Dashboard",
    "⌚ Smartwatch",
    "📈 Health Summary",
    "🤖 AI Assistant",
    "💡 Accuracy Tips",
    "ℹ️ About"
]

if "current_page" not in st.session_state:
    st.session_state.current_page = NAV_ITEMS[0]

if "heart_dashboard_tab" not in st.session_state:
    st.session_state.heart_dashboard_tab = "📊 VITALS"

if "health_summary_scroll_target" not in st.session_state:
    st.session_state.health_summary_scroll_target = None

# Application Layout Header
st.markdown(
    f"""
    <div class="top-navbar">
        <div class="navbar-brand">
            <img src="{LOGO_URL}" width="38" style="border-radius:10px; filter: drop-shadow(0 0 8px rgba(0,229,255,0.4));">
            <div>
                <div class="navbar-title">PulseGuard</div>
            </div>
            <div style="display:flex; align-items:center; gap:6px; background:rgba(0, 229, 255, 0.08); border:1px solid rgba(0, 229, 255, 0.2); padding:4px 12px; border-radius:20px; margin-left:12px;">
                <div class="pulse-dot"></div>
                <span style="font-size:11px; font-weight:700; color:#00E5FF; letter-spacing:0.05em;">LIVE MONITORING</span>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="font-size:12px; color:#8A99AD; font-family:'JetBrains Mono', monospace;">
                {datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y")}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Pill Navigation Bar
_nav_cols = st.columns(len(NAV_ITEMS))
for _col, _item in zip(_nav_cols, NAV_ITEMS):
    with _col:
        _is_active = st.session_state.current_page == _item
        if st.button(_item, key=f"nav_{_item}", use_container_width=True,
                     type="primary" if _is_active else "secondary"):
            st.session_state.current_page = _item
            st.rerun()

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

page = st.session_state.current_page

# --------------------------------------------------
# Device & Live Data Controls
# --------------------------------------------------
with st.expander("⚙️ Device & Live Data Controls", expanded=False):
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
        <div class="glass-card" style="padding:28px; background: linear-gradient(135deg, rgba(13, 23, 40, 0.95) 0%, rgba(8, 17, 31, 0.98) 100%);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;">
                <div>
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                        <span style="font-size:28px; font-weight:800; color:#FFFFFF;">{time_greeting}! 👋</span>
                        <div style="display:flex; align-items:center; gap:8px; background:rgba(0, 229, 255, 0.1); border:1px solid rgba(0, 229, 255, 0.3); padding:4px 14px; border-radius:20px;">
                            <div class="pulse-dot"></div>
                            <span style="font-size:12px; font-weight:700; color:#00E5FF; letter-spacing:0.04em;">LIVE {st.session_state.heart_rate} BPM</span>
                        </div>
                    </div>
                    <div style="font-size:18px; font-weight:600; color:#E2E8F0;">
                        Your heart health is looking steady and resilient today.
                    </div>
                    <div style="font-size:13px; color:#8A99AD; margin-top:6px;">
                        Continuous telemetry streaming from {st.session_state.selected_watch} • Synced {last_sync}
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:16px;">
                    <div style="background:{hex_to_rgba(_score_color, 0.12)}; border:1px solid {hex_to_rgba(_score_color, 0.35)}; padding:12px 20px; border-radius:18px; text-align:center;">
                        <div style="font-size:11px; font-weight:700; color:#8A99AD; text-transform:uppercase; letter-spacing:0.06em;">Vital Score</div>
                        <div style="font-size:28px; font-weight:800; color:{_score_color}; font-family:'Plus Jakarta Sans';">{_today_score}<span style="font-size:14px; color:#8A99AD;">/100</span></div>
                    </div>
                    <div style="background:rgba(255, 183, 3, 0.1); border:1px solid rgba(255, 183, 3, 0.3); padding:12px 20px; border-radius:18px; text-align:center;">
                        <div style="font-size:11px; font-weight:700; color:#8A99AD; text-transform:uppercase; letter-spacing:0.06em;">Active Streak</div>
                        <div style="font-size:28px; font-weight:800; color:#FFB703;">🔥 {st.session_state.streak_days} <span style="font-size:14px; color:#8A99AD;">Days</span></div>
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
        <div class="glass-card" style="border-left: 4px solid #00E5FF; padding:18px 24px;">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:14px;">
                    <div style="font-size:24px; background:rgba(0,229,255,0.12); padding:10px; border-radius:14px;">🎯</div>
                    <div>
                        <div style="font-size:12px; font-weight:800; color:#00E5FF; text-transform:uppercase; letter-spacing:0.08em;">Today's Recommended Focus</div>
                        <div style="font-size:14px; color:#F0F4F8; font-weight:600; margin-top:2px;">{focus_insight}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:12px; font-weight:700; color:#8A99AD; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:10px;'>⚡ Quick Actions</div>", unsafe_allow_html=True)
    qa_cols = st.columns(4)
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
            st.session_state.current_page = "❤️ Heart Dashboard"
            st.session_state.heart_dashboard_tab = "🫀 3D MODEL"
            st.rerun()

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:12px; font-weight:700; color:#8A99AD; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px;'>📊 Core Telemetry Metrics</div>", unsafe_allow_html=True)
    
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
        st.markdown("<div style='font-size:12px; font-weight:800; color:#00E5FF; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:14px;'>🕒 Live Telemetry Activity Feed</div>", unsafe_allow_html=True)
        
        feed_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
        for item in st.session_state.activity_feed[:4]:
            feed_html += f"""
            <div style='display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:8px;'>
                <div style='display:flex; align-items:center; gap:10px;'>
                    <div style='width:6px; height:6px; border-radius:50%; background:#00E5FF;'></div>
                    <span style='font-size:13px; color:#F0F4F8; font-weight:500;'>{item['event']}</span>
                </div>
                <span style='font-size:11px; color:#8A99AD; font-family:"JetBrains Mono";'>{item['time']}</span>
            </div>
            """
        feed_html += "</div>"
        st.markdown(feed_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_habits:
        st.markdown('<div class="glass-card" style="padding:22px;">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; font-weight:800; color:#7C5CFF; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:14px;'>🎯 Goal Rings & Habit Progress</div>", unsafe_allow_html=True)

        step_pct = min(100, int((steps / 10000) * 100))
        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px;'><span>👟 Step Goal ({steps:,} / 10,000)</span><span style='color:#00E5FF; font-weight:700;'>{step_pct}%</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{step_pct}%; background:#00E5FF;'></div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px;'><span>😴 Sleep Quality Target</span><span style='color:#7C5CFF; font-weight:700;'>{sleep_quality}%</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{sleep_quality}%; background:#7C5CFF;'></div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        hyd_pct = min(100, int((st.session_state.hydration_oz / 64) * 100))
        st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px;'><span>💧 Hydration Goal ({st.session_state.hydration_oz} / 64 oz)</span><span style='color:#4F8BFF; font-weight:700;'>{hyd_pct}%</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{hyd_pct}%; background:#4F8BFF;'></div></div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# HEART DASHBOARD PAGE
# =====================================================
elif page == "❤️ Heart Dashboard":

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
            <div class="glass-card" style="border-left: 4px solid #00E5FF;">
                <div style="font-size:12px; font-weight:700; color:#8A99AD; text-transform:uppercase;">Connected Device</div>
                <div style="font-size:28px; font-weight:800; color:#FFFFFF; margin:8px 0;">{watch_plain_name}</div>
                <div style="display:flex; gap:16px; margin-top:16px;">
                    <div><span style="color:#8A99AD; font-size:12px;">Battery:</span> <strong style="color:#00E5FF;">{battery}%</strong></div>
                    <div><span style="color:#8A99AD; font-size:12px;">Last Sync:</span> <strong>{last_sync}</strong></div>
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
                <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#8A99AD;">Score trend, last {trend_range}</div>
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
                    <span style="font-size:14px; color:#E6F3FA;">{driver_label} is the biggest drag on today's score.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:18px;">✨</span>
                    <span style="font-size:14px; color:#E6F3FA;">Every tracked metric is in a healthy range today.</span>
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
        .st-key-report_card { color: #EAF6FF !important; }
        .st-key-report_card .report-metric-value { color: #FFFFFF !important; font-weight:800; font-size:36px; opacity:1 !important; text-shadow: 0 2px 10px rgba(0,0,0,0.6); }
        .st-key-report_card .report-metric-label { color:#9fb0c0 !important; font-size:12px; margin-top:6px; }

        /* Direct native input overrides to enforce dark background & match UI scheme */
        .st-key-report_card input[type="text"],
        .st-key-report_card div[data-baseweb="select"] > div,
        .st-key-report_card div[data-baseweb="input"] > div,
        .st-key-report_card .stTextInput input,
        .st-key-report_card .stSelectbox [data-baseweb="select"] {
            background-color: rgba(13, 23, 40, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            color: #E6F3FA !important;
            border-radius: 10px !important;
        }

        /* Download Button Styling - Dark Primary Gradient */
        .st-key-report_card button[kind="primary"],
        .st-key-report_card div.stDownloadButton > button {
            background: linear-gradient(135deg, #00E5FF 0%, #7C5CFF 100%) !important;
            color: #051022 !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            border: none !important;
            box-shadow: 0 6px 30px rgba(79,139,255,0.25) !important;
            transition: all 0.2s ease !important;
        }
        .st-key-report_card button[kind="primary"]:hover,
        .st-key-report_card div.stDownloadButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 35px rgba(0,229,255,0.4) !important;
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


# =====================================================
# AI CHAT ASSISTANT PAGE
# =====================================================
elif page == "🤖 AI Assistant":

    st.markdown("<h2 style='font-weight:800;'>🤖 PulseGuard AI Assistant</h2>", unsafe_allow_html=True)
    st.caption("Ask questions about your telemetry, resting trends, or HRV values.")
    st.markdown("---")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            ("assistant", "Hello! I am your PulseGuard AI companion. How can I help analyze your cardiovascular metrics today?")
        ]

    for role, content in st.session_state.chat_history:
        if role == "user":
            st.markdown(f'<div class="chat-bubble-user">{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble-ai">🤖 <strong>PulseGuard AI:</strong><br>{content}</div>', unsafe_allow_html=True)

    user_question = st.chat_input("Ask a question about your heart health...")
    if user_question:
        with st.spinner("Analyzing your telemetry and preparing a response..."):
            assistant_response = get_ai_response(user_question)
        st.session_state.chat_history.append(("user", user_question))
        st.session_state.chat_history.append(("assistant", assistant_response))
        st.rerun()

# =====================================================
# ACCURACY TIPS PAGE
# =====================================================
elif page == "💡 Accuracy Tips":

    st.markdown("<h2 style='font-weight:800;'>💡 Optimization & Sensor Accuracy</h2>", unsafe_allow_html=True)
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="glass-card">
                <h3>⌚ Wearable Placement</h3>
                <p style="color:#8A99AD;">Ensure your wearable fits snugly above the wrist bone. Movement artifacts can create false PPG polling spikes.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="glass-card">
                <h3>💧 Hydration & Signal Quality</h3>
                <p style="color:#8A99AD;">Dehydration lowers blood volume, leading to elevated resting heart rates and reduced Heart Rate Variability (HRV).</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# =====================================================
# ABOUT PAGE
# =====================================================
elif page == "ℹ️ About":

    st.markdown("<h2 style='font-weight:800;'>ℹ️ About PulseGuard Platform</h2>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        """
        <div class="glass-card">
            <h3>Mission Overview</h3>
            <p style="color:#8A99AD;">PulseGuard is developed in coordination with New Jersey Heart Disease Prevention (NJHDP) to transform wearable telemetry into preventative cardiovascular health insights.</p>
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
    <div style="text-align:center; padding:24px; color:#8A99AD; font-size:12px; border-top:1px solid rgba(255,255,255,0.05);">
        PulseGuard Health Telemetry • Version 2.0 Actionable Dashboard<br>
        New Jersey Heart Disease Prevention (NJHDP)
    </div>
    """,
    unsafe_allow_html=True
)

if st.session_state.autoplay:
    time.sleep(3)
    idx = st.session_state.scenario_idx % len(SCENARIOS)
    scenario = SCENARIOS[idx]
    for _k, _v in scenario.items():
        st.session_state[_k] = _v
    st.session_state.scenario_idx = idx + 1
    st.rerun()