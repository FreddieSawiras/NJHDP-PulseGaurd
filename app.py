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
# Set up the page
# --------------------------------------------------
st.set_page_config(
    page_title="PulseGaurd",
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
    "dark_mode": False,
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

# --------------------------------------------------
# Preset "auto-play" demo scenarios
# --------------------------------------------------
SCENARIOS = [
    {  # Healthy Day
        "heart_rate": 68, "resting_hr": 58, "hrv": 72,
        "blood_pressure_variability": 4, "heart_rate_recovery": 30,
        "sleep_quality": 92, "steps": 11200, "battery": 91,
    },
    {  # Stressful Day
        "heart_rate": 104, "resting_hr": 79, "hrv": 28,
        "blood_pressure_variability": 16, "heart_rate_recovery": 14,
        "sleep_quality": 58, "steps": 3200, "battery": 46,
    },
    {  # Poor Sleep Night
        "heart_rate": 88, "resting_hr": 70, "hrv": 38,
        "blood_pressure_variability": 9, "heart_rate_recovery": 18,
        "sleep_quality": 41, "steps": 5100, "battery": 63,
    },
]

WATCH_OPTIONS = {
    "⌚ Apple Watch": "#1d1d1f",
    "⌚ Samsung Galaxy Watch": "#6a1b9a",
    "⌚ Google Pixel Watch": "#1a73e8",
    "⌚ Garmin": "#0077c8",
    "⌚ Fitbit": "#00b0b9",
}

# --------------------------------------------------
# Color palette (Light / Dark mode) — "Aurora" theme:
# indigo/violet primary with an emerald accent, replacing
# the old navy/teal look for a more modern SaaS feel.
# --------------------------------------------------
if st.session_state.dark_mode:
    C = dict(
        bg="#0d0f1a", card_bg="#171a28", text="#e9eaf3", subtitle="#98a0b8",
        title="#8b7cf6", accent="#22d3ae", gold="#fbbf24",
        border="#282c40", chip_bg_alpha="33",
    )
else:
    C = dict(
        bg="#f5f6fb", card_bg="#ffffff", text="#1c1f2b", subtitle="#666f80",
        title="#6d5ce7", accent="#0f9d8a", gold="#d97706",
        border="#e6e8f2", chip_bg_alpha="1f",
    )

# GOOD/WARN/DANGER stay reserved for genuine health-status signals (green/amber/red)
# so alerts remain instantly recognizable — the brand identity itself uses the
# indigo/emerald/gold palette above instead of red, to keep the app feeling calm and safe.
GOOD, WARN, DANGER = "#2e7d32", "#f9a825", "#c62828"



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
# Global styling
# --------------------------------------------------
st.markdown(f"""
<style>

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap');

.stApp, .stApp * {{
    color:{C['text']} !important;
    font-family: 'Inter', -apple-system, sans-serif;
}}

h1, h2, h3, .main-title, [data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {{
    font-family: 'Poppins', -apple-system, sans-serif !important;
}}

.stApp {{
    background-color:{C['bg']};
}}

/* Sidebar has been removed in favor of a top navbar — hide any residual
   sidebar chrome (including the collapse arrow) so nothing is left behind. */
section[data-testid="stSidebar"], [data-testid="collapsedControl"] {{
    display: none !important;
}}

.main-title{{
    font-size:46px;
    font-weight:700;
    color:{C['title']} !important;
}}

.subtitle{{
    color:{C['subtitle']} !important;
    font-size:20px;
}}

.navbar-brand{{
    display:flex;
    align-items:center;
    gap:14px;
}}

.navbar-title{{
    font-family:'Poppins',sans-serif;
    font-size:22px;
    font-weight:700;
    color:{C['title']} !important;
    line-height:1.1;
}}

.navbar-subtitle{{
    font-size:11px;
    letter-spacing:1.3px;
    color:{C['subtitle']} !important;
    text-transform:uppercase;
    margin-top:2px;
}}

/* Pill-style top navigation tabs, built from a row of st.button widgets */
.nav-row .stButton > button{{
    border-radius: 999px !important;
    justify-content: center !important;
    font-size: 14px !important;
    padding: 0.45rem 0.6rem !important;
}}

.nav-row {{
    margin-bottom: 6px;
}}


.metric-card{{
    background:{C['card_bg']};
    border-radius:18px;
    padding:20px;
    box-shadow:0px 4px 14px {hex_to_rgba(C['title'], 0.10)};
    margin-bottom:15px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}

.metric-card:hover{{
    transform: translateY(-4px);
    box-shadow:0px 10px 24px {hex_to_rgba(C['title'], 0.16)};
}}

.metric-title{{
    font-size:17px;
    color:{C['subtitle']} !important;
}}

.metric-value{{
    font-size:34px;
    font-weight:bold;
    color:{C['text']} !important;
}}

.chip{{
    display:inline-block;
    padding:5px 14px;
    border-radius:20px;

    font-size:13px;
    font-weight:600;
    margin:4px 6px 4px 0;
}}

.hero-banner{{
    background: linear-gradient(135deg, {hex_to_rgba(C['title'], 0.16)}, {hex_to_rgba(C['accent'], 0.10)});
    border-radius:22px;
    padding:28px 32px;
    margin-bottom:20px;
    display:flex;
    align-items:center;
    gap:20px;
    border: 1px solid {hex_to_rgba(C['title'], 0.15)};
}}

.device-card{{
    background:{C['card_bg']};
    border-radius:16px;
    padding:14px;
    text-align:center;
    margin-top:10px;
    box-shadow:0px 3px 10px {hex_to_rgba(C['title'], 0.10)};
}}

.device-card small, .device-sub {{
    color:{C['subtitle']} !important;
}}

.footer{{
    text-align:center;
    color:{C['subtitle']} !important;
    font-size:13px;
}}

/* Alert boxes (st.info/success/warning/error) already inherit the
   theme text color from the wildcard rule above, which is correct here
   since Streamlit renders alert backgrounds dark-tinted in dark mode
   and light-tinted in light mode. */

/* --- Buttons (sidebar + everywhere) --- */
.stButton > button, .stDownloadButton > button {{
    border-radius: 12px !important;
    border: 1.5px solid {C['title']} !important;
    background-color: transparent !important;
    color: {C['title']} !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.15s ease !important;
    justify-content: flex-start !important;
}}

.stButton > button:hover, .stDownloadButton > button:hover {{
    background-color: {hex_to_rgba(C['title'], 0.10)} !important;
    color: {C['title']} !important;
    box-shadow: 0px 4px 12px {hex_to_rgba(C['title'], 0.15)} !important;
    transform: translateX(2px);
}}

/* Active nav item — solid filled gradient */
.stButton > button[kind="primary"] {{
    border: none !important;
    background: linear-gradient(135deg, {C['title']}, {C['accent']}) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0px 4px 14px {hex_to_rgba(C['title'], 0.35)} !important;
}}

.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, {C['title']}, {C['accent']}) !important;
    color: #ffffff !important;
    transform: translateX(2px);
}}

.stButton > button p, .stDownloadButton > button p {{
    color: inherit !important;
}}

/* --- Dividers --- */
hr {{
    border: none !important;
    border-top: 1px solid {C['border']} !important;
    margin: 16px 0 !important;
    opacity: 1 !important;
}}

/* --- Select boxes / dropdowns --- */
[data-baseweb="select"] > div {{
    border-radius: 10px !important;
}}

/* --- Sliders --- */
[data-testid="stSlider"] [role="slider"] {{
    background-color: {C['title']} !important;
}}

@keyframes scorePop {{
    0%   {{ opacity: 0; transform: scale(0.85); }}
    100% {{ opacity: 1; transform: scale(1); }}
}}

.score-pop {{
    animation: scorePop 0.4s ease-out;
}}

/* --------------------------------------------------
   Fix: the wildcard "font-family: Inter" rule above
   also lands on Streamlit's icon fonts (e.g. header
   icons), which replaces the glyph with literal
   icon-name text. Restore the icon font specifically
   for those elements.
   -------------------------------------------------- */
[data-testid="stIconMaterial"],
span[class*="material-icons"],
button[kind="header"] span {{
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    font-weight: normal !important;
}}

/* --------------------------------------------------
   Fix: prevent text from different elements crowding
   or overlapping each other (headers, cards, chips,
   nav labels).
   -------------------------------------------------- */
.stApp p, .stApp span, .stApp div, .stApp label {{
    line-height: 1.55 !important;
}}

.main-title {{
    line-height: 1.2 !important;
}}

.subtitle {{
    line-height: 1.4 !important;
    margin-top: 4px !important;
}}

.hero-banner {{
    flex-wrap: wrap;
    row-gap: 12px;
}}

.metric-card {{
    min-height: 96px;
}}

.metric-title {{
    line-height: 1.3 !important;
    margin-bottom: 6px;
}}

.metric-value {{
    line-height: 1.15 !important;
}}

.chip {{
    white-space: nowrap;
    line-height: 1.4 !important;
}}

[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
    line-height: 1.3 !important;
}}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def metric_status(kind, value):
    """Return (status_label, color, score_0_to_100) for a metric value."""
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
        <div class="metric-card" style="border-left:8px solid {color};">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value_str}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_chips(items):
    """items: list of (text, color) tuples, rendered as inline pill chips."""
    html = '<div style="display:flex;flex-wrap:wrap;">'
    for text, color in items:
        html += (
            f'<span class="chip" style="background:{color}{C["chip_bg_alpha"]};'
            f'color:{color} !important;border:1px solid {color};">{text}</span>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_score_gauge(score):
    bar_color = score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'color': C['text']}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': C['text']},
            'bar': {'color': bar_color},
            'bgcolor': C['card_bg'],
            'steps': [
                {'range': [0, 50], 'color': "#ffcdd2"},
                {'range': [50, 75], 'color': "#fff59d"},
                {'range': [75, 100], 'color': "#c8e6c9"},
            ],
        }
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=C['text'],
    )
    st.plotly_chart(fig, use_container_width=True)


def render_radar_chart(hr, rhr, hrv_v, bp, rec, sleep, steps_v):
    categories = ["Heart Rate", "Resting HR", "HRV", "BP Variability", "Recovery", "Sleep", "Steps"]
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
        line_color=C['title'], fillcolor=hex_to_rgba(C['title'], 0.25)
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], color=C['text']),
            angularaxis=dict(color=C['text']),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=C['text'],
    )
    st.plotly_chart(fig, use_container_width=True)


def render_trend_chart(hr, sleep, steps_v):
    days = ["6 days ago", "5 days ago", "4 days ago", "3 days ago", "2 days ago", "Yesterday", "Today"]
    hr_series = st.session_state.trend_data["heart_rate"] + [hr]
    sleep_series = st.session_state.trend_data["sleep_quality"] + [sleep]
    steps_series = st.session_state.trend_data["steps"] + [steps_v]

    df = pd.DataFrame({
        "Day": days,
        "Heart Rate (BPM)": hr_series,
        "Sleep Quality (%)": sleep_series,
    }).set_index("Day")

    steps_df = pd.DataFrame({"Day": days, "Steps": steps_series}).set_index("Day")

    st.caption("Simulated 7-day trend (last 6 days are sample data; today reflects your slider values)")
    st.line_chart(df)
    st.bar_chart(steps_df)


def render_ecg_animation(hr):
    html_code = f"""
    <div style="background:#0d1b2a;border-radius:12px;padding:10px;">
    <canvas id="ecgCanvas" width="900" height="150" style="width:100%;display:block;"></canvas>
    </div>
    <script>
    const canvas = document.getElementById("ecgCanvas");
    const ctx = canvas.getContext("2d");
    let offset = 0;
    const hr = {hr};
    const speedFactor = Math.max(0.4, hr / 70);

    function drawECG() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#00e676";
        ctx.lineWidth = 2;
        ctx.beginPath();
        const midY = canvas.height / 2;

        for (let x = 0; x < canvas.width; x++) {{
            const t = (x + offset) * 0.05 * speedFactor;
            let y = midY;
            const beatPos = t % 20;
            if (beatPos > 9 && beatPos < 9.5) y -= 10;
            else if (beatPos > 9.5 && beatPos < 10) y += 40;
            else if (beatPos > 10 && beatPos < 10.5) y -= 60;
            else if (beatPos > 10.5 && beatPos < 11) y += 15;
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
    components.html(html_code, height=180)


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

    # Overall score is the average of each metric's own 0-100 health score
    # (the same scores driving the radar chart), so one bad metric genuinely
    # moves the needle instead of a small fixed-point deduction.
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
    """Count consecutive 'healthy' days (score >= 75) ending today, walking backward through history."""
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
    """
    Build an averages/min/max/trend summary across the last `days` days
    (including today's live slider values), pulled from simulated history.
    Returns a dict keyed by metric with {avg, min, max, trend} plus a
    day-by-day series usable for a period chart.
    """
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
    """fpdf2 core fonts only support latin-1; strip anything outside that (emoji, etc.)."""
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
        return "Hi! I'm the PulseGuard demo assistant. Ask me about your heart rate, sleep, HRV, steps, recovery, or overall score."

    return (
        "I can answer questions about your heart rate, sleep, HRV, steps, recovery, or overall score. "
        "Try asking something like 'why is my score low today?' or 'how's my sleep?'"
    )


class _PulseGuardPDF(FPDF):
    """FPDF subclass so we get a consistent footer with page numbers on every page."""

    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, _pdf_safe(f"PulseGuard Health Report  |  Page {self.page_no()}"), align="C")


def _pdf_section_header(pdf, text, content_width, rgb=(27, 58, 92)):
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

    # ---------- Letterhead ----------
    pdf.set_fill_color(27, 58, 92)
    pdf.rect(0, 0, pdf.w, 32, style="F")
    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(content_width, 10, _pdf_safe("PulseGuard Cardiovascular Report"), ln=True)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(content_width, 6, _pdf_safe("New Jersey Heart Disease Prevention (NJHDP)"), ln=True)
    pdf.set_y(36)
    pdf.set_text_color(20, 20, 20)

    # ---------- Report metadata ----------
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    meta_label = patient_name.strip() or "Not provided"
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Patient / User: {meta_label}"))
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Report Period: {period_label}"), ln=True)
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Report Generated: {generated_on} ({last_sync} ET)"))
    pdf.cell(content_width / 2, 6, _pdf_safe(f"Data Source Device: {watch_name}"), ln=True)
    pdf.ln(3)

    # ---------- Score banner ----------
    if score >= 90:
        score_rgb = (46, 125, 50)
        score_word = "Good"
    elif score >= 75:
        score_rgb = (191, 144, 0)
        score_word = "Fair"
    else:
        score_rgb = (198, 40, 40)
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

    # ---------- Current reading table ----------
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

    # ---------- Period trend table (week / month views) ----------
    if period_stats and period_stats.get("days", 1) > 1:
        _pdf_section_header(pdf, f"Trend Summary — Last {period_stats['days']} Days", content_width)
        pdf.set_font("Helvetica", "B", 10)
        col_w = [60, 30, 30, 30, 34]
        headers = ["Metric", "Average", "Min", "Max", "Trend"]
        pdf.set_fill_color(27, 58, 92)
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

    # ---------- Clinical observations ----------
    if positives:
        _pdf_section_header(pdf, "Favorable Findings", content_width, rgb=(46, 125, 50))
        pdf.set_font("Helvetica", "", 10.5)
        for p in positives:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_width, 6, _pdf_safe(f"-  {p}"))
        pdf.ln(2)

    if concerns:
        _pdf_section_header(pdf, "Findings Warranting Follow-Up", content_width, rgb=(198, 40, 40))
        pdf.set_font("Helvetica", "", 10.5)
        for c in concerns:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_width, 6, _pdf_safe(f"-  {c}"))
        pdf.ln(2)

    # ---------- Clinical summary narrative ----------
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

    # ---------- Disclaimer ----------
    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(120, 120, 120)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(content_width, 5, _pdf_safe(
        "This report is generated by PulseGuard, an educational prototype, from consumer "
        "wearable-device estimates. It does not constitute a medical diagnosis and is not a "
        "substitute for professional medical advice, evaluation, or treatment. Please share this "
        "report with a qualified healthcare provider and consult them regarding any concerns "
        "before making medical decisions."
    ))

    return bytes(pdf.output())


def _load_font(bold, size):
    """Try real TrueType fonts first (much nicer than the tiny bitmap default), fall back safely."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
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


def _draw_gradient(draw, W, H, top_rgb, bottom_rgb):
    for y in range(H):
        t = y / H
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _draw_heart(draw, cx, cy, size, fill):
    """Simple two-circle + triangle heart glyph, drawn with primitives (no external assets)."""
    r = size / 2
    draw.ellipse([cx - r, cy - r, cx, cy], fill=fill)
    draw.ellipse([cx, cy - r, cx + r, cy], fill=fill)
    draw.polygon(
        [(cx - r, cy - r * 0.15), (cx + r, cy - r * 0.15), (cx, cy + r * 1.35)],
        fill=fill,
    )


def generate_share_card(score, heart_rate, sleep_quality, steps, watch_name):
    W, H = 1080, 1920
    if score >= 90:
        accent = (46, 168, 90)
    elif score >= 75:
        accent = (233, 168, 45)
    else:
        accent = (214, 69, 69)

    dark_navy = (13, 22, 38)
    deep_navy = (24, 38, 58)

    img = Image.new("RGB", (W, H), dark_navy)
    draw = ImageDraw.Draw(img)
    _draw_gradient(draw, W, H, deep_navy, dark_navy)

    f_brand = _load_font(True, 62)
    f_tagline = _load_font(False, 32)
    f_giant = _load_font(True, 190)
    f_slash = _load_font(True, 44)
    f_label = _load_font(True, 40)
    f_value = _load_font(True, 46)
    f_footer = _load_font(False, 28)
    f_pill = _load_font(True, 30)

    # ---- Header lockup ----
    _draw_heart(draw, 90, 108, 66, accent)
    draw.text((150, 66), "PulseGuard", font=f_brand, fill=(255, 255, 255))
    draw.text((150, 140), "Daily Heart Health Summary", font=f_tagline, fill=(178, 190, 205))

    # ---- Status pill ----
    status_word = "GOOD" if score >= 90 else ("FAIR" if score >= 75 else "MONITOR")
    pill_bbox = draw.textbbox((0, 0), status_word, font=f_pill)
    pill_w = (pill_bbox[2] - pill_bbox[0]) + 60
    draw.rounded_rectangle([W - 60 - pill_w, 60, W - 60, 60 + 64], radius=32, fill=accent)
    _centered_text(draw, W - 60 - pill_w / 2, 76, status_word, f_pill, (255, 255, 255))

    # ---- Score ring ----
    ring_cx, ring_cy, ring_r = W / 2, 560, 270
    ring_bbox = [ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r]
    draw.arc(ring_bbox, 0, 360, fill=(52, 66, 88), width=30)
    sweep_end = -90 + 360 * max(0, min(100, score)) / 100
    draw.arc(ring_bbox, -90, sweep_end, fill=accent, width=30)

    _centered_text(draw, ring_cx, ring_cy - 130, "HEART HEALTH SCORE", f_label, (150, 165, 182))
    score_txt = f"{score}"
    score_bbox = draw.textbbox((0, 0), score_txt, font=f_giant)
    score_w = score_bbox[2] - score_bbox[0]
    draw.text((ring_cx - score_w / 2, ring_cy - 110), score_txt, font=f_giant, fill=(255, 255, 255))
    _centered_text(draw, ring_cx, ring_cy + 95, "/ 100", f_slash, (150, 165, 182))

    # ---- Stat cards (2x2 grid) ----
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
        draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=26, fill=(30, 44, 66))
        draw.rounded_rectangle([x, y, x + 10, y + card_h], radius=6, fill=accent)
        draw.text((x + 36, y + 32), label.upper(), font=f_footer, fill=(150, 165, 182))
        draw.text((x + 36, y + 90), value, font=f_value, fill=(255, 255, 255))

    # ---- Footer ----
    footer_y = grid_top + 2 * card_h + gap + 60
    draw.line([(60, footer_y), (W - 60, footer_y)], fill=(52, 66, 88), width=2)
    _centered_text(draw, W / 2, footer_y + 30, "Generated with PulseGuard — educational prototype",
                   f_footer, (140, 155, 172))
    _centered_text(draw, W / 2, footer_y + 70, "Not a medical diagnosis. Consult a healthcare professional.",
                   f_footer, (110, 124, 140))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def animate_score(final_score):
    st.markdown(
        f"""
        <div class="metric-card score-pop" style="text-align:center;">
            <div class="metric-title">❤️ Heart Health Score</div>
            <div class="metric-value" style="font-size:44px;">{final_score}/100</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------
# Top Navbar (replaces the old sidebar)
# --------------------------------------------------
NAV_ITEMS = [
    "🏠 Home",
    "❤️ Heart Dashboard",
    "⌚ Smartwatch",
    "📈 Health Summary",
    "🤖 Ask PulseGuard AI",
    "💡 Accuracy Tips",
    "ℹ️ About"
]

if "current_page" not in st.session_state:
    st.session_state.current_page = NAV_ITEMS[0]

with st.container(border=True):
    navbar_left, navbar_right = st.columns([3, 2])
    with navbar_left:
        st.markdown(
            f"""
            <div class="navbar-brand">
                <img src="{LOGO_URL}" width="46" style="border-radius:12px;box-shadow:0 4px 12px {hex_to_rgba(C['title'], 0.30)};">
                <div>
                    <div class="navbar-title">PulseGuard</div>
                    <div class="navbar-subtitle">Heart Health Companion</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with navbar_right:
        _badge_col, _toggle_col = st.columns([2, 1])
        with _badge_col:
            st.markdown(
                f"""
                <div style="background:{hex_to_rgba(C['accent'], 0.15)};border:1px solid {C['accent']};
                color:{C['accent']} !important;padding:8px 14px;border-radius:20px;text-align:center;
                font-weight:600;font-size:13px;">
                    🧪 Sprint 1 Prototype
                </div>
                """,
                unsafe_allow_html=True
            )
        with _toggle_col:
            st.toggle("🌙 Dark", key="dark_mode")

    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    _nav_cols = st.columns(len(NAV_ITEMS))
    for _col, _item in zip(_nav_cols, NAV_ITEMS):
        with _col:
            _is_active = st.session_state.current_page == _item
            if st.button(_item, key=f"nav_{_item}", use_container_width=True,
                         type="primary" if _is_active else "secondary"):
                st.session_state.current_page = _item
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.current_page

# --------------------------------------------------
# Device & Live Data Controls (collapsible, top of page)
# --------------------------------------------------
with st.expander("⚙️ Device & Live Data Controls", expanded=False):
    st.caption(
        "No real smartwatch is connected in this prototype. Pick a simulated device, "
        "drag the sliders, simulate a random reading, or auto-play a scenario."
    )

    device_col, action_col = st.columns([2, 1])
    with device_col:
        st.subheader("⌚ Choose Your Device")
        st.session_state.selected_watch = st.selectbox(
            "Simulated device",
            list(WATCH_OPTIONS.keys()),
            index=list(WATCH_OPTIONS.keys()).index(st.session_state.selected_watch)
        )
        _watch_color = WATCH_OPTIONS[st.session_state.selected_watch]
        watch_plain_name = " ".join(st.session_state.selected_watch.split(" ")[1:])
        st.markdown(
            f"""
            <div class="device-card" style="border-top:5px solid {_watch_color};text-align:left;padding:14px 18px;">
                <div style="display:flex;align-items:center;gap:14px;">
                    <div style="font-size:36px;">{st.session_state.selected_watch.split(" ")[0]}</div>
                    <div>
                        <div style="font-weight:700;">{watch_plain_name}</div>
                        <div style="font-size:12px;color:{C['subtitle']} !important;">Connected since {st.session_state.connected_since}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with action_col:
        st.subheader("🎲 Quick Actions")
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
            "▶️ Auto-Play Demo (cycles scenarios every few seconds)",
            value=st.session_state.autoplay
        )

    st.markdown("---")
    st.subheader("🎛️ Live Metric Sliders")

    slider_row1 = st.columns(4)
    with slider_row1[0]:
        heart_rate = st.slider("❤️ Heart Rate (BPM)", 30, 180, key="heart_rate")
    with slider_row1[1]:
        resting_hr = st.slider("💓 Resting Heart Rate (BPM)", 30, 130, key="resting_hr")
    with slider_row1[2]:
        hrv = st.slider("📊 Heart Rate Variability (ms)", 0, 150, key="hrv")
    with slider_row1[3]:
        blood_pressure_variability = st.slider("🩺 Blood Pressure Variability (mmHg)", 0, 40, key="blood_pressure_variability")

    slider_row2 = st.columns(4)
    with slider_row2[0]:
        heart_rate_recovery = st.slider("🏃 Heart Rate Recovery (BPM)", 0, 60, key="heart_rate_recovery")
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

    st.markdown(
        f"""
        <div class="hero-banner">
            <img src="{LOGO_URL}" width="70" style="border-radius:14px;">
            <div style="flex:1;min-width:220px;">
                <div class="main-title" style="margin-bottom:0;">❤️ PulseGuard</div>
                <div class="subtitle">Simple steps for a stronger, healthier heart.</div>
            </div>
            <div style="text-align:center;background:{hex_to_rgba(_score_color, 0.14)};
                        border:2px solid {_score_color};border-radius:18px;padding:14px 26px;">
                <div style="font-size:12px;letter-spacing:1px;color:{C['subtitle']} !important;
                            text-transform:uppercase;font-weight:700;">Today's Score</div>
                <div style="font-size:38px;font-weight:800;color:{_score_color} !important;line-height:1.1;">
                    {_today_score}<span style="font-size:16px;color:{C['subtitle']} !important;">/100</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tip_col, streak_col = st.columns([2, 1])
    with tip_col:
        st.info(f"**Tip of the Day:** {TIPS[st.session_state.tip_index]}")
    with streak_col:
        _streak = compute_streak(_today_score)
        if _streak > 0:
            st.warning(f"🔥 **{_streak}-day streak** of good heart health!")
        else:
            st.info("No active streak yet — a score of 75+ starts one!")

    col1, col2 = st.columns(2)

    with col1:
        if watch_connected:
            st.success(f"🟢 {st.session_state.selected_watch} Connected")
        else:
            st.error("🔴 Smartwatch Not Connected")

        mcol1, mcol2 = st.columns(2)
        with mcol1:
            st.metric("Battery", f"{battery}%")
        with mcol2:
            st.metric("Last Sync", last_sync)
        st.button("🔄 Refresh Data", use_container_width=True)

    with col2:
        st.markdown(
            f"""
            <div class="metric-card" style="height:100%;">
                <div class="metric-title" style="margin-bottom:10px;">📡 What PulseGuard Monitors</div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    {''.join(
                        f'<span class="chip" style="background:{hex_to_rgba(C["title"], 0.12)};'
                        f'color:{C["title"]} !important;border:1px solid {hex_to_rgba(C["title"], 0.3)};">{label}</span>'
                        for label in ["❤️ Heart Rate", "💓 Resting HR", "📊 HRV", "🩺 BP Variability",
                                      "🏃 Recovery", "😴 Sleep", "👟 Steps"]
                    )}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.subheader("📊 Today's Health Snapshot")

    snap_row1 = st.columns(4)
    snap_items = [
        ("❤️ Heart Rate", f"{heart_rate} BPM", "heart_rate", heart_rate),
        ("💓 Resting HR", f"{resting_hr} BPM", "resting_hr", resting_hr),
        ("📊 HRV", f"{hrv} ms", "hrv", hrv),
        ("🩺 BP Variability", f"{blood_pressure_variability} mmHg", "bp_variability", blood_pressure_variability),
    ]
    for _col, (_title, _val, _kind, _raw) in zip(snap_row1, snap_items):
        with _col:
            _, _color, _ = metric_status(_kind, _raw)
            render_metric_card(_title, _val, _color)

    snap_row2 = st.columns(3)
    snap_items2 = [
        ("🏃 Recovery", f"{heart_rate_recovery} BPM", "recovery", heart_rate_recovery),
        ("😴 Sleep", f"{sleep_quality}%", "sleep", sleep_quality),
        ("👟 Steps", f"{steps:,}", "steps", steps),
    ]
    for _col, (_title, _val, _kind, _raw) in zip(snap_row2, snap_items2):
        with _col:
            _, _color, _ = metric_status(_kind, _raw)
            render_metric_card(_title, _val, _color)

    st.progress(min(steps / 10000, 1.0))
    st.caption("Daily step goal: 10,000 steps")

    st.markdown("---")
    viz_col, radar_col = st.columns([3, 2])
    with viz_col:
        st.subheader("📉 7-Day Trend Preview")
        render_trend_chart(heart_rate, sleep_quality, steps)
    with radar_col:
        st.subheader("🕸️ Vitals at a Glance")
        render_radar_chart(heart_rate, resting_hr, hrv, blood_pressure_variability,
                            heart_rate_recovery, sleep_quality, steps)

    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("❤️ Full Dashboard", use_container_width=True):
            st.session_state.current_page = "❤️ Heart Dashboard"
            st.rerun()
    with qa2:
        if st.button("📈 Health Summary", use_container_width=True):
            st.session_state.current_page = "📈 Health Summary"
            st.rerun()
    with qa3:
        if st.button("🤖 Ask PulseGuard AI", use_container_width=True):
            st.session_state.current_page = "🤖 Ask PulseGuard AI"
            st.rerun()
    with qa4:
        if st.button("⌚ Smartwatch", use_container_width=True):
            st.session_state.current_page = "⌚ Smartwatch"
            st.rerun()

# =====================================================
# HEART DASHBOARD
# =====================================================
elif page == "❤️ Heart Dashboard":

    st.title("❤️ Heart Health Dashboard")
    st.write("View your latest heart-health information collected from your connected smartwatch.")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        _, color, _ = metric_status("heart_rate", heart_rate)
        render_metric_card("Heart Rate", f"{heart_rate} BPM", color)
        if 60 <= heart_rate <= 100:
            st.success("Normal resting heart rate")
        elif heart_rate < 60:
            st.warning("Below the normal resting range")
        else:
            st.error("Above the normal resting range")

    with col2:
        _, color, _ = metric_status("resting_hr", resting_hr)
        render_metric_card("Resting Heart Rate", f"{resting_hr} BPM", color)
        if 50 <= resting_hr <= 80:
            st.success("Healthy resting heart rate")
        else:
            st.warning("Monitor this value over time")

    with col3:
        _, color, _ = metric_status("hrv", hrv)
        render_metric_card("Heart Rate Variability", f"{hrv} ms", color)
        if hrv >= 50:
            st.success("Good HRV")
        elif hrv >= 30:
            st.warning("Average HRV")
        else:
            st.error("Low HRV")

    st.markdown("---")

    col4, col5, col6 = st.columns(3)
    with col4:
        _, color, _ = metric_status("bp_variability", blood_pressure_variability)
        render_metric_card("Blood Pressure Variability", f"{blood_pressure_variability} mmHg", color)
        if blood_pressure_variability <= 10:
            st.success("Within expected range")
        else:
            st.warning("Keep monitoring")

    with col5:
        _, color, _ = metric_status("recovery", heart_rate_recovery)
        render_metric_card("Heart Rate Recovery", f"{heart_rate_recovery} BPM", color)
        if heart_rate_recovery >= 20:
            st.success("Healthy recovery")
        else:
            st.warning("Recovery may be slower")

    with col6:
        _, color, _ = metric_status("sleep", sleep_quality)
        render_metric_card("Sleep Quality", f"{sleep_quality}%", color)
        st.progress(sleep_quality / 100)
        if sleep_quality >= 80:
            st.success("Great sleep quality")
        elif sleep_quality >= 60:
            st.warning("Average sleep quality")
        else:
            st.error("Poor sleep quality")

    st.markdown("---")
    st.subheader("💓 Live Heart Rhythm (simulated)")
    render_ecg_animation(heart_rate)
    st.caption("This waveform is a stylized animation for demonstration purposes, not a real ECG reading.")

    st.markdown("---")
    st.subheader("🕸️ Vitals at a Glance")
    render_radar_chart(heart_rate, resting_hr, hrv, blood_pressure_variability, heart_rate_recovery, sleep_quality, steps)

    st.markdown("---")
    st.subheader("📉 7-Day Trend")
    render_trend_chart(heart_rate, sleep_quality, steps)

    st.markdown("---")
    st.subheader("👟 Daily Step Count")
    st.metric("Today's Steps", f"{steps:,}")
    st.progress(min(steps / 10000, 1.0))
    if steps >= 10000:
        st.success("🎉 Daily step goal reached!")
    elif steps >= 7500:
        st.info("You're getting close to today's goal.")
    else:
        st.warning("Keep moving to reach today's goal!")

    st.markdown("---")
    st.subheader("📖 What These Metrics Mean")

    with st.expander("❤️ Heart Rate"):
        st.write("Your heart rate is the number of times your heart beats each minute.")
    with st.expander("💓 Resting Heart Rate"):
        st.write("This is your heart rate while you are resting. Tracking changes over time can be useful.")
    with st.expander("📊 Heart Rate Variability (HRV)"):
        st.write("HRV measures the variation in time between heartbeats. It can provide information about recovery and overall wellness.")
    with st.expander("🩺 Blood Pressure Variability"):
        st.write("Some wearable devices estimate changes in blood pressure. Availability depends on your smartwatch.")
    with st.expander("🏃 Heart Rate Recovery"):
        st.write("Heart rate recovery measures how quickly your heart rate decreases after exercise.")
    with st.expander("😴 Sleep Quality"):
        st.write("Sleep quality summarizes how well you slept based on information from your wearable device.")

    st.info("These values are educational examples for the Sprint 1 prototype and should not be used to diagnose medical conditions.")

# =====================================================
# SMARTWATCH CONNECTION PAGE
# =====================================================
elif page == "⌚ Smartwatch":

    st.title("⌚ Smartwatch Connection")
    st.write("Connect your smartwatch to automatically sync your heart-health information.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if watch_connected:
            st.success(f"🟢 {st.session_state.selected_watch} Connected")
        else:
            st.error("🔴 Not Connected")

        st.metric("Battery", f"{battery}%")
        st.metric("Last Sync", last_sync)
        st.caption(f"Connected since {st.session_state.connected_since}")
        st.button("🔄 Sync Now")

    with col2:
        st.subheader("Supported Devices")
        st.write("✅ Apple Watch")
        st.write("✅ Fitbit")
        st.write("✅ Garmin")
        st.write("✅ Samsung Galaxy Watch")
        st.write("✅ Google Pixel Watch")
        st.info("Sprint 1 uses simulated smartwatch data. Future versions will connect to real wearable devices.")

    st.markdown("---")
    st.subheader("Connected Health Metrics")

    st.checkbox("Heart Rate", value=True, disabled=True)
    st.checkbox("Resting Heart Rate", value=True, disabled=True)
    st.checkbox("Heart Rate Variability", value=True, disabled=True)
    st.checkbox("Blood Pressure (Supported Devices)", value=True, disabled=True)
    st.checkbox("Heart Rate Recovery", value=True, disabled=True)
    st.checkbox("Sleep Quality", value=True, disabled=True)
    st.checkbox("Daily Step Count", value=True, disabled=True)

    st.markdown("---")
    st.warning("A real smartwatch connection will be added in a future sprint using the manufacturer's API.")

# =====================================================
# HEALTH SUMMARY PAGE
# =====================================================
elif page == "📈 Health Summary":

    st.title("📈 Daily Health Summary")
    st.success("Here is today's overall health summary.")
    st.markdown("---")

    score, positives, concerns = generate_health_summary()

    _prev_score = st.session_state.get("_prev_score", score)
    _prev_steps_goal = st.session_state.get("_prev_steps_goal_hit", steps >= 10000)
    if score >= 75 and _prev_score < 75:
        st.balloons()
    if steps >= 10000 and not _prev_steps_goal:
        st.balloons()
    st.session_state._prev_score = score
    st.session_state._prev_steps_goal_hit = steps >= 10000

    _streak = compute_streak(score)
    if _streak > 0:
        st.markdown(f"🔥 **{_streak}-day streak** of good heart health!")

    gauge_col, anim_col = st.columns([1, 1])
    with gauge_col:
        render_score_gauge(score)
    with anim_col:
        animate_score(score)

    st.markdown("---")
    st.subheader("🧠 PulseGuard Health Insights")

    if score >= 90:
        st.success("Overall, your heart health data looks very good today.")
    elif score >= 75:
        st.info("Your heart health looks good, but there are a few things to monitor.")
    else:
        st.warning("Some measurements deserve extra attention. Continue monitoring your trends.")

    ai_insight = generate_ai_insight(score, positives, concerns)
    st.write("**🤖 AI-Generated Insight**")
    st.info(ai_insight)

    if positives:
        st.write("### ✅ What's Going Well")
        render_chips([(p, GOOD) for p in positives])

    if concerns:
        st.write("### ⚠ Areas to Watch")
        render_chips([(c, DANGER) for c in concerns])

    st.markdown("---")
    st.write("### Summary")

    st.info(f"""
**Heart Rate:** {heart_rate} BPM

**Resting Heart Rate:** {resting_hr} BPM

**Heart Rate Variability:** {hrv} ms

**Blood Pressure Variability:** {blood_pressure_variability} mmHg

**Heart Rate Recovery:** {heart_rate_recovery} BPM

**Sleep Quality:** {sleep_quality}%

**Daily Steps:** {steps:,}

**Watch Battery:** {battery}%

**Last Sync:** {last_sync}
""")

    st.markdown("---")
    st.subheader("Today's Highlights")

    highlight_chips = []
    if sleep_quality >= 80:
        highlight_chips.append(("😴 Excellent sleep recorded", GOOD))
    if steps >= 7500:
        highlight_chips.append(("👟 Great job staying active!", GOOD))
    if 60 <= heart_rate <= 100:
        highlight_chips.append(("❤️ Heart rate within expected range", GOOD))
    if hrv >= 50:
        highlight_chips.append(("📊 HRV looks good", GOOD))
    if highlight_chips:
        render_chips(highlight_chips)
    else:
        st.caption("No standout highlights for today's readings.")

    st.markdown("---")
    st.subheader("Health Recommendations")
    st.write("• Continue wearing your smartwatch throughout the day.")
    st.write("• Stay physically active.")
    st.write("• Aim for 7–9 hours of sleep.")
    st.write("• Stay hydrated.")
    st.write("• Schedule regular checkups with your healthcare provider.")

    st.markdown("---")
    st.subheader("🚨 Early Warning Detector")

    alerts = []
    if heart_rate > 100:
        alerts.append("Elevated heart rate detected.")
    if hrv < 30:
        alerts.append("Low heart rate variability detected.")
    if sleep_quality < 60:
        alerts.append("Poor sleep quality may affect heart health.")
    if heart_rate_recovery < 15:
        alerts.append("Slow heart rate recovery detected.")

    if len(alerts) == 0:
        st.success("🟢 No unusual patterns were detected today.")
    else:
        st.warning("PulseGuard noticed the following patterns:")
        render_chips([(a, DANGER) for a in alerts])

    st.caption(
        "This feature is an educational prototype and does not provide a medical diagnosis. "
        "If you have concerning symptoms, seek advice from a qualified healthcare professional."
    )

    st.markdown("---")
    st.subheader("📅 Browse Past Days")
    st.caption("Sample simulated history — pick a date to see how that day's readings would have scored.")

    _hist_dates = sorted(st.session_state.full_history.keys())
    _date_labels = ["Today (live)"] + [
        datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y") for d in _hist_dates
    ]
    _selected_label = st.selectbox("Select a date", _date_labels)

    if _selected_label == "Today (live)":
        st.info(f"Today's Heart Health Score: **{score}/100**")
    else:
        _sel_date = _hist_dates[_date_labels.index(_selected_label) - 1]
        _day = st.session_state.full_history[_sel_date]
        _day_score, _day_positives, _day_concerns = generate_health_summary(
            heart_rate=_day["heart_rate"], resting_hr=_day["resting_hr"], hrv=_day["hrv"],
            sleep_quality=_day["sleep_quality"], steps=_day["steps"],
            heart_rate_recovery=_day["heart_rate_recovery"],
            blood_pressure_variability=_day["blood_pressure_variability"]
        )
        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        with dcol1:
            st.metric("Score", f"{_day_score}/100")
        with dcol2:
            st.metric("Heart Rate", f"{_day['heart_rate']} BPM")
        with dcol3:
            st.metric("Sleep", f"{_day['sleep_quality']}%")
        with dcol4:
            st.metric("Steps", f"{_day['steps']:,}")
        if _day_concerns:
            render_chips([(c, DANGER) for c in _day_concerns])
        else:
            st.caption("No concerns flagged for this simulated day.")

    st.markdown("---")
    st.subheader("📤 Export & Share")
    st.caption("Choose how much history to include in the doctor report, then download your files below.")

    RANGE_OPTIONS = {
        "1 Day": 1,
        "1 Week": 7,
        "1 Month": 30,
    }
    _range_label = st.radio(
        "🗓️ Report range",
        list(RANGE_OPTIONS.keys()),
        index=0,
        horizontal=True,
        help="Controls how much simulated history is summarized in the Doctor Report PDF.",
    )
    _range_days = RANGE_OPTIONS[_range_label]

    _today_values = {
        "heart_rate": heart_rate,
        "resting_hr": resting_hr,
        "hrv": hrv,
        "blood_pressure_variability": blood_pressure_variability,
        "heart_rate_recovery": heart_rate_recovery,
        "sleep_quality": sleep_quality,
        "steps": steps,
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
            f"📄 Download Doctor Report — {_range_label} (PDF)",
            data=pdf_bytes,
            file_name=f"PulseGuard_Report_{_range_label.replace(' ', '')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with dl_col2:
        st.download_button(
            "📸 Download Shareable Summary Card",
            data=share_card_bytes,
            file_name="PulseGuard_Summary.png",
            mime="image/png",
            use_container_width=True,
        )

    st.caption(
        "This report is for educational purposes and is not intended to replace professional medical advice."
    )

# =====================================================
# AI CHAT ASSISTANT PAGE
# =====================================================
elif page == "🤖 Ask PulseGuard AI":

    st.title("🤖 Ask PulseGuard AI")
    st.caption(
        "This is a simulated, rule-based demo assistant — it reads your current sidebar values "
        "and answers with simple templated logic. It is not a real AI model and not medical advice."
    )
    st.markdown("---")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            ("assistant", "Hi! Ask me about your heart rate, sleep, HRV, steps, recovery, or overall score.")
        ]

    for role, content in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(content)

    user_question = st.chat_input("Ask about your heart health...")
    if user_question:
        st.session_state.chat_history.append(("user", user_question))
        _score, _positives, _concerns = generate_health_summary()
        response = ai_chat_response(
            user_question, _score, _positives, _concerns,
            heart_rate, resting_hr, hrv, sleep_quality, steps, heart_rate_recovery
        )
        st.session_state.chat_history.append(("assistant", response))
        st.rerun()

elif page == "💡 Accuracy Tips":

    st.markdown(
        f"""
        <div class="hero-banner">
            <div style="font-size:48px;">💡</div>
            <div>
                <div class="main-title" style="font-size:34px;margin-bottom:0;">Accuracy Tips</div>
                <div class="subtitle" style="font-size:17px;">
                    Follow these tips to help your smartwatch collect the most reliable heart-health information.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    def _tip_card(icon, text, color):
        st.markdown(
            f"""
            <div class="metric-card" style="border-left:6px solid {color};padding:16px 18px;">
                <div style="font-size:22px;margin-bottom:6px;">{icon}</div>
                <div style="font-size:15px;color:{C['text']} !important;">{text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("⌚ Wearing Your Smartwatch")
    wear_tips = [
        ("✅", "Wear your watch snugly, but comfortably — not too loose."),
        ("🧼", "Keep the sensors clean and free of lotion, sweat, or dirt."),
        ("🔋", "Charge your watch regularly to avoid gaps in tracking."),
        ("📍", "Wear the watch in the same position each day for consistency."),
    ]
    wear_cols = st.columns(len(wear_tips))
    for _col, (icon, text) in zip(wear_cols, wear_tips):
        with _col:
            _tip_card(icon, text, GOOD)

    st.markdown("---")
    st.subheader("❤️ Heart Health Habits")
    health_tips = [
        ("🏃", "Exercise regularly to strengthen your cardiovascular system."),
        ("🥗", "Eat a heart-healthy diet rich in fruits, vegetables, and whole grains."),
        ("💧", "Stay hydrated throughout the day."),
        ("😴", "Aim for 7–9 hours of consistent, quality sleep."),
        ("🚭", "Avoid smoking and limit exposure to secondhand smoke."),
        ("🧘", "Manage stress with breathing exercises, mindfulness, or rest."),
    ]
    health_cols_row1 = st.columns(3)
    for _col, (icon, text) in zip(health_cols_row1, health_tips[:3]):
        with _col:
            _tip_card(icon, text, C["title"])
    health_cols_row2 = st.columns(3)
    for _col, (icon, text) in zip(health_cols_row2, health_tips[3:]):
        with _col:
            _tip_card(icon, text, C["title"])

    st.markdown("---")
    st.subheader("⚠️ When Should You Contact a Doctor?")

    warn_symptoms = [
        "Chest pain", "Difficulty breathing", "Severe dizziness",
        "Fainting", "Unusually fast or slow heart rate", "Any symptom that concerns you",
    ]
    st.markdown(
        f"""
        <div class="metric-card" style="border-left:6px solid {WARN};">
            <div class="metric-title" style="margin-bottom:10px;">Seek medical attention if you experience:</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;">
                {''.join(
                    f'<span class="chip" style="background:{hex_to_rgba(WARN, 0.15)};'
                    f'color:{WARN} !important;border:1px solid {WARN};">⚠ {s}</span>'
                    for s in warn_symptoms
                )}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div style="background:{hex_to_rgba(DANGER, 0.14)};border:2px solid {DANGER};
                    border-radius:16px;padding:18px 22px;margin-top:16px;
                    display:flex;align-items:center;gap:14px;">
            <div style="font-size:34px;">🚨</div>
            <div style="color:{DANGER} !important;font-weight:700;font-size:15px;">
                If you think you are experiencing a medical emergency, call your local emergency
                services immediately.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =====================================================
# ABOUT PAGE
# =====================================================
elif page == "ℹ️ About":

    st.title("ℹ️ About PulseGuard")
    st.markdown("---")

    st.subheader("Our Mission")
    st.write(
        "PulseGuard is developed by New Jersey Heart Disease Prevention (NJHDP). "
        "Our mission is to reduce preventable heart disease by helping people monitor "
        "their cardiovascular health before emergencies occur."
    )

    st.markdown("---")
    st.subheader("Sprint 1 Features")
    st.markdown("""
✅ Heart Rate

✅ Resting Heart Rate

✅ Heart Rate Variability (HRV)

✅ Blood Pressure Variability

✅ Heart Rate Recovery

✅ Sleep Quality

✅ Daily Step Count

✅ Smartwatch Connection Prototype

✅ Health Summary

✅ Accuracy Tips

✅ Downloadable Health Report
""")

    st.markdown("---")
    st.subheader("Future Features")
    st.markdown("""
🔹 AI Heart Risk Score

🔹 AI Health Assistant

🔹 Symptom Tracker

🔹 Long-Term Health Trends

🔹 Emergency Alerts

🔹 Nearby Doctors

🔹 Telehealth Recommendations

🔹 Share Reports with Healthcare Providers

🔹 Personalized Health Insights
""")

    st.markdown("---")
    st.subheader("Disclaimer")
    st.caption("""
PulseGuard is an educational prototype created for a school project.

It is NOT a medical device and should not be used to diagnose or treat medical conditions.

Always consult a qualified healthcare professional regarding your health.
""")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("---")
st.markdown(
    """
<div class="footer">
<b>❤️ PulseGuard</b><br>
New Jersey Heart Disease Prevention (NJHDP)<br><br>
Sprint 1 Prototype • Version 1.0<br>
Helping people monitor their heart health before emergencies occur.
</div>
""",
    unsafe_allow_html=True
)

# --------------------------------------------------
# Auto-Play Demo engine (runs after the full page has
# rendered so the current scenario is visible briefly
# before the app advances to the next one)
# --------------------------------------------------
if st.session_state.autoplay:
    time.sleep(3)
    idx = st.session_state.scenario_idx % len(SCENARIOS)
    scenario = SCENARIOS[idx]
    for _k, _v in scenario.items():
        st.session_state[_k] = _v
    st.session_state.scenario_idx = idx + 1
    st.rerun()
