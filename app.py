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
# CSS Theme Architecture
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #060C17 !important;
    background-image: 
        radial-gradient(circle at 10% 10%, rgba(0, 229, 255, 0.05) 0%, transparent 45%),
        radial-gradient(circle at 90% 20%, rgba(124, 92, 255, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 50% 85%, rgba(255, 77, 109, 0.04) 0%, transparent 55%),
        linear-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px) !important;
    background-size: 100% 100%, 100% 100%, 100% 100%, 32px 32px, 32px 32px !important;
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    color: #F0F4F8 !important;
}

section[data-testid="stSidebar"], [data-testid="collapsedControl"], header[data-testid="stHeader"] {
    display: none !important;
}

.stMainBlockContainer {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* Glassmorphism Cards */
.glass-card {
    background: rgba(13, 23, 40, 0.6) !important;
    backdrop-filter: blur(24px) saturate(190%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(190%) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    position: relative;
}

.glass-card:hover {
    border-color: rgba(0, 229, 255, 0.25) !important;
    box-shadow: 0 20px 45px rgba(0, 229, 255, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
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
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8A99AD;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #FFFFFF;
}

/* Header & Logo */
.brand-container {
    display: flex;
    align-items: center;
    gap: 14px;
}

.brand-title {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #FFFFFF 40%, #00E5FF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.brand-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0, 229, 255, 0.08);
    border: 1px solid rgba(0, 229, 255, 0.25);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    color: #00E5FF;
    letter-spacing: 0.05em;
}

.pulse-dot {
    width: 7px;
    height: 7px;
    background-color: #00E5FF;
    border-radius: 50%;
    box-shadow: 0 0 10px #00E5FF;
    animation: pulseGlow 1.8s infinite;
}

@keyframes pulseGlow {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(0, 229, 255, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 229, 255, 0); }
}

/* Clean Custom Button Overrides */
.stButton > button {
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    background: rgba(255, 255, 255, 0.03) !important;
    color: #C5CEE0 !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 0.55rem 1.1rem !important;
    transition: all 0.2s ease !important;
    backdrop-filter: blur(10px) !important;
}

.stButton > button:hover {
    background: rgba(0, 229, 255, 0.08) !important;
    border-color: rgba(0, 229, 255, 0.4) !important;
    color: #00E5FF !important;
    box-shadow: 0 0 15px rgba(0, 229, 255, 0.15) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00E5FF 0%, #3B82F6 100%) !important;
    color: #040914 !important;
    border: none !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(0, 229, 255, 0.3) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 25px rgba(0, 229, 255, 0.5) !important;
    transform: translateY(-1px) !important;
    color: #040914 !important;
}

div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background-color: rgba(8, 17, 31, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #FFFFFF !important;
}

/* Chat Bubbles */
.chat-bubble-user {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(124, 92, 255, 0.2));
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
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Helper Functions
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

# Count-Up Animated Score Component
def render_animated_score(score):
    color = score_color(score)
    html_code = f"""
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px; font-family:'Plus Jakarta Sans', sans-serif;">
        <div style="position:relative; width:220px; height:220px;">
            <svg width="220" height="220" viewBox="0 0 220 220">
                <circle cx="110" cy="110" r="90" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="16" />
                <circle id="scoreProgress" cx="110" cy="110" r="90" fill="none" stroke="{color}" stroke-width="16"
                        stroke-dasharray="565.48" stroke-dashoffset="565.48" stroke-linecap="round"
                        transform="rotate(-90 110 110)" style="transition: stroke-dashoffset 2.5s cubic-bezier(0.1, 0.8, 0.2, 1), stroke 0.5s ease;" />
            </svg>
            <div style="position:absolute; top:0; left:0; width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <span id="scoreVal" style="font-size:56px; font-weight:800; color:#FFFFFF; line-height:1;">0</span>
                <span style="font-size:13px; font-weight:700; color:#8A99AD; letter-spacing:0.08em; margin-top:4px;">OUT OF 100</span>
            </div>
        </div>
        <div style="margin-top:16px; padding:6px 18px; border-radius:20px; background:{hex_to_rgba(color,0.15)}; color:{color}; font-weight:700; font-size:13px; border:1px solid {hex_to_rgba(color,0.3)};">
            {"OPTIMAL HEALTH" if score >= 80 else ("STABLE CONDITION" if score >= 60 else "ATTENTION RECOMMENDED")}
        </div>
    </div>
    <script>
    (function() {{
        let targetScore = {score};
        let duration = 2500;
        let startTime = null;
        let scoreValEl = document.getElementById('scoreVal');
        let progressEl = document.getElementById('scoreProgress');
        let circumference = 565.48;

        function animate(currentTime) {{
            if (!startTime) startTime = currentTime;
            let elapsed = currentTime - startTime;
            let progress = Math.min(elapsed / duration, 1);
            let easeProgress = 1 - Math.pow(1 - progress, 3);
            
            let currentScore = Math.floor(easeProgress * targetScore);
            scoreValEl.innerText = currentScore;
            
            let offset = circumference - (easeProgress * targetScore / 100 * circumference);
            progressEl.style.strokeDashoffset = offset;

            if (progress < 1) {{
                requestAnimationFrame(animate);
            }}
        }}
        requestAnimationFrame(animate);
    }})();
    </script>
    """
    components.html(html_code, height=310)

# Interactive 3D Canvas Heart Component
def render_3d_heart():
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; overflow: hidden; background: transparent; font-family: 'Plus Jakarta Sans', sans-serif; }
            #container { width: 100vw; height: 100vh; position: relative; }
            #infoBox {
                position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
                background: rgba(8, 17, 31, 0.85); backdrop-filter: blur(12px);
                border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 14px;
                padding: 12px 24px; color: #FFFFFF; font-size: 13px; font-weight: 600;
                text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                pointer-events: none; transition: all 0.3s ease;
                z-index: 10;
            }
            .part-tag { color: #00E5FF; font-weight: 700; }
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    </head>
    <body>
        <div id="container">
            <div id="infoBox">💡 Drag to rotate • Scroll to zoom • Hover glowing nodes for details</div>
        </div>
        <script>
            const container = document.getElementById('container');
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(0, 0, 14);

            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            // Ambient & Point Lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);

            const mainLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
            mainLight.position.set(5, 10, 7);
            scene.add(mainLight);

            const redLight = new THREE.PointLight(0xff2b55, 2, 20);
            redLight.position.set(-5, -2, 5);
            scene.add(redLight);

            // Create Procedural Anatomical 3D Heart Group
            const heartGroup = new THREE.Group();

            // Main Ventricles Object
            const heartGeo = new THREE.SphereGeometry(2.5, 32, 32);
            heartGeo.scale(1, 1.3, 0.9);
            const positions = heartGeo.attributes.position;
            for (let i = 0; i < positions.count; i++) {
                let y = positions.getY(i);
                if (y < 0) {
                    let factor = 1 + (y * 0.25);
                    positions.setX(i, positions.getX(i) * Math.max(0.1, factor));
                    positions.setZ(i, positions.getZ(i) * Math.max(0.1, factor));
                }
            }
            heartGeo.computeVertexNormals();

            const heartMat = new THREE.MeshStandardMaterial({
                color: 0xe63946, roughness: 0.3, metalness: 0.2,
                emissive: 0x3a0007, emissiveIntensity: 0.3
            });
            const mainHeart = new THREE.Mesh(heartGeo, heartMat);
            heartGroup.add(mainHeart);

            // Aorta Curve
            const aortaCurve = new THREE.CatmullRomCurve3([
                new THREE.Vector3(0, 2, 0),
                new THREE.Vector3(0, 3.5, 0),
                new THREE.Vector3(-0.8, 4.3, 0),
                new THREE.Vector3(-1.5, 3.8, -0.5),
                new THREE.Vector3(-1.5, 2.2, -0.8)
            ]);
            const aortaGeo = new THREE.TubeGeometry(aortaCurve, 32, 0.55, 16, false);
            const aortaMat = new THREE.MeshStandardMaterial({ color: 0xff4d6d, roughness: 0.2, metalness: 0.1 });
            const aorta = new THREE.Mesh(aortaGeo, aortaMat);
            heartGroup.add(aorta);

            // Atria Bulges
            const atriumGeo = new THREE.SphereGeometry(1.1, 24, 24);
            const atriumMat = new THREE.MeshStandardMaterial({ color: 0xc1121f, roughness: 0.4 });
            
            const leftAtrium = new THREE.Mesh(atriumGeo, atriumMat);
            leftAtrium.position.set(1.4, 1.8, -0.3);
            heartGroup.add(leftAtrium);

            const rightAtrium = new THREE.Mesh(atriumGeo, atriumMat);
            rightAtrium.position.set(-1.4, 1.8, -0.3);
            heartGroup.add(rightAtrium);

            // Hotspot setup
            const hotspotGeo = new THREE.SphereGeometry(0.2, 16, 16);
            const hotspotMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });

            const hotspots = [
                { pos: new THREE.Vector3(0, 3.8, 0.2), title: "AORTA", desc: "Main artery routing oxygenated blood to systemic circulation." },
                { pos: new THREE.Vector3(0.8, -0.5, 1.8), title: "LEFT VENTRICLE", desc: "Primary muscular pumping chamber sending blood to the body." },
                { pos: new THREE.Vector3(-1.5, 1.8, 0.8), title: "RIGHT ATRIUM", desc: "Receives deoxygenated blood returning from systemic veins." },
                { pos: new THREE.Vector3(0, 0.5, 2.1), title: "CORONARY ARTERY", desc: "Supplies oxygenated blood directly to cardiac tissue." }
            ];

            const hotspotMeshes = [];
            hotspots.forEach(data => {
                const mesh = new THREE.Mesh(hotspotGeo, hotspotMat.clone());
                mesh.position.copy(data.pos);
                mesh.userData = data;
                heartGroup.add(mesh);
                hotspotMeshes.push(mesh);
            });

            scene.add(heartGroup);

            // Raycasting for interactivity
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const infoBox = document.getElementById('infoBox');

            window.addEventListener('mousemove', (e) => {
                mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
                mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(hotspotMeshes);

                if (intersects.length > 0) {
                    const data = intersects[0].object.userData;
                    infoBox.innerHTML = `<span class="part-tag">📍 ${data.title}:</span> ${data.desc}`;
                    document.body.style.cursor = 'pointer';
                } else {
                    document.body.style.cursor = 'default';
                }
            });

            // Heartbeat Pulse Animation Loop
            let clock = new THREE.Clock();
            function animate() {
                requestAnimationFrame(animate);
                let elapsedTime = clock.getElapsedTime();

                // Realistic double-thump pulse scale
                let beat = 1 + Math.sin(elapsedTime * 4) * 0.03 + Math.sin(elapsedTime * 8) * 0.015;
                mainHeart.scale.set(beat, beat * 1.3, beat * 0.9);

                // Idle Rotation
                heartGroup.rotation.y += 0.005;

                // Hotspot pulse
                hotspotMeshes.forEach(m => {
                    let s = 1 + Math.sin(elapsedTime * 6) * 0.3;
                    m.scale.set(s, s, s);
                });

                controls.update();
                renderer.render(scene, camera);
            }
            animate();

            window.addEventListener('resize', () => {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            });
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=500)

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
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True)

def render_trend_chart(hr, sleep, steps_v):
    days = ["6d ago", "5d ago", "4d ago", "3d ago", "2d ago", "Yesterday", "Today"]
    hr_series = st.session_state.trend_data["heart_rate"] + [hr]
    sleep_series = st.session_state.trend_data["sleep_quality"] + [sleep]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=hr_series, name="Heart Rate (BPM)", mode='lines+markers', line=dict(color='#FF4D6D', width=3, shape='spline')))
    fig.add_trace(go.Scatter(x=days, y=sleep_series, name="Sleep Quality (%)", mode='lines+markers', line=dict(color='#7C5CFF', width=3, shape='spline')))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
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

    positives, concerns = [], []

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
        trend = "up" if avg_second > avg_first * 1.03 else ("down" if avg_second < avg_first * 0.97 else "flat")
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

    return "I can answer questions about your heart rate, sleep, HRV, steps, recovery, or overall score."

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

    score_rgb = (0, 180, 200) if score >= 75 else ((191, 144, 0) if score >= 50 else (255, 77, 109))
    score_word = "Good" if score >= 75 else ("Fair" if score >= 50 else "Needs Attention")

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

    _pdf_section_header(pdf, "Summary for Clinical Review", content_width)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(content_width, 6, _pdf_safe(ai_insight))
    pdf.ln(4)

    return bytes(pdf.output())

def _load_font(bold, size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def generate_share_card(score, heart_rate, sleep_quality, steps, watch_name):
    W, H = 1080, 1920
    accent = (0, 229, 255) if score >= 75 else ((255, 183, 3) if score >= 50 else (255, 77, 109))
    img = Image.new("RGB", (W, H), (8, 17, 31))
    draw = ImageDraw.Draw(img)

    f_brand = _load_font(True, 62)
    f_tagline = _load_font(False, 32)
    f_giant = _load_font(True, 190)
    f_label = _load_font(True, 40)
    f_value = _load_font(True, 46)
    f_footer = _load_font(False, 28)

    draw.text((150, 66), "PulseGuard", font=f_brand, fill=(255, 255, 255))
    draw.text((150, 140), "Daily Heart Health Intelligence", font=f_tagline, fill=(138, 153, 173))

    ring_cx, ring_cy, ring_r = W / 2, 560, 270
    draw.arc([ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r], 0, 360, fill=(20, 35, 60), width=30)
    sweep_end = -90 + 360 * max(0, min(100, score)) / 100
    draw.arc([ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r], -90, sweep_end, fill=accent, width=30)

    score_txt = f"{score}"
    draw.text((ring_cx - 80, ring_cy - 100), score_txt, font=f_giant, fill=(255, 255, 255))

    stats = [
        ("Heart Rate", f"{heart_rate} BPM"),
        ("Sleep Quality", f"{sleep_quality}%"),
        ("Daily Steps", f"{steps:,}"),
        ("Device", watch_name),
    ]
    grid_top, card_w, card_h, gap = 950, 470, 190, 40
    positions = [(60, grid_top), (60 + card_w + gap, grid_top), (60, grid_top + card_h + gap), (60 + card_w + gap, grid_top + card_h + gap)]
    for (x, y), (label, value) in zip(positions, stats):
        draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=26, fill=(13, 23, 40))
        draw.rounded_rectangle([x, y, x + 10, y + card_h], radius=6, fill=accent)
        draw.text((x + 36, y + 32), label.upper(), font=f_footer, fill=(138, 153, 173))
        draw.text((x + 36, y + 90), value, font=f_value, fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --------------------------------------------------
# Sleek Navigation Header
# --------------------------------------------------
NAV_ITEMS = [
    "🏠 Home",
    "❤️ Heart Analytics",
    "🔬 3D Heart Explorer",
    "⌚ Smartwatch",
    "📈 Health Summary",
    "🤖 AI Assistant",
    "💡 Accuracy Tips",
]

if "current_page" not in st.session_state:
    st.session_state.current_page = NAV_ITEMS[0]

# Unboxed Top Header
header_col1, header_col2 = st.columns([1, 1])
with header_col1:
    st.markdown(
        f"""
        <div class="brand-container">
            <img src="{LOGO_URL}" width="40" style="filter: drop-shadow(0 0 10px rgba(0,229,255,0.5));">
            <div>
                <div class="brand-title">PulseGuard</div>
            </div>
            <div class="brand-badge">
                <div class="pulse-dot"></div>
                <span>LIVE TELEMETRY</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with header_col2:
    st.markdown(
        f"""
        <div style="text-align:right; font-size:13px; color:#8A99AD; font-family:'JetBrains Mono', monospace; margin-top:8px;">
            📅 {datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")}
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# Modern Pill Navigation Bar
nav_cols = st.columns(len(NAV_ITEMS))
for _col, _item in zip(nav_cols, NAV_ITEMS):
    with _col:
        _is_active = st.session_state.current_page == _item
        if st.button(_item, key=f"nav_{_item}", use_container_width=True, type="primary" if _is_active else "secondary"):
            st.session_state.current_page = _item
            st.rerun()

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

page = st.session_state.current_page

# --------------------------------------------------
# Device & Data Controls Drawer
# --------------------------------------------------
with st.expander("⚙️ Device Telemetry Controls & Simulation", expanded=False):
    device_col, action_col = st.columns([2, 1])
    with device_col:
        st.session_state.selected_watch = st.selectbox(
            "Select Connected Wearable Device",
            list(WATCH_OPTIONS.keys()),
            index=list(WATCH_OPTIONS.keys()).index(st.session_state.selected_watch)
        )
        watch_plain_name = " ".join(st.session_state.selected_watch.split(" ")[1:])
    with action_col:
        if st.button("🎲 Simulate New Reading", use_container_width=True):
            st.session_state.heart_rate = random.randint(55, 130)
            st.session_state.resting_hr = random.randint(45, 90)
            st.session_state.hrv = random.randint(15, 90)
            st.session_state.blood_pressure_variability = random.randint(0, 20)
            st.session_state.heart_rate_recovery = random.randint(5, 40)
            st.session_state.sleep_quality = random.randint(30, 100)
            st.session_state.steps = random.randint(500, 15000)
            st.session_state.battery = random.randint(10, 100)
            st.rerun()

    st.markdown("---")
    s1, s2, s3, s4 = st.columns(4)
    with s1: heart_rate = st.slider("❤️ Heart Rate (BPM)", 30, 180, key="heart_rate")
    with s2: resting_hr = st.slider("💓 Resting HR (BPM)", 30, 130, key="resting_hr")
    with s3: hrv = st.slider("📊 HRV (ms)", 0, 150, key="hrv")
    with s4: blood_pressure_variability = st.slider("🩺 BP Var (mmHg)", 0, 40, key="blood_pressure_variability")

    s5, s6, s7, s8 = st.columns(4)
    with s5: heart_rate_recovery = st.slider("🏃 Recovery (BPM)", 0, 60, key="heart_rate_recovery")
    with s6: sleep_quality = st.slider("😴 Sleep Quality (%)", 0, 100, key="sleep_quality")
    with s7: steps = st.slider("👟 Daily Steps", 0, 20000, step=100, key="steps")
    with s8: battery = st.slider("🔋 Watch Battery (%)", 0, 100, key="battery")

watch_plain_name = " ".join(st.session_state.selected_watch.split(" ")[1:])
last_sync = datetime.now(ZoneInfo("America/New_York")).strftime("%I:%M %p")

# =====================================================
# REDESIGNED CLEAN HOME PAGE
# =====================================================
if page == "🏠 Home":

    today_score, today_positives, today_concerns = generate_health_summary()
    _color = score_color(today_score)

    # Hero Section
    st.markdown(
        f"""
        <div class="glass-card" style="padding:48px; margin-bottom:28px; background: linear-gradient(135deg, rgba(13, 23, 40, 0.95) 0%, rgba(6, 12, 23, 0.98) 100%); border: 1px solid rgba(0, 229, 255, 0.15);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:30px;">
                <div style="max-width:680px;">
                    <div style="display:inline-flex; align-items:center; gap:8px; padding:6px 14px; border-radius:20px; background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.25); color:#00E5FF; font-size:12px; font-weight:700; margin-bottom:16px;">
                        <span>✨ NEXT-GEN CARDIOVASCULAR TELEMETRY</span>
                    </div>
                    <h1 style="font-size:46px; font-weight:800; letter-spacing:-0.03em; margin:0 0 16px 0; line-height:1.15; background:linear-gradient(135deg, #FFFFFF 50%, #8A99AD 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                        Predictive Heart Health Intelligence.
                    </h1>
                    <p style="font-size:16.5px; color:#8A99AD; margin:0 0 24px 0; line-height:1.6;">
                        PulseGuard seamlessly connects with your wearable device to provide continuous cardiac telemetry, autonomic stress index tracking, and clinical-grade health reporting.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Heart Health Score with Count-Up Animated Gauge
    col_score, col_summary = st.columns([1, 2])

    with col_score:
        st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; font-weight:700; color:#8A99AD; letter-spacing:0.08em; text-transform:uppercase;'>Cardiovascular Index</div>", unsafe_allow_html=True)
        render_animated_score(today_score)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_summary:
        st.markdown('<div class="glass-card" style="height:100%;">', unsafe_allow_html=True)
        st.subheader("💡 Today's Heart Insight & Status")
        _streak = compute_streak(today_score)
        st.markdown(f"🔥 **{_streak}-Day Optimal Health Streak Active**")
        st.write(f"**Daily Tip:** {TIPS[st.session_state.tip_index]}")
        st.markdown("---")
        st.write("### AI Clinical Preview")
        st.write(generate_ai_insight(today_score, today_positives, today_concerns))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

    # Interactive Quick-Action Cards
    st.subheader("⚡ Explore Platform Features")
    feat1, feat2, feat3 = st.columns(3)

    with feat1:
        st.markdown(
            """
            <div class="glass-card">
                <div style="font-size:32px; margin-bottom:12px;">❤️</div>
                <h3 style="font-size:18px; margin:0 0 8px 0; color:#FFFFFF;">Heart Analytics</h3>
                <p style="font-size:13.5px; color:#8A99AD; margin:0 0 16px 0;">Monitor real-time heart rate dynamics, ECG wave simulations, and HRV variability.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Heart Analytics", key="btn_feat1", use_container_width=True):
            st.session_state.current_page = "❤️ Heart Analytics"
            st.rerun()

    with feat2:
        st.markdown(
            """
            <div class="glass-card">
                <div style="font-size:32px; margin-bottom:12px;">🔬</div>
                <h3 style="font-size:18px; margin:0 0 8px 0; color:#FFFFFF;">3D Heart Explorer</h3>
                <p style="font-size:13.5px; color:#8A99AD; margin:0 0 16px 0;">Interactive 3D anatomical model with clickable hotspots detailing cardiac structures.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Launch 3D Explorer", key="btn_feat2", use_container_width=True, type="primary"):
            st.session_state.current_page = "🔬 3D Heart Explorer"
            st.rerun()

    with feat3:
        st.markdown(
            """
            <div class="glass-card">
                <div style="font-size:32px; margin-bottom:12px;">📈</div>
                <h3 style="font-size:18px; margin:0 0 8px 0; color:#FFFFFF;">Clinical PDF Exports</h3>
                <p style="font-size:13.5px; color:#8A99AD; margin:0 0 16px 0;">Generate doctor-ready PDF health summaries and printable telemetry reports.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Generate Reports", key="btn_feat3", use_container_width=True):
            st.session_state.current_page = "📈 Health Summary"
            st.rerun()

# =====================================================
# 3D HEART EXPLORER PAGE
# =====================================================
elif page == "🔬 3D Heart Explorer":

    st.markdown("<h2 style='font-weight:800;'>🔬 Interactive 3D Cardiac Anatomy</h2>", unsafe_allow_html=True)
    st.caption("Rotate, zoom, and inspect real-time anatomical structures of the human heart.")
    st.markdown("---")

    heart_col, desc_col = st.columns([3, 2])
    with heart_col:
        st.markdown('<div class="glass-card" style="padding:10px;">', unsafe_allow_html=True)
        render_3d_heart()
        st.markdown('</div>', unsafe_allow_html=True)

    with desc_col:
        st.markdown(
            """
            <div class="glass-card" style="height:100%;">
                <h3 style="color:#00E5FF; margin-top:0;">🫀 Anatomical Structure Guide</h3>
                <p style="color:#8A99AD; font-size:14px; line-height:1.6;">
                    The human heart is a four-chambered muscular organ that pumps blood through the circulatory system.
                </p>
                <hr style="border-color:rgba(255,255,255,0.08);">
                <div style="margin-bottom:14px;">
                    <strong style="color:#FFFFFF;">1. Aorta</strong>
                    <p style="color:#8A99AD; font-size:13px; margin:2px 0 0 0;">The largest artery in the body, conducting oxygenated blood under high pressure from the left ventricle to systemic circulation.</p>
                </div>
                <div style="margin-bottom:14px;">
                    <strong style="color:#FFFFFF;">2. Left Ventricle</strong>
                    <p style="color:#8A99AD; font-size:13px; margin:2px 0 0 0;">The thickest cardiac chamber responsible for generating systemic pumping force.</p>
                </div>
                <div style="margin-bottom:14px;">
                    <strong style="color:#FFFFFF;">3. Right Atrium</strong>
                    <p style="color:#8A99AD; font-size:13px; margin:2px 0 0 0;">Receives deoxygenated venous blood returned from systemic tissue.</p>
                </div>
                <div>
                    <strong style="color:#FFFFFF;">4. Coronary Arteries</strong>
                    <p style="color:#8A99AD; font-size:13px; margin:2px 0 0 0;">Networks of blood vessels delivering oxygen directly to myocardial muscle.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# =====================================================
# HEART ANALYTICS PAGE
# =====================================================
elif page == "❤️ Heart Analytics":

    st.markdown("<h2 style='font-weight:800;'>❤️ Heart Telemetry & Biomarkers</h2>", unsafe_allow_html=True)
    st.caption("Detailed metric deep-dives, historical trends, and simulated ECG telemetry.")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1: render_metric_card("Heart Rate", f"{heart_rate} BPM", metric_status("heart_rate", heart_rate)[1])
    with col2: render_metric_card("Resting HR", f"{resting_hr} BPM", metric_status("resting_hr", resting_hr)[1])
    with col3: render_metric_card("HRV", f"{hrv} ms", metric_status("hrv", hrv)[1])
    with col4: render_metric_card("BP Var", f"{blood_pressure_variability} mmHg", metric_status("bp_variability", blood_pressure_variability)[1])

    st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

    col5, col6, col7 = st.columns(3)
    with col5: render_metric_card("HR Recovery", f"{heart_rate_recovery} BPM", metric_status("recovery", heart_rate_recovery)[1])
    with col6: render_metric_card("Sleep Quality", f"{sleep_quality}%", metric_status("sleep", sleep_quality)[1])
    with col7: render_metric_card("Daily Steps", f"{steps:,}", metric_status("steps", steps)[1])

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("💓 Real-Time ECG Waveform Simulation")
    render_ecg_animation(heart_rate)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns([3, 2])
    with chart_col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📉 7-Day Performance Trends")
        render_trend_chart(heart_rate, sleep_quality, steps)
        st.markdown('</div>', unsafe_allow_html=True)
    with chart_col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🕸️ Multi-Biomarker Radar")
        render_radar_chart(heart_rate, resting_hr, hrv, blood_pressure_variability, heart_rate_recovery, sleep_quality, steps)
        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# SMARTWATCH PAGE
# =====================================================
elif page == "⌚ Smartwatch":

    st.markdown("<h2 style='font-weight:800;'>⌚ Connected Wearable Device</h2>", unsafe_allow_html=True)
    st.caption("Manage paired optical sensors and sync intervals.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="glass-card" style="border-left: 4px solid #00E5FF;">
                <div style="font-size:12px; font-weight:700; color:#8A99AD; text-transform:uppercase;">Active Device</div>
                <div style="font-size:28px; font-weight:800; color:#FFFFFF; margin:8px 0;">{watch_plain_name}</div>
                <div style="display:flex; gap:20px; margin-top:16px;">
                    <div><span style="color:#8A99AD; font-size:12px;">Battery:</span> <strong style="color:#00E5FF;">{battery}%</strong></div>
                    <div><span style="color:#8A99AD; font-size:12px;">Last Sync:</span> <strong>{last_sync}</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="glass-card">
                <h3>Supported Ecosystems</h3>
                <p style="color:#8A99AD;">Continuous bidirectional integration available for Apple HealthKit, WHOOP, Oura Ring, Garmin Connect, and Google Fit.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# =====================================================
# HEALTH SUMMARY PAGE
# =====================================================
elif page == "📈 Health Summary":

    st.markdown("<h2 style='font-weight:800;'>📈 Health Summary & Clinical Exports</h2>", unsafe_allow_html=True)
    st.markdown("---")

    score, positives, concerns = generate_health_summary()

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🧠 PulseGuard Clinical Insight")
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
    st.subheader("📤 Export Clinical PDF Reports & Cards")

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
        battery, last_sync, watch_plain_name, period_label=_period_label, period_stats=_period_stats
    )
    share_card_bytes = generate_share_card(score, heart_rate, sleep_quality, steps, watch_plain_name)

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("📄 Download Doctor PDF Report", data=pdf_bytes, file_name="PulseGuard_Report.pdf", mime="application/pdf", use_container_width=True, type="primary")
    with dl2:
        st.download_button("📸 Download Social Share Card", data=share_card_bytes, file_name="PulseGuard_Card.png", mime="image/png", use_container_width=True)

# =====================================================
# AI ASSISTANT PAGE
# =====================================================
elif page == "🤖 AI Assistant":

    st.markdown("<h2 style='font-weight:800;'>🤖 PulseGuard AI Assistant</h2>", unsafe_allow_html=True)
    st.caption("Inquire about your real-time heart metrics or HRV trends.")
    st.markdown("---")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            ("assistant", "Hello! I am your PulseGuard AI companion. How can I assist you with your cardiovascular metrics today?")
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
        response = ai_chat_response(user_question, _score, _positives, _concerns, heart_rate, resting_hr, hrv, sleep_quality, steps, heart_rate_recovery)
        st.session_state.chat_history.append(("assistant", response))
        st.rerun()

# =====================================================
# ACCURACY TIPS PAGE
# =====================================================
elif page == "💡 Accuracy Tips":

    st.markdown("<h2 style='font-weight:800;'>💡 Sensor Optimization Tips</h2>", unsafe_allow_html=True)
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="glass-card">
                <h3>⌚ Wearable Placement</h3>
                <p style="color:#8A99AD;">Ensure your wearable fits snugly above the wrist bone to minimize motion artifacts during optical PPG polling.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="glass-card">
                <h3>💧 Hydration & PPG Quality</h3>
                <p style="color:#8A99AD;">Dehydration lowers systemic blood volume, causing elevated resting heart rates and reduced HRV readings.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# --------------------------------------------------
# Footer & Simulation Autoplay Engine
# --------------------------------------------------
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; padding:24px; color:#8A99AD; font-size:12px; border-top:1px solid rgba(255,255,255,0.05);">
        PulseGuard Health Telemetry • Version 2.0 Ultra Dashboard<br>
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
