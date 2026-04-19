"""Shared design system for TrueHire Streamlit pages.

Usage
-----
from apps.web._styles import inject_styles, layout_html

inject_styles()
st.markdown(layout_html("dashboard"), unsafe_allow_html=True)
"""
from __future__ import annotations

import streamlit as st

# ── Design tokens + global CSS ────────────────────────────────────────────────

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

/* ── Hide Streamlit chrome ─────────────────────────────────────────── */
#MainMenu, footer, header { display: none !important; }
[data-testid="stSidebar"]    { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── CSS variables ─────────────────────────────────────────────────── */
:root {
    --primary:                  #00425e;
    --secondary:                #006a6a;
    --surface:                  #f8f9fd;
    --surface-container-lowest: #ffffff;
    --surface-container-low:    #f2f4f7;
    --surface-container:        #eceef1;
    --surface-container-high:   #e6e8eb;
    --on-surface:               #191c1e;
    --on-surface-variant:       #40484e;
    --outline-variant:          #c0c7ce;
    --secondary-container:      #90efef;
    --on-secondary-container:   #006e6e;
    --primary-fixed:            #c6e7ff;
    --error:                    #ba1a1a;
    --error-container:          #ffdad6;
}

/* ── Base reset ────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
    background: #f8f9fd !important;
    color: #191c1e !important;
}

/* ── Content area offset for fixed nav + sidebar ───────────────────── */
.block-container {
    max-width: 100% !important;
    padding-left: 296px !important;
    padding-right: 2.5rem !important;
    padding-top: 5rem !important;
    padding-bottom: 5rem !important;
    margin-top: 0 !important;
}
[data-testid="stAppViewContainer"] { background: #f8f9fd !important; }

/* ── Nav items ─────────────────────────────────────────────────────── */
.ch-nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.625rem 1.5rem;
    text-decoration: none;
    font-family: Manrope, sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #40484e;
    transition: background 0.15s, color 0.15s;
    border-right: 3px solid transparent;
}
.ch-nav-item:hover {
    background: #eef2f5;
    color: #00425e;
}
.ch-nav-item.active {
    background: #ffffff;
    color: #00425e;
    border-right: 3px solid #00425e;
}
.ch-nav-icon {
    font-size: 1.25rem;
    font-family: 'Material Symbols Outlined';
    font-weight: 300;
    color: inherit;
}

/* ── Typography ────────────────────────────────────────────────────── */
.ch-overline {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
    color: #40484e;
    opacity: 0.7;
    margin-bottom: 0.4rem;
    display: block;
    font-family: Inter, sans-serif;
}
.ch-section {
    font-family: Manrope, sans-serif;
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 700;
    color: #40484e;
    margin: 2rem 0 1rem;
    display: block;
}
.ch-heading {
    font-family: Manrope, sans-serif;
    font-size: 1.875rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #191c1e;
    line-height: 1.1;
    margin-bottom: 1.25rem;
}
.ch-subheading {
    font-family: Manrope, sans-serif;
    font-size: 1.125rem;
    font-weight: 700;
    color: #191c1e;
    margin-bottom: 0.5rem;
}

/* ── Cards ─────────────────────────────────────────────────────────── */
.ch-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    border: 1px solid #eceef1;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.ch-card-primary  { border-left: 3px solid #00425e; }
.ch-card-success  { border-left: 3px solid #006a6a; }
.ch-card-warning  { border-left: 3px solid #b45309; }
.ch-card-neutral  { border-left: 3px solid #40484e; }
.ch-card-dark {
    background: #00425e;
    color: #ffffff;
    border: none;
}

/* ── Chips ─────────────────────────────────────────────────────────── */
.ch-chip {
    display: inline-block;
    background: #eceef1;
    border-radius: 6px;
    padding: 0.25rem 0.65rem;
    font-size: 11px;
    font-weight: 600;
    color: #40484e;
    margin-right: 0.4rem;
    margin-bottom: 0.4rem;
    font-family: Inter, sans-serif;
}
.ch-chip-teal  { background: #ccfbf1; color: #0f766e; }
.ch-chip-amber { background: #fef3c7; color: #92400e; }
.ch-chip-blue  { background: #c6e7ff; color: #00425e; }

/* ── Progress bars ─────────────────────────────────────────────────── */
.ch-progress-track {
    height: 6px;
    background: #eceef1;
    border-radius: 3px;
    overflow: hidden;
}
.ch-progress-fill {
    height: 100%;
    background: #00425e;
    border-radius: 3px;
    transition: width 0.4s ease;
}
.ch-progress-fill-teal { background: #006a6a; }

/* ── Streamlit button overrides ────────────────────────────────────── */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.625rem 1.25rem !important;
    width: 100% !important;
    background-color: #eceef1 !important;
    color: #191c1e !important;
    transition: all 0.12s !important;
}
.stButton > button:hover {
    background-color: #e6e8eb !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}
.stButton > button:active { transform: scale(0.98) !important; }
.stButton > button[kind="primary"] {
    background-color: #00425e !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #005b7f !important;
}
.stButton > button:disabled { opacity: 0.4 !important; cursor: not-allowed !important; }

/* ── Streamlit form widget overrides ───────────────────────────────── */
.stTextInput input, .stTextArea textarea {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    background: #f2f4f7 !important;
    border: 1px solid #c0c7ce !important;
    border-radius: 8px !important;
    color: #191c1e !important;
    padding: 0.625rem 0.875rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #00425e !important;
    box-shadow: 0 0 0 2px rgba(0,66,94,0.12) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label,
.stNumberInput label, .stSlider label, .stFileUploader label {
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: #40484e !important;
}
.stSelectbox > div > div {
    font-family: 'Inter', sans-serif !important;
    background: #f2f4f7 !important;
    border: 1px solid #c0c7ce !important;
    border-radius: 8px !important;
    color: #191c1e !important;
}
.stNumberInput input {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    background: #f2f4f7 !important;
    border: 1px solid #c0c7ce !important;
    border-radius: 8px !important;
    color: #191c1e !important;
    padding: 0.75rem 1rem !important;
}
.stNumberInput input:focus {
    border-color: #00425e !important;
    box-shadow: 0 0 0 2px rgba(0,66,94,0.12) !important;
}
.stSlider .stSlider { color: #00425e !important; }

/* ── Expander ───────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #eceef1 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
}

/* ── Assessment specific ────────────────────────────────────────────── */
.ca-stimulus {
    background: #f2f4f7;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 220px;
    margin-bottom: 1.5rem;
    position: relative;
}
.ca-digit-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 1.25rem 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #eceef1;
    box-shadow: 0 4px 16px rgba(0,46,61,0.06);
}
.ca-tile {
    background: #eceef1;
    border-radius: 8px;
    padding: 1rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 3rem;
    font-size: 1.25rem;
    font-weight: 800;
    color: #191c1e;
}
.ca-tile-active { background: #00425e; color: #ffffff; }
.ca-card {
    background: #f2f4f7;
    border-radius: 10px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.25rem;
    font-size: 0.9375rem;
    line-height: 1.7;
    color: #191c1e;
}
.ca-card-accent { border-left: 4px solid #00425e; }
.ca-overline {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
    color: #40484e;
    opacity: 0.7;
    margin-bottom: 0.5rem;
    display: block;
    font-family: Inter, sans-serif;
}
.ca-heading {
    font-family: Manrope, sans-serif;
    font-size: 1.875rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #191c1e;
    line-height: 1.1;
    margin-bottom: 1.5rem;
}
.ca-badge {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    background: #eceef1;
    color: #40484e;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 0.75rem;
}
.ca-bottom-nav {
    position: fixed;
    bottom: 0; left: 256px; right: 0;
    z-index: 999;
    background: #f2f4f7;
    border-top: 1px solid #eceef1;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #00425e;
}
.ca-progress-rail {
    position: fixed;
    bottom: 0; left: 256px; right: 0;
    width: calc(100% - 256px); height: 3px;
    background: rgba(0,66,94,0.12);
    z-index: 998;
}
.ca-progress-fill {
    height: 100%;
    background: #00425e;
    transition: width 0.4s ease;
}
"""

# ── Nav + Sidebar HTML ────────────────────────────────────────────────────────

_NAV_ITEMS = [
    ("dashboard",    "dashboard",       "Dashboard",   "/dashboard"),
    ("assessments",  "psychology",      "Assessments", "/cognitive"),
    ("resume",       "description",     "Resume",      "/profile"),
    ("jobs",         "work_outline",    "Jobs",        "/results"),
    ("interview",    "record_voice_over", "Interview", "#"),
    ("skills",       "auto_stories",    "Skills",      "/skills"),
]


def layout_html(active_page: str) -> str:
    """Return the full fixed nav + sidebar HTML string."""
    nav_items_html = ""
    for key, icon, label, href in _NAV_ITEMS:
        active_class = "active" if key == active_page else ""
        nav_items_html += (
            f'<a href="{href}" class="ch-nav-item {active_class}">'
            f'<span class="material-symbols-outlined" style="font-size:1.25rem;">{icon}</span>'
            f'{label}'
            f'</a>'
        )

    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">

<nav style="position:fixed;top:0;left:0;right:0;z-index:1000;background:rgba(255,255,255,0.92);backdrop-filter:blur(20px);border-bottom:1px solid rgba(192,199,206,0.3);height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
  <div style="display:flex;align-items:center;gap:2rem;">
    <span style="font-family:Manrope,sans-serif;font-size:1.125rem;font-weight:800;color:#00425e;letter-spacing:-0.03em;">Cognitive Architect</span>
  </div>
  <div style="display:flex;align-items:center;gap:1rem;">
    <span class="material-symbols-outlined" style="color:#40484e;cursor:pointer;font-size:1.25rem;">notifications</span>
    <span class="material-symbols-outlined" style="color:#40484e;cursor:pointer;font-size:1.25rem;">help_outline</span>
    <div style="width:32px;height:32px;border-radius:50%;background:#c6e7ff;display:flex;align-items:center;justify-content:center;">
      <span class="material-symbols-outlined" style="color:#00425e;font-size:1rem;">person</span>
    </div>
  </div>
</nav>

<aside style="position:fixed;left:0;top:0;height:100vh;width:256px;background:#f8fafc;border-right:1px solid #e2e8f0;padding-top:80px;padding-bottom:2rem;display:flex;flex-direction:column;z-index:999;">
  <div style="padding:0 1.5rem 1.5rem;">
    <div style="font-family:Manrope,sans-serif;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;color:#70787e;">Workspace</div>
    <div style="font-size:11px;color:#40484e;margin-top:2px;font-family:Inter,sans-serif;">Interview Intelligence</div>
  </div>
  <nav style="flex:1;display:flex;flex-direction:column;gap:2px;">
    {nav_items_html}
  </nav>
  <div style="border-top:1px solid #e2e8f0;padding:1rem 1.5rem 0;">
    <a href="#" style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;text-decoration:none;color:#40484e;font-family:Manrope,sans-serif;font-size:13px;font-weight:600;">
      <span class="material-symbols-outlined" style="font-size:1.25rem;">settings</span>Settings
    </a>
    <a href="#" style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;text-decoration:none;color:#40484e;font-family:Manrope,sans-serif;font-size:13px;font-weight:600;">
      <span class="material-symbols-outlined" style="font-size:1.25rem;">contact_support</span>Support
    </a>
  </div>
</aside>
"""


def inject_styles() -> None:
    """Inject the full TrueHire design system CSS."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ── Backward-compatible helpers ───────────────────────────────────────────────

def inject_css(profile: str = "full") -> None:
    """Backward-compat wrapper — calls inject_styles()."""
    inject_styles()


def topbar_html(page_label: str = "") -> str:
    """Backward-compat: returns empty string (nav is now injected via layout_html)."""
    return ""


def readiness_ring_html(score: float, size: int = 120) -> str:
    """Backward-compat: delegates to readiness_ring_svg."""
    return readiness_ring_svg(score, size)


# ── SVG readiness ring ────────────────────────────────────────────────────────

def readiness_ring_svg(score: float, size: int = 192) -> str:
    """Return an SVG-based readiness ring HTML string."""
    r = size // 2 - 12
    circumference = 2 * 3.14159 * r
    offset = circumference * (1 - score / 100)
    cx = cy = size // 2
    return f"""
<div style="position:relative;width:{size}px;height:{size}px;display:flex;align-items:center;justify-content:center;">
  <svg width="{size}" height="{size}" style="transform:rotate(-90deg);position:absolute;top:0;left:0;">
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="transparent" stroke="#eceef1" stroke-width="10"/>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="transparent" stroke="#00425e" stroke-width="12"
            stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}" stroke-linecap="round"/>
  </svg>
  <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
    <span style="font-family:Manrope,sans-serif;font-size:{size//4}px;font-weight:800;color:#00425e;line-height:1;">{score:.0f}</span>
    <span style="font-family:Inter,sans-serif;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#40484e;">Readiness</span>
  </div>
</div>"""
