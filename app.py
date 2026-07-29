import streamlit as st
import base64
import os

# Set page configuration to wide mode
st.set_page_config(
    page_title="AquaPure", 
    page_icon="💧", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS to remove Streamlit padding, header, footer, and fix page scrolling ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
        }
        
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
            background-color: #030712;
        }

        iframe { display: block; border: none; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# Function to read and convert local logo to Base64
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    return ""

logo_base64 = get_image_base64("logo.png")

# Combined HTML, CSS, Three.js, Chart.js, and Tailwind CSS code
html_code = f"""
<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AquaPure — Pure Water. Shared Hope.</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

  <script src="https://cdn.tailwindcss.com"></script>
  
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      padding: 0;
      width: 100%;
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: #030712;
      color: #f3f4f6;
      overflow-x: hidden;
    }}

    /* ANIMATED CUSTOM WATER SCROLLBAR */
    ::-webkit-scrollbar {{
      width: 12px;
    }}

    ::-webkit-scrollbar-track {{
      background: #030712;
      border-left: 1px solid rgba(255, 255, 255, 0.05);
    }}

    ::-webkit-scrollbar-thumb {{
      background: linear-gradient(180deg, #06b6d4, #38bdf8, #2563eb, #06b6d4);
      background-size: 100% 300%;
      border-radius: 20px;
      border: 2px solid #030712;
      box-shadow: 0 0 12px rgba(6, 182, 212, 0.5);
      animation: animatedScrollbar 6s ease-in-out infinite;
    }}

    ::-webkit-scrollbar-thumb:hover {{
      background: linear-gradient(180deg, #22d3ee, #0284c7, #38bdf8, #22d3ee);
      background-size: 100% 300%;
      box-shadow: 0 0 18px rgba(34, 211, 238, 0.85);
    }}

    @keyframes animatedScrollbar {{
      0% {{ background-position: 0% 0%; }}
      50% {{ background-position: 0% 100%; }}
      100% {{ background-position: 0% 0%; }}
    }}

    .bg-mesh {{
      position: relative;
      background: #030712;
      overflow: hidden;
    }}

    /* Animated Ambient Water Orbs */
    .orb {{
      position: absolute;
      width: 650px;
      height: 650px;
      border-radius: 50%;
      filter: blur(140px);
      z-index: 0;
      opacity: 0.16;
      animation: OrbFloat 22s infinite ease-in-out;
    }}
    .orb-1 {{ background: #0ea5e9; top: -10%; left: -10%; }}
    .orb-2 {{ background: #06b6d4; bottom: 10%; right: -5%; animation-delay: -6s; }}

    @keyframes OrbFloat {{
      0%, 100% {{ transform: translate(0, 0) scale(1); }}
      50% {{ transform: translate(60px, 90px) scale(1.12); }}
    }}

    /* Glassmorphism Cards */
    .glass-card {{
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(25px);
      -webkit-backdrop-filter: blur(25px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .glass-card:hover {{
      border-color: rgba(56, 189, 248, 0.4);
      transform: translateY(-5px);
      box-shadow: 0 20px 40px -15px rgba(14, 165, 233, 0.25);
    }}

    .glass-nav {{
      background: rgba(3, 7, 18, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }}

    .nav-btn.active {{
      color: #38bdf8;
      border-bottom: 2px solid #38bdf8;
    }}

    .canvas-glow::after {{
      content: '';
      position: absolute;
      bottom: -15px;
      left: 15%;
      right: 15%;
      height: 15px;
      background: radial-gradient(ellipse at center, rgba(56, 189, 248, 0.25) 0%, transparent 70%);
      pointer-events: none;
    }}

    #particles-canvas {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1;
    }}
  </style>
</head>

<body class="bg-mesh min-h-screen relative pb-12">
  <canvas id="particles-canvas"></canvas>
  
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>

  <header class="fixed top-0 left-0 right-0 z-50 glass-nav border-b border-white/10 shadow-2xl">
    <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
      
      <a href="#" onclick="switchTab('tab-all')" class="flex items-center gap-4 group">
        <div class="p-2 rounded-2xl bg-white/5 border border-white/10 group-hover:border-cyan-500/50 transition-all duration-300 shadow-md">
          <img src="{logo_base64}" alt="AquaPure Logo" class="h-14 md:h-16 w-auto object-contain transition-transform duration-300 group-hover:scale-105" />
        </div>
        <div class="flex flex-col">
          <span class="text-2xl md:text-3xl font-extrabold tracking-wider bg-gradient-to-r from-white via-slate-200 to-cyan-400 bg-clip-text text-transparent">
            AQUAPURE
          </span>
          <span class="text-[10px] md:text-xs font-semibold tracking-widest text-cyan-400/90 uppercase mt-0.5">
            Pure Water. Shared Hope.
          </span>
        </div>
      </a>

      <nav class="hidden lg:flex items-center gap-6 text-xs font-bold uppercase tracking-widest text-slate-300">
        <button id="nav-all" onclick="switchTab('tab-all')" class="nav-btn active hover:text-cyan-400 transition-colors py-2">Overview</button>
        <button id="nav-mission" onclick="switchTab('tab-mission')" class="nav-btn hover:text-cyan-400 transition-colors py-2">Mission</button>
        <button id="nav-pfd" onclick="switchTab('tab-pfd')" class="nav-btn hover:text-cyan-400 transition-colors py-2">CAD 3D PFD</button>
        <button id="nav-data" onclick="switchTab('tab-data')" class="nav-btn hover:text-cyan-400 transition-colors py-2"><i class="fa-solid fa-chart-line text-cyan-400 mr-1"></i> Data & Analytics</button>
        <button id="nav-impact" onclick="switchTab('tab-impact')" class="nav-btn hover:text-cyan-400 transition-colors py-2">Global Impact</button>
        <button id="nav-involved" onclick="switchTab('tab-involved')" class="nav-btn hover:text-cyan-400 transition-colors py-2">Get Involved</button>
      </nav>

      <button onclick="switchTab('tab-involved')" class="px-6 py-3 rounded-full text-xs font-bold uppercase tracking-wider bg-cyan-500 text-black hover:bg-cyan-400 transition-all duration-300 shadow-lg shadow-cyan-500/25 active:scale-95">
        Join Us
      </button>
    </div>
  </header>

  <section class="relative z-10 max-w-7xl mx-auto px-6 pt-48 pb-12 text-center">
    <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-semibold uppercase tracking-widest mb-8">
      <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
      Industrial CAD Architecture Integrated
    </div>

    <h1 class="text-4xl md:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-tight max-w-5xl mx-auto mb-6">
      Transforming Contaminated Water Into <span class="bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500 bg-clip-text text-transparent">Safe Drinkable Hope.</span>
    </h1>

    <p class="text-slate-400 text-base md:text-lg max-w-2xl mx-auto font-normal leading-relaxed mb-10">
      Empowering off-grid communities with gravity-fed, multi-cartridge stainless & polymer filtration housings engineered for infinite continuous use.
    </p>

    <div class="flex flex-wrap items-center justify-center gap-3 bg-white/5 p-2 rounded-full border border-white/10 max-w-3xl mx-auto mb-8">
      <button onclick="switchTab('tab-mission')" class="px-5 py-2 rounded-full text-xs font-semibold text-slate-300 hover:bg-cyan-500/20 hover:text-cyan-300 transition-all">
        <i class="fa-solid fa-earth-americas mr-1"></i> Mission
      </button>
      <button onclick="switchTab('tab-pfd')" class="px-5 py-2 rounded-full text-xs font-semibold text-cyan-400 hover:bg-cyan-500/20 transition-all">
        <i class="fa-solid fa-cube mr-1"></i> CAD 3D Assembly
      </button>
      <button onclick="switchTab('tab-data')" class="px-5 py-2 rounded-full text-xs font-semibold text-slate-300 hover:bg-cyan-500/20 hover:text-cyan-300 transition-all">
        <i class="fa-solid fa-chart-pie mr-1"></i> Metrics & Data
      </button>
      <button onclick="switchTab('tab-impact')" class="px-5 py-2 rounded-full text-xs font-semibold text-slate-300 hover:bg-cyan-500/20 hover:text-cyan-300 transition-all">
        <i class="fa-solid fa-globe mr-1"></i> Global Deployments
      </button>
    </div>
  </section>

  <main id="tab-container" class="relative z-10 max-w-7xl mx-auto px-6 pt-4 pb-32 mb-16 space-y-16">

    <div id="tab-mission-content" class="tab-pane space-y-8">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="glass-card p-8 rounded-3xl relative overflow-hidden group">
          <div class="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-6 group-hover:scale-110 transition-transform">
            <i class="fa-solid fa-earth-americas text-xl"></i>
          </div>
          <h3 class="text-2xl font-bold text-white mb-3">Our Core Mission</h3>
          <p class="text-slate-400 leading-relaxed text-sm md:text-base">
            Over <strong class="text-white">2.2 billion people</strong> lack access to safe drinking water. Our industrial CAD-driven filtration housings operate off pure hydrostatic pressure, eliminating electric pumps and expensive chemical replacements.
          </p>
        </div>

        <div class="glass-card p-8 rounded-3xl relative overflow-hidden group">
          <div class="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-6 group-hover:scale-110 transition-transform">
            <i class="fa-solid fa-gears text-xl"></i>
          </div>
          <h3 class="text-2xl font-bold text-white mb-3">Precision CAD Architecture</h3>
          <p class="text-slate-400 leading-relaxed text-sm md:text-base">
            Featuring top pressure relief valves, industrial bolted flange plates, side outlet sampling ports, and bottom sediment drain valves for quick field cleaning and maintenance.
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-2">
        <div class="glass-card p-6 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-cyan-400 mb-1">0 kWh</div>
          <div class="text-xs uppercase tracking-widest text-slate-400">Electricity Required</div>
        </div>
        <div class="glass-card p-6 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-cyan-400 mb-1">99.999%</div>
          <div class="text-xs uppercase tracking-widest text-slate-400">Pathogen Removal</div>
        </div>
        <div class="glass-card p-6 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-cyan-400 mb-1">15+ Yrs</div>
          <div class="text-xs uppercase tracking-widest text-slate-400">Chamber Operational Life</div>
        </div>
      </div>
    </div>

    <div id="tab-pfd-content" class="tab-pane space-y-8">
      
      <div class="glass-card p-8 rounded-3xl text-center border border-cyan-500/20 bg-gradient-to-b from-cyan-950/20 to-slate-950/50">
        <span class="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2 block">Industrial Engineering Design</span>
        <h2 class="text-3xl md:text-4xl font-extrabold text-white mb-4">Multi-Cartridge CAD Filtration Housing</h2>
        <p class="text-slate-400 max-w-3xl mx-auto text-sm md:text-base">
          Interactive 3D model reflecting our exact mechanical CAD blueprint—complete with pressure gauge, flange bolt rings, inlet/outlet piping, internal cartridge tubes, and support tripod stand.
        </p>
      </div>

      <div class="glass-card p-6 md:p-10 rounded-3xl border border-white/10 relative">
        <div class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <div class="flex items-center gap-2 text-cyan-400 font-semibold text-xs tracking-widest uppercase mb-1">
              <i class="fa-solid fa-cube"></i> Interactive CAD Assembly
            </div>
            <h2 class="text-2xl md:text-3xl font-bold text-white">Full Housing Mechanical Model</h2>
          </div>
          <p class="text-slate-400 text-xs md:text-sm max-w-sm">
            Click and drag to rotate, zoom, and inspect the internal multi-cartridge core, top gauge, and flange connections.
          </p>
        </div>

        <div id="pfd-container" class="canvas-glow w-full h-[520px] rounded-2xl bg-gray-950/90 border border-white/5 overflow-hidden cursor-grab active:cursor-grabbing relative"></div>

        <div class="flex items-center justify-between mt-4 text-xs text-slate-500 px-2">
          <span class="flex items-center gap-2"><i class="fa-solid fa-arrows-spin"></i> 360° Real-time Three.js CAD View</span>
          <span>AquaPure CAD Vessel v3.2</span>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <div class="glass-card p-8 rounded-3xl relative overflow-hidden group flex flex-col">
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-xl font-bold text-white">PFD Community Master</h4>
            <span class="text-3xl font-extrabold text-cyan-400">$34.99</span>
          </div>
          <p class="text-sm text-slate-400 mb-6 flex-grow">Full-scale multi-cartridge housing with pressure gauge & tripod base for village-scale distribution.</p>
          <ul class="text-xs text-slate-300 space-y-2 border-t border-white/10 pt-4">
            <li><i class="fa-solid fa-droplet text-cyan-400 mr-2"></i> Flow Rate: 1.5 Liters/min</li>
            <li><i class="fa-solid fa-gauge-high text-cyan-400 mr-2"></i> Top Pressure Relief Gauge</li>
            <li><i class="fa-solid fa-gears text-cyan-400 mr-2"></i> Bolted Flange Housing</li>
            <li><i class="fa-solid fa-layer-group text-cyan-400 mr-2"></i> 5 Multi-Cartridge Array</li>
          </ul>
        </div>

        <div class="glass-card p-8 rounded-3xl relative overflow-hidden group flex flex-col border-t-2 border-cyan-500">
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-xl font-bold text-white">PFD Family Core</h4>
            <span class="text-3xl font-extrabold text-cyan-400">$24.99</span>
          </div>
          <p class="text-sm text-slate-400 mb-6 flex-grow">Compact multi-tube vessel designed for high reliability in household environments.</p>
          <ul class="text-xs text-slate-300 space-y-2 border-t border-white/10 pt-4">
            <li><i class="fa-solid fa-droplet text-cyan-400 mr-2"></i> Flow Rate: 1.0 Liters/min</li>
            <li><i class="fa-solid fa-shield-halved text-cyan-400 mr-2"></i> Removal Rate: 99.99%</li>
            <li><i class="fa-solid fa-hourglass text-cyan-400 mr-2"></i> Life Expectancy: 10 Years</li>
            <li><i class="fa-solid fa-layer-group text-cyan-400 mr-2"></i> 3 Multi-Cartridge Array</li>
          </ul>
        </div>

        <div class="glass-card p-8 rounded-3xl relative overflow-hidden group flex flex-col">
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-xl font-bold text-white">PFD Nomad Ultra</h4>
            <span class="text-3xl font-extrabold text-cyan-400">$14.99</span>
          </div>
          <p class="text-sm text-slate-400 mb-6 flex-grow">Lightweight portable unit for rapid emergency response and personal field use.</p>
          <ul class="text-xs text-slate-300 space-y-2 border-t border-white/10 pt-4">
            <li><i class="fa-solid fa-droplet text-cyan-400 mr-2"></i> Flow Rate: 0.6 Liters/min</li>
            <li><i class="fa-solid fa-shield-halved text-cyan-400 mr-2"></i> Removal Rate: 99.9%</li>
            <li><i class="fa-solid fa-suitcase text-cyan-400 mr-2"></i> Rapid Relief Deployment</li>
            <li><i class="fa-solid fa-layer-group text-cyan-400 mr-2"></i> Single Core Cartridge</li>
          </ul>
        </div>
      </div>
    </div>

    <div id="tab-data-content" class="tab-pane space-y-8">
      <div class="glass-card p-8 rounded-3xl text-center border border-cyan-500/20 bg-gradient-to-b from-cyan-950/20 to-slate-950/50">
        <span class="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2 block"><i class="fa-solid fa-chart-line mr-1"></i> Empirical Data & Field Performance</span>
        <h2 class="text-3xl md:text-4xl font-extrabold text-white mb-4">Quantitative System Metrics</h2>
        <p class="text-slate-400 max-w-3xl mx-auto text-sm md:text-base">
          Power demand comparisons, volumetric flow rates, cost allocations per capita, and target regional population numbers.
        </p>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-cyan-400">
          <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Energy Demand</div>
          <div class="text-2xl font-extrabold text-cyan-300">0 kWh</div>
          <div class="text-[11px] text-slate-500 mt-1">Hydrostatic Gravity Driven</div>
        </div>

        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-cyan-400">
          <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Peak Flow Output</div>
          <div class="text-2xl font-extrabold text-cyan-300">1.5 L/min</div>
          <div class="text-[11px] text-slate-500 mt-1">90 Liters / Hour</div>
        </div>

        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-cyan-400">
          <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Starting Price</div>
          <div class="text-2xl font-extrabold text-cyan-300">$14.99</div>
          <div class="text-[11px] text-slate-500 mt-1">Subsidized NGO Direct</div>
        </div>

        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-cyan-400">
          <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Population Reach</div>
          <div class="text-2xl font-extrabold text-cyan-300">2.2 Billion</div>
          <div class="text-[11px] text-slate-500 mt-1">Target Off-Grid Demographic</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="glass-card p-6 md:p-8 rounded-3xl">
          <h3 class="text-lg font-bold text-white mb-2">Power Consumption vs Alternatives</h3>
          <p class="text-xs text-slate-400 mb-6">kWh required per 1,000 Liters of purified water</p>
          <div class="h-[280px] w-full">
            <canvas id="chartElectricity"></canvas>
          </div>
        </div>

        <div class="glass-card p-6 md:p-8 rounded-3xl">
          <h3 class="text-lg font-bold text-white mb-2">Model Pricing vs Flow Rate</h3>
          <p class="text-xs text-slate-400 mb-6">Flow capacity (L/min) across production models</p>
          <div class="h-[280px] w-full">
            <canvas id="chartPriceFlow"></canvas>
          </div>
        </div>
      </div>
    </div>

    <div id="tab-impact-content" class="tab-pane space-y-8">
      <div class="glass-card p-6 md:p-10 rounded-3xl border border-white/10 relative">
        <div class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <div class="flex items-center gap-2 text-cyan-400 font-semibold text-xs tracking-widest uppercase mb-1">
              <i class="fa-solid fa-globe"></i> Active Deployment Zones & Global Supply Network
            </div>
            <h2 class="text-2xl md:text-3xl font-bold text-white">Target Regions & Water Flow Lines</h2>
          </div>
          <p class="text-slate-400 text-xs md:text-sm max-w-sm">
            Click on any pulsing glowing marker to view site status, local daily flow rates, and deployment metrics.
          </p>
        </div>

        <div id="globe-container" class="canvas-glow w-full h-[560px] rounded-2xl bg-gray-950/90 border border-white/5 overflow-hidden cursor-grab active:cursor-grabbing relative">
          
          <div id="globe-popup" class="hidden absolute top-6 right-6 z-30 max-w-sm w-full bg-slate-900/90 backdrop-blur-2xl border border-cyan-500/40 p-6 rounded-2xl shadow-2xl transition-all duration-300">
            <div class="flex items-center justify-between mb-3 border-b border-white/10 pb-3">
              <div class="flex items-center gap-2">
                <span id="popup-type" class="px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px] font-bold uppercase tracking-wider border border-cyan-500/30">Hub</span>
                <h3 id="popup-title" class="text-lg font-bold text-white">Region Name</h3>
              </div>
              <button onclick="closeGlobePopup()" class="text-slate-400 hover:text-white text-sm"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <p id="popup-desc" class="text-xs text-slate-300 mb-4 leading-relaxed">Location summary and details go here.</p>
            <div class="grid grid-cols-2 gap-3 text-xs mb-4">
              <div class="bg-white/5 p-2.5 rounded-xl border border-white/5">
                <span class="text-[10px] uppercase text-slate-400 block mb-0.5">Active Units</span>
                <span id="popup-units" class="text-base font-extrabold text-cyan-400">0</span>
              </div>
              <div class="bg-white/5 p-2.5 rounded-xl border border-white/5">
                <span class="text-[10px] uppercase text-slate-400 block mb-0.5">Daily Capacity</span>
                <span id="popup-capacity" class="text-base font-extrabold text-cyan-400">0 L</span>
              </div>
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-white/10">
              <span>Status: <strong id="popup-status" class="text-emerald-400">Operational</strong></span>
              <span id="popup-coordinates" class="font-mono text-slate-500">0° N, 0° E</span>
            </div>
          </div>

        </div>
      </div>
    </div>

    <div id="tab-involved-content" class="tab-pane space-y-8 pb-12">
      <div class="glass-card p-8 md:p-12 rounded-3xl text-center border border-cyan-500/20 bg-gradient-to-b from-cyan-950/20 to-slate-950/50">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 text-cyan-400 text-2xl mb-6 border border-cyan-500/30">
          <i class="fa-solid fa-hand-holding-droplet"></i>
        </div>
        <h2 class="text-3xl md:text-4xl font-extrabold text-white mb-4">Partner With AquaPure</h2>
        <p class="text-slate-400 max-w-2xl mx-auto mb-8 text-sm md:text-base">
          Join forces with our engineering team, humanitarian organizations, and local field managers to deploy CAD-tested water units globally.
        </p>
        <div class="flex flex-wrap items-center justify-center gap-4">
          <a href="mailto:contact@aquapure.org" class="px-8 py-4 rounded-full bg-cyan-500 text-black font-bold text-sm hover:bg-cyan-400 transition-all shadow-lg shadow-cyan-500/25 active:scale-95">
            <i class="fa-solid fa-envelope mr-2"></i> Contact Engineering Team
          </a>
        </div>
      </div>
    </div>

  </main>

  <footer class="border-t border-white/5 py-12 text-center text-xs text-slate-500 relative z-10">
    <div class="flex items-center justify-center gap-4 mb-4">
      <img src="{logo_base64}" alt="AquaPure" class="h-12 w-auto opacity-90" />
      <span class="font-bold text-slate-200 text-base tracking-widest">AQUAPURE</span>
    </div>
    <p>© 2026 AquaPure Engineering Team. Pure Water. Shared Hope.</p>
  </footer>

  <script>
    // Dynamic Height Reporting for Streamlit Iframe
    function sendHeightToParent() {{
      const height = document.documentElement.scrollHeight;
      window.parent.postMessage({{ frameHeight: height }}, '*');
    }}

    const resizeObserver = new ResizeObserver(() => sendHeightToParent());
    resizeObserver.observe(document.body);

    // --- BACKGROUND PARTICLE CANVAS ENGINE ---
    const canvas = document.getElementById('particles-canvas');
    const ctx = canvas.getContext('2d');
    let particles = [];

    function initParticles() {{
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      particles = [];
      for(let i = 0; i < 45; i++) {{
        particles.push({{
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 2 + 1,
          speed: Math.random() * 0.4 + 0.15,
          opacity: Math.random() * 0.35 + 0.05
        }});
      }}
    }}

    function drawParticles() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {{
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56, 189, 248, ${{p.opacity}})`;
        ctx.fill();
        p.y -= p.speed;
        if(p.y < -10) p.y = canvas.height + 10;
      }});
      requestAnimationFrame(drawParticles);
    }}

    initParticles();
    drawParticles();

    // --- TAB SWITCHING SYSTEM ---
    function switchTab(tabId) {{
      const tabs = ['tab-mission', 'tab-pfd', 'tab-data', 'tab-impact', 'tab-involved'];
      
      if (tabId === 'tab-all') {{
        tabs.forEach(id => {{
          document.getElementById(id + '-content').style.display = 'block';
        }});
      }} else {{
        tabs.forEach(id => {{
          const el = document.getElementById(id + '-content');
          if (id + '-content' === tabId + '-content') {{
            el.style.display = 'block';
          }} else {{
            el.style.display = 'none';
          }}
        }});
      }}

      const navBtns = {{
        'tab-all': 'nav-all',
        'tab-mission': 'nav-mission',
        'tab-pfd': 'nav-pfd',
        'tab-data': 'nav-data',
        'tab-impact': 'nav-impact',
        'tab-involved': 'nav-involved'
      }};

      Object.keys(navBtns).forEach(key => {{
        const btn = document.getElementById(navBtns[key]);
        if (btn) {{
          if (key === tabId) {{
            btn.classList.add('active');
          }} else {{
            btn.classList.remove('active');
          }}
        }}
      }});

      setTimeout(() => {{
        window.dispatchEvent(new Event('resize'));
        sendHeightToParent();
      }}, 120);
    }}

    switchTab('tab-all');

    // --- CHART.JS METRICS ---
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";

    new Chart(document.getElementById('chartElectricity').getContext('2d'), {{
      type: 'bar',
      data: {{
        labels: ['AquaPure CAD', 'UV Sanitizer', 'Reverse Osmosis', 'Electric Pump'],
        datasets: [{{
          label: 'Electricity (kWh / 1000L)',
          data: [0, 0.45, 2.2, 1.1],
          backgroundColor: ['#06b6d4', '#334155', '#334155', '#334155'],
          borderRadius: 8
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }} }}, x: {{ grid: {{ display: false }} }} }}
      }}
    }});

    new Chart(document.getElementById('chartPriceFlow').getContext('2d'), {{
      type: 'line',
      data: {{
        labels: ['Nomad Ultra ($14.99)', 'Family Core ($24.99)', 'Community Master ($34.99)'],
        datasets: [{{
          label: 'Flow Rate (L/min)',
          data: [0.6, 1.0, 1.5],
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.15)',
          fill: true,
          tension: 0.4,
          pointRadius: 6,
          pointBackgroundColor: '#06b6d4'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }} }}, x: {{ grid: {{ display: false }} }} }}
      }}
    }});

    // --- THREE.JS INDUSTRIAL CAD HOUSING MODEL ---
    const pfdContainer = document.getElementById('pfd-container');
    const pfdScene = new THREE.Scene();
    const pfdCamera = new THREE.PerspectiveCamera(45, pfdContainer.clientWidth / pfdContainer.clientHeight, 0.1, 1000);
    pfdCamera.position.set(0, 0.5, 7.5);

    const pfdRenderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
    pfdRenderer.setSize(pfdContainer.clientWidth, pfdContainer.clientHeight);
    pfdRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    pfdContainer.appendChild(pfdRenderer.domElement);

    const pfdControls = new THREE.OrbitControls(pfdCamera, pfdRenderer.domElement);
    pfdControls.enableDamping = true;
    pfdControls.dampingFactor = 0.05;
    pfdControls.autoRotate = true;
    pfdControls.autoRotateSpeed = 1.0;

    // Lighting Setup
    pfdScene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const mainDirLight = new THREE.DirectionalLight(0x38bdf8, 2.0);
    mainDirLight.position.set(6, 10, 8);
    pfdScene.add(mainDirLight);

    const backDirLight = new THREE.DirectionalLight(0x0284c7, 1.2);
    backDirLight.position.set(-6, -5, -6);
    pfdScene.add(backDirLight);

    const cadAssembly = new THREE.Group();

    // 1. Transparent Outer Cylinder Vessel
    const vesselGeo = new THREE.CylinderGeometry(1.35, 1.35, 3.0, 32);
    const vesselMat = new THREE.MeshPhysicalMaterial({{
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.22,
      roughness: 0.08,
      transmission: 0.88,
      thickness: 0.6,
      clearcoat: 1.0
    }});
    const outerVessel = new THREE.Mesh(vesselGeo, vesselMat);
    cadAssembly.add(outerVessel);

    // 2. Bolted Top Flange Head Plate & Bottom Flange Head
    const flangeRingGeo = new THREE.CylinderGeometry(1.55, 1.55, 0.18, 32);
    const steelMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, roughness: 0.25, metalness: 0.85 }});

    const topFlange = new THREE.Mesh(flangeRingGeo, steelMat);
    topFlange.position.y = 1.55;
    cadAssembly.add(topFlange);

    const bottomFlange = new THREE.Mesh(flangeRingGeo, steelMat);
    bottomFlange.position.y = -1.55;
    cadAssembly.add(bottomFlange);

    // Flange Bolts Array around perimeter
    const numBolts = 12;
    const boltGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.28, 12);
    const boltMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 }});

    for(let i = 0; i < numBolts; i++) {{
      const angle = (i / numBolts) * Math.PI * 2;
      const bx = Math.cos(angle) * 1.45;
      const bz = Math.sin(angle) * 1.45;

      const topBolt = new THREE.Mesh(boltGeo, boltMat);
      topBolt.position.set(bx, 1.55, bz);
      cadAssembly.add(topBolt);

      const bottomBolt = new THREE.Mesh(boltGeo, boltMat);
      bottomBolt.position.set(bx, -1.55, bz);
      cadAssembly.add(bottomBolt);
    }}

    // 3. Top Dome Cap & Bottom Conical Dish
    const domeGeo = new THREE.SphereGeometry(1.35, 32, 16, 0, Math.PI * 2, 0, Math.PI / 3);
    const topDome = new THREE.Mesh(domeGeo, steelMat);
    topDome.position.y = 1.64;
    cadAssembly.add(topDome);

    const coneGeo = new THREE.ConeGeometry(1.35, 0.6, 32);
    const bottomCone = new THREE.Mesh(coneGeo, steelMat);
    bottomCone.position.y = -1.85;
    bottomCone.rotation.x = Math.PI;
    cadAssembly.add(bottomCone);

    // 4. Pressure Relief Gauge on Top
    const gaugeStemGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.4, 16);
    const gaugeStem = new THREE.Mesh(gaugeStemGeo, steelMat);
    gaugeStem.position.y = 2.4;
    cadAssembly.add(gaugeStem);

    const gaugeBodyGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.12, 24);
    const gaugeFaceMat = new THREE.MeshStandardMaterial({{ color: 0xf8fafc, roughness: 0.1 }});
    const gaugeBody = new THREE.Mesh(gaugeBodyGeo, gaugeFaceMat);
    gaugeBody.position.y = 2.65;
    gaugeBody.rotation.x = Math.PI / 2;
    cadAssembly.add(gaugeBody);

    const gaugeBezelGeo = new THREE.TorusGeometry(0.3, 0.03, 16, 32);
    const gaugeBezel = new THREE.Mesh(gaugeBezelGeo, steelMat);
    gaugeBezel.position.set(0, 2.65, 0.06);
    cadAssembly.add(gaugeBezel);

    // 5. Inlet / Outlet Pipe Ports & Bottom Drain Valve
    const pipeGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.6, 20);
    const cyanPipeMat = new THREE.MeshStandardMaterial({{ color: 0x0284c7, metalness: 0.6, roughness: 0.3 }});

    const topInletPipe = new THREE.Mesh(pipeGeo, cyanPipeMat);
    topInletPipe.position.set(0, 2.1, 0);
    cadAssembly.add(topInletPipe);

    const sideOutletPipe = new THREE.Mesh(pipeGeo, cyanPipeMat);
    sideOutletPipe.position.set(1.5, -0.8, 0);
    sideOutletPipe.rotation.z = Math.PI / 2;
    cadAssembly.add(sideOutletPipe);

    const drainValveGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.5, 16);
    const drainValve = new THREE.Mesh(drainValveGeo, steelMat);
    drainValve.position.set(0, -2.35, 0);
    cadAssembly.add(drainValve);

    // 6. Internal Multi-Cartridge Array (5 Filter Tubes)
    const numTubes = 5;
    const tubeRadius = 0.26;
    const tubeHeight = 2.6;
    const arrayRadius = 0.65;

    const tubeGeo = new THREE.CylinderGeometry(tubeRadius, tubeRadius, tubeHeight, 24);
    const tubeMat = new THREE.MeshStandardMaterial({{ color: 0xf1f5f9, roughness: 0.5, metalness: 0.1 }});

    for(let i = 0; i < numTubes; i++) {{
      const angle = (i / numTubes) * Math.PI * 2;
      const tx = Math.cos(angle) * arrayRadius;
      const tz = Math.sin(angle) * arrayRadius;

      const filterTube = new THREE.Mesh(tubeGeo, tubeMat);
      filterTube.position.set(tx, 0, tz);

      // Top & Bottom Sealing Fittings
      const sealGeo = new THREE.CylinderGeometry(tubeRadius + 0.04, tubeRadius + 0.04, 0.14, 16);
      const sealMat = new THREE.MeshStandardMaterial({{ color: 0x06b6d4 }});

      const topSeal = new THREE.Mesh(sealGeo, sealMat);
      topSeal.position.set(tx, tubeHeight / 2, tz);

      const bottomSeal = new THREE.Mesh(sealGeo, sealMat);
      bottomSeal.position.set(tx, -tubeHeight / 2, tz);

      cadAssembly.add(filterTube);
      cadAssembly.add(topSeal);
      cadAssembly.add(bottomSeal);
    }}

    // 7. Structural Tripod Support Legs Frame
    const legGeo = new THREE.CylinderGeometry(0.06, 0.06, 2.2, 16);
    const numLegs = 3;

    for(let i = 0; i < numLegs; i++) {{
      const angle = (i / numLegs) * Math.PI * 2;
      const lx = Math.cos(angle) * 1.5;
      const lz = Math.sin(angle) * 1.5;

      const leg = new THREE.Mesh(legGeo, steelMat);
      leg.position.set(lx, -2.4, lz);
      leg.rotation.z = Math.cos(angle) * 0.22;
      leg.rotation.x = -Math.sin(angle) * 0.22;
      cadAssembly.add(leg);
    }}

    cadAssembly.position.y = 0.2;
    pfdScene.add(cadAssembly);

    // --- ENHANCED THREE.JS GLOBE ENGINE WITH SLOWER ROTATION & SLOWER PULSES ---
    const globeContainer = document.getElementById('globe-container');
    const globeScene = new THREE.Scene();
    const globeCamera = new THREE.PerspectiveCamera(45, globeContainer.clientWidth / globeContainer.clientHeight, 0.1, 1000);
    globeCamera.position.set(0, 0, 7.2);

    const globeRenderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
    globeRenderer.setSize(globeContainer.clientWidth, globeContainer.clientHeight);
    globeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    globeContainer.appendChild(globeRenderer.domElement);

    const globeControls = new THREE.OrbitControls(globeCamera, globeRenderer.domElement);
    globeControls.enableDamping = true;
    globeControls.dampingFactor = 0.05;
    globeControls.autoRotate = true;
    globeControls.autoRotateSpeed = 0.3; // SLOWER ROTATION SPEED

    globeScene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const globeDir = new THREE.DirectionalLight(0x38bdf8, 1.8);
    globeDir.position.set(5, 3, 5);
    globeScene.add(globeDir);

    const earthGroup = new THREE.Group();
    const globeRadius = 2.2;
    const textureLoader = new THREE.TextureLoader();
    const earthTexture = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_atmos_2048.jpg');

    const sphereGeo = new THREE.SphereGeometry(globeRadius, 64, 64);
    const sphereMat = new THREE.MeshPhongMaterial({{ map: earthTexture, shininess: 15, color: 0x0284c7, emissive: 0x021d38 }});
    const earthMesh = new THREE.Mesh(sphereGeo, sphereMat);
    earthGroup.add(earthMesh);

    // Locations Data Registry
    const locationData = [
      {{ id: 'hq', name: 'Engineering HQ (USA)', lat: 37.7749, lon: -122.4194, type: 'Manufacturing Hub', units: 1200, capacity: '1,800,000', desc: 'Primary R&D facility and automated CAD filtration housing manufacturing plant.', status: 'Active HQ' }},
      {{ id: 'sa', name: 'Amazon Basin (Brazil)', lat: -14.235, lon: -51.925, type: 'Field Zone', units: 340, capacity: '306,000', desc: 'Off-grid riverfront deployments operating without electricity in remote villages.', status: 'Operational' }},
      {{ id: 'wa', name: 'Lagos & Rural Grid (Nigeria)', lat: 9.082, lon: 8.675, type: 'Regional Hub', units: 620, capacity: '558,000', desc: 'Multi-cartridge Community Master filtration vessels supplying 42 local communities.', status: 'Operational' }},
      {{ id: 'ea', name: 'Rift Valley (Kenya)', lat: -1.292, lon: 36.821, type: 'Field Zone', units: 480, capacity: '432,000', desc: 'High-turbidity sediment filtration installations connected to surface water sources.', status: 'Operational' }},
      {{ id: 'sa_asia', name: 'Ganges Basin (India)', lat: 20.593, lon: 78.962, type: 'Regional Hub', units: 890, capacity: '801,000', desc: 'High-volume community clean water distribution network.', status: 'Operational' }},
      {{ id: 'se_asia', name: 'Mekong Delta (Vietnam)', lat: 10.823, lon: 106.629, type: 'Field Zone', units: 290, capacity: '261,000', desc: 'Heavy silt and pathogen removal units for riverland agricultural communities.', status: 'Operational' }}
    ];

    const pulsingRings = [];
    const interactiveMarkerMeshes = [];

    // Helper: Convert Lat/Lon to 3D Vector
    function latLonToVector3(lat, lon, radius) {{
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      const x = -(radius) * Math.sin(phi) * Math.cos(theta);
      const z = (radius) * Math.sin(phi) * Math.sin(theta);
      const y = (radius) * Math.cos(phi);
      return new THREE.Vector3(x, y, z);
    }}

    // Add Glowing & Pulsing Location Markers
    locationData.forEach(loc => {{
      const pos = latLonToVector3(loc.lat, loc.lon, globeRadius + 0.02);

      // Core Marker Sphere
      const markerGeo = new THREE.SphereGeometry(0.065, 16, 16);
      const markerMat = new THREE.MeshBasicMaterial({{ color: loc.type === 'Manufacturing Hub' ? 0x22d3ee : 0x38bdf8 }});
      const markerMesh = new THREE.Mesh(markerGeo, markerMat);
      markerMesh.position.copy(pos);
      markerMesh.userData = loc;
      earthGroup.add(markerMesh);
      interactiveMarkerMeshes.push(markerMesh);

      // Glowing Atmosphere Shell
      const glowGeo = new THREE.SphereGeometry(0.1, 16, 16);
      const glowMat = new THREE.MeshBasicMaterial({{ color: 0x38bdf8, transparent: true, opacity: 0.35 }});
      const glowMesh = new THREE.Mesh(glowGeo, glowMat);
      glowMesh.position.copy(pos);
      earthGroup.add(glowMesh);

      // Pulsing Ring
      const ringGeo = new THREE.RingGeometry(0.08, 0.12, 32);
      const ringMat = new THREE.MeshBasicMaterial({{ color: 0x38bdf8, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }});
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.copy(pos.clone().multiplyScalar(1.01));
      ringMesh.lookAt(pos.clone().multiplyScalar(2));
      earthGroup.add(ringMesh);

      pulsingRings.push({{ mesh: ringMesh, scale: 1, opacity: 0.8 }});
    }});

    // Draw Animated Supply Lines / Water Network Arcs
    const arcConnections = [
      ['hq', 'sa'], ['hq', 'wa'], ['hq', 'sa_asia'],
      ['wa', 'ea'], ['sa_asia', 'se_asia']
    ];

    const animatedArcCurves = [];

    arcConnections.forEach(pair => {{
      const loc1 = locationData.find(l => l.id === pair[0]);
      const loc2 = locationData.find(l => l.id === pair[1]);

      if (loc1 && loc2) {{
        const v1 = latLonToVector3(loc1.lat, loc1.lon, globeRadius + 0.02);
        const v2 = latLonToVector3(loc2.lat, loc2.lon, globeRadius + 0.02);

        // Arc mid point elevated off the earth surface
        const distance = v1.distanceTo(v2);
        const mid = v1.clone().add(v2).multiplyScalar(0.5);
        mid.normalize().multiplyScalar(globeRadius + 0.02 + distance * 0.28);

        const curve = new THREE.QuadraticBezierCurve3(v1, mid, v2);
        const points = curve.getPoints(50);
        const curveGeo = new THREE.BufferGeometry().setFromPoints(points);

        // Static Arc Tube Line
        const lineMat = new THREE.LineBasicMaterial({{ color: 0x0284c7, transparent: true, opacity: 0.45 }});
        const arcLine = new THREE.Line(curveGeo, lineMat);
        earthGroup.add(arcLine);

        // Flow Pulse Particle traveling along the curve
        const flowParticleGeo = new THREE.SphereGeometry(0.03, 12, 12);
        const flowParticleMat = new THREE.MeshBasicMaterial({{ color: 0x38bdf8 }});
        const flowParticle = new THREE.Mesh(flowParticleGeo, flowParticleMat);
        earthGroup.add(flowParticle);

        animatedArcCurves.push({{ curve, particle: flowParticle, progress: Math.random() }});
      }}
    }});

    globeScene.add(earthGroup);

    // --- RAYCASTING CLICK INTERACTION FOR MARKERS ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    globeContainer.addEventListener('click', (e) => {{
      const rect = globeContainer.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / globeContainer.clientWidth) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / globeContainer.clientHeight) * 2 + 1;

      raycaster.setFromCamera(mouse, globeCamera);
      const intersects = raycaster.intersectObjects(interactiveMarkerMeshes);

      if (intersects.length > 0) {{
        const data = intersects[0].object.userData;
        showGlobePopup(data);
        globeControls.autoRotate = false;
      }}
    }});

    function showGlobePopup(data) {{
      document.getElementById('popup-title').innerText = data.name;
      document.getElementById('popup-type').innerText = data.type;
      document.getElementById('popup-desc').innerText = data.desc;
      document.getElementById('popup-units').innerText = data.units.toLocaleString();
      document.getElementById('popup-capacity').innerText = data.capacity + ' L';
      document.getElementById('popup-status').innerText = data.status;
      document.getElementById('popup-coordinates').innerText = `${{data.lat.toFixed(1)}}°, ${{data.lon.toFixed(1)}}°`;
      document.getElementById('globe-popup').classList.remove('hidden');
    }}

    function closeGlobePopup() {{
      document.getElementById('globe-popup').classList.add('hidden');
      globeControls.autoRotate = true;
    }}

    // Resize Handler
    window.addEventListener('resize', () => {{
      initParticles();

      if (pfdContainer.clientWidth > 0) {{
        pfdCamera.aspect = pfdContainer.clientWidth / pfdContainer.clientHeight;
        pfdCamera.updateProjectionMatrix();
        pfdRenderer.setSize(pfdContainer.clientWidth, pfdContainer.clientHeight);
      }}

      if (globeContainer.clientWidth > 0) {{
        globeCamera.aspect = globeContainer.clientWidth / globeContainer.clientHeight;
        globeCamera.updateProjectionMatrix();
        globeRenderer.setSize(globeContainer.clientWidth, globeContainer.clientHeight);
      }}
    }});

    // Animation Loop
    function animate() {{
      requestAnimationFrame(animate);

      pfdControls.update();
      globeControls.update();

      // SLOWER Pulsing Marker Rings Animation
      pulsingRings.forEach(ring => {{
        ring.scale += 0.006;   // Reduced expansion speed
        ring.opacity -= 0.005; // Reduced opacity decay speed
        if (ring.scale > 2.2) {{
          ring.scale = 1;
          ring.opacity = 0.8;
        }}
        ring.mesh.scale.set(ring.scale, ring.scale, ring.scale);
        ring.mesh.material.opacity = Math.max(0, ring.opacity);
      }});

      // Animate Arc Water Flow Particles
      animatedArcCurves.forEach(arc => {{
        arc.progress += 0.004; // Smooth, relaxed flow Along Arcs
        if (arc.progress > 1) arc.progress = 0;
        const p = arc.curve.getPoint(arc.progress);
        arc.particle.position.copy(p);
      }});

      pfdRenderer.render(pfdScene, pfdCamera);
      globeRenderer.render(globeScene, globeCamera);
    }}
    animate();
  </script>
</body>
</html>
"""

# Render full screen HTML inside Streamlit
st.components.v1.html(html_code, height=5200, scrolling=True)
