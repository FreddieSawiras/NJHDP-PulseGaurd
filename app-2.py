import streamlit as st

# Set up the app title, page layout, and simple brand colors.
st.set_page_config(
    page_title="PulseGuard",
    page_icon="❤️",
    layout="wide"
)

st.markdown("""
<style>
    .main-title {
        font-size: 42px;
        font-weight: 700;
        color: #c62828;
        margin-bottom: 0;
    }
    .subtitle {
        color: #555555;
        font-size: 18px;
        margin-top: 0;
    }
    .metric-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #dddddd;
        background-color: #ffffff;
        text-align: center;
        margin-bottom: 12px;
    }
    .metric-name {
        font-size: 16px;
        color: #555555;
    }
    .metric-value {
        font-size: 30px;
        font-weight: 700;
        color: #1b5e20;
    }
</style>
""", unsafe_allow_html=True)

# Show the PulseGuard header and explain what Sprint 1 does.
st.markdown('<div class="main-title">❤️ PulseGuard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Simple heart-health monitoring for everyday prevention.</div>',
    unsafe_allow_html=True
)

st.info(
    "Sprint 1 prototype: This screen shows heart-health data in an easy-to-read format. "
    "A real smartwatch connection will provide the live values after the appropriate device "
    "integration is added."
)

# Create the navigation menu for the main parts of the app.
page = st.sidebar.radio(
    "Navigate",
    ["Heart Dashboard", "Accuracy Tips", "About PulseGuard"]
)

# Show the main heart-health dashboard.
if page == "Heart Dashboard":
    st.header("Heart Health Dashboard")

    # Let the team test the dashboard with simple sample values.
    st.subheader("Connected Watch Data")

    st.caption(
        "Prototype values are entered below so the team can test the interface. "
        "They are not a medical diagnosis."
    )

    heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, max_value=250, value=72)
    resting_rate = st.number_input("Resting Heart Rate (BPM)", min_value=0, max_value=200, value=62)
    hrv = st.number_input("Heart Rate Variability (ms)", min_value=0, max_value=500, value=55)
    bp_variability = st.number_input(
        "Blood Pressure Variability (mmHg)",
        min_value=0,
        max_value=100,
        value=5
    )
    recovery = st.number_input(
        "Heart Rate Recovery (BPM)",
        min_value=0,
        max_value=100,
        value=25
    )
    sleep = st.number_input("Sleep Quality (%)", min_value=0, max_value=100, value=85)
    steps = st.number_input("Daily Steps", min_value=0, max_value=100000, value=6500)

    # Display the collected metrics in easy-to-read cards.
    st.subheader("Today's Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">Heart Rate</div>'
            f'<div class="metric-value">{heart_rate} BPM</div></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">Resting Heart Rate</div>'
            f'<div class="metric-value">{resting_rate} BPM</div></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">HRV</div>'
            f'<div class="metric-value">{hrv} ms</div></div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">Blood Pressure Variability</div>'
            f'<div class="metric-value">{bp_variability} mmHg</div></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">Heart Rate Recovery</div>'
            f'<div class="metric-value">{recovery} BPM</div></div>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">Sleep Quality</div>'
            f'<div class="metric-value">{sleep}%</div></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="metric-card"><div class="metric-name">Daily Steps</div>'
            f'<div class="metric-value">{steps:,}</div></div>',
            unsafe_allow_html=True
        )

    # Give a simple status message without pretending the app can diagnose disease.
    st.subheader("Data Status")

    if heart_rate == 0:
        st.warning("No heart-rate data has been entered.")
    else:
        st.success("Heart-health data is available for this prototype.")

    st.caption(
        "Important: PulseGuard is a monitoring prototype, not a medical device or diagnosis tool. "
        "If someone has concerning or emergency symptoms, they should seek appropriate medical care."
    )

# Show tips for getting more reliable smartwatch measurements.
elif page == "Accuracy Tips":
    st.header("⌚ Accuracy Tips")

    st.write("For better smartwatch readings:")

    st.markdown("""
    - Wear the watch securely and according to the manufacturer's instructions.
    - Keep the watch sensor clean.
    - Make sure the watch has enough battery.
    - Keep the watch positioned consistently on your wrist.
    - Avoid entering estimated values when actual measurements are available.
    - Give the watch enough time to collect data before judging a trend.
    - Look at trends over time instead of relying on one measurement.
    - Remember that smartwatch measurements can have limitations and may not replace clinical testing.
    """)

    st.warning(
        "Do not use PulseGuard as the only way to decide whether a medical emergency is happening."
    )

# Explain the purpose of PulseGuard and the Sprint 1 prototype.
elif page == "About PulseGuard":
    st.header("About PulseGuard")

    st.write(
        "PulseGuard is being developed by New Jersey Heart Disease Prevention (NJHDP) "
        "to make preventive heart-health monitoring easier and more accessible."
    )

    st.subheader("Sprint 1 Goal")
    st.write(
        "Create a simple interface that can display important cardiovascular and activity "
        "metrics from a smartwatch."
    )

    st.subheader("Sprint 1 Metrics")
    st.markdown("""
    - ❤️ Heart rate
    - ❤️ Resting heart rate
    - 📊 Heart-rate variability (HRV)
    - 🩺 Blood-pressure variability
    - 🏃 Heart-rate recovery
    - 😴 Sleep quality
    - 👟 Daily step count
    """)

    st.subheader("Next Development Step")
    st.write(
        "The next step is replacing the prototype input boxes with a real smartwatch data "
        "connection. Streamlit by itself cannot directly connect to Apple Watch, Fitbit, "
        "or Garmin hardware, so that part will require the appropriate platform/API integration."
    )
