import streamlit as st
import random
from datetime import datetime

# --------------------------------------------------
# Set up the page
# --------------------------------------------------
st.set_page_config(
    page_title="PulseGaurd",
    page_icon="❤️",
    layout="wide"
)

# --------------------------------------------------
# PulseGuard Colors and Styling
# --------------------------------------------------
st.markdown("""
<style>

.main {
    background-color:#f8f9fa;
}

.main-title{
    font-size:46px;
    font-weight:bold;
    color:#c62828;
}

.subtitle{
    color:#555;
    font-size:20px;
}

.metric-card{
    background:white;
    border-radius:15px;
    padding:20px;
    border-left:8px solid #2e7d32;
    box-shadow:0px 3px 8px rgba(0,0,0,.08);
    margin-bottom:15px;
}

.metric-title{
    font-size:17px;
    color:#666;
}

.metric-value{
    font-size:34px;
    font-weight:bold;
    color:#c62828;
}

.good{
    color:green;
    font-weight:bold;
}

.warning{
    color:orange;
    font-weight:bold;
}

.danger{
    color:red;
    font-weight:bold;
}

.footer{
    text-align:center;
    color:gray;
    font-size:13px;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Sidebar Navigation
# --------------------------------------------------
st.sidebar.image(
    "https://plain-enam-prod-public.komododecks.com/202607/27/VZS1Q3WWHJ5eZyOEZXiM/image.png",
    width=80
)

st.sidebar.title("❤️ PulseGuard")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "❤️ Heart Dashboard",
        "⌚ Smartwatch",
        "📈 Health Summary",
        "💡 Accuracy Tips",
        "ℹ️ About"
    ]
)

st.sidebar.markdown("---")
st.sidebar.success("Sprint 1 Prototype")

# --------------------------------------------------
# Simulated smartwatch data (Live Demo Controls)
# No real smartwatch is connected yet, so these values
# are driven by sliders in the sidebar instead of being
# hardcoded. Drag them (or hit "Simulate New Reading")
# to watch the Heart Health Score and insights update live.
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
}

for _key, _val in _defaults.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Live Demo Controls")
st.sidebar.caption(
    "No real smartwatch is connected in this prototype. "
    "Drag these sliders (or hit the button below) to simulate live readings."
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

heart_rate = st.sidebar.slider("❤️ Heart Rate (BPM)", 30, 180, key="heart_rate")
resting_hr = st.sidebar.slider("💓 Resting Heart Rate (BPM)", 30, 130, key="resting_hr")
hrv = st.sidebar.slider("📊 Heart Rate Variability (ms)", 0, 150, key="hrv")
blood_pressure_variability = st.sidebar.slider("🩺 Blood Pressure Variability (mmHg)", 0, 40, key="blood_pressure_variability")
heart_rate_recovery = st.sidebar.slider("🏃 Heart Rate Recovery (BPM)", 0, 60, key="heart_rate_recovery")
sleep_quality = st.sidebar.slider("😴 Sleep Quality (%)", 0, 100, key="sleep_quality")
steps = st.sidebar.slider("👟 Daily Steps", 0, 20000, step=100, key="steps")
battery = st.sidebar.slider("🔋 Watch Battery (%)", 0, 100, key="battery")

watch_connected = True
last_sync = datetime.now().strftime("%I:%M %p")
# --------------------------------------------------
# Create a simple health summary based on today's data
# --------------------------------------------------

def generate_health_summary():

    score = 100
    positives = []
    concerns = []

    # Heart Rate
    if 60 <= heart_rate <= 100:
        positives.append("Your heart rate is within the expected resting range.")
    else:
        score -= 10
        concerns.append("Your heart rate is outside the expected resting range.")

    # Resting Heart Rate
    if 50 <= resting_hr <= 80:
        positives.append("Your resting heart rate looks healthy.")
    else:
        score -= 5
        concerns.append("Your resting heart rate may be unusual.")

    # HRV
    if hrv >= 50:
        positives.append("Your heart rate variability is strong.")
    else:
        score -= 8
        concerns.append("Your heart rate variability is lower than normal.")

    # Sleep
    if sleep_quality >= 80:
        positives.append("Excellent sleep quality.")
    elif sleep_quality >= 60:
        score -= 3
        concerns.append("Your sleep quality could improve.")
    else:
        score -= 8
        concerns.append("Poor sleep quality detected.")

    # Steps
    if steps >= 10000:
        positives.append("You reached your daily activity goal.")
    elif steps >= 7500:
        positives.append("You stayed fairly active today.")
    else:
        score -= 7
        concerns.append("Try increasing your daily activity.")

    # Heart Rate Recovery
    if heart_rate_recovery >= 20:
        positives.append("Heart rate recovery looks healthy.")
    else:
        score -= 5
        concerns.append("Heart rate recovery is slower than expected.")

    score = max(score, 0)

    return score, positives, concerns

# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

if page == "🏠 Home":

    st.markdown(
        "<div class='main-title'>❤️ PulseGuard</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='subtitle'>Simple Steps for a Stronger, Healthier Heart.</div>",
        unsafe_allow_html=True
    )

    st.write("")

    st.success(
        "Welcome to PulseGuard. Track your symptoms, understand your heart health, and get guidance to help lower your risk of heart disease.     "
        "Important heart-health information in one place."
    )

    col1,col2=st.columns(2)

    with col1:

        if watch_connected:
            st.success("🟢 Smartwatch Connected")
        else:
            st.error("🔴 Smartwatch Not Connected")

        st.metric("Battery",f"{battery}%")
        st.metric("Last Sync",last_sync)

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

    c1,c2,c3=st.columns(3)

    with c1:
        st.metric("❤️ Heart Rate",f"{heart_rate} BPM")

    with c2:
        st.metric("😴 Sleep",f"{sleep_quality}%")

    with c3:
        st.metric("👟 Steps",f"{steps:,}")

    st.progress(min(steps/10000,1.0))

    st.caption("Daily step goal: 10,000 steps")
# --------------------------------------------------
# HEART DASHBOARD
# --------------------------------------------------

elif page == "❤️ Heart Dashboard":

    st.title("❤️ Heart Health Dashboard")
    st.write(
        "View your latest heart-health information collected from your connected smartwatch."
    )

    st.markdown("---")

    # First row of metric cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Heart Rate</div>
                <div class="metric-value">{heart_rate} BPM</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if 60 <= heart_rate <= 100:
            st.success("Normal resting heart rate")
        elif heart_rate < 60:
            st.warning("Below the normal resting range")
        else:
            st.error("Above the normal resting range")

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Resting Heart Rate</div>
                <div class="metric-value">{resting_hr} BPM</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if 50 <= resting_hr <= 80:
            st.success("Healthy resting heart rate")
        else:
            st.warning("Monitor this value over time")

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Heart Rate Variability</div>
                <div class="metric-value">{hrv} ms</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if hrv >= 50:
            st.success("Good HRV")
        elif hrv >= 30:
            st.warning("Average HRV")
        else:
            st.error("Low HRV")

    st.markdown("---")

    # Second row
    col4, col5, col6 = st.columns(3)

    with col4:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Blood Pressure Variability</div>
                <div class="metric-value">{blood_pressure_variability} mmHg</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if blood_pressure_variability <= 10:
            st.success("Within expected range")
        else:
            st.warning("Keep monitoring")

    with col5:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Heart Rate Recovery</div>
                <div class="metric-value">{heart_rate_recovery} BPM</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if heart_rate_recovery >= 20:
            st.success("Healthy recovery")
        else:
            st.warning("Recovery may be slower")

    with col6:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Sleep Quality</div>
                <div class="metric-value">{sleep_quality}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.progress(sleep_quality / 100)

        if sleep_quality >= 80:
            st.success("Great sleep quality")
        elif sleep_quality >= 60:
            st.warning("Average sleep quality")
        else:
            st.error("Poor sleep quality")

    st.markdown("---")

    st.subheader("👟 Daily Step Count")

    st.metric("Today's Steps", f"{steps:,}")

    step_progress = min(steps / 10000, 1.0)
    st.progress(step_progress)

    if steps >= 10000:
        st.success("🎉 Daily step goal reached!")
    elif steps >= 7500:
        st.info("You're getting close to today's goal.")
    else:
        st.warning("Keep moving to reach today's goal!")

    st.markdown("---")

    st.subheader("📖 What These Metrics Mean")

    with st.expander("❤️ Heart Rate"):
        st.write(
            "Your heart rate is the number of times your heart beats each minute."
        )

    with st.expander("💓 Resting Heart Rate"):
        st.write(
            "This is your heart rate while you are resting. Tracking changes over time can be useful."
        )

    with st.expander("📊 Heart Rate Variability (HRV)"):
        st.write(
            "HRV measures the variation in time between heartbeats. It can provide information about recovery and overall wellness."
        )

    with st.expander("🩺 Blood Pressure Variability"):
        st.write(
            "Some wearable devices estimate changes in blood pressure. Availability depends on your smartwatch."
        )

    with st.expander("🏃 Heart Rate Recovery"):
        st.write(
            "Heart rate recovery measures how quickly your heart rate decreases after exercise."
        )

    with st.expander("😴 Sleep Quality"):
        st.write(
            "Sleep quality summarizes how well you slept based on information from your wearable device."
        )

    st.info(
        "These values are educational examples for the Sprint 1 prototype and should not be used to diagnose medical conditions."
    )
    # --------------------------------------------------
# SMARTWATCH CONNECTION PAGE
# --------------------------------------------------

elif page == "⌚ Smartwatch":

    st.title("⌚ Smartwatch Connection")

    st.write(
        "Connect your smartwatch to automatically sync your heart-health information."
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:

        if watch_connected:
            st.success("🟢 Connected")
        else:
            st.error("🔴 Not Connected")

        st.metric("Battery", f"{battery}%")
        st.metric("Last Sync", last_sync)

        st.button("🔄 Sync Now")

    with col2:

        st.subheader("Supported Devices")

        st.write("✅ Apple Watch")
        st.write("✅ Fitbit")
        st.write("✅ Garmin")
        st.write("✅ Samsung Galaxy Watch")
        st.write("✅ Google Pixel Watch")

        st.info(
            "Sprint 1 uses simulated smartwatch data. Future versions will connect to real wearable devices."
        )

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

    st.warning(
        "A real smartwatch connection will be added in a future sprint using the manufacturer's API."
    )

# --------------------------------------------------
# HEALTH SUMMARY PAGE
# --------------------------------------------------

elif page == "📈 Health Summary":

    st.title("📈 Daily Health Summary")

    st.success("Here is today's overall health summary.")

    st.markdown("---")

    score, positives, concerns = generate_health_summary()

    st.metric("❤️ Heart Health Score", f"{score}/100")
    st.progress(score / 100)

    st.markdown("---")

    st.subheader("🧠 PulseGuard Health Insights")

    if score >= 90:
        st.success("Overall, your heart health data looks very good today.")
    elif score >= 75:
        st.info("Your heart health looks good, but there are a few things to monitor.")
    else:
        st.warning("Some measurements deserve extra attention. Continue monitoring your trends.")

    if positives:
        st.write("### ✅ What's Going Well")
        for item in positives:
            st.write(f"• {item}")

    if concerns:
        st.write("### ⚠ Areas to Watch")
        for item in concerns:
            st.write(f"• {item}")

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

    if sleep_quality >= 80:
        st.success("😴 Excellent sleep recorded.")

    if steps >= 7500:
        st.success("👟 Great job staying active!")

    if 60 <= heart_rate <= 100:
        st.success("❤️ Heart rate is within the expected resting range.")

    if hrv >= 50:
        st.success("📊 Heart Rate Variability looks good.")

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

        for alert in alerts:
            st.write("• " + alert)

    st.caption(
        "This feature is an educational prototype and does not provide a medical diagnosis. "
        "If you have concerning symptoms, seek advice from a qualified healthcare professional."
    )

    st.markdown("---")

    st.download_button(
        "📄 Download Health Report",
        data=f"""
PulseGuard Daily Report

Heart Rate: {heart_rate} BPM
Resting Heart Rate: {resting_hr} BPM
Heart Rate Variability: {hrv} ms
Blood Pressure Variability: {blood_pressure_variability} mmHg
Heart Rate Recovery: {heart_rate_recovery} BPM
Sleep Quality: {sleep_quality}%
Daily Steps: {steps}
Overall Score: {score}/100
""",
        file_name="PulseGuard_Report.txt"
    )

    st.caption(
        "This report is for educational purposes and is not intended to replace professional medical advice."
    )# --------------------------------------------------
# ACCURACY TIPS PAGE
# --------------------------------------------------

elif page == "💡 Accuracy Tips":

    st.title("💡 Accuracy Tips")

    st.write(
        "Follow these tips to help your smartwatch collect the most reliable heart-health information."
    )

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

    st.error(
        "If you think you are experiencing a medical emergency, call your local emergency services immediately."
    )

# --------------------------------------------------
# ABOUT PAGE
# --------------------------------------------------

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
