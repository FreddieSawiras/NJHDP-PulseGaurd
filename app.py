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
# Set up page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="PulseGuard — Heart Health Intelligence",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_URL = "https://plain-enam-prod-public.komododecks.com/202607/27/VZS1Q3WWHJ5eZyOEZXiM/image.png"

# --------------------------------------------------
# Session state defaults (100% Preserved)
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

# --------------------------------------------------
# Advanced Ultra-Premium CSS & Custom Theme Architecture
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* Global Reset and High-Tech Background */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #08111F !important;
    background-image: 
        radial-gradient(circle at 15% 15%, rgba(0, 229, 255, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 85% 20%, rgba(124, 92, 255, 0.06) 0%, transparent 40%),
        radial-gradient(circle at 50% 80%, rgba(255, 43, 85, 0.04) 0%, transparent 50%),
        linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px) !important;
    background-size: 100% 100%, 100% 100%, 100% 100%, 30px 30px, 30px 30px !important;
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    color: #F0F4F8 !important;
}

section[data-testid="stSidebar"], [data-testid="collapsedControl"], header[data-testid="stHeader"] {
    display: none !important;
}

.stMainBlockContainer {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* Glassmorphic Container Cards */
.glass-card {
    background: rgba(13, 23, 40, 0.65) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    position: relative;
    overflow: hidden;
}

.glass-card:hover {
    border-color: rgba(0, 229, 255, 0.3) !important;
    box-shadow: 0 20px 40px rgba(0, 229, 255, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    transform: translateY(-3px) !important;
}

/* Metric Cards */
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

.metric-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8A99AD;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #FFFFFF;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Top Navbar */
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

/* Custom Buttons Override */
.stButton > button {
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    background: rgba(255, 255, 255, 0.03) !important;
    color: #D1D5DB !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    backdrop-filter: blur(10px) !important;
}

.stButton > button:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(0, 229, 255, 0.4) !important;
    color: #00E5FF !important;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.15) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00E5FF, #4F8BFF) !important;
    color: #040914 !important;
    border: none !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(0, 229, 255, 0.35) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 25px rgba(0, 229, 255, 0.5) !important;
    transform: translateY(-2px) !important;
    color: #040914 !important;
}

/* Streamlit Inputs Dark Modern Overrides */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background-color: rgba(8, 17, 31, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #FFFFFF !important;
}

.stSlider [data-baseweb="slider"] {
    margin-top: 8px;
}

/* Chat Bubbles */
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

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #08111F;
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 229, 255, 0.4);
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Helper Functions (100% Preserved Logic)
# --------------------------------------------------
def metric_status(kind, value):
    if kind == "heart_rate":
        if 60 <= value <= 100:
            return "Good", GOOD, 100
        elif 50 <= value < 60 or 100 < value <= 110:
            return "Monitor", WARN, 60
        else:
            return "Concern", DANGER, 30
    if kind == "resting_hr":
        if 50 <= value <= 80:
            return "Good", GOOD, 100
        elif 40 <= value < 50 or 80 < value <= 90:
            return "Monitor", WARN, 60
        else:
            return "Concern", DANGER, 30
    if kind == "hrv":
        if value >= 50:
            return "Good", GOOD, min(100, value)
        elif value >= 30:
            return "Monitor", WARN, 60
        else:
            return "Concern", DANGER, 30
    if kind == "bp_variability":
        if value <= 10:
            return "Good", GOOD, 100
        elif value <= 15:
            return "Monitor", WARN, 60
        else:
            return "Concern", DANGER, 30
    if kind == "recovery":
        if value >= 20:
            return "Good", GOOD, min(100, value * 2)
        elif value >= 15:
            return "Monitor", WARN, 60
        else:
            return "Concern", DANGER, 30
    if kind == "sleep":
        if value >= 80:
            return "Good", GOOD, value
        elif value >= 60:
            return "Monitor", WARN, value
        else:
            return "Concern", DANGER, value
    if kind == "steps":
        pct = min(100, value / 10000 * 100)
        if value >= 10000:
            return "Good", GOOD, 100
        elif value >= 7500:
            return "Monitor", WARN, pct
        else:
            return "Concern", DANGER, pct
    return "Good", GOOD, 100

def render_metric_card(title, value_str, color):
    st.markdown(
        f"""
        <div class="metric-card-wrapper" style="border-top: 3px solid {color};">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value_str}</div>
            <div style="position: absolute; top: 18px; right: 18px; width: 8px; height: 8px; border-radius: 50%; background: {color}; box-shadow: 0 0 10px {color};"></div>
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

def render_radar_chart(hr, rhr, hrv_v, bp, rec, sleep, steps_v):
    categories = ["Heart Rate", "Resting HR", "HRV", "BP Var", "Recovery", "Sleep", "Steps"]
    values = [
        metric_status("heart_rate", hr)[2],
        metric_status("resting_hr", rhr)[2],
        metric_status("hrv", hrv_v)[2],
        metric_status("bp_variability", bp)[2],
        metric_status("recovery", rec)[2],
        metric_status("sleep", sleep)[2],
        metric_status("steps", steps_v)[2],
    ]
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself',
        line=dict(color="#00E5FF", width=2),
        fillcolor="rgba(0, 229, 255, 0.15)"
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], color="rgba(255,255,255,0.4)", gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(color="#8A99AD", gridcolor="rgba(255,255,255,0.08)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=30, b=30),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True)

def render_trend_chart(hr, sleep, steps_v):
    days = ["6d ago", "5d ago", "4d ago", "3d ago", "2d ago", "Yesterday", "Today"]
    hr_series = st.session_state.trend_data["heart_rate"] + [hr]
    sleep_series = st.session_state.trend_data["sleep_quality"] + [sleep]
    steps_series = st.session_state.trend_data["steps"] + [steps_v]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=hr_series, name="Heart Rate (BPM)", mode='lines+markers', line=dict(color='#FF4D6D', width=3, shape='spline')))
    fig.add_trace(go.Scatter(x=days, y=sleep_series, name="Sleep Quality (%)", mode='lines+markers', line=dict(color='#7C5CFF', width=3, shape='spline')))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=240,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#8A99AD")),
        xaxis=dict(showgrid=False, color="#8A99AD"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#8A99AD")
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

def render_3d_heart(hr=72):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body {{ margin: 0; overflow: hidden; background: transparent; font-family: 'Plus Jakarta Sans', sans-serif; }}
            #container {{ width: 100%; height: 100%; position: relative; }}
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
                z-index: 5;
            }}
            #hud {{
                position: absolute; top: 14px; left: 16px;
                color: rgba(255,255,255,0.6); font-size: 11px; font-weight: 700;
                letter-spacing: 0.04em; z-index: 10;
            }}
            #bpmTag {{
                position: absolute; top: 14px; right: 16px;
                color: #FF4D6D; font-size: 11px; font-weight: 700;
                letter-spacing: 0.04em; z-index: 10;
            }}
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    </head>
    <body>
        <div id="container">
            <div id="loading">⚡ BUILDING 3D ANATOMICAL MODEL...</div>
            <div id="hud">HEART // INTERACTIVE MODEL</div>
            <div id="bpmTag">❤️ {hr} BPM</div>
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
            controls.minDistance = 4;
            controls.maxDistance = 14;

            // ---------- Lighting ----------
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
            scene.add(ambientLight);

            const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
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

            // ---------- Procedural anatomical heart shape ----------
            // Built from a heart-curve cross section, extruded and beveled for a
            // realistic rounded muscular silhouette (no external model download needed).
            function buildHeartGeometry() {{
                const shape = new THREE.Shape();
                const x = 0, y = 0;
                shape.moveTo(x, y + 0.7);
                shape.bezierCurveTo(x, y + 1.1, x - 1.1, y + 1.3, x - 1.1, y + 0.55);
                shape.bezierCurveTo(x - 1.1, y - 0.15, x - 0.55, y - 0.85, x, y - 1.6);
                shape.bezierCurveTo(x + 0.55, y - 0.85, x + 1.1, y - 0.15, x + 1.1, y + 0.55);
                shape.bezierCurveTo(x + 1.1, y + 1.3, x, y + 1.1, x, y + 0.7);

                const extrudeSettings = {{
                    steps: 4,
                    depth: 1.1,
                    bevelEnabled: true,
                    bevelThickness: 0.35,
                    bevelSize: 0.35,
                    bevelOffset: 0,
                    bevelSegments: 12,
                    curveSegments: 24
                }};

                const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
                geo.center();
                geo.computeVertexNormals();
                return geo;
            }}

            const heartMat = new THREE.MeshPhysicalMaterial({{
                color: 0xb5121b,
                roughness: 0.35,
                metalness: 0.05,
                clearcoat: 0.6,
                clearcoatRoughness: 0.3,
                sheen: 1.0,
                sheenColor: new THREE.Color(0xff4d6d),
                emissive: 0x2a0508,
                emissiveIntensity: 0.4
            }});

            const heartMesh = new THREE.Mesh(buildHeartGeometry(), heartMat);
            heartMesh.rotation.x = Math.PI; // point downward, like an anatomical heart
            heartMesh.scale.set(1.15, 1.15, 1.0);
            heartGroup.add(heartMesh);

            // Subtle wireframe overlay for a "scan" feel
            const wireMat = new THREE.MeshBasicMaterial({{ color: 0x00e5ff, wireframe: true, transparent: true, opacity: 0.08 }});
            const wireMesh = new THREE.Mesh(heartMesh.geometry, wireMat);
            wireMesh.rotation.copy(heartMesh.rotation);
            wireMesh.scale.copy(heartMesh.scale);
            heartGroup.add(wireMesh);

            // Aorta / great vessel (curved tube arcing off the top)
            const vesselCurve = new THREE.CatmullRomCurve3([
                new THREE.Vector3(0.1, 1.5, 0.1),
                new THREE.Vector3(0.4, 2.0, -0.1),
                new THREE.Vector3(0.0, 2.3, -0.4),
                new THREE.Vector3(-0.5, 2.1, -0.3),
                new THREE.Vector3(-0.8, 1.6, 0.1)
            ]);
            const vesselGeo = new THREE.TubeGeometry(vesselCurve, 40, 0.22, 12, false);
            const vesselMat = new THREE.MeshPhysicalMaterial({{ color: 0xd94f5c, roughness: 0.4, metalness: 0.1 }});
            const vesselMesh = new THREE.Mesh(vesselGeo, vesselMat);
            heartGroup.add(vesselMesh);

            // ---------- Hotspots ----------
            const hotspotGeo = new THREE.SphereGeometry(0.09, 16, 16);
            const hotspotMat = new THREE.MeshBasicMaterial({{ color: 0x00e5ff }});

            const hotspots = [
                {{ pos: new THREE.Vector3(0.0, 2.15, -0.35), title: "AORTA", desc: "Main artery routing oxygenated blood to systemic circulation." }},
                {{ pos: new THREE.Vector3(0.55, -0.5, 0.55), title: "LEFT VENTRICLE", desc: "Primary muscular pumping chamber sending blood to the body." }},
                {{ pos: new THREE.Vector3(-0.85, 0.75, 0.35), title: "RIGHT ATRIUM", desc: "Receives deoxygenated blood returning from systemic veins." }},
                {{ pos: new THREE.Vector3(0.15, 0.35, 0.85), title: "CORONARY ARTERY", desc: "Supplies oxygenated blood directly to cardiac tissue." }},
                {{ pos: new THREE.Vector3(-0.4, -0.6, 0.6), title: "RIGHT VENTRICLE", desc: "Pumps deoxygenated blood to the lungs via the pulmonary artery." }}
            ];

            const hotspotMeshes = [];
            hotspots.forEach(data => {{
                const mesh = new THREE.Mesh(hotspotGeo, hotspotMat.clone());
                mesh.position.copy(data.pos);
                mesh.userData = data;
                heartGroup.add(mesh);
                hotspotMeshes.push(mesh);

                const ringGeo = new THREE.RingGeometry(0.13, 0.16, 24);
                const ringMat = new THREE.MeshBasicMaterial({{ color: 0x00e5ff, transparent: true, opacity: 0.5, side: THREE.DoubleSide }});
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.position.copy(data.pos);
                ring.lookAt(camera.position);
                heartGroup.add(ring);
                mesh.userData.ring = ring;
            }});

            document.getElementById('loading').style.display = 'none';

            // ---------- Raycasting for interactivity ----------
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const infoBox = document.getElementById('infoBox');
            const defaultInfo = infoBox.innerHTML;

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
                }} else {{
                    infoBox.innerHTML = defaultInfo;
                    container.style.cursor = 'default';
                }}
            }}

            window.addEventListener('mousemove', (e) => updatePointer(e.clientX, e.clientY));
            window.addEventListener('touchmove', (e) => {{
                if (e.touches.length > 0) updatePointer(e.touches[0].clientX, e.touches[0].clientY);
            }}, {{ passive: true }});

            // ---------- Heartbeat pulse animation (speed follows live BPM) ----------
            const clock = new THREE.Clock();
            const bpm = {hr};
            const beatFreq = Math.max(0.4, bpm / 60); // beats per second, roughly

            function animate() {{
                requestAnimationFrame(animate);
                const t = clock.getElapsedTime() * beatFreq;

                // Realistic double-thump pulse (lub-dub), scaled by live heart rate
                const pulse = 1 + Math.sin(t * 4) * 0.035 + Math.max(0, Math.sin(t * 8)) * 0.02;
                heartMesh.scale.set(1.15 * pulse, 1.15 * pulse, 1.0 * pulse);
                wireMesh.scale.copy(heartMesh.scale);

                heartGroup.rotation.y += 0.004;

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

def compute_streak(today_score):
    streak = 1 if today_score >= 75 else 0
    if streak == 0:
        return 0
    dates_sorted = sorted(st.session_state.full_history.keys(), reverse=True)
    for d in dates_sorted:
        day = st.session_state.full_history[d]
        day_score, _, _ = generate_health_summary(
            heart_rate=day["heart_rate"], resting_hr=day["resting_hr"], hrv=day["hrv"],
            sleep_quality=day["sleep_quality"], steps=day["steps"],
            heart_rate_recovery=day["heart_rate_recovery"],
            blood_pressure_variability=day["blood_pressure_variability"]
        )
        if day_score >= 75:
            streak += 1
        else:
            break
    return streak

def compute_period_stats(days, today_values):
    metrics = [
        "heart_rate", "resting_hr", "hrv", "blood_pressure_variability",
        "heart_rate_recovery", "sleep_quality", "steps",
    ]
    dates_sorted = sorted(st.session_state.full_history.keys())
    past_days = dates_sorted[-(days - 1):] if days > 1 else []

    series = {m: [] for m in metrics}
    labels = []
    for d in past_days:
        day = st.session_state.full_history[d]
        labels.append(datetime.strptime(d, "%Y-%m-%d").strftime("%b %d"))
        for m in metrics:
            series[m].append(day[m])
    labels.append("Today")
    for m in metrics:
        series[m].append(today_values[m])

    summary = {}
    for m in metrics:
        vals = series[m]
        first_half = vals[: max(1, len(vals) // 2)]
        second_half = vals[max(1, len(vals) // 2):] or vals
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        if avg_second > avg_first * 1.03:
            trend = "up"
        elif avg_second < avg_first * 0.97:
            trend = "down"
        else:
            trend = "flat"
        summary[m] = {
            "avg": round(sum(vals) / len(vals), 1),
            "min": min(vals),
            "max": max(vals),
            "trend": trend,
        }

    return {"labels": labels, "series": series, "summary": summary, "days": days}

def _pdf_safe(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

def ai_chat_response(question, score, positives, concerns, hr, rhr, hrv_v, sleep_q, steps_v, rec):
    q = question.lower()

    if "score" in q:
        extra = concerns[0] if concerns else "All your key metrics are within healthy ranges today."
        return f"Your current Heart Health Score is {score}/100. {extra}"
    if "sleep" in q:
        note = "That's excellent." if sleep_q >= 80 else "Try aiming for 7-9 hours of consistent sleep to improve this."
        return f"Your sleep quality today is {sleep_q}%. {note}"
    if "hrv" in q or "variability" in q:
        note = "That's a strong reading." if hrv_v >= 50 else "Lower HRV can be linked to stress or incomplete recovery — consider prioritizing rest."
        return f"Your heart rate variability is {hrv_v} ms. {note}"
    if "recover" in q:
        note = "That's a healthy recovery rate." if rec >= 20 else "Recovery is a bit slower than typical — regular cardio can help improve this over time."
        return f"Your heart rate recovery is {rec} BPM. {note}"
    if "step" in q or "activity" in q or "exercise" in q or "walk" in q:
        note = "Great job staying active today!" if steps_v >= 7500 else "Try to work in more movement throughout the day."
        return f"You've logged {steps_v:,} steps today. {note}"
    if "heart rate" in q or " hr " in f" {q} " or q.strip() in ("hr", "bpm"):
        note = "Both are within a typical healthy range." if (60 <= hr <= 100 and 50 <= rhr <= 80) else "One of these is outside the typical range — worth keeping an eye on."
        return f"Your heart rate is {hr} BPM and resting heart rate is {rhr} BPM. {note}"
    if "why" in q and ("low" in q or "bad" in q or "concern" in q or "wrong" in q):
        if concerns:
            return "Based on today's readings, here's what stands out: " + " ".join(concerns)
        return "Nothing concerning stands out in today's readings — your metrics all look healthy!"
    if "good" in q or "well" in q or "great" in q:
        if positives:
            return "Here's what's going well today: " + " ".join(positives)
        return "No standout positives flagged yet today — keep monitoring your trends."
    if "hi" in q or "hello" in q or "hey" in q:
        return "Hi! I'm the PulseGuard assistant. Ask me about your heart rate, sleep, HRV, steps, recovery, or overall score."

    return (
        "I can answer questions about your heart rate, sleep, HRV, steps, recovery, or overall score. "
        "Try asking something like 'why is my score low today?' or 'how's my sleep?'"
    )

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

def _trend_arrow(trend):
    return {"up": "Rising", "down": "Falling", "flat": "Stable"}.get(trend, "Stable")

def generate_pdf_report(score, positives, concerns, ai_insight, heart_rate, resting_hr, hrv,
                         bp, recovery, sleep_quality, steps, battery, last_sync, watch_name,
                         period_label="Today", period_stats=None, patient_name=""):
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
    pdf.cell(content_width, 10, _pdf_safe("PulseGuard Cardiovascular Report"), ln=True)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(content_width, 6, _pdf_safe("New Jersey Heart Disease Prevention (NJHDP)"), ln=True)
    pdf.set_y(36)
    pdf.set_text_color(20, 20, 20)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    meta_label = patient_name.strip() or "Not provided"
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

    _pdf_section_header(pdf, f"Current Readings — {period_label}", content_width)
    pdf.set_font("Helvetica", "", 10.5)

    rows = [
        ("Heart Rate", f"{heart_rate} BPM"),
        ("Resting Heart Rate", f"{resting_hr} BPM"),
        ("Heart Rate Variability", f"{hrv} ms"),
        ("Blood Pressure Variability", f"{bp} mmHg"),
        ("Heart Rate Recovery", f"{recovery} BPM"),
        ("Sleep Quality", f"{sleep_quality}%"),
        ("Daily Steps", f"{steps:,}"),
        ("Watch Battery", f"{battery}%"),
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

    if period_stats and period_stats.get("days", 1) > 1:
        _pdf_section_header(pdf, f"Trend Summary — Last {period_stats['days']} Days", content_width)
        pdf.set_font("Helvetica", "B", 10)
        col_w = [60, 30, 30, 30, 34]
        headers = ["Metric", "Average", "Min", "Max", "Trend"]
        pdf.set_fill_color(8, 17, 31)
        pdf.set_text_color(255, 255, 255)
        for w, h in zip(col_w, headers):
            pdf.cell(w, 8, _pdf_safe(h), border=0, fill=True, align="C")
        pdf.ln(8)
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "", 10)

        metric_display = {
            "heart_rate": ("Heart Rate", "BPM"),
            "resting_hr": ("Resting HR", "BPM"),
            "hrv": ("HRV", "ms"),
            "blood_pressure_variability": ("BP Variability", "mmHg"),
            "heart_rate_recovery": ("HR Recovery", "BPM"),
            "sleep_quality": ("Sleep Quality", "%"),
            "steps": ("Daily Steps", ""),
        }
        summary = period_stats["summary"]
        for i, (key, (name, unit)) in enumerate(metric_display.items()):
            s = summary[key]
            fill = (245, 245, 245) if i % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill)
            pdf.cell(col_w[0], 8, "  " + _pdf_safe(name), border="B", fill=True)
            pdf.cell(col_w[1], 8, _pdf_safe(f"{s['avg']:,.0f}{unit}"), border="B", fill=True, align="C")
            pdf.cell(col_w[2], 8, _pdf_safe(f"{s['min']:,.0f}{unit}"), border="B", fill=True, align="C")
            pdf.cell(col_w[3], 8, _pdf_safe(f"{s['max']:,.0f}{unit}"), border="B", fill=True, align="C")
            pdf.cell(col_w[4], 8, _pdf_safe(_trend_arrow(s["trend"])), border="B", fill=True, align="C", ln=True)
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

    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(120, 120, 120)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(content_width, 5, _pdf_safe(
        "This report is generated by PulseGuard, an educational prototype, from consumer "
        "wearable-device estimates. It does not constitute a medical diagnosis and is not a "
        "substitute for professional medical advice, evaluation, or treatment."
    ))

    return bytes(pdf.output())

def _load_font(bold, size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

def _centered_text(draw, cx, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), text, font=font, fill=fill)

def generate_share_card(score, heart_rate, sleep_quality, steps, watch_name):
    W, H = 1080, 1920
    accent = (0, 229, 255) if score >= 75 else ((255, 183, 3) if score >= 50 else (255, 77, 109))
    dark_navy = (8, 17, 31)

    img = Image.new("RGB", (W, H), dark_navy)
    draw = ImageDraw.Draw(img)

    f_brand = _load_font(True, 62)
    f_tagline = _load_font(False, 32)
    f_giant = _load_font(True, 190)
    f_slash = _load_font(True, 44)
    f_label = _load_font(True, 40)
    f_value = _load_font(True, 46)
    f_footer = _load_font(False, 28)

    draw.text((150, 66), "PulseGuard", font=f_brand, fill=(255, 255, 255))
    draw.text((150, 140), "Daily Heart Health Intelligence", font=f_tagline, fill=(138, 153, 173))

    ring_cx, ring_cy, ring_r = W / 2, 560, 270
    ring_bbox = [ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r]
    draw.arc(ring_bbox, 0, 360, fill=(20, 35, 60), width=30)
    sweep_end = -90 + 360 * max(0, min(100, score)) / 100
    draw.arc(ring_bbox, -90, sweep_end, fill=accent, width=30)

    _centered_text(draw, ring_cx, ring_cy - 130, "HEART HEALTH SCORE", f_label, (138, 153, 173))
    score_txt = f"{score}"
    score_bbox = draw.textbbox((0, 0), score_txt, font=f_giant)
    score_w = score_bbox[2] - score_bbox[0]
    draw.text((ring_cx - score_w / 2, ring_cy - 110), score_txt, font=f_giant, fill=(255, 255, 255))
    _centered_text(draw, ring_cx, ring_cy + 95, "/ 100", f_slash, (138, 153, 173))

    stats = [
        ("Heart Rate", f"{heart_rate} BPM"),
        ("Sleep Quality", f"{sleep_quality}%"),
        ("Daily Steps", f"{steps:,}"),
        ("Device", watch_name),
    ]
    grid_top = 950
    card_w, card_h, gap = 470, 190, 40
    positions = [
        (60, grid_top), (60 + card_w + gap, grid_top),
        (60, grid_top + card_h + gap), (60 + card_w + gap, grid_top + card_h + gap),
    ]
    for (x, y), (label, value) in zip(positions, stats):
        draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=26, fill=(13, 23, 40))
        draw.rounded_rectangle([x, y, x + 10, y + card_h], radius=6, fill=accent)
        draw.text((x + 36, y + 32), label.upper(), font=f_footer, fill=(138, 153, 173))
        draw.text((x + 36, y + 90), value, font=f_value, fill=(255, 255, 255))

    footer_y = grid_top + 2 * card_h + gap + 60
    draw.line([(60, footer_y), (W - 60, footer_y)], fill=(20, 35, 60), width=2)
    _centered_text(draw, W / 2, footer_y + 30, "Generated with PulseGuard Digital Health", f_footer, (138, 153, 173))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

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
# Device & Live Data Controls (Preserved Logic)
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
        if st.button("🎲 Simulate New Reading", use_container_width=True):
            st.session_state.heart_rate = random.randint(55, 130)
            st.session_state.resting_hr = random.randint(45, 90)
            st.session_state.hrv = random.randint(15, 90)
            st.session_state.blood_pressure_variability = random.randint(0, 20)
            st.session_state.heart_rate_recovery = random.randint(5, 40)
            st.session_state.sleep_quality = random.randint(30, 100)
            st.session_state.steps = random.randint(500, 15000)
            st.session_state.battery = random.randint(10, 100)
            st.session_state.tip_index = random.randint(0, len(TIPS) - 1)

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

    # Hero Banner Design
    st.markdown(
        f"""
        <div class="glass-card" style="padding:40px; margin-bottom:24px; background: linear-gradient(135deg, rgba(13, 23, 40, 0.9) 0%, rgba(8, 17, 31, 0.95) 100%);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;">
                <div style="max-width:650px;">
                    <div style="display:inline-block; padding:4px 12px; border-radius:20px; background:rgba(0,229,255,0.1); border:1px solid rgba(0,229,255,0.3); color:#00E5FF; font-size:12px; font-weight:700; margin-bottom:12px;">
                        NEXT-GEN CARDIOVASCULAR INTELLIGENCE
                    </div>
                    <h1 style="font-size:42px; font-weight:800; letter-spacing:-0.03em; margin:0 0 12px 0; background:linear-gradient(135deg, #FFFFFF 40%, #8A99AD 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                        Protect Your Heart Before It Warns You.
                    </h1>
                    <p style="font-size:16px; color:#8A99AD; margin:0; line-height:1.6;">
                        Continuous wearable telemetric analysis detecting real-time cardiovascular shifts, recovery states, and stress indexes.
                    </p>
                </div>
                <div style="text-align:center; background:rgba(8, 17, 31, 0.8); border:2px solid {hex_to_rgba(_score_color, 0.5)}; border-radius:24px; padding:24px 36px; box-shadow:0 0 30px {hex_to_rgba(_score_color, 0.2)};">
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#8A99AD;">Cardiovascular Health Score</div>
                    <div style="font-size:52px; font-weight:800; color:{_score_color}; line-height:1; margin:8px 0;">
                        {_today_score}
                    </div>
                    <span style="font-size:12px; font-weight:600; color:#8A99AD;">OUT OF 100</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tip_col, streak_col = st.columns([2, 1])
    with tip_col:
        st.markdown(
            f"""
            <div class="glass-card" style="padding:16px 20px; display:flex; align-items:center; gap:14px;">
                <div style="font-size:20px;">💡</div>
                <div style="font-size:13.5px; color:#E2E8F0;">
                    <strong style="color:#00E5FF;">Daily Insight:</strong> {TIPS[st.session_state.tip_index]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with streak_col:
        _streak = compute_streak(_today_score)
        st.markdown(
            f"""
            <div class="glass-card" style="padding:16px 20px; text-align:center;">
                <span style="font-size:14px; font-weight:700; color:#FFB703;">🔥 {_streak}-Day Optimal Health Streak</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.subheader("📊 Vital Statistics")

    snap_row1 = st.columns(4)
    snap_items = [
        ("❤️ Heart Rate", f"{heart_rate} BPM", "heart_rate", heart_rate),
        ("💓 Resting HR", f"{resting_hr} BPM", "resting_hr", resting_hr),
        ("📊 HRV", f"{hrv} ms", "hrv", hrv),
        ("🩺 BP Var", f"{blood_pressure_variability} mmHg", "bp_variability", blood_pressure_variability),
    ]
    for _col, (_title, _val, _kind, _raw) in zip(snap_row1, snap_items):
        with _col:
            _, _color, _ = metric_status(_kind, _raw)
            render_metric_card(_title, _val, _color)

    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    snap_row2 = st.columns(3)
    snap_items2 = [
        ("🏃 Recovery", f"{heart_rate_recovery} BPM", "recovery", heart_rate_recovery),
        ("😴 Sleep Quality", f"{sleep_quality}%", "sleep", sleep_quality),
        ("👟 Daily Steps", f"{steps:,}", "steps", steps),
    ]
    for _col, (_title, _val, _kind, _raw) in zip(snap_row2, snap_items2):
        with _col:
            _, _color, _ = metric_status(_kind, _raw)
            render_metric_card(_title, _val, _color)

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
    viz_col, radar_col = st.columns([3, 2])
    with viz_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📉 7-Day Performance Trends")
        render_trend_chart(heart_rate, sleep_quality, steps)
        st.markdown('</div>', unsafe_allow_html=True)
    with radar_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🕸️ Comprehensive Biomarkers")
        render_radar_chart(heart_rate, resting_hr, hrv, blood_pressure_variability,
                            heart_rate_recovery, sleep_quality, steps)
        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# HEART DASHBOARD PAGE
# =====================================================
elif page == "❤️ Heart Dashboard":

    st.markdown("<h2 style='font-weight:800;'>❤️ Cardiovascular Analytics</h2>", unsafe_allow_html=True)
    st.caption("Deep-dive metrics evaluating real-time heart rate dynamics and autonomic recovery.")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        _, color, _ = metric_status("heart_rate", heart_rate)
        render_metric_card("Heart Rate", f"{heart_rate} BPM", color)
    with col2:
        _, color, _ = metric_status("resting_hr", resting_hr)
        render_metric_card("Resting Heart Rate", f"{resting_hr} BPM", color)
    with col3:
        _, color, _ = metric_status("hrv", hrv)
        render_metric_card("Heart Rate Variability", f"{hrv} ms", color)

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        _, color, _ = metric_status("bp_variability", blood_pressure_variability)
        render_metric_card("Blood Pressure Variability", f"{blood_pressure_variability} mmHg", color)
    with col5:
        _, color, _ = metric_status("recovery", heart_rate_recovery)
        render_metric_card("Heart Rate Recovery", f"{heart_rate_recovery} BPM", color)
    with col6:
        _, color, _ = metric_status("sleep", sleep_quality)
        render_metric_card("Sleep Quality", f"{sleep_quality}%", color)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🫀 Interactive 3D Anatomical Heart")
    st.caption("Drag to rotate, scroll to zoom, hover the glowing nodes to explore key structures. Beat speed follows your live heart rate.")
    render_3d_heart(heart_rate)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)
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

    gauge_col, anim_col = st.columns([1, 1])
    with gauge_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        render_score_gauge(score)
        st.markdown('</div>', unsafe_allow_html=True)
    with anim_col:
        animate_score(score)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🧠 PulseGuard AI Clinical Summary")
    ai_insight = generate_ai_insight(score, positives, concerns)
    st.write(ai_insight)
    st.markdown('</div>', unsafe_allow_html=True)

    if positives:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        st.write("### ✅ Favorable Parameters")
        render_chips([(p, GOOD) for p in positives])

    if concerns:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        st.write("### ⚠ Areas Requiring Attention")
        render_chips([(c, DANGER) for c in concerns])

    st.markdown("---")
    st.subheader("📤 Export Clinical Reports & Cards")

    RANGE_OPTIONS = {"1 Day": 1, "1 Week": 7, "1 Month": 30}
    _range_label = st.radio("🗓️ Report Timeline Range", list(RANGE_OPTIONS.keys()), horizontal=True)
    _range_days = RANGE_OPTIONS[_range_label]

    _today_values = {
        "heart_rate": heart_rate, "resting_hr": resting_hr, "hrv": hrv,
        "blood_pressure_variability": blood_pressure_variability,
        "heart_rate_recovery": heart_rate_recovery, "sleep_quality": sleep_quality, "steps": steps,
    }
    _period_stats = compute_period_stats(_range_days, _today_values) if _range_days > 1 else None
    _period_label = f"{_range_label} ({datetime.now(ZoneInfo('America/New_York')).strftime('%b %d, %Y')})"

    pdf_bytes = generate_pdf_report(
        score, positives, concerns, ai_insight, heart_rate, resting_hr, hrv,
        blood_pressure_variability, heart_rate_recovery, sleep_quality, steps,
        battery, last_sync, watch_plain_name,
        period_label=_period_label, period_stats=_period_stats,
    )
    share_card_bytes = generate_share_card(score, heart_rate, sleep_quality, steps, watch_plain_name)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            f"📄 Download Doctor PDF Report ({_range_label})",
            data=pdf_bytes,
            file_name=f"PulseGuard_Report_{_range_label.replace(' ', '')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    with dl_col2:
        st.download_button(
            "📸 Download Social Share Card",
            data=share_card_bytes,
            file_name="PulseGuard_Summary.png",
            mime="image/png",
            use_container_width=True,
        )

# =====================================================
# AI CHAT ASSISTANT PAGE
# =====================================================
elif page == "🤖 AI Assistant":

    st.markdown("<h2 style='font-weight:800;'>🤖 PulseGuard AI Assistant</h2>", unsafe_allow_html=True)
    st.caption("Ask questions about your real-time telemetry, resting heart rates, or HRV values.")
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
        st.session_state.chat_history.append(("user", user_question))
        _score, _positives, _concerns = generate_health_summary()
        response = ai_chat_response(
            user_question, _score, _positives, _concerns,
            heart_rate, resting_hr, hrv, sleep_quality, steps, heart_rate_recovery
        )
        st.session_state.chat_history.append(("assistant", response))
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
                <p style="color:#8A99AD;">Ensure your wearable fits snugly above the wrist bone. Movement artifacts can create false heart rate spikes during optical PPG sensor polling.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="glass-card">
                <h3>💧 Hydration & PPG Signal Quality</h3>
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
# Footer & Autoplay Logic (100% Preserved)
# --------------------------------------------------
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; padding:24px; color:#8A99AD; font-size:12px; border-top:1px solid rgba(255,255,255,0.05);">
        PulseGuard Health Telemetry • Version 2.0 Premium Dashboard<br>
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
