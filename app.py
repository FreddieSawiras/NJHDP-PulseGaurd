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
    layout="wide"
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
    for _i in range(14, 0, -1):
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
    "🟦 Samsung Galaxy Watch": "#6a1b9a",
    "🟢 Google Pixel Watch": "#1a73e8",
    "🏃 Garmin": "#0077c8",
    "🎽 Fitbit": "#00b0b9",
}

# --------------------------------------------------
# Color palette (Light / Dark mode)
# --------------------------------------------------
if st.session_state.dark_mode:
    C = dict(
        bg="#0f1115", card_bg="#1b1e24", text="#e8e8e8", subtitle="#a8a8a8",
        title="#ff6b6b", border="#2a2d33", chip_bg_alpha="33",
    )
else:
    C = dict(
        bg="#f8f9fa", card_bg="#ffffff", text="#222222", subtitle="#555555",
        title="#c62828", border="#e5e5e5", chip_bg_alpha="22",
    )

GOOD, WARN, DANGER = "#2e7d32", "#f9a825", "#c62828"


def hex_to_rgba(hex_color, alpha=0.2):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def score_color(score):
    if score >= 90:
        return GOOD
    elif score >= 75:
        return WARN
    else:
        return DANGER

# --------------------------------------------------
# Global styling
# --------------------------------------------------
st.markdown(f"""
<style>

.stApp, .stApp *,
section[data-testid="stSidebar"], section[data-testid="stSidebar"] * {{
    color:{C['text']} !important;
}}

.stApp {{
    background-color:{C['bg']};
}}

section[data-testid="stSidebar"] {{
    background-color:{C['card_bg']} !important;
}}

.main-title{{
    font-size:46px;
    font-weight:bold;
    color:{C['title']} !important;
}}

.subtitle{{
    color:{C['subtitle']} !important;
    font-size:20px;
}}

.metric-card{{
    background:{C['card_bg']};
    border-radius:15px;
    padding:20px;
    box-shadow:0px 3px 8px rgba(0,0,0,.12);
    margin-bottom:15px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}

.metric-card:hover{{
    transform: translateY(-4px);
    box-shadow:0px 8px 18px rgba(0,0,0,.18);
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
    background: linear-gradient(135deg, {C['title']}22, {C['card_bg']});
    border-radius:20px;
    padding:28px 32px;
    margin-bottom:20px;
    display:flex;
    align-items:center;
    gap:20px;
}}

.device-card{{
    background:{C['card_bg']};
    border-radius:14px;
    padding:14px;
    text-align:center;
    margin-top:10px;
    box-shadow:0px 2px 6px rgba(0,0,0,.10);
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

@keyframes scorePop {{
    0%   {{ opacity: 0; transform: scale(0.85); }}
    100% {{ opacity: 1; transform: scale(1); }}
}}

.score-pop {{
    animation: scorePop 0.4s ease-out;
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
                             sleep_quality=None, steps=None, heart_rate_recovery=None):
    heart_rate = st.session_state.heart_rate if heart_rate is None else heart_rate
    resting_hr = st.session_state.resting_hr if resting_hr is None else resting_hr
    hrv = st.session_state.hrv if hrv is None else hrv
    sleep_quality = st.session_state.sleep_quality if sleep_quality is None else sleep_quality
    steps = st.session_state.steps if steps is None else steps
    heart_rate_recovery = st.session_state.heart_rate_recovery if heart_rate_recovery is None else heart_rate_recovery

    score = 100
    positives = []
    concerns = []

    if 60 <= heart_rate <= 100:
        positives.append("Your heart rate is within the expected resting range.")
    else:
        score -= 10
        concerns.append("Your heart rate is outside the expected resting range.")

    if 50 <= resting_hr <= 80:
        positives.append("Your resting heart rate looks healthy.")
    else:
        score -= 5
        concerns.append("Your resting heart rate may be unusual.")

    if hrv >= 50:
        positives.append("Your heart rate variability is strong.")
    else:
        score -= 8
        concerns.append("Your heart rate variability is lower than normal.")

    if sleep_quality >= 80:
        positives.append("Excellent sleep quality.")
    elif sleep_quality >= 60:
        score -= 3
        concerns.append("Your sleep quality could improve.")
    else:
        score -= 8
        concerns.append("Poor sleep quality detected.")

    if steps >= 10000:
        positives.append("You reached your daily activity goal.")
    elif steps >= 7500:
        positives.append("You stayed fairly active today.")
    else:
        score -= 7
        concerns.append("Try increasing your daily activity.")

    if heart_rate_recovery >= 20:
        positives.append("Heart rate recovery looks healthy.")
    else:
        score -= 5
        concerns.append("Heart rate recovery is slower than expected.")

    score = max(score, 0)
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
            heart_rate_recovery=day["heart_rate_recovery"]
        )
        if day_score >= 75:
            streak += 1
        else:
            break
    return streak


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


def generate_pdf_report(score, positives, concerns, ai_insight, heart_rate, resting_hr, hrv,
                         bp, recovery, sleep_quality, steps, battery, last_sync, watch_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(198, 40, 40)
    pdf.cell(0, 12, _pdf_safe("PulseGuard Health Report"), ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, _pdf_safe(f"Generated {last_sync} ET  |  Device: {watch_name}"), ln=True)
    pdf.ln(4)

    if score >= 90:
        score_rgb = (46, 125, 50)
    elif score >= 75:
        score_rgb = (249, 168, 37)
    else:
        score_rgb = (198, 40, 40)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*score_rgb)
    pdf.cell(0, 10, _pdf_safe(f"Heart Health Score: {score}/100"), ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "Today's Metrics", ln=True)
    pdf.set_font("Helvetica", "", 11)

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
    for label, value in rows:
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(90, 8, _pdf_safe(label), border=0, fill=True)
        pdf.cell(0, 8, _pdf_safe(value), border=0, fill=True, ln=True)

    pdf.ln(4)

    if positives:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(46, 125, 50)
        pdf.cell(0, 8, "What's Going Well", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(20, 20, 20)
        for p in positives:
            pdf.multi_cell(0, 6, _pdf_safe(f"- {p}"))
        pdf.ln(2)

    if concerns:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(198, 40, 40)
        pdf.cell(0, 8, "Areas to Watch", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(20, 20, 20)
        for c in concerns:
            pdf.multi_cell(0, 6, _pdf_safe(f"- {c}"))
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "AI-Generated Insight", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, _pdf_safe(ai_insight))
    pdf.ln(4)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, _pdf_safe(
        "This report is generated by an educational prototype and is not a medical diagnosis. "
        "It is not intended to replace professional medical advice. Consult a qualified "
        "healthcare provider regarding any concerns."
    ))

    return bytes(pdf.output())


def generate_share_card(score, heart_rate, sleep_quality, steps, watch_name):
    W, H = 1080, 1920
    if score >= 90:
        accent = (46, 125, 50)
    elif score >= 75:
        accent = (249, 168, 37)
    else:
        accent = (198, 40, 40)

    img = Image.new("RGB", (W, H), (18, 18, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 420], fill=accent)

    try:
        f_brand = ImageFont.load_default(size=56)
        f_giant = ImageFont.load_default(size=240)
        f_label = ImageFont.load_default(size=46)
        f_small = ImageFont.load_default(size=34)
    except TypeError:
        f_brand = f_giant = f_label = f_small = ImageFont.load_default()

    draw.text((60, 60), "PulseGuard", font=f_brand, fill=(255, 255, 255))
    draw.text((60, 160), "Daily Heart Health Summary", font=f_small, fill=(255, 255, 255))

    draw.text((60, 520), "Heart Health Score", font=f_label, fill=(190, 190, 190))
    draw.text((60, 590), f"{score}", font=f_giant, fill=accent)
    draw.text((60, 900), "/ 100", font=f_label, fill=(140, 140, 140))

    rows = [
        ("Heart Rate", f"{heart_rate} BPM"),
        ("Sleep Quality", f"{sleep_quality}%"),
        ("Daily Steps", f"{steps:,}"),
        ("Device", watch_name),
    ]
    y = 1050
    for label, value in rows:
        draw.text((60, y), label, font=f_small, fill=(160, 160, 160))
        draw.text((60, y + 45), value, font=f_label, fill=(255, 255, 255))
        y += 140

    draw.text((60, H - 100), "Generated with PulseGuard (prototype)", font=f_small, fill=(110, 110, 110))

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
# Sidebar
# --------------------------------------------------
st.sidebar.image(LOGO_URL, width=80)
st.sidebar.title("❤️ PulseGuard")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "❤️ Heart Dashboard",
        "⌚ Smartwatch",
        "📈 Health Summary",
        "🤖 Ask PulseGuard",
        "💡 Accuracy Tips",
        "ℹ️ About"
    ]
)

st.sidebar.markdown("---")
st.sidebar.success("Sprint 1 Prototype")
st.sidebar.toggle("🌙 Dark Mode", key="dark_mode")

st.sidebar.markdown("---")
st.sidebar.subheader("⌚ Choose Your Device")
st.session_state.selected_watch = st.sidebar.selectbox(
    "Simulated device",
    list(WATCH_OPTIONS.keys()),
    index=list(WATCH_OPTIONS.keys()).index(st.session_state.selected_watch)
)
_watch_color = WATCH_OPTIONS[st.session_state.selected_watch]
watch_plain_name = " ".join(st.session_state.selected_watch.split(" ")[1:])
st.sidebar.markdown(
    f"""
    <div class="device-card" style="border-top:5px solid {_watch_color};">
        <div style="font-size:36px;">{st.session_state.selected_watch.split(" ")[0]}</div>
        <div style="font-weight:700;">{watch_plain_name}</div>
        <div style="font-size:12px;color:{C['subtitle']} !important;">Connected since {st.session_state.connected_since}</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Live Demo Controls")
st.sidebar.caption(
    "No real smartwatch is connected in this prototype. "
    "Drag these sliders, simulate a random reading, or auto-play a scenario."
)

if st.sidebar.button("🎲 Simulate New Reading"):
    st.session_state.heart_rate = random.randint(55, 130)
    st.session_state.resting_hr = random.randint(45, 90)
    st.session_state.hrv = random.randint(15, 90)
    st.session_state.blood_pressure_variability = random.randint(0, 20)
    st.session_state.heart_rate_recovery = random.randint(5, 40)
    st.session_state.sleep_quality = random.randint(30, 100)
    st.session_state.steps = random.randint(500, 15000)
    st.session_state.battery = random.randint(10, 100)
    st.session_state.tip_index = random.randint(0, len(TIPS) - 1)

st.session_state.autoplay = st.sidebar.checkbox(
    "▶️ Auto-Play Demo (cycles scenarios every few seconds)",
    value=st.session_state.autoplay
)

heart_rate = st.sidebar.slider("❤️ Heart Rate (BPM)", 30, 180, key="heart_rate")
resting_hr = st.sidebar.slider("💓 Resting Heart Rate (BPM)", 30, 130, key="resting_hr")
hrv = st.sidebar.slider("📊 Heart Rate Variability (ms)", 0, 150, key="hrv")
blood_pressure_variability = st.sidebar.slider("🩺 Blood Pressure Variability (mmHg)", 0, 40, key="blood_pressure_variability")
heart_rate_recovery = st.sidebar.slider("🏃 Heart Rate Recovery (BPM)", 0, 60, key="heart_rate_recovery")
sleep_quality = st.sidebar.slider("😴 Sleep Quality (%)", 0, 100, key="sleep_quality")
steps = st.sidebar.slider("👟 Daily Steps", 0, 20000, step=100, key="steps")
battery = st.sidebar.slider("🔋 Watch Battery (%)", 0, 100, key="battery")

watch_connected = True
last_sync = datetime.now(ZoneInfo("America/New_York")).strftime("%I:%M %p")

# =====================================================
# HOME PAGE
# =====================================================
if page == "🏠 Home":

    st.markdown(
        f"""
        <div class="hero-banner">
            <img src="{LOGO_URL}" width="70" style="border-radius:14px;">
            <div>
                <div class="main-title" style="margin-bottom:0;">❤️ PulseGuard</div>
                <div class="subtitle">Simple Steps for a Stronger, Healthier Heart.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.success(
        "Welcome to PulseGuard. Track your symptoms, understand your heart health, and get guidance to help lower your risk of heart disease.     "
        "Important heart-health information in one place."
    )

    tip_col, streak_col = st.columns([2, 1])
    with tip_col:
        st.info(f"**Tip of the Day:** {TIPS[st.session_state.tip_index]}")
    with streak_col:
        _today_score, _, _ = generate_health_summary()
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

        st.metric("Battery", f"{battery}%")
        st.metric("Last Sync", last_sync)
        st.button("🔄 Refresh Data")

    with col2:
        st.info(
            """
PulseGuard helps you monitor:

• Heart Rate

• Resting Heart Rate

• Heart Rate Variability

• Blood Pressure Variability

• Heart Rate Recovery

• Sleep Quality

• Daily Step Count
"""
        )

    st.markdown("---")
    st.subheader("Today's Health Snapshot")

    c1, c2, c3 = st.columns(3)
    with c1:
        _, color, _ = metric_status("heart_rate", heart_rate)
        render_metric_card("❤️ Heart Rate", f"{heart_rate} BPM", color)
    with c2:
        _, color, _ = metric_status("sleep", sleep_quality)
        render_metric_card("😴 Sleep", f"{sleep_quality}%", color)
    with c3:
        _, color, _ = metric_status("steps", steps)
        render_metric_card("👟 Steps", f"{steps:,}", color)

    st.progress(min(steps / 10000, 1.0))
    st.caption("Daily step goal: 10,000 steps")

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
    if score >= 90 and _prev_score < 90:
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
            heart_rate_recovery=_day["heart_rate_recovery"]
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

    report_text = f"""PulseGuard Daily Report

Heart Rate: {heart_rate} BPM
Resting Heart Rate: {resting_hr} BPM
Heart Rate Variability: {hrv} ms
Blood Pressure Variability: {blood_pressure_variability} mmHg
Heart Rate Recovery: {heart_rate_recovery} BPM
Sleep Quality: {sleep_quality}%
Daily Steps: {steps}
Overall Score: {score}/100

AI Insight Summary:
{ai_insight}
"""

    pdf_bytes = generate_pdf_report(
        score, positives, concerns, ai_insight, heart_rate, resting_hr, hrv,
        blood_pressure_variability, heart_rate_recovery, sleep_quality, steps,
        battery, last_sync, watch_plain_name
    )
    share_card_bytes = generate_share_card(score, heart_rate, sleep_quality, steps, watch_plain_name)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            "📄 Download Doctor Report (PDF)",
            data=pdf_bytes,
            file_name="PulseGuard_Report.pdf",
            mime="application/pdf"
        )
    with dl_col2:
        st.download_button(
            "📸 Download Shareable Summary Card",
            data=share_card_bytes,
            file_name="PulseGuard_Summary.png",
            mime="image/png"
        )

    st.caption(
        "This report is for educational purposes and is not intended to replace professional medical advice."
    )

# =====================================================
# AI CHAT ASSISTANT PAGE
# =====================================================
elif page == "🤖 Ask PulseGuard":

    st.title("🤖 Ask PulseGuard")
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

    st.title("💡 Accuracy Tips")
    st.write("Follow these tips to help your smartwatch collect the most reliable heart-health information.")
    st.markdown("---")

    st.subheader("⌚ Wearing Your Smartwatch")
    st.success("✔ Wear your watch snugly, but comfortably.")
    st.success("✔ Keep the sensors clean.")
    st.success("✔ Charge your watch regularly.")
    st.success("✔ Wear the watch in the same position each day.")

    st.markdown("---")
    st.subheader("❤️ Heart Health Tips")
    st.info("❤️ Exercise regularly.")
    st.info("🥗 Eat a heart-healthy diet.")
    st.info("💧 Stay hydrated.")
    st.info("😴 Aim for 7–9 hours of sleep.")
    st.info("🚭 Avoid smoking.")
    st.info("🧘 Manage stress.")

    st.markdown("---")
    st.subheader("⚠ When Should You Contact a Doctor?")
    st.warning("""
You should seek medical attention if you experience:

• Chest pain

• Difficulty breathing

• Severe dizziness

• Fainting

• An unusually fast or slow heart rate

• Any symptoms that concern you
""")

    st.error("If you think you are experiencing a medical emergency, call your local emergency services immediately.")

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
