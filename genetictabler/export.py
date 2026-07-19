"""Export and display functions for completed timetables.

All functions are pure (no class state) and accept a timetable plus
configuration as arguments.
"""

from __future__ import annotations

import csv
import json

from genetictabler.types import Timetable


def pretty_print(
    tables: Timetable,
    course_names: list[str],
    class_names: list[str],
    day_names: list[str],
    slot_count: int,
    day_count: int,
    class_idx: int | None = None,
) -> None:
    """Print timetable(s) to the terminal in a grid format."""
    classes_to_print = range(len(class_names)) if class_idx is None else [class_idx]
    col_w = max(len(n) for n in course_names) + 2

    for cls in classes_to_print:
        print(f"\n{'=' * 50}")
        print(f"  {'\U0001f4da'}  {class_names[cls]}")
        print(f"{'=' * 50}")

        header = " " * 10
        for day_name in day_names:
            header += day_name.center(col_w)
        print(header)
        print(" " * 10 + ("─" * col_w * day_count))

        for s in range(slot_count):
            row_label = f"  Slot {s + 1}  │"
            row_str = row_label
            for d in range(day_count):
                course_no = tables[cls][d][s]
                label = "FREE" if course_no == 0 else course_names[course_no - 1]
                row_str += label.center(col_w)
            print(row_str)

    print()


def export_json(
    tables: Timetable,
    class_names: list[str],
    day_names: list[str],
    course_names: list[str],
    slot_count: int,
    filepath: str,
) -> None:
    """Save the timetable to a JSON file."""
    output: dict = {}
    for cls_idx, cls_name in enumerate(class_names):
        output[cls_name] = {}
        for day_idx, day_name in enumerate(day_names):
            slots_list = []
            for s in range(slot_count):
                cn = tables[cls_idx][day_idx][s]
                slots_list.append(course_names[cn - 1] if cn > 0 else "FREE")
            output[cls_name][day_name] = slots_list

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Timetable exported → {filepath}")


def export_csv(
    tables: Timetable,
    class_names: list[str],
    day_names: list[str],
    course_names: list[str],
    slot_count: int,
    filepath: str,
) -> None:
    """Save the timetable as a flat CSV file."""
    rows: list[list[str]] = [["Class", "Day", "Slot", "Course"]]
    for cls_idx, cls_name in enumerate(class_names):
        for day_idx, day_name in enumerate(day_names):
            for s in range(slot_count):
                cn = tables[cls_idx][day_idx][s]
                course_label = course_names[cn - 1] if cn > 0 else "FREE"
                rows.append([cls_name, day_name, f"Slot {s + 1}", course_label])

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"Timetable exported → {filepath}")


def export_html(
    tables: Timetable,
    class_names: list[str],
    day_names: list[str],
    course_names: list[str],
    slot_count: int,
    course_count: int,
    filepath: str,
) -> None:
    """Export a colour-coded HTML timetable — one table per class."""

    def course_colour(course_no: int) -> str:
        hue = int((course_no - 1) * 360 / max(course_count, 1))
        return f"hsl({hue}, 60%, 80%)"

    lines = [
        "<!DOCTYPE html><html><head>",
        "<meta charset='utf-8'>",
        "<title>Timetable</title>",
        "<style>",
        "  body { font-family: Arial, sans-serif; padding: 20px; }",
        "  table { border-collapse: collapse; margin-bottom: 30px; }",
        "  th, td { border: 1px solid #999; padding: 8px 14px; text-align: center; }",
        "  th { background: #444; color: #fff; }",
        "  h2 { margin-top: 40px; }",
        "</style></head><body>",
        "<h1>\U0001f4c5 Generated Timetable</h1>",
    ]

    for cls_idx, cls_name in enumerate(class_names):
        lines.append(f"<h2>{cls_name}</h2>")
        lines.append("<table>")
        header_cells = "<th>Slot</th>" + "".join(f"<th>{d}</th>" for d in day_names)
        lines.append(f"<tr>{header_cells}</tr>")

        for s in range(slot_count):
            cells = f"<td><b>Slot {s + 1}</b></td>"
            for d in range(len(day_names)):
                cn = tables[cls_idx][d][s]
                label = course_names[cn - 1] if cn > 0 else "FREE"
                colour = course_colour(cn) if cn > 0 else "#eee"
                cells += f"<td style='background:{colour}'>{label}</td>"
            lines.append(f"<tr>{cells}</tr>")

        lines.append("</table>")

    lines.append("</body></html>")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Timetable exported → {filepath}")
