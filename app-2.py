import streamlit as st
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
# Fake smartwatch data
# (Later these values will come from a real smartwatch)
# --------------------------------------------------

heart_rate = 72
resting_hr = 61
hrv = 55
blood_pressure_variability = 5
heart_rate_recovery = 27
sleep_quality = 86
steps = 6840

watch_connected = True
battery = 87
last_sync = datetime.now().strftime("%I:%M %p")

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

    score = 92

    st.metric("Overall Heart Health Score", f"{score}/100")

    st.progress(score/100)

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
