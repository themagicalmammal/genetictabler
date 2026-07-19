"""Streamlit GUI for genetictabler — shadcn/ui-style design.

Run with:  streamlit run genetictabler_gui.py

Features:
  * Parameter controls (sliders, text inputs, checkboxes)
  * Named inputs (editable course/class/day names)
  * Color-coded timetable display (one tab per class)
  * Analytics panel (runtime, violations, cache hit ratio, course frequency)
  * Export buttons (JSON, CSV, HTML download links)
  * Dark/light mode toggle
"""

from __future__ import annotations

import tempfile

import streamlit as st

# ── Imports from genetictabler ───────────────────────────────────────────────
from genetictabler import GenerateTimeTable

# ── Session state defaults ───────────────────────────────────────────────────

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if "last_scheduler" not in st.session_state:
    st.session_state.last_scheduler = None  # type: ignore[assignment]

if "last_analytics" not in st.session_state:
    st.session_state.last_analytics = None  # type: ignore[assignment]

if "last_timetable" not in st.session_state:
    st.session_state.last_timetable = None  # type: ignore[assignment]

# ── Custom CSS (shadcn/ui-style) ─────────────────────────────────────────────

DARK_CSS = """
<style>
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 3.9%;
  --primary: 240 5.9% 10%;
  --primary-foreground: 0 0% 98%;
  --secondary: 240 4.8% 95.9%;
  --secondary-foreground: 240 5.9% 10%;
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;
  --accent: 240 4.8% 95.9%;
  --border: 240 5.9% 90%;
  --radius: 0.5rem;
}
.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --card: 240 10% 3.9%;
  --card-foreground: 0 0% 98%;
  --primary: 0 0% 98%;
  --primary-foreground: 240 5.9% 10%;
  --secondary: 240 3.7% 15.9%;
  --secondary-foreground: 0 0% 98%;
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;
  --accent: 240 3.7% 15.9%;
  --border: 240 3.7% 15.9%;
}

/* Global overrides */
[data-testid="stAppViewContainer"] {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
}
.stMarkdown, .stText, h1, h2, h3, h4, h5, h6 {
  color: hsl(var(--foreground)) !important;
}
[data-testid="stHeader"] {
  color: hsl(var(--foreground)) !important;
}
.stMetric {
  background-color: hsl(var(--card) / 0.5);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
}
.css-1d3uqb2 {
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
}
.stButton > button {
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  background-color: hsl(var(--secondary));
  color: hsl(var(--secondary-foreground));
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.stButton > button:hover {
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
}
.stTabs [data-baseweb="tab"] {
  height: 40px;
  border-radius: var(--radius);
  padding: 0.5rem 1rem;
  background: hsl(var(--secondary));
}
</style>
"""

LIGHT_CSS = """
<style>
[data-testid="stAppViewContainer"] {
  background-color: #ffffff;
  color: #09090b;
}
.stMarkdown, .stText, h1, h2, h3, h4, h5, h6 {
  color: #09090b !important;
}
.stMetric {
  background-color: #f9fafb;
  border: 1px solid #e4e4e7;
  border-radius: 0.5rem;
}
.css-1d3uqb2 {
  border: 1px solid #e4e4e7;
  border-radius: 0.5rem;
}
.stButton > button {
  border-radius: 0.5rem;
  border: 1px solid #e4e4e7;
  background-color: #f4f4f5;
  color: #18181b;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.stButton > button:hover {
  background-color: #18181b;
  color: #fafafa;
  border-color: #18181b;
}
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
}
.stTabs [data-baseweb="tab"] {
  height: 40px;
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f4f4f5;
}
</style>
"""


# ── Helper functions ─────────────────────────────────────────────────────────

COURSE_COLORS: dict[int, str] = {
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


def _build_scheduler(**params) -> GenerateTimeTable:
    """Build a scheduler from session params."""
    kwargs = {k: v for k, v in params.items() if v is not None}
    return GenerateTimeTable(**kwargs)


def _build_timetable_html(
    tables,
    class_names,
    day_names,
    course_names,
    slots,
    days,
    courses,
) -> str:
    """Build an HTML table for a single class's timetable."""
    html = '<table style="border-collapse:collapse;width:100%;font-size:0.8rem;">'
    # Header
    html += "<thead><tr>"
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
                color = COURSE_COLORS.get(course_id, "#6b7280")
                name = course_names[course_id - 1] if course_id <= len(course_names) else f"C{course_id}"
                html += f'<td style="padding:8px;border:1px solid #e4e4e7;background:{color}15;color:{color};text-align:center;font-weight:500;border-radius:4px;">{name}</td>'
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
        color = COURSE_COLORS.get(abs(hash(name)) % 10 + 1, "#6b7280")
        html += f"""
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="min-width:100px;font-size:0.8rem;text-align:right;color:#374151;">{name}</span>
          <div style="flex:1;background:#f3f4f6;border-radius:4px;height:20px;overflow:hidden;">
            <div style="width:{pct}%;background:{color};height:100%;border-radius:4px;transition:width 0.3s;"></div>
          </div>
          <span style="min-width:30px;font-size:0.8rem;color:#6b7280;">{count}</span>
        </div>
        """
    html += "</div>"
    return html


# ── Page layout ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Genetic Timetable Generator",
    page_icon="🧬",
    layout="wide",
)

# Header
st.markdown("# 🧬 Genetic Timetable Generator")
st.caption("Conflict-free school and university timetables via genetic algorithms")

# Dark mode toggle (key manages session state automatically)
dark = st.toggle("🌙 Dark mode", key="dark_mode")

# Theme CSS (must come after widgets that use dark_mode key)
if dark:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# ── Sidebar: Configuration ───────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    # General parameters
    st.subheader("📋 General")
    num_classes = st.slider("Classes", 1, 20, 4)
    num_courses = st.slider("Courses", 1, 15, 6)
    slots_per_day = st.slider("Slots per Day", 1, 10, 6)
    num_days = st.slider("Days", 1, 7, 5)

    # GA parameters
    st.subheader("🧬 GA Parameters")
    population_size = st.slider("Population Size", 10, 200, 60)
    max_generations = st.slider("Max Generations", 10, 500, 80)
    mutation_rate = st.slider("Mutation Rate", 0.01, 0.99, 0.25, 0.01)
    adaptive = st.toggle("Adaptive Mutation", True)
    seed_val = st.number_input("Seed (None for random)", min_value=0, max_value=999999, value=42, step=1)
    seed_val = int(seed_val) if seed_val else None

    # Labels
    st.subheader("🏷️ Labels")
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
    st.subheader("📐 Constraints")
    repeat_val = st.number_input("Repeat (slots per course per day)", min_value=1, max_value=5, value=2)
    teacher_val = st.number_input("Teachers (simultaneous slots)", min_value=1, max_value=5, value=1)

    # Run button
    run_clicked = st.button("▶ Run Scheduler", use_container_width=True, type="primary")

# ── Main area ────────────────────────────────────────────────────────────────

if run_clicked:
    with st.spinner("Running genetic algorithm..."):
        sched = _build_scheduler(
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
        validation = analytics.get("validation", {})

        # Store in session state
        st.session_state.last_scheduler = sched
        st.session_state.last_analytics = analytics
        st.session_state.last_timetable = timetable

# ── Display results ──────────────────────────────────────────────────────────

if st.session_state.last_timetable:
    tables = st.session_state.last_timetable
    analytics = st.session_state.last_analytics or {}
    sched = st.session_state.last_scheduler

    # Analytics summary
    st.subheader("📊 Analytics")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("⏱ Runtime", f"{analytics.get('runtime_s', 0):.2f}s")
    with col_b:
        v = analytics.get("validation", {})
        st.metric("🔒 Violations", f"{v.get('total_violations', 0)}")
    with col_c:
        st.metric("💾 Cache hit", f"{analytics.get('cache_hit_ratio', 0) * 100:.1f}%")
    with col_d:
        st.metric("📦 Slots filled", f"{analytics.get('slots_filled', 0)}")

    st.divider()

    # Timetable display with tabs
    st.subheader("📅 Timetable")
    class_tabs = st.tabs([f"📋 {name}" for name in (sched.class_names if sched else class_names)])
    for idx, tab in enumerate(class_tabs):
        with tab:
            if idx < len(tables):
                class_table = tables[idx]
                html = _build_timetable_html(
                    class_table,
                    sched.class_names if sched else class_names,
                    sched.day_names if sched else day_names,
                    sched.course_names if sched else course_names,
                    slots_per_day,
                    num_days,
                    num_courses,
                )
                st.markdown(html, unsafe_allow_html=True)

    st.divider()

    # Course frequency chart
    st.subheader("📈 Course Frequency")
    freq = analytics.get("course_frequency", {})
    st.markdown(_build_frequency_chart(freq))

    # Validation details
    st.subheader("🔍 Constraint Violations")
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

    st.divider()

    # Export
    st.subheader("📤 Export")
    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        if st.button("📄 Export JSON", use_container_width=True):
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
        if st.button("📊 Export CSV", use_container_width=True):
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
        if st.button("🌐 Export HTML", use_container_width=True):
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
    st.info("Configure parameters in the sidebar and click **Run Scheduler** to generate a timetable.")

    # Show a preview of what the output looks like
    st.subheader("Preview")
    preview_html = """
    <div style="padding:3rem;text-align:center;color:#6b7280;">
        <p style="font-size:3rem;">🧬</p>
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
