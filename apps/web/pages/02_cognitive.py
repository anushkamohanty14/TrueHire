"""Phase 3 — Cognitive Assessment Task Delivery UI.

State machine: intro → testing → complete
"""
from __future__ import annotations

import random
import time
from typing import Any, List

import streamlit as st

from core.src.core.scoring import ScoringEngine
from core.src.core.storage.mongo_store import MongoUserStore
from core.src.core.tasks import (
    DigitSpanGenerator,
    MathReasoningGenerator,
    RuleViolationGenerator,
    SequenceCompletionGenerator,
    StroopGenerator,
    SyllogismGenerator,
    SymbolSearchGenerator,
    TimeShareGenerator,
    WrittenComprehensionGenerator,
)
from core.src.core.tasks.base import TaskItem, TaskResponse

st.set_page_config(
    page_title="Cognitive Assessment",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Generators ────────────────────────────────────────────────────────────────

GENERATORS = {
    "deductive_reasoning":    SyllogismGenerator(),
    "mathematical_reasoning": MathReasoningGenerator(),
    "memorization":           DigitSpanGenerator(),
    "perceptual_speed":       SymbolSearchGenerator(),
    "problem_sensitivity":    RuleViolationGenerator(),
    "selective_attention":    StroopGenerator(),
    "speed_of_closure":       SequenceCompletionGenerator(),
    "time_sharing":           TimeShareGenerator(),
    "written_comprehension":  WrittenComprehensionGenerator(),
}

BATTERY_CONFIG = [
    ("deductive_reasoning",    2, 3),
    ("mathematical_reasoning", 2, 3),
    ("memorization",           2, 3),
    ("perceptual_speed",       2, 3),
    ("problem_sensitivity",    2, 3),
    ("selective_attention",    2, 3),
    ("speed_of_closure",       2, 3),
    ("time_sharing",           2, 3),
    ("written_comprehension",  2, 3),
]

ABILITY_LABELS = {
    "deductive_reasoning":    "Deductive Reasoning",
    "mathematical_reasoning": "Mathematical Reasoning",
    "memorization":           "Memorization",
    "perceptual_speed":       "Perceptual Speed",
    "problem_sensitivity":    "Problem Sensitivity",
    "selective_attention":    "Selective Attention",
    "speed_of_closure":       "Speed of Closure",
    "time_sharing":           "Time Sharing",
    "written_comprehension":  "Written Comprehension",
}

# ink colour name → CSS hex (for Stroop)
INK_COLORS = {
    "red":    "#dc2626",
    "blue":   "#2563eb",
    "green":  "#16a34a",
    "yellow": "#ca8a04",
    "orange": "#ea580c",
    "purple": "#9333ea",
}

# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* hide streamlit chrome */
    #MainMenu, footer, header { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #f8f9fc !important;
        color: #191c1e !important;
    }
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 5rem !important;
        max-width: 780px !important;
    }

    /* top bar */
    .ca-topbar {
        background: #f8fafc;
        border-bottom: 1px solid rgba(226,232,240,0.5);
        padding: 0 1.5rem;
        height: 64px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: -1rem -1rem 2rem -1rem;
    }
    .ca-topbar-title {
        font-size: 1.125rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #0c4a6e;
    }

    /* fixed bottom nav */
    .ca-bottom-nav {
        position: fixed;
        bottom: 0; left: 0;
        width: 100%;
        z-index: 999;
        background: #f1f5f9;
        border-top: 1px solid #e2e8f0;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #075985;
    }
    .ca-progress-rail {
        position: fixed;
        bottom: 0; left: 0;
        width: 100%; height: 2px;
        background: rgba(7,89,133,0.12);
        z-index: 998;
    }
    .ca-progress-fill {
        height: 100%;
        background: #075985;
        transition: width 0.4s ease;
    }

    /* overline */
    .ca-overline {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        font-weight: 700;
        color: #40484e;
        opacity: 0.7;
        margin-bottom: 0.5rem;
        display: block;
    }
    /* heading */
    .ca-heading {
        font-size: 1.875rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #191c1e;
        line-height: 1.1;
        margin-bottom: 1.5rem;
    }

    /* card */
    .ca-card {
        background: #f3f3f7;
        border-radius: 0.25rem;
        padding: 1.5rem 2rem;
        margin-bottom: 1.25rem;
        font-size: 0.9375rem;
        line-height: 1.7;
        color: #191c1e;
    }
    .ca-card-accent {
        border-left: 4px solid #00425e;
    }

    /* stimulus display area */
    .ca-stimulus {
        background: #f3f3f7;
        border-radius: 0.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 220px;
        margin-bottom: 1.5rem;
        position: relative;
    }

    /* digit card */
    .ca-digit-card {
        background: #ffffff;
        border-radius: 0.25rem;
        padding: 1.25rem 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 2px solid rgba(0,66,94,0.12);
        box-shadow: 0 8px 24px rgba(0,46,61,0.05);
    }

    /* sequence tile */
    .ca-tile {
        background: #edeef1;
        border-radius: 0.25rem;
        padding: 1rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 3rem;
        font-size: 1.25rem;
        font-weight: 800;
        color: #191c1e;
    }
    .ca-tile-active {
        background: #00425e;
        color: #ffffff;
    }

    /* pill badge */
    .ca-badge {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        background: #e7e8eb;
        color: #40484e;
        padding: 0.2rem 0.5rem;
        border-radius: 0.125rem;
        display: inline-block;
        margin-bottom: 0.75rem;
    }

    /* Streamlit button: default style */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        border: none !important;
        border-radius: 0.25rem !important;
        padding: 0.875rem 1.5rem !important;
        width: 100% !important;
        background-color: #edeef1 !important;
        color: #191c1e !important;
        transition: all 0.12s !important;
    }
    .stButton > button:hover {
        background-color: #e7e8eb !important;
        transform: scale(0.99) !important;
    }
    .stButton > button:active { transform: scale(0.97) !important; }

    /* primary button */
    .stButton > button[kind="primary"] {
        background-color: #00425e !important;
        color: #ffffff !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #005b7f !important;
    }

    /* disabled button */
    .stButton > button:disabled {
        opacity: 0.4 !important;
        cursor: not-allowed !important;
    }

    /* number input */
    .stNumberInput input {
        font-family: 'Inter', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        background: #edeef1 !important;
        border: none !important;
        border-bottom: 2px solid #c0c7ce !important;
        border-radius: 0 !important;
        color: #191c1e !important;
        padding: 0.875rem 1rem !important;
    }
    .stNumberInput input:focus {
        border-bottom-color: #00425e !important;
        box-shadow: none !important;
    }
    .stNumberInput label {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.15em !important;
        color: #40484e !important;
    }

    /* text input */
    .stTextInput input {
        font-family: 'Inter', sans-serif !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.15em !important;
        background: #edeef1 !important;
        border: none !important;
        border-bottom: 2px solid #c0c7ce !important;
        border-radius: 0 !important;
        color: #191c1e !important;
        padding: 0.875rem 1rem !important;
    }
    .stTextInput label {
        font-family: 'Inter', sans-serif !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.15em !important;
        color: #40484e !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Shared render helpers ─────────────────────────────────────────────────────

def _topbar() -> None:
    st.markdown(
        '<div class="ca-topbar">'
        '<span class="ca-topbar-title">Cognitive Assessment</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _bottom_nav(current: int, total: int) -> None:
    pct = (current / total) * 100
    st.markdown(
        f'<div class="ca-bottom-nav">Task {current} of {total}</div>'
        f'<div class="ca-progress-rail">'
        f'<div class="ca-progress-fill" style="width:{pct:.1f}%"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _overline(text: str) -> None:
    st.markdown(f'<span class="ca-overline">{text}</span>', unsafe_allow_html=True)


def _heading(text: str) -> None:
    st.markdown(f'<h2 class="ca-heading">{text}</h2>', unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "ca_phase":       "intro",
        "task_queue":     [],
        "current_idx":    0,
        "responses":      [],
        "task_start_ms":  None,
        "digit_phase":    "show",   # "show" | "recall"
        "ts_b_answer":    None,     # dual-task task-B selection
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Battery generation ────────────────────────────────────────────────────────

def _generate_battery() -> List[TaskItem]:
    items: List[TaskItem] = []
    for ability, difficulty, n in BATTERY_CONFIG:
        items.extend(GENERATORS[ability].generate(difficulty=difficulty, n=n))
    random.shuffle(items)
    return items


# ── RT + response recording ───────────────────────────────────────────────────

def _start_rt() -> None:
    if st.session_state.task_start_ms is None:
        st.session_state.task_start_ms = time.time() * 1000


def _get_rt() -> float:
    if st.session_state.task_start_ms is None:
        return 5000.0
    return time.time() * 1000 - st.session_state.task_start_ms


def _record_and_advance(task: TaskItem, user_answer: Any) -> None:
    rt_ms = _get_rt()
    gen = GENERATORS[task.ability]
    response = TaskResponse(
        task_item=task,
        user_answer=user_answer,
        reaction_time_ms=rt_ms,
        is_correct=gen.score_response(task, user_answer),
    )
    st.session_state.responses.append(response)
    st.session_state.current_idx += 1
    st.session_state.task_start_ms = None
    st.session_state.digit_phase   = "show"
    st.session_state.ts_b_answer   = None

    if st.session_state.current_idx >= len(st.session_state.task_queue):
        st.session_state.ca_phase = "complete"
    st.rerun()


# ── Task renderers ────────────────────────────────────────────────────────────

def _render_stroop(task: TaskItem) -> None:
    _start_rt()
    q       = task.question
    word    = q["word"]
    ink     = q["ink_color"]
    options = q["options"]
    css_col = INK_COLORS.get(ink, ink)

    _overline("Active Protocol")
    _heading("What colour is the ink?")

    # Stimulus
    st.markdown(f"""
    <div class="ca-stimulus">
        <span style="font-size:6rem; font-weight:900; letter-spacing:-0.05em;
                     color:{css_col}; font-family:'Inter',sans-serif;">{word}</span>
        <div style="position:absolute; top:1rem; right:1rem;
                    background:rgba(225,226,230,0.85); backdrop-filter:blur(8px);
                    padding:0.35rem 0.75rem; border-radius:0.25rem;
                    display:flex; align-items:center; gap:0.5rem;">
            <div style="width:8px; height:8px; border-radius:50%; background:#006a6a;"></div>
            <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                         letter-spacing:0.1em; color:#40484e;">Calibrated</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Colour swatch + label buttons
    cols = st.columns(len(options))
    for col, opt in zip(cols, options):
        dot = INK_COLORS.get(opt.lower(), "#64748b")
        col.markdown(
            f'<div style="display:flex; flex-direction:column; align-items:center;'
            f'background:#edeef1; border-radius:0.25rem; padding:1.25rem 0.5rem 0.5rem;">'
            f'<div style="width:2rem; height:2rem; border-radius:50%; background:{dot};'
            f'margin-bottom:0.5rem;"></div></div>',
            unsafe_allow_html=True,
        )
        if col.button(opt.capitalize(), key=f"stroop_{opt}"):
            _record_and_advance(task, opt.lower())


def _render_symbol_search(task: TaskItem) -> None:
    _start_rt()
    q      = task.question
    target = q["target"]
    grid   = q["grid"]

    _overline("Assessment Phase: Visual Scanning")
    _heading("Does the target symbol appear in the sequence below?")

    col_t, col_g = st.columns([4, 8])

    with col_t:
        st.markdown(f"""
        <div style="background:#f3f3f7; border-radius:0.25rem; padding:2rem;
                    display:flex; flex-direction:column; align-items:center;
                    border-bottom:4px solid #00425e; height:100%;">
            <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                         letter-spacing:0.15em; color:#40484e; margin-bottom:1.25rem;">Target Symbol</span>
            <div style="width:6rem; height:6rem; background:#ffffff; border-radius:0.25rem;
                        display:flex; align-items:center; justify-content:center;
                        box-shadow:0 1px 4px rgba(0,0,0,0.08);">
                <span style="font-size:3.5rem; color:#00425e;">{target}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g:
        st.markdown(
            '<span style="font-size:10px; font-weight:700; text-transform:uppercase;'
            'letter-spacing:0.15em; color:#40484e; display:block; margin-bottom:0.75rem;">'
            'Search Sequence</span>',
            unsafe_allow_html=True,
        )
        tiles = "".join(
            f'<div style="width:3.25rem; height:3.25rem; background:#ffffff; border-radius:0.25rem;'
            f'border:1px solid rgba(192,199,206,0.25); display:inline-flex;'
            f'align-items:center; justify-content:center; margin:0.2rem;">'
            f'<span style="font-size:1.75rem; color:#40484e;">{s}</span></div>'
            for s in grid
        )
        st.markdown(
            f'<div style="display:flex; flex-wrap:wrap; gap:0.25rem;">{tiles}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✗  No", key="ss_no", use_container_width=True):
            _record_and_advance(task, "no")
    with c2:
        if st.button("✓  Yes", key="ss_yes", use_container_width=True):
            _record_and_advance(task, "yes")


def _render_digit_span(task: TaskItem) -> None:
    q        = task.question
    sequence = q["sequence"]

    if st.session_state.digit_phase == "show":
        _overline("Memory Sequence Acquisition")
        _heading("Memorise the digits shown below")

        cols = st.columns(len(sequence))
        for col, digit in zip(cols, sequence):
            col.markdown(
                f'<div class="ca-digit-card">'
                f'<span style="font-size:4.5rem; font-weight:900; letter-spacing:-0.04em;'
                f'color:#00425e; font-family:Inter,sans-serif;">{digit}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<p style="text-align:center; font-size:0.875rem; color:#40484e;'
            'font-family:Inter,sans-serif; margin-bottom:1rem;">'
            'Sequence disappears when you click Ready</p>',
            unsafe_allow_html=True,
        )
        _, mid, _ = st.columns([2, 3, 2])
        with mid:
            if st.button("Ready?", key="digit_ready", type="primary", use_container_width=True):
                st.session_state.digit_phase  = "recall"
                st.session_state.task_start_ms = time.time() * 1000
                st.rerun()

    else:  # recall phase
        _overline("Memory Recall")
        _heading("Type the digits in order")
        st.markdown(
            '<p style="font-size:0.875rem; color:#40484e; margin-bottom:1.25rem;'
            'font-family:Inter,sans-serif;">Separate each digit with a space — e.g. 7 2 9 4</p>',
            unsafe_allow_html=True,
        )
        answer = st.text_input("Digit sequence", key="digit_recall", placeholder="_ _ _ _")
        _, mid, _ = st.columns([2, 3, 2])
        with mid:
            if st.button("Submit", key="digit_submit", type="primary", use_container_width=True):
                if answer.strip():
                    _record_and_advance(task, answer.strip())


def _render_sequence_completion(task: TaskItem) -> None:
    _start_rt()
    q        = task.question
    sequence = q["sequence"]
    options  = q["options"]

    _overline("Pattern Recognition")
    _heading("What comes next in the sequence?")

    tiles = "".join(
        f'<div class="ca-tile {"ca-tile-active" if s == "?" else ""}"'
        f' style="margin:0 0.25rem;">{s}</div>'
        for s in sequence
    )
    st.markdown(
        f'<div style="background:#f3f3f7; border-radius:0.25rem; padding:2rem;'
        f'display:flex; align-items:center; justify-content:center;'
        f'flex-wrap:wrap; gap:0.5rem; margin-bottom:1.5rem;">{tiles}</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(options))
    for col, opt in zip(cols, options):
        if col.button(str(opt), key=f"seq_{opt}", use_container_width=True):
            _record_and_advance(task, opt)


def _render_rule_violation(task: TaskItem) -> None:
    _start_rt()
    q        = task.question
    rule     = q["rule"]
    scenario = q["scenario"]

    _overline("Problem Sensitivity")
    _heading("Was the rule violated?")

    st.markdown(f"""
    <div style="background:#edeef1; border-left:4px solid #00425e; border-radius:0.25rem;
                padding:1rem 1.5rem; margin-bottom:1rem;">
        <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                     letter-spacing:0.12em; color:#40484e; display:block; margin-bottom:0.25rem;">Rule</span>
        <span style="font-size:0.9375rem; font-weight:600; color:#191c1e;
                     font-family:Inter,sans-serif;">{rule}</span>
    </div>
    <div class="ca-card">{scenario}</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✗  No — rule was followed", key="rv_no", use_container_width=True):
            _record_and_advance(task, "no")
    with c2:
        if st.button("✓  Yes — rule was violated", key="rv_yes", use_container_width=True):
            _record_and_advance(task, "yes")


def _render_syllogism(task: TaskItem) -> None:
    _start_rt()
    _overline("Deductive Reasoning")
    _heading("Does the conclusion follow?")

    st.markdown(
        f'<div class="ca-card ca-card-accent">{task.question["text"]}</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✗  No", key="syl_no", use_container_width=True):
            _record_and_advance(task, "no")
    with c2:
        if st.button("✓  Yes", key="syl_yes", use_container_width=True):
            _record_and_advance(task, "yes")


def _render_math(task: TaskItem) -> None:
    _start_rt()
    _overline("Mathematical Reasoning")
    _heading("Solve the problem")

    st.markdown(
        f'<div class="ca-card">{task.question["text"]}</div>',
        unsafe_allow_html=True,
    )

    answer = st.number_input("Your answer", step=1, format="%d", key="math_ans")
    st.markdown("<br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([2, 3, 2])
    with mid:
        if st.button("Submit Answer", key="math_submit", type="primary", use_container_width=True):
            _record_and_advance(task, int(answer))


def _render_written_comp(task: TaskItem) -> None:
    _start_rt()
    q       = task.question
    passage = q["passage"]
    question = q["question"]
    options  = q["options"]

    _overline("Written Comprehension")
    _heading(question)

    st.markdown(
        f'<div class="ca-card" style="border-left:3px solid rgba(0,66,94,0.2);">{passage}</div>',
        unsafe_allow_html=True,
    )

    for i, opt in enumerate(options):
        if st.button(opt, key=f"wc_{i}", use_container_width=True):
            _record_and_advance(task, opt)


def _render_dual_task(task: TaskItem) -> None:
    _start_rt()
    q      = task.question
    task_a = q["task_a"]
    task_b = q["task_b"]
    opts_b = task_b.get("options", ["yes", "no"])

    _overline("Dual Processing — Answer Both Tasks")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"""
        <div style="background:#f3f3f7; border-radius:0.25rem; padding:1.5rem;
                    border-left:4px solid rgba(0,66,94,0.25); min-height:15rem;">
            <span class="ca-badge">Module Alpha</span>
            <div style="font-size:1.625rem; font-weight:800; letter-spacing:-0.03em;
                        color:#191c1e; font-family:Inter,sans-serif; line-height:1.2;
                        margin-bottom:1.25rem;">{task_a['text']}</div>
        </div>
        """, unsafe_allow_html=True)
        a_val = st.number_input("Numerical answer", step=1, format="%d", key="ts_a")

    with col_b:
        st.markdown(f"""
        <div style="background:#f3f3f7; border-radius:0.25rem; padding:1.5rem;
                    border-left:4px solid rgba(0,106,106,0.25); min-height:15rem;">
            <span class="ca-badge">Module Beta</span>
            <div style="font-size:1.125rem; font-weight:700; letter-spacing:-0.02em;
                        color:#191c1e; font-family:Inter,sans-serif; line-height:1.4;
                        margin-bottom:1.25rem;">{task_b['text']}</div>
        </div>
        """, unsafe_allow_html=True)
        for opt in opts_b:
            selected = st.session_state.ts_b_answer == opt
            label = f"{'● ' if selected else ''}{opt.capitalize()}"
            if st.button(label, key=f"ts_b_{opt}", use_container_width=True):
                st.session_state.ts_b_answer = opt
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    b_done = st.session_state.ts_b_answer is not None
    _, mid, _ = st.columns([2, 4, 2])
    with mid:
        if st.button(
            "Submit Response Pair",
            key="ts_submit",
            type="primary",
            use_container_width=True,
            disabled=not b_done,
        ):
            _record_and_advance(task, {"a": int(a_val), "b": st.session_state.ts_b_answer})


# Map task_type → renderer
_RENDERERS = {
    "syllogism":               _render_syllogism,
    "arithmetic_word_problem": _render_math,
    "digit_span":              _render_digit_span,
    "symbol_search":           _render_symbol_search,
    "rule_violation":          _render_rule_violation,
    "stroop":                  _render_stroop,
    "sequence_completion":     _render_sequence_completion,
    "dual_task":               _render_dual_task,
    "passage_mcq":             _render_written_comp,
}


# ── Phase screens ─────────────────────────────────────────────────────────────

def _render_intro() -> None:
    _topbar()
    st.markdown("""
    <div style="text-align:center; padding:3rem 0 2rem;">
        <span class="ca-overline" style="text-align:center; display:block;">CogniHire</span>
        <h1 style="font-size:2.5rem; font-weight:900; letter-spacing:-0.04em;
                   color:#191c1e; font-family:Inter,sans-serif; margin-bottom:1rem; line-height:1.1;">
            Cognitive Assessment
        </h1>
        <p style="font-size:1rem; color:#40484e; max-width:440px; margin:0 auto 0.75rem;
                  font-family:Inter,sans-serif; line-height:1.6;">
            27 short tasks across 9 cognitive abilities.<br>
            Answer as quickly and accurately as you can.
        </p>
        <p style="font-size:0.875rem; font-weight:600; color:#191c1e;
                  font-family:Inter,sans-serif; margin-bottom:2.5rem;">
            Do not use calculators or external aids.
        </p>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([2, 3, 2])
    with mid:
        uid_input = st.text_input(
            "User ID",
            value=st.session_state.get("user_id", ""),
            placeholder="Enter the same ID used on the Profile page",
            key="intro_uid",
        )
        if uid_input.strip():
            st.session_state["user_id"] = uid_input.strip()

        if st.button("Begin Assessment", key="begin", type="primary", use_container_width=True):
            if not st.session_state.get("user_id", "").strip():
                st.error("Enter a User ID before starting.")
            else:
                st.session_state.task_queue  = _generate_battery()
                st.session_state.current_idx = 0
                st.session_state.responses   = []
                st.session_state.ca_phase    = "testing"
                st.rerun()

    st.markdown(
        '<p style="text-align:center; font-size:10px; text-transform:uppercase;'
        'letter-spacing:0.15em; font-weight:700; color:#40484e; opacity:0.6;'
        'margin-top:1.5rem; font-family:Inter,sans-serif;">Estimated time: 15–20 minutes</p>',
        unsafe_allow_html=True,
    )


def _render_testing() -> None:
    _topbar()
    idx   = st.session_state.current_idx
    queue = st.session_state.task_queue
    total = len(queue)

    if idx >= total:
        st.session_state.ca_phase = "complete"
        st.rerun()
        return

    task     = queue[idx]
    renderer = _RENDERERS.get(task.task_type)

    if renderer is None:
        st.error(f"No renderer for task_type='{task.task_type}'. Skipping.")
        if st.button("Skip →"):
            st.session_state.current_idx += 1
            st.rerun()
        return

    renderer(task)
    _bottom_nav(idx + 1, total)


@st.cache_resource
def _get_engine() -> ScoringEngine:
    return ScoringEngine()


def _compute_readiness(percentiles: dict) -> float:
    """Overall readiness score: simple mean of all ability percentiles (0–100)."""
    vals = [v for v in percentiles.values() if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else 50.0


def _render_complete() -> None:
    _topbar()

    if "ability_profile" not in st.session_state:
        engine  = _get_engine()
        user_id = st.session_state.get("user_id", "anonymous")
        profile = engine.score_session(user_id=user_id, responses=st.session_state.responses)
        st.session_state.ability_profile = profile

        # Convert to Title Case keys (required by Phase 7 recommender)
        percentiles_titled = {
            ABILITY_LABELS[k]: v
            for k, v in profile.ability_percentiles.items()
            if k in ABILITY_LABELS
        }
        readiness = _compute_readiness(percentiles_titled)

        # Save to MongoDB — merge with existing profile if present
        try:
            store = MongoUserStore()
            existing = store.get_profile(user_id) or {"user_id": user_id}
            existing["ability_percentiles"] = percentiles_titled
            existing["readiness_score"]     = readiness
            existing["assessed_at"]         = profile.assessed_at.isoformat()
            store.upsert_profile(existing)
            st.session_state["_mongo_save_ok"]       = True
            st.session_state["_readiness_score"]     = readiness
        except Exception as exc:
            st.session_state["_mongo_save_ok"]   = False
            st.session_state["_mongo_save_error"] = str(exc)

    profile = st.session_state.ability_profile

    readiness = st.session_state.get("_readiness_score")

    # ── Save status notification ──────────────────────────────────────────────
    if st.session_state.get("_mongo_save_ok") is True:
        pass  # silent success — shown via readiness panel below
    elif st.session_state.get("_mongo_save_ok") is False:
        st.warning(
            f"Results could not be saved to your profile: "
            f"{st.session_state.get('_mongo_save_error', 'unknown error')}. "
            "Check your .env MONGODB_URI and try again."
        )

    # ── Heading + readiness ring ──────────────────────────────────────────────
    readiness_pct  = readiness if readiness is not None else 50.0
    readiness_text = f"{readiness_pct:.0f}"
    st.markdown(f"""
    <div style="text-align:center; padding:2rem 0 2.5rem;">
        <span class="ca-overline" style="display:block; text-align:center;">Assessment Complete</span>
        <h1 style="font-size:2.25rem; font-weight:900; letter-spacing:-0.04em;
                   color:#191c1e; font-family:Inter,sans-serif; margin-bottom:0.5rem;">
            Your Results
        </h1>
        <p style="font-size:0.9375rem; color:#40484e; font-family:Inter,sans-serif;">
            Scores are percentile ranks against a population of 9,000+ test-takers.
        </p>
    </div>
    <div style="display:flex; flex-direction:column; align-items:center; margin-bottom:2.5rem;">
        <div style="width:120px; height:120px; border-radius:50%;
                    background:conic-gradient(#00425e {readiness_pct:.1f}%, #e1e2e6 0);
                    display:flex; align-items:center; justify-content:center;">
            <div style="width:90px; height:90px; border-radius:50%; background:#f8f9fc;
                        display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <span style="font-size:1.5rem; font-weight:900; color:#00425e;
                             font-family:Inter,sans-serif; line-height:1;">{readiness_text}</span>
                <span style="font-size:9px; font-weight:700; text-transform:uppercase;
                             letter-spacing:0.1em; color:#40484e; line-height:1.5;">Readiness</span>
            </div>
        </div>
        <p style="font-size:0.8125rem; color:#40484e; font-family:Inter,sans-serif;
                  margin-top:0.75rem; text-align:center;">
            Overall cognitive readiness vs. population<br>
            <strong style="color:#191c1e;">{readiness_text}th percentile</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    for ability, label in ABILITY_LABELS.items():
        pct = profile.ability_percentiles.get(ability)
        if pct is None:
            continue
        if pct >= 67:
            tier, tier_color = "High",   "#006a6a"
        elif pct >= 33:
            tier, tier_color = "Mid",    "#00425e"
        else:
            tier, tier_color = "Low",    "#70787e"

        st.markdown(f"""
        <div style="margin-bottom:1.125rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem;">
                <span style="font-size:0.8125rem; font-weight:600; color:#191c1e;
                             font-family:Inter,sans-serif;">{label}</span>
                <div style="display:flex; gap:0.75rem; align-items:center;">
                    <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                                 letter-spacing:0.1em; color:{tier_color};">{tier}</span>
                    <span style="font-size:0.875rem; font-weight:800; color:#191c1e;
                                 font-family:Inter,sans-serif;">{pct:.0f}<sup>th</sup></span>
                </div>
            </div>
            <div style="height:5px; background:#e1e2e6; border-radius:3px; overflow:hidden;">
                <div style="height:100%; width:{pct:.1f}%; background:#00425e;
                            border-radius:3px; transition:width 0.5s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([2, 3, 2])
    with mid:
        if st.button("Continue to Job Matches →", key="to_jobs", type="primary", use_container_width=True):
            st.switch_page("pages/04_results.py")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    _inject_css()
    _init_state()

    phase = st.session_state.ca_phase
    if phase == "intro":
        _render_intro()
    elif phase == "testing":
        _render_testing()
    elif phase == "complete":
        _render_complete()


main()
