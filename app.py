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
# Advanced CSS & Clean Tabs
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

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

.glass-card {
    background: rgba(13, 23, 40, 0.65) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    margin-bottom: 16px;
}

/* Tab Styling Fixes */
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-weight: 700 !important;
    font-size: 14px !important;
    color: #8A99AD !important;
    background-color: transparent !important;
    padding: 10px 20px !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #00E5FF !important;
    border-bottom: 2px solid #00E5FF !important;
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
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.navbar-title {
    font-size: 20px;
    font-weight: 800;
    color: #FFFFFF;
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
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def metric_status(kind, value):
    if kind == "heart_rate":
        if 60 <= value <= 100: return "Optimal", GOOD, 100
        elif 50 <= value < 60 or 100 < value <= 110: return "Elevated", WARN, 60
        else: return "Anomaly", DANGER, 30
    if kind == "resting_hr":
        if 50 <= value <= 80: return "Optimal", GOOD, 100
        elif 40 <= value < 50 or 80 < value <= 90: return "Elevated", WARN, 60
        else: return "High", DANGER, 30
    if kind == "hrv":
        if value >= 50: return "Optimal", GOOD, min(100, value)
        elif value >= 30: return "Moderate", WARN, 60
        else: return "Low Recovery", DANGER, 30
    if kind == "bp_variability":
        if value <= 10: return "Stable", GOOD, 100
        elif value <= 15: return "Moderate", WARN, 60
        else: return "High", DANGER, 30
    if kind == "recovery":
        if value >= 20: return "Optimal", GOOD, min(100, value * 2)
        elif value >= 15: return "Fair", WARN, 60
        else: return "Delayed", DANGER, 30
    if kind == "sleep":
        if value >= 80: return "Restful", GOOD, value
        elif value >= 60: return "Fair", WARN, value
        else: return "Restless", DANGER, value
    if kind == "steps":
        pct = min(100, value / 10000 * 100)
        if value >= 10000: return "Goal Met", GOOD, 100
        elif value >= 7500: return "Active", WARN, pct
        else: return "Below Goal", DANGER, pct
    return "Optimal", GOOD, 100

def render_metric_card(title, value_str, color, micro_insight="", trend_str="", trend_class="trend-neutral"):
    st.container()
    with st.container(border=True):
        st.caption(f"{title.upper()} {f'({trend_str})' if trend_str else ''}")
        st.subheader(value_str)
        if micro_insight:
            st.caption(micro_insight)

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
    <div style="background: rgba(8, 17, 31, 0.9); border-radius: 16px; padding: 12px; border: 1px solid rgba(0, 229, 255, 0.2);">
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
    {"title": "Aorta", "desc": "Main artery routing oxygenated blood from the heart."},
    {"title": "Left Ventricle", "desc": "Primary pumping chamber sending blood to the body."},
    {"title": "Right Atrium", "desc": "Receives deoxygenated blood returning from the body."},
    {"title": "Coronary Artery", "desc": "Supplies blood directly to cardiac tissue."},
    {"title": "Right Ventricle", "desc": "Pumps deoxygenated blood to the lungs."},
]

def render_heart_structure_reference():
    cols = st.columns(len(HEART_STRUCTURES))
    for _col, _struct in zip(cols, HEART_STRUCTURES):
        with _col:
            st.caption(f"📍 {_struct['title']}")
            st.write(_struct['desc'])

def render_3d_heart(hr=72):
    MODEL_URL = "https://cdn.jsdelivr.net/gh/FreddieSawiras/NJHDP-PulseGaurd@main/assets/scene.gltf"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body {{ margin: 0; height: 100%; overflow: hidden; background: transparent; font-family: sans-serif; }}
            #container {{ width: 100%; height: 100%; min-height: 500px; position: relative; }}
            #infoBox {{
                position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
                background: rgba(8, 17, 31, 0.85);
                border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 14px;
                padding: 10px 20px; color: #FFFFFF; font-size: 12.5px; text-align: center;
                pointer-events: none; z-index: 10;
            }}
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    </head>
    <body>
        <div id="container">
            <div id="infoBox">💡 Drag to rotate • Scroll to zoom</div>
        </div>
        <script>
            const container = document.getElementById('container');
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0.3, 7.5);

            const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            const ambientLight = new THREE.AmbientLight(0xffffff, 1.1);
            scene.add(ambientLight);

            const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
            keyLight.position.set(5, 8, 6);
            scene.add(keyLight);

            const heartGroup = new THREE.Group();
            scene.add(heartGroup);

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
                    heartGroup.add(model);
                }}
            );

            const clock = new THREE.Clock();
            function animate() {{
                requestAnimationFrame(animate);
                const t = clock.getElapsedTime();
                const pulse = 1 + Math.sin(t * 4) * 0.035;
                heartGroup.scale.set(pulse, pulse, pulse);
                heartGroup.rotation.y += 0.0012;
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=520)

def generate_health_summary():
    metric_scores = [
        metric_status("heart_rate", st.session_state.heart_rate)[2],
        metric_status("resting_hr", st.session_state.resting_hr)[2],
        metric_status("hrv", st.session_state.hrv)[2],
        metric_status("bp_variability", st.session_state.blood_pressure_variability)[2],
        metric_status("recovery", st.session_state.heart_rate_recovery)[2],
        metric_status("sleep", st.session_state.sleep_quality)[2],
        metric_status("steps", st.session_state.steps)[2],
    ]
    score = round(sum(metric_scores) / len(metric_scores))
    return score, ["Stable resting baseline"], ["Monitor sleep quality"]

def animate_score(final_score):
    c = score_color(final_score)
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; padding:32px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:#8A99AD;">Overall Vital Status</div>
            <div style="font-size:56px; font-weight:800; color:{c}; margin:8px 0;">
                {final_score}<span style="font-size:24px; color:#8A99AD;">/100</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------------
# Top Floating Navigation Header
# --------------------------------------------------
NAV_ITEMS = ["🏠 Home", "❤️ Heart Dashboard", "⌚ Smartwatch", "📈 Health Summary", "🤖 AI Assistant", "💡 Accuracy Tips", "ℹ️ About"]

if "current_page" not in st.session_state:
    st.session_state.current_page = NAV_ITEMS[0]

st.markdown(
    f"""
    <div class="top-navbar">
        <div class="navbar-brand">
            <img src="{LOGO_URL}" width="38" style="border-radius:10px;">
            <div class="navbar-title">PulseGuard</div>
        </div>
        <div style="font-size:12px; color:#8A99AD; font-family:'JetBrains Mono', monospace;">
            {datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y")}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

_nav_cols = st.columns(len(NAV_ITEMS))
for _col, _item in zip(_nav_cols, NAV_ITEMS):
    with _col:
        _is_active = st.session_state.current_page == _item
        if st.button(_item, key=f"nav_{_item}", use_container_width=True, type="primary" if _is_active else "secondary"):
            st.session_state.current_page = _item
            st.rerun()

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
page = st.session_state.current_page

# --------------------------------------------------
# Device & Live Data Controls
# --------------------------------------------------
with st.expander("⚙️ Device & Live Data Controls", expanded=False):
    slider_row1 = st.columns(4)
    with slider_row1[0]:
        st.slider("❤️ Heart Rate (BPM)", 30, 180, key="heart_rate")
    with slider_row1[1]:
        st.slider("💓 Resting HR (BPM)", 30, 130, key="resting_hr")
    with slider_row1[2]:
        st.slider("📊 HRV (ms)", 0, 150, key="hrv")
    with slider_row1[3]:
        st.slider("🩺 BP Var (mmHg)", 0, 40, key="blood_pressure_variability")

# =====================================================
# PAGES
# =====================================================
if page == "🏠 Home":
    _today_score, _, _ = generate_health_summary()
    _score_color = score_color(_today_score)

    st.markdown("## 👋 Welcome back!")
    
    stat_cols = st.columns(4)
    with stat_cols[0]:
        render_metric_card("Heart Rate", f"{st.session_state.heart_rate} BPM", GOOD, "Normal baseline")
    with stat_cols[1]:
        render_metric_card("Resting HR", f"{st.session_state.resting_hr} BPM", GOOD, "Optimal")
    with stat_cols[2]:
        render_metric_card("HRV Recovery", f"{st.session_state.hrv} ms", GOOD, "Good balance")
    with stat_cols[3]:
        render_metric_card("BP Var", f"{st.session_state.blood_pressure_variability} mmHg", GOOD, "Stable")

elif page == "❤️ Heart Dashboard":
    st.markdown("## ❤️ Cardiovascular Analytics")

    # Tabs with fixed rendering
    tab_vitals, tab_3d, tab_ecg = st.tabs(["📊 VITALS", "🫀 3D MODEL", "💓 ECG WAVEFORM"])

    with tab_vitals:
        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card("Heart Rate", f"{st.session_state.heart_rate} BPM", GOOD)
        with col2:
            render_metric_card("Resting Heart Rate", f"{st.session_state.resting_hr} BPM", GOOD)
        with col3:
            render_metric_card("Heart Rate Variability", f"{st.session_state.hrv} ms", GOOD)

        col4, col5, col6 = st.columns(3)
        with col4:
            render_metric_card("Blood Pressure Var", f"{st.session_state.blood_pressure_variability} mmHg", GOOD)
        with col5:
            render_metric_card("Heart Rate Recovery", f"{st.session_state.heart_rate_recovery} BPM", GOOD)
        with col6:
            render_metric_card("Sleep Quality", f"{st.session_state.sleep_quality}%", GOOD)

    with tab_3d:
        st.subheader("🫀 Interactive 3D Anatomical Heart")
        render_3d_heart(st.session_state.heart_rate)
        st.markdown("<br>", unsafe_allow_html=True)
        render_heart_structure_reference()

    with tab_ecg:
        st.subheader("💓 Simulated Real-Time Waveform (ECG)")
        render_ecg_animation(st.session_state.heart_rate)

elif page == "⌚ Smartwatch":
    st.markdown("## ⌚ Connected Wearable Device")
    st.info(f"Connected to {st.session_state.selected_watch}")

elif page == "📈 Health Summary":
    st.markdown("## 📈 Daily Health Summary")
    score, positives, concerns = generate_health_summary()
    render_score_gauge(score)

elif page == "🤖 AI Assistant":
    st.markdown("## 🤖 PulseGuard AI Assistant")
    st.chat_input("Ask a question about your health metrics...")

elif page == "💡 Accuracy Tips":
    st.markdown("## 💡 Accuracy Tips")
    st.write("Wear your watch snugly above your wrist bone for accurate readings.")

elif page == "ℹ️ About":
    st.markdown("## ℹ️ About PulseGuard")
    st.write("PulseGuard is a cardiovascular health intelligence dashboard.")
