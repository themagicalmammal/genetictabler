"""Streamlit GUI for genetictabler.

Generate conflict-free school and university timetables using a genetic algorithm.

Run with:  streamlit run genetictabler_gui.py
"""

from __future__ import annotations

import tempfile
import time
from contextlib import suppress

import streamlit as st

from genetictabler import GenerateTimeTable

# ── Session state defaults ───────────────────────────────────────────────────

if "_result" not in st.session_state:
    st.session_state._result = None  # type: ignore[assignment]
if "_last_config" not in st.session_state:
    st.session_state._last_config = None  # type: ignore[assignment]
if "_gen_log" not in st.session_state:
    st.session_state._gen_log = []  # type: ignore[assignment]
if "_has_run" not in st.session_state:
    st.session_state._has_run = False
if "_run_key" not in st.session_state:
    st.session_state._run_key = 0
if "_show_info" not in st.session_state:
    st.session_state._show_info = True  # hero/info banner toggled by user

# ── Teachers config (persists across reruns) ─────────────────────────────

if "_teachers" not in st.session_state:
    st.session_state._teachers = []  # type: ignore[assignment]

# ── Global CSS ───────────────────────────────────────────────────────────────

_CSS = """
/* ── General page ──────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] { background-color: #f8fafc !important; }
.stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, span, label, a, .css-1d3uqb2 {
  color: #0f172a !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background-color: #ffffff !important;
  border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] > div { color: #0f172a !important; }
[data-testid="stSidebar"] .stSubheader { color: #0f172a !important; }
[data-testid="stSidebar"] .stSlider > div { color: #0f172a !important; }

/* ── Cards / metrics ───────────────────────────────────────────────────────── */
.stMetric {
  background: linear-gradient(135deg, #ffffff, #f8fafc) !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 0.75rem !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
  color: #0f172a !important;
  padding: 0.75rem 1rem !important;
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.stMetric > div { color: #0f172a !important; }

/* ── Buttons ────────────────────────────────────────────────────────────────── */
.stButton > button {
  border-radius: 0.625rem !important;
  border: 1px solid #cbd5e1 !important;
  background: linear-gradient(180deg, #ffffff, #f1f5f9) !important;
  color: #1e293b !important;
  padding: 0.5rem 1.25rem !important;
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
.stButton > button:hover {
  background: linear-gradient(180deg, #3b82f6, #2563eb) !important;
  color: #ffffff !important;
  border-color: #3b82f6 !important;
  box-shadow: 0 4px 12px rgba(59,130,246,0.35) !important;
  transform: translateY(-1px);
}

/* ── Primary button (Run Scheduler) ────────────────────────────────────────── */
.stButton[data-testid="stFormContainer"] button[type="submit"],
.stFormSubmitButton {
  background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 0.625rem !important;
  padding: 0.75rem 2rem !important;
  font-size: 0.95rem !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
  transition: all 0.25s ease !important;
  letter-spacing: 0.01em;
}
.stButton[data-testid="stFormContainer"] button[type="submit"]:hover,
.stFormSubmitButton:hover {
  background: linear-gradient(135deg, #4f46e5, #4338ca) !important;
  box-shadow: 0 6px 20px rgba(79,70,229,0.5) !important;
  transform: translateY(-2px);
}

/* ── Tabs ───────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"],
.css-1d3uqb2 {
  border: 1px solid #e2e8f0 !important;
  border-radius: 0.5rem !important;
  background: #f8fafc !important;
  color: #475569 !important;
  padding: 0.5rem 1.25rem !important;
  font-weight: 500 !important;
  transition: all 0.15s ease !important;
}
.stTabs [aria-selected="true"] {
  background: #ffffff !important;
  color: #1e293b !important;
  border-bottom-color: #6366f1 !important;
  box-shadow: 0 -2px 0 #6366f1 !important;
}

/* ── Progress bar ───────────────────────────────────────────────────────────── */
.stProgress > div > div {
  background: linear-gradient(90deg, #6366f1, #3b82f6) !important;
  border-radius: 0.5rem !important;
  height: 0.75rem !important;
  transition: width 0.15s ease;
}
.stProgress > div {
  background-color: #e2e8f0 !important;
  border-radius: 0.5rem !important;
  height: 0.75rem !important;
}

/* ── Divider ────────────────────────────────────────────────────────────────── */
.stDivider { margin: 1.5rem 0 !important; }

/* ── Info banner ────────────────────────────────────────────────────────────── */
.info-banner {
  background: linear-gradient(135deg, #ede9fe, #ddd6fe, #e0e7ff);
  border: 1px solid #c4b5fd;
  border-radius: 1rem;
  padding: 1.5rem 2rem;
  margin: 1rem 0 1.5rem 0;
  box-shadow: 0 4px 24px rgba(139,92,246,0.1);
}
.info-banner h2 {
  margin: 0 0 0.75rem 0;
  font-size: 1.5rem;
  color: #3b0764;
  font-weight: 700;
}
.info-banner p {
  color: #4c1d95;
  font-size: 1.05rem;
  line-height: 1.65;
  margin: 0 0 0.75rem 0;
}
.info-banner .features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}
.info-banner .feature-card {
  background: rgba(255,255,255,0.7);
  border: 1px solid rgba(196,181,253,0.5);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  text-align: center;
}
.info-banner .feature-card .icon { font-size: 1.5rem; display: block; margin-bottom: 0.25rem; }
.info-banner .feature-card .label { font-size: 0.85rem; font-weight: 600; color: #3b0764; }
.info-banner .feature-card .desc { font-size: 0.78rem; color: #6d5c8a; margin-top: 0.15rem; }

/* ── Hero title ─────────────────────────────────────────────────────────────── */
.hero-title {
  font-size: 2.2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #4f46e5, #7c3aed, #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0;
}
.hero-sub {
  font-size: 1.1rem;
  color: #475569;
  margin-top: 0.25rem;
}

/* ── Section heading ────────────────────────────────────────────────────────── */
.section-hd {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin-top: 1.75rem;
  margin-bottom: 0.75rem;
}

/* ── Export buttons ─────────────────────────────────────────────────────────── */
.export-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

/* ── Animations ─────────────────────────────────────────────────────────────── */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.6; }
}
.animate-fade-in { animation: fadeIn 0.5s ease forwards; }
.animate-pulse { animation: pulse 2s ease-in-out infinite; }
"""

_JS_INJECT = f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var style = document.createElement('style');
  style.textContent = `{_CSS}`;
  document.head.appendChild(style);
}});
</script>
"""
st.markdown(_JS_INJECT, unsafe_allow_html=True)

# ── Config helpers ───────────────────────────────────────────────────────────

def _parse_names(raw: str, want: int, prefix: str) -> list[str]:
    """Parse a comma-separated name string into at least *want* entries."""
    names = [n.strip() for n in raw.split(",") if n.strip()]
    idx = 1
    while len(names) < want:
        names.append(f"{prefix}{idx}")
        idx += 1
    return names

_COURSE_COLORS: dict[int, str] = {
    1: "#3b82f6", 2: "#10b981", 3: "#f59e0b", 4: "#ef4444",
    5: "#8b5cf6", 6: "#ec4899", 7: "#06b6d4", 8: "#84cc16",
    9: "#f97316", 10: "#6366f1",
}

# ── Helper functions ─────────────────────────────────────────────────────────

def _build_timetable_html(
    tables: list,
    day_names: list,
    course_names: list,
    slots: int,
    days: int,
) -> str:
    """Build an HTML table for a single class's timetable."""
    html = '<table style="border-collapse:collapse;width:100%;font-size:0.8rem;">'
    html += '<thead><tr>'
    html += '<th style="padding:10px;border:1px solid #e5e7eb;background:#f3f4f6;text-align:center;font-weight:700;font-size:0.75rem;letter-spacing:0.04em;text-transform:uppercase;color:#374151;">Time</th>'
    for day in day_names:
        html += f'<th style="padding:10px;border:1px solid #e5e7eb;background:#f3f4f6;text-align:center;font-weight:700;font-size:0.75rem;letter-spacing:0.04em;text-transform:uppercase;color:#374151;">{day}</th>'
    html += "</tr></thead><tbody>"

    for slot in range(1, slots + 1):
        html += "<tr>"
        html += f'<td style="padding:8px;border:1px solid #f3f4f6;text-align:center;font-weight:600;color:#9ca3af;font-size:0.75rem;">Slot {slot}</td>'
        for day in range(days):
            course_id = tables[day][slot - 1]
            if course_id == 0:
                html += '<td style="padding:10px;border:1px solid #f9fafb;background:#fafafa;text-align:center;color:#d1d5db;font-size:0.75rem;">—</td>'
            else:
                color = _COURSE_COLORS.get(course_id, "#6b7280")
                name = (
                    course_names[course_id - 1]
                    if course_id <= len(course_names)
                    else f"C{course_id}"
                )
                html += (
                    f'<td style="padding:10px;border:1px solid {color}25;'
                    f'background:{color}10;color:{color};text-align:center;'
                    f'font-weight:600;border-radius:6px;font-size:0.8rem;">{name}</td>'
                )
        html += "</tr>"
    html += "</tbody></table>"
    return html


def _build_frequency_chart(freq: dict) -> str:
    """Build a horizontal bar chart from frequency dict."""
    if not freq:
        return "<p style='color:#9ca3af;'>No data yet.</p>"
    max_val = max(freq.values()) if freq else 1
    html = '<div style="display:flex;flex-direction:column;gap:8px;">'
    for name, count in sorted(freq.items(), key=lambda x: -x[1]):
        pct = count / max_val * 100 if max_val else 0
        color = _COURSE_COLORS.get(abs(hash(name)) % 10 + 1, "#6b7280")
        html += (
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span style="min-width:100px;font-size:0.82rem;text-align:right;font-weight:500;color:#374151;">{name}</span>'
            f'<div style="flex:1;background:#f3f4f6;border-radius:6px;height:22px;overflow:hidden;">'
            f'<div style="width:{pct:.1f}%;background:{color};height:100%;border-radius:6px;transition:width 0.4s ease;display:flex;align-items:center;padding-left:8px;">'
            f'<span style="color:#fff;font-size:0.7rem;font-weight:600;">{count}</span></div>'
            f'</div></div>'
        )
    html += "</div>"
    return html


def _st_metric_card(label: str, value: str, icon: str = "") -> None:
    """Render a styled metric card."""
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#ffffff,#f8fafc);'
        f'border:1px solid #e2e8f0;border-radius:0.75rem;padding:0.85rem 1rem;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06);display:flex;flex-direction:column;gap:0.15rem;">'
        f'<span style="font-size:0.78rem;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:0.04em;">{label}</span>'
        f'<span style="font-size:1.5rem;font-weight:700;color:#1e293b;">{icon} {value}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Genetictabler",
    page_icon="\U0001f9ec",
    layout="wide",
)

st.markdown(
    '<h1 class="hero-title">Genetictabler</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-sub">Generate conflict-free timetables for schools and universities using a genetic algorithm.</p>',
    unsafe_allow_html=True,
)
st.caption(
    "Configure parameters in the sidebar and click **Run Scheduler** to get started."
)

st.divider()

# ── Info / Feature Banner ────────────────────────────────────────────────────

if st.session_state._show_info:
    with st.container():
        st.markdown(
            """
            <div class="info-banner">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;">
                        <h2>\U0001f9ec What is Genetictabler?</h2>
                        <p>
                            <strong>Genetictabler</strong> is a timetable generation engine that uses a
                            <strong>genetic algorithm</strong> to automatically produce conflict-free
                            schedules for schools and universities.  It intelligently allocates courses
                            to time-slots while respecting real-world constraints — no teacher
                            double-booking, no student timetable collisions, no back-to-back overload.
                        </p>
                        <p style="margin-bottom:0;">
                            You can use it to plan <strong>class schedules</strong>,
                            <strong>exam timetables</strong>, <strong>university module rosters</strong>,
                            or any domain where resources (rooms, teachers, equipment) must be shared
                            without conflicts across a fixed set of time slots.
                        </p>
                    </div>
                </div>
                <div class="features">
                    <div class="feature-card">
                        <span class="icon">⚡</span>
                        <span class="label">Instant Scheduling</span>
                        <span class="desc">Generate full weekly timetables in seconds</span>
                    </div>
                    <div class="feature-card">
                        <span class="icon">\U0001f512</span>
                        <span class="label">Constraint Enforcement</span>
                        <span class="desc">No teacher clashes, no course overlap</span>
                    </div>
                    <div class="feature-card">
                        <span class="icon">\U0001f9ec</span>
                        <span class="label">Genetic Algorithm</span>
                        <span class="desc">Optimised through evolution, not brute force</span>
                    </div>
                    <div class="feature-card">
                        <span class="icon">\U0001f4da</span>
                        <span class="label">Multi-Export</span>
                        <span class="desc">Download as HTML, JSON, or CSV</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Close-button for info banner
st.button(
    "✕  Hide info",
    use_container_width=False,
    key="_hide_info_btn",
    on_click=lambda: setattr(st.session_state, "_show_info", False),
)
if not st.session_state._show_info:
    st.balloons()

st.divider()

# ── Sidebar: Configuration ───────────────────────────────────────────────────

with st.sidebar:
    st.header("\U0001f9e0 Configuration")

    st.subheader("\U0001f4cb General")
    num_classes = st.slider("Classes", 1, 20, 4)
    num_courses = st.slider("Courses", 1, 15, 6)
    slots_per_day = st.slider("Slots per Day", 1, 10, 6)
    num_days = st.slider("Days", 1, 7, 5)

    st.subheader("\U0001f9ec GA Parameters")
    population_size = st.slider("Population Size", 10, 200, 60)
    max_generations = st.slider("Max Generations", 10, 500, 80)
    mutation_rate = st.slider("Mutation Rate", 0.01, 0.99, 0.25, 0.01)
    adaptive = st.toggle("Adaptive Mutation", True)
    seed_val = st.number_input(
        "Seed (None for random)", min_value=0, max_value=999999, value=42, step=1
    )
    seed_val = int(seed_val) if seed_val else None

    st.subheader("\U0001f3f7️ Names")
    course_names_input = st.text_area(
        "Course names",
        value="Maths,English,Science,History,PE,Art",
    )
    class_names_input = st.text_area(
        "Class names",
        value="Year 7A,Year 7B,Year 8A,Year 8B",
    )
    day_names_input = st.text_input(
        "Day names",
        value="Mon,Tue,Wed,Thu,Fri",
    )

    # ── Parse names (inside sidebar so variables are in scope) ──────────
    course_names = _parse_names(course_names_input, num_courses, "Course")
    class_names = _parse_names(class_names_input, num_classes, "Class")
    day_names = _parse_names(day_names_input, num_days, "Day")

    st.subheader("\U0001f4d0 Constraints")
    repeat_val = st.number_input(
        "Max times a course per day", min_value=1, max_value=5, value=2
    )
    teacher_val = st.number_input(
        "Teachers (simultaneous)", min_value=1, max_value=5, value=1
    )

    st.subheader("\U0001f468‍\U0001f3eb Teachers")
    st.caption(
        "Define individual teachers with course assignments and weekly quotas. "
        "Leave empty to use the simple 'Teachers' setting above."
    )
    _teacher_list: list[dict] = st.session_state._teachers  # type: ignore[assignment]

    for idx, t in enumerate(_teacher_list):
        with st.container():
            t_col1, t_col2 = st.columns([2, 1])
            with t_col1:
                name = st.text_input(
                    f"Teacher {idx + 1} name",
                    value=t.get("name", ""),
                    key=f"_tname_{idx}",
                    label_visibility="collapsed",
                )
            with t_col2:
                if st.button("\U0001f5d1", key=f"_trem_{idx}", use_container_width=True):
                    _teacher_list.pop(idx)
                    st.session_state._teachers = _teacher_list  # type: ignore[misc]
                    st.rerun()

            if name:
                # Course checkboxes
                st.markdown("**Teaches:**", key=f"_tcourses_{idx}")
                selected = t.get("courses", [])
                cols_c = st.columns(min(len(course_names), 3))
                for ci, cn in enumerate(course_names):
                    cidx = ci % len(cols_c)
                    checked = st.checkbox(
                        cn,
                        value=cn in selected,
                        key=f"_tchk_{idx}_{ci}",
                    )
                    if checked and cn not in selected:
                        selected.append(cn)
                    elif not checked and cn in selected:
                        selected.remove(cn)

                # Per-course quotas
                quotas = t.get("course_quota", {})
                st.markdown("**Per-course weekly quota:**", key=f"_tq_{idx}")
                for cn in selected:
                    cn_idx = course_names.index(cn) + 1  # 1-based course ID
                    q_key = f"_tqval_{idx}_{cn_idx}"
                    default = quotas.get(cn_idx, 0)
                    q_val = st.number_input(
                        f"  {cn}:",
                        min_value=0, max_value=20, value=default,
                        key=q_key,
                        label_visibility="collapsed",
                    )
                    quotas[cn_idx] = q_val

                # Total weekly cap
                total_q_key = f"_ttotal_{idx}"
                total_q = st.number_input(
                    "Total weekly cap:",
                    min_value=0, max_value=50,
                    value=t.get("total_quota", 0),
                    key=total_q_key,
                    label_visibility="collapsed",
                )

                # Save back to session state
                _teacher_list[idx] = {
                    "name": name,
                    "courses": selected,
                    "course_quota": quotas,
                    "total_quota": total_q,
                }

    if st.button("+ Add Teacher", use_container_width=True):
        _teacher_list.append({
            "name": "",
            "courses": [],
            "course_quota": {},
            "total_quota": 0,
        })
        st.session_state._teachers = _teacher_list  # type: ignore[misc]

# ── Parse names ──────────────────────────────────────────────────────────────

course_names = _parse_names(course_names_input, num_courses, "Course")
class_names = _parse_names(class_names_input, num_classes, "Class")
day_names = _parse_names(day_names_input, num_days, "Day")

# ── Config tracking & run trigger ────────────────────────────────────────────

current_config = (
    num_classes, num_courses, slots_per_day, num_days,
    population_size, max_generations, mutation_rate, adaptive, seed_val,
    repeat_val, teacher_val,
    course_names_input, class_names_input, day_names_input,
    tuple(st.session_state._teachers),  # type: ignore[arg-type]
)

config_changed = (
    st.session_state._last_config is not None
    and st.session_state._last_config != current_config
)

with st.form(key="run_form"):
    run_clicked = st.form_submit_button("\U0001f680 Run Scheduler", use_container_width=True)

if run_clicked and st.session_state._has_run:
    st.session_state._run_key += 1

# ── Execute scheduler ───────────────────────────────────────────────────────

should_run = run_clicked or (config_changed)

if should_run:
    st.session_state._gen_log = []
    st.session_state._result = None  # type: ignore[assignment]
    st.session_state._has_run = True
    st.session_state._last_config = current_config

    sched = GenerateTimeTable(
        classes=num_classes,
        courses=num_courses,
        slots=slots_per_day,
        days=num_days,
        repeat=repeat_val,
        teachers=teacher_val,
        population_size=population_size,
        max_generations=max_generations,
        mutation_rate=mutation_rate,
        adaptive=adaptive,
        seed=seed_val,
        course_names=course_names,
        class_names=class_names,
        day_names=day_names,
    )

    # Apply teachers_config if defined (overrides teachers for matching courses)
    _teacher_list = st.session_state._teachers  # type: ignore[union-attr]
    if _teacher_list:
        from genetictabler import TeacherConfig

        tc_list = []
        for t in _teacher_list:
            if t.get("name"):
                # Map course names to 1-based indices
                courses = []
                for cn in t.get("courses", []):
                    with suppress(ValueError):
                        courses.append(course_names.index(cn) + 1)
                tc = TeacherConfig(
                    name=t["name"],
                    courses=courses,
                    course_quota=t.get("course_quota", {}),
                    total_quota=t.get("total_quota", 0),
                )
                tc_list.append(tc)
        if tc_list:
            sched.teachers_config = tc_list
    timetable = sched.run()
    analytics = sched.analytics()

    st.session_state._result = {  # type: ignore[assignment]
        "timetable": timetable,
        "analytics": analytics,
        "sched": sched,
    }
    st.session_state._gen_log = list(analytics.get("generation_log_tail", []))  # type: ignore[union-attr]

# ── Display ──────────────────────────────────────────────────────────────────

result = st.session_state._result  # type: ignore[union-attr]

if result is None and config_changed:
    st.warning(
        "⚠️ Parameters changed. Click **Run Scheduler** to regenerate."
    )

if result is not None:
    tables = result["timetable"]
    analytics = result["analytics"]
    sched = result["sched"]

    # ── Generation progress animation ────────────────────────────────────
    gen_log = st.session_state._gen_log
    if gen_log:
        st.subheader("\U0001f9ea Generation Progress")
        max_fitness = analytics.get("best_fitness", 0)

        gen_bar = st.progress(0)
        empty = st.empty()

        for i, gen in enumerate(gen_log):
            pct = (i + 1) / len(gen_log)
            gen_bar.progress(pct)
            time.sleep(0.08)

            with empty:
                st.markdown(
                    f"**Gen {gen['generation']:>4}**  "
                    f"Best: {gen['best_fitness']:>8.2f}  "
                    f"Avg:  {gen['avg_fitness']:>8.2f}  "
                    f"Worst: {gen['worst_fitness']:>8.2f}  "
                    f"Mutation: {gen['mutation_rate']:.2f}"
                )

        time.sleep(0.2)
        with empty:
            st.markdown(f"✅ **Done.** Best fitness: {max_fitness:.2f}")

    # ── Analytics cards ──────────────────────────────────────────────────
    st.markdown('<p class="section-hd">\U0001f4ca Analytics</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        _st_metric_card("Runtime", f"{analytics.get('runtime_s', 0):.2f}s", "⏱")
    with cols[1]:
        v = analytics.get("validation", {})
        _st_metric_card("Violations", str(v.get("total_violations", 0)), "\U0001f512")
    with cols[2]:
        _st_metric_card(
            "Cache hit",
            f"{analytics.get('cache_hit_ratio', 0) * 100:.1f}%",
            "\U0001f4be",
        )
    with cols[3]:
        _st_metric_card("Slots filled", str(analytics.get("slots_filled", 0)), "\U0001f4e6")

    # ── Timetable tabs ───────────────────────────────────────────────────
    st.markdown('<p class="section-hd">\U0001f4c5 Timetable</p>', unsafe_allow_html=True)

    try:
        num_cls = len(tables)
        num_slots = len(tables[0][0]) if tables and tables[0] else 0
        num_ds = len(tables[0]) if tables else 0
    except (IndexError, TypeError):
        num_cls, num_slots, num_ds = 0, 0, 0

    dim_ok = (num_cls == num_classes and num_slots == slots_per_day and num_ds == num_days)
    if not dim_ok:
        st.warning(
            f"⚠️ Stored timetable dimensions ({num_cls}×{num_ds}×{num_slots}) "
            f"don't match current config ({num_classes}×{num_days}×{slots_per_day}). "
            f"Re-run to refresh."
        )

    sched_class_names = getattr(sched, "class_names", class_names)
    sched_day_names = getattr(sched, "day_names", day_names)
    sched_course_names = getattr(sched, "course_names", course_names)

    tab_names = [f"\U0001f4cb {n}" for n in sched_class_names]
    tabs = st.tabs(tab_names)
    for idx, tab in enumerate(tabs):
        with tab:
            if idx < len(tables):
                html = _build_timetable_html(
                    tables[idx],
                    sched_day_names,
                    sched_course_names,
                    slots_per_day,
                    num_days,
                )
                st.markdown(html, unsafe_allow_html=True)

    # ── Course frequency ─────────────────────────────────────────────────
    st.markdown('<p class="section-hd">\U0001f4c8 Course Frequency</p>', unsafe_allow_html=True)
    freq = analytics.get("course_frequency", {})
    st.markdown(_build_frequency_chart(freq), unsafe_allow_html=True)

    # ── Validation details ───────────────────────────────────────────────
    st.markdown('<p class="section-hd">\U0001f50d Constraint Check</p>', unsafe_allow_html=True)
    v = analytics.get("validation", {})
    v_cols = st.columns(4)
    with v_cols[0]:
        _st_metric_card("Empty cells", str(v.get("empty_cells", 0)))
    with v_cols[1]:
        _st_metric_card("Teacher clashes", str(v.get("teacher_clashes", 0)))
    with v_cols[2]:
        _st_metric_card("Back-to-back", str(v.get("back_to_back", 0)))
    with v_cols[3]:
        _st_metric_card("Total", str(v.get("total_violations", 0)))

    # ── Export ───────────────────────────────────────────────────────────
    st.markdown('<p class="section-hd">\U0001f4e4 Export</p>', unsafe_allow_html=True)

    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        if st.button("\U0001f4c4  Export JSON", use_container_width=True):
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                sched.export_json(f.name)
                with open(f.name, "rb") as fh:
                    st.download_button(
                        label="Download JSON",
                        data=fh.read(),
                        file_name="timetable.json",
                        mime="application/json",
                        use_container_width=True,
                    )
    with export_col2:
        if st.button("\U0001f4ca  Export CSV", use_container_width=True):
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                sched.export_csv(f.name)
                with open(f.name, "rb") as fh:
                    st.download_button(
                        label="Download CSV",
                        data=fh.read(),
                        file_name="timetable.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
    with export_col3:
        if st.button("\U0001f310  Export HTML", use_container_width=True):
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
                sched.export_html(f.name)
                with open(f.name, "rb") as fh:
                    st.download_button(
                        label="Download HTML",
                        data=fh.read(),
                        file_name="timetable.html",
                        mime="text/html",
                        use_container_width=True,
                    )

else:
    # ── Empty state with illustration ──────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center;padding:4rem 2rem;">
            <p style="font-size:4rem;margin:0;">\U0001f9ec</p>
            <h2 style="color:#475569;font-weight:600;margin:1rem 0 0.5rem;">
                Ready to generate a timetable
            </h2>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:400px;margin:0 auto;">
                Adjust the settings in the sidebar and hit <strong>Run Scheduler</strong> to
                generate your conflict-free schedule.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Footer ───────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Genetictabler v3.0  •  Genetic Algorithm Timetable Generator  •  "
    "Python stdlib only  •  "
    '[GitHub](https://github.com/themagicalmammal/genetictabler)'
)
