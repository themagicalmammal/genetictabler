"""Query helpers for timetable lookups.

All functions are pure and accept timetable data plus configuration.
"""

from __future__ import annotations

from genetictabler.types import Timetable


def get_class_timetable(
    tables: Timetable,
    class_names: list[str],
    class_name: str,
) -> list[list[int]] | None:
    """Retrieve the timetable for a specific class by name.

    Returns:
        2-D list ``[day][slot]`` = course_number, or ``None`` if not found.
    """
    if class_name not in class_names:
        return None
    idx = class_names.index(class_name)
    return tables[idx]


def find_course_slots(
    tables: Timetable,
    class_names: list[str],
    day_names: list[str],
    course_names: list[str],
    slot_count: int,
    course_name: str,
    class_name: str | None = None,
) -> list[tuple[str, str, str]]:
    """Find all scheduled occurrences of a course.

    Args:
        course_name: Must match one of ``course_names``.
        class_name: Optional filter; if ``None``, searches all classes.

    Returns:
        List of ``(class_name, day_name, "Slot N")`` tuples.
    """
    if course_name not in course_names:
        return []

    course_no = course_names.index(course_name) + 1
    results: list[tuple[str, str, str]] = []
    class_range = ([class_names.index(class_name)]
                   if class_name
                   else range(len(class_names)))

    for cls_idx in class_range:
        for day_idx in range(len(day_names)):
            for s in range(slot_count):
                if tables[cls_idx][day_idx][s] == course_no:
                    results.append((
                        class_names[cls_idx],
                        day_names[day_idx],
                        f"Slot {s + 1}",
                    ))
    return results


def get_teacher_schedule(
    tables: Timetable,
    class_names: list[str],
    day_names: list[str],
    course_names: list[str],
    slot_count: int,
    course_name: str,
) -> dict[str, list[str]]:
    """Build a teacher-eye view: which classes are taught in each slot.

    Returns:
        Dict like ``{"Mon Slot 2": ["Class-1", "Class-3"], ...}``.
    """
    if course_name not in course_names:
        return {}

    course_no = course_names.index(course_name) + 1
    schedule: dict[str, list[str]] = {}

    for day_idx, day_name in enumerate(day_names):
        for s in range(slot_count):
            classes_in_slot: list[str] = []
            for cls_idx, cls_name in enumerate(class_names):
                if tables[cls_idx][day_idx][s] == course_no:
                    classes_in_slot.append(cls_name)
            if classes_in_slot:
                schedule[f"{day_name} Slot {s + 1}"] = classes_in_slot

    return schedule
