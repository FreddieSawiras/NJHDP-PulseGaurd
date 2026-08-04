# ❤️ PulseGuard

**Your heart's personal hype squad, anomaly detective, and occasional nag — all in one Streamlit app.**

PulseGuard watches your vitals, learns what's *normal for you specifically*, renders your heart in actual 3D, reads your pulse off your webcam, and — when something looks off — doesn't wait around for you to check. It comes and finds you.

This isn't a "log your steps" app. This is the app that texts (okay, emails) you like a worried friend.

---

## 🩺 What This Thing Actually Does

### 🏠 Home — Your Vital Score at a Glance
The first thing you see is a single number: your **Vital Score (0–100)**, computed from resting heart rate, HRV, sleep quality, steps, heart rate recovery, and blood pressure variability. Color-coded, glowing, impossible to ignore. Below it, Quick Actions let you simulate new readings, jump straight to your doctor report, ping the AI, or pull up the 3D heart.

### ❤️ Heart Dashboard — Three Ways to Look at One Heart
A segmented pill-toggle (that actually *lights up* when selected, thank you very much) switches between:
- **📊 VITALS** — the raw numbers, sliders and all
- **🫀 3D MODEL** — a real, rotating, rendered heart built in **Three.js**, right inside the browser
- **💓 ECG WAVEFORM** — a live animated waveform that reacts to your current heart rate

### ⌚ Smartwatch — Or Just Use Your Face
Simulates syncing with Apple HealthKit, WHOOP, Oura, Garmin, Google Fit... or, if you don't have a wearable at all, **scan your pulse with your webcam.** This uses remote photoplethysmography (rPPG) — detecting the microscopic color shifts in your skin caused by blood flow, frame by frame, and turning that into a real BPM reading. No hardware required. Just your face and some decent lighting.

### 🩺 Symptom Check-In — "More Accurate Details"
Numbers don't always tell the whole story. Hit **"More Accurate Details"** and PulseGuard asks what you're actually feeling — chest pain, dizziness, palpitations, fatigue, whatever's going on — plus a free-text box for anything else. That gets sent, along with your live telemetry, straight to **Gemini**, which decides how much (if any) to adjust your Vital Score downward, and explains its reasoning in plain language. It never inflates your score based on self-report — only ever pulls it toward caution.

### 📈 Health Summary — The Report Your Doctor Actually Wants
A full breakdown of positives, concerns, and a doctor recommendation tier based on your score, exportable as a clean **PDF report** (built with FPDF) you can hand to an actual physician.

### 🤖 AI Assistant — Powered by Gemini
A chat interface that has full context on your current vitals and can answer questions about what's going on with your data — not a generic chatbot, an assistant that actually knows your numbers.

### 🧠 AI Insights — Your Weekly Story
Click **"Generate My Weekly Story"** and Gemini writes a narrative recap of your week — like a health-focused Spotify Wrapped, minus the smugness.

### 📧 Proactive Alerts — The App That Reaches Out First
This is the real party trick. PulseGuard doesn't wait for you to open it and check on yourself.

- It builds a **personal baseline** from your rolling history (using z-scores, not generic "normal ranges" — because *your* normal isn't the population's normal).
- Every time the app runs, it silently checks your latest readings against that baseline.
- If something's a real outlier, it **emails you** — automatically, throttled to once a day so it doesn't spam you into ignoring it.
- No wearable-company subscription. No Twilio compliance paperwork. Just plain SMTP email, running quietly in the background of every page load.

> ⚠️ **Honest limitation:** since this runs inside Streamlit's request/response model, it only checks in when the app itself is actively running — it's not a 24/7 background watcher. A true "always-on, even with the app closed" version would need a small scheduled job (cron / cloud function) calling the same detection logic on a timer.

### 🔐 Login & Signup — Real Accounts, Not Just Session State
Username/password auth backed by a **Google Sheet** acting as your user database — passwords hashed, never stored in plaintext. Each user's full app state (telemetry, symptom history, alert preferences, everything) persists across sessions and logins as a saved JSON blob, so nobody loses their data when they close the tab.

### ℹ️ About
The mission statement page. You know the one.

---

## 🧰 Tech Stack

| Layer | What's Used |
|---|---|
| App framework | Streamlit |
| 3D rendering | Three.js (r128) |
| Charts | Plotly |
| AI / reasoning | Google Gemini (`google-genai`) |
| Auth & data storage | Google Sheets via `gspread` |
| PDF reports | `fpdf` |
| Image handling | Pillow |
| Email alerts | Python `smtplib` (Gmail SMTP) |
| Camera pulse detection | Browser `getUserMedia` + canvas frame analysis (rPPG) |

---

## ⚙️ Setup — Secrets You'll Need

Add these to your `.streamlit/secrets.toml` (or the Secrets panel if you're on Streamlit Community Cloud):

```toml
# Gemini — powers the AI Assistant, Weekly Story, and Symptom Check-In
GEMINI_API_KEY = "your_gemini_api_key"
# Optional override, defaults to gemini-3.6-flash
GEMINI_MODEL = "gemini-3.6-flash"

# Google Sheets — user accounts + persisted app data
# Create a Google Cloud service account, share your "PulseGuard_Users"
# sheet with its email, and paste the full JSON key below as a table:
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key = "..."
client_email = "..."
# ...(the rest of the standard service account JSON fields)

# Email alerts — plain Gmail SMTP, no third-party account needed
# 1. Turn on 2-Step Verification: myaccount.google.com/security
# 2. Create an App Password: myaccount.google.com/apppasswords
ALERT_EMAIL_ADDRESS = "youraccount@gmail.com"
ALERT_EMAIL_APP_PASSWORD = "your_16_char_app_password"
```

Then:

```bash
pip install streamlit pandas numpy plotly fpdf2 pillow gspread google-auth google-genai
streamlit run app.py
```

Restart (not just save) the app after adding or changing secrets — Streamlit reads `secrets.toml` once at startup.

---

## 🗺️ Where Things Live (for Future You)

- `render_login_gate()` — the whole auth screen, styled independently since it runs *before* the main theme's CSS block loads
- `generate_health_summary()` — the scoring engine; takes `apply_symptom_adjustment=True/False` so historical trend data never gets skewed by *today's* symptom check-in
- `get_symptom_risk_assessment()` — the Gemini call behind "More Accurate Details"
- `detect_anomalies()` / `get_anomaly_alert_message()` — the personal-baseline anomaly logic behind proactive alerts
- `send_sms_alert()` — historically named, now sends email via SMTP (renamed the transport, not the function, for continuity)
- `PERSIST_KEYS` — the list of session_state keys that get saved to/restored from each user's Google Sheets data blob

---

## 🚧 Where This Could Go Next

- A scheduled job (cron / cloud function) for true always-on anomaly watching, independent of anyone having the app open
- Multi-user family view — monitor a linked account (e.g. an aging parent) from your own login
- Correlation engine surfacing patterns across your own metrics ("your score drops on days you sleep under 6 hours")
- Shareable, expiring doctor-report links instead of a raw PDF download

---

*Built with equal parts Streamlit, caffeine, and mild concern for everyone's cardiovascular health.*
