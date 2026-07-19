"""Streamlit GUI for genetictabler — shadcn/ui-style design.

Run with:  streamlit run genetictabler_gui.py

Features:
  * Parameter controls (sliders, text inputs, checkboxes)
  * Named inputs (editable course/class/day names)
  * Color-coded timetable display (one tab per class)
  * Live GA generation progress animation
  * Analytics panel (runtime, violations, cache hit ratio, course frequency)
  * Export buttons (JSON, CSV, HTML download links)
"""

from __future__ import annotations

import tempfile
import time

import streamlit as st

# ── Imports from genetictabler ───────────────────────────────────────────────
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

# ── Custom CSS (shadcn/ui-style) ─────────────────────────────────────────────

# CSS overrides injected globally into the document head.
CSS_OVERRIDES = """
[data-testid="stAppViewContainer"] {
  background-color: #ffffff !important;
  color: #09090b !important;
}
.stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, span, label, a {
  color: #09090b !important;
}
.stMetric {
  background-color: #f9fafb !important;
  border: 1px solid #e4e4e7 !important;
  border-radius: 0.5rem !important;
  color: #09090b !important;
}
.stMetric div {
  color: #09090b !important;
}
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
}
.stTabs [data-baseweb="tab"],
.css-1d3uqb2 {
  border: 1px solid #e4e4e7 !important;
  border-radius: 0.5rem !important;
  background-color: #f4f4f5 !important;
  color: #18181b !important;
}
.stButton > button {
  border-radius: 0.5rem !important;
  border: 1px solid #e4e4e7 !important;
  background-color: #f4f4f5 !important;
  color: #18181b !important;
  padding: 0.5rem 1rem !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
}
.stButton > button:hover {
  background-color: #18181b !important;
  color: #fafafa !important;
  border-color: #18181b !important;
}
[data-testid="stSidebar"] {
  background-color: #fafafa !important;
  border-right: 1px solid #e4e4e7 !important;
}
[data-testid="stSidebar"] > div {
  color: #09090b !important;
}
[data-testid="stSidebar"] .stSubheader,
[data-testid="stSidebar"] .stHeader {
  color: #09090b !important;
}
[data-testid="stSidebar"] .stSlider > div {
  color: #09090b !important;
}
"""


# ── Helper functions ─────────────────────────────────────────────────────────

_COURSE_COLORS: dict[int, str] = {
    1: "#3b82f6",  # blue
    2: "#10b981",  # green
    3: "#f59e0b",  # amber
    4: "#ef4444",  # red
    5: "#8b5cf6",  # purple
    6: "#ec4899",  # pink
    7: "#06b6d4",  # cyan
    8: "#84cc16",  # lime
    9: "#f97316",  # orange
    10: "#6366f1",  # indigo
}


def _build_timetable_html(
    tables: list,
    day_names: list,
    course_names: list,
    slots: int,
    days: int,
) -> str:
    """Build an HTML table for a single class's timetable.

    Parameters
    ----------
    tables : list
        2-D list indexed as [day][slot] = 1-based course number (0 = empty).
    """
    html = '<table style="border-collapse:collapse;width:100%;font-size:0.8rem;">'
    html += '<thead><tr>'
    html += '<th style="padding:8px;border:1px solid #e4e4e7;background:#f4f4f5;text-align:center;font-weight:600;">Time</th>'
    for day in day_names:
        html += f'<th style="padding:8px;border:1px solid #e4e4e7;background:#f4f4f5;text-align:center;font-weight:600;">{day}</th>'
    html += "</tr></thead><tbody>"

    for slot in range(1, slots + 1):
        html += "<tr>"
        html += f'<td style="padding:6px;border:1px solid #e4e4e7;text-align:center;font-weight:500;color:#6b7280;">Slot {slot}</td>'
        for day in range(days):
            course_id = tables[day][slot - 1]
            if course_id == 0:
                html += '<td style="padding:8px;border:1px solid #f3f4f6;background:#fafafa;text-align:center;color:#9ca3af;">—</td>'
            else:
                color = _COURSE_COLORS.get(course_id, "#6b7280")
                name = (
                    course_names[course_id - 1]
                    if course_id <= len(course_names)
                    else f"C{course_id}"
                )
                html += (
                    f'<td style="padding:8px;border:1px solid #e4e4e7;'
                    f'background:{color}15;color:{color};text-align:center;'
                    f'font-weight:500;border-radius:4px;">{name}</td>'
                )
        html += "</tr>"
    html += "</tbody></table>"
    return html


def _build_frequency_chart(freq: dict) -> str:
    """Build a simple horizontal bar chart from frequency dict."""
    if not freq:
        return "<p style='color:#6b7280;'>No data yet.</p>"
    max_val = max(freq.values()) if freq else 1
    html = '<div style="display:flex;flex-direction:column;gap:6px;">'
    for name, count in sorted(freq.items(), key=lambda x: -x[1]):
        pct = count / max_val * 100 if max_val else 0
        color = _COURSE_COLORS.get(abs(hash(name)) % 10 + 1, "#6b7280")
        html += (
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="min-width:100px;font-size:0.8rem;text-align:right;color:#374151;">{name}</span>'
            f'<div style="flex:1;background:#f3f4f6;border-radius:4px;height:20px;overflow:hidden;">'
            f'<div style="width:{pct:.1f}%;background:{color};height:100%;border-radius:4px;transition:width 0.3s;"></div>'
            f'</div>'
            f'<span style="min-width:30px;font-size:0.8rem;color:#6b7280;">{count}</span>'
            f'</div>'
        )
    html += "</div>"
    return html


# ── Page layout ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Genetic Timetable Generator",
    page_icon="\U0001f9ec",
    layout="wide",
)

# Inject CSS globally by appending <style> to document.head via JS.
_js_inject = f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var style = document.createElement('style');
  style.textContent = `{CSS_OVERRIDES}`;
  document.head.appendChild(style);
}});
</script>
"""
st.markdown(_js_inject, unsafe_allow_html=True)

# Header
st.markdown("# \U0001f9ec Genetic Timetable Generator")
st.caption("Conflict-free school and university timetables via genetic algorithms")

# ── Sidebar: Configuration ───────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    # General parameters
    st.subheader("\U0001f4cb General")
    num_classes = st.slider("Classes", 1, 20, 4)
    num_courses = st.slider("Courses", 1, 15, 6)
    slots_per_day = st.slider("Slots per Day", 1, 10, 6)
    num_days = st.slider("Days", 1, 7, 5)

    # GA parameters
    st.subheader("\U0001f9ec GA Parameters")
    population_size = st.slider("Population Size", 10, 200, 60)
    max_generations = st.slider("Max Generations", 10, 500, 80)
    mutation_rate = st.slider("Mutation Rate", 0.01, 0.99, 0.25, 0.01)
    adaptive = st.toggle("Adaptive Mutation", True)
    seed_val = st.number_input(
        "Seed (None for random)", min_value=0, max_value=999999, value=42, step=1
    )
    seed_val = int(seed_val) if seed_val else None

    # Labels
    st.subheader("\U0001f3f7️ Labels")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        course_names_input = st.text_area(
            "Course names (comma-separated)",
            value="Maths,English,Science,History,PE,Art",
        )
    with col_l2:
        class_names_input = st.text_area(
            "Class names (comma-separated)",
            value="Year 7A,Year 7B,Year 8A,Year 8B",
        )

    day_names_input = st.text_input(
        "Day names (comma-separated)",
        value="Mon,Tue,Wed,Thu,Fri",
    )

    # Build name lists
    course_names = [n.strip() for n in course_names_input.split(",") if n.strip()]
    class_names = [n.strip() for n in class_names_input.split(",") if n.strip()]
    day_names = [n.strip() for n in day_names_input.split(",") if n.strip()]

    # Ensure we have enough names
    while len(course_names) < num_courses:
        course_names.append(f"Course-{len(course_names) + 1}")
    while len(class_names) < num_classes:
        class_names.append(f"Class-{len(class_names) + 1}")
    while len(day_names) < num_days:
        day_names.append(f"Day-{len(day_names) + 1}")

    # Repeat and Teachers
    st.subheader("\U0001f4d0 Constraints")
    repeat_val = st.number_input(
        "Repeat (slots per course per day)", min_value=1, max_value=5, value=2
    )
    teacher_val = st.number_input(
        "Teachers (simultaneous slots)", min_value=1, max_value=5, value=1
    )

# ── Compute current config tuple ────────────────────────────────────────────

current_config = (
    num_classes, num_courses, slots_per_day, num_days,
    population_size, max_generations, mutation_rate, adaptive, seed_val,
    repeat_val, teacher_val,
    course_names_input, class_names_input, day_names_input,
)

# ── Detect config change + run trigger ──────────────────────────────────────

# If the stored config differs from current, a new run is needed
config_changed = (
    st.session_state._last_config is not None
    and st.session_state._last_config != current_config
)

# Use a form so each "Run" click triggers a fresh rerun even after the first run.
with st.form(key="run_form"):
    run_clicked = st.form_submit_button("Run Scheduler", use_container_width=True, type="primary")

# If run was clicked, bump the key so the next click also fires
if run_clicked and st.session_state._has_run:
    st.session_state._run_key += 1

# ── Execute scheduler ───────────────────────────────────────────────────────

should_run = run_clicked or (
    config_changed
    and not (st.session_state._last_config == current_config)
)

if should_run:
    # Clear state for a fresh run
    st.session_state._gen_log = []
    st.session_state._result = None  # type: ignore[assignment]
    st.session_state._has_run = True
    st.session_state._last_config = current_config

    # Build and run scheduler
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
    timetable = sched.run()
    analytics = sched.analytics()

    # Store in session state
    st.session_state._result = {  # type: ignore[assignment]
        "timetable": timetable,
        "analytics": analytics,
        "sched": sched,
    }
    st.session_state._gen_log = list(analytics.get("generation_log_tail", []))  # type: ignore[union-attr]

# ── Display ──────────────────────────────────────────────────────────────────

result = st.session_state._result  # type: ignore[union-attr]

if result is None and config_changed:
    # Config just changed but we haven't auto-ran yet — nudge user
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
        empty = st.empty()  # reusable placeholder for the animation loop

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

        # Final state
        time.sleep(0.2)
        with empty:
            st.markdown(f"✅ **Done.** Best fitness: {max_fitness:.2f}")

    # ── Analytics summary ────────────────────────────────────────────────
    st.divider()
    st.subheader("\U0001f4ca Analytics")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("⏱ Runtime", f"{analytics.get('runtime_s', 0):.2f}s")
    with col_b:
        v = analytics.get("validation", {})
        st.metric("\U0001f512 Violations", f"{v.get('total_violations', 0)}")
    with col_c:
        st.metric("\U0001f4be Cache hit", f"{analytics.get('cache_hit_ratio', 0) * 100:.1f}%")
    with col_d:
        st.metric("\U0001f4e6 Slots filled", f"{analytics.get('slots_filled', 0)}")

    # ── Timetable display with tabs ──────────────────────────────────────
    st.divider()
    st.subheader("\U0001f4c5 Timetable")

    # Guard: ensure displayed dimensions match stored timetable
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
                class_table = tables[idx]
                html = _build_timetable_html(
                    class_table,
                    sched_day_names,
                    sched_course_names,
                    slots_per_day,
                    num_days,
                )
                st.markdown(html, unsafe_allow_html=True)

    # ── Course frequency chart ───────────────────────────────────────────
    st.divider()
    st.subheader("\U0001f4c8 Course Frequency")
    freq = analytics.get("course_frequency", {})
    st.markdown(_build_frequency_chart(freq), unsafe_allow_html=True)

    # ── Validation details ───────────────────────────────────────────────
    st.divider()
    st.subheader("\U0001f50d Constraint Violations")
    v = analytics.get("validation", {})
    v_cols = st.columns(4)
    with v_cols[0]:
        st.metric("Empty cells", v.get("empty_cells", 0))
    with v_cols[1]:
        st.metric("Teacher clashes", v.get("teacher_clashes", 0))
    with v_cols[2]:
        st.metric("Back-to-back", v.get("back_to_back", 0))
    with v_cols[3]:
        st.metric("Total", v.get("total_violations", 0))

    # ── Export ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("\U0001f4e4 Export")
    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        if st.button("\U0001f4c4 Export JSON", use_container_width=True):
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
        if st.button("\U0001f4ca Export CSV", use_container_width=True):
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
        if st.button("\U0001f310 Export HTML", use_container_width=True):
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
    # Empty state
    st.info(
        "\U0001f527 Configure parameters in the sidebar and click **Run Scheduler** "
        "to generate a timetable."
    )

    # Show a preview of what the output looks like
    st.subheader("Preview")
    preview_html = """
    <div style="padding:3rem;text-align:center;color:#6b7280;">
        <p style="font-size:3rem;">\U0001f9ec</p>
        <p>Your conflict-free timetable will appear here.</p>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "genetictabler v3.0 — Genetic Algorithm Timetable Generator | "
    "Python stdlib only | [GitHub](https://github.com/themagicalmammal/genetictabler)"
)
