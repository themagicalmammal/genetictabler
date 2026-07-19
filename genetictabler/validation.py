"""Constraint violation validation for completed timetables."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from genetictabler.encoding import GeneEncoder
    from genetictabler.types import Timetable, ValidationResult


def validate(
    tables: Timetable,
    encoder: GeneEncoder,
    teacher_quota: list[int],
    class_count: int,
    day_count: int,
    slot_count: int,
) -> ValidationResult:
    """Scan the completed timetable for constraint violations.

    Checks performed:
      * Empty cells (unfilled slots)
      * Double-booked slots (same class, same slot, used twice)
      * Teacher clashes (same course in same slot across too many classes)
      * Back-to-back repetitions (same course in consecutive slots, same class)

    Returns:
        Dict with keys: ``empty_cells``, ``teacher_clashes``,
        ``back_to_back``, ``total_violations``.
    """
    empty = 0
    clashes = 0
    back2back = 0

    for day in range(day_count):
        for slot in range(slot_count):
            slot_courses = Counter(
                tables[cls][day][slot] for cls in range(class_count)
            )
            for course, count in slot_courses.items():
                if course == 0:
                    empty += count
                elif count > teacher_quota[course - 1]:
                    clashes += count - teacher_quota[course - 1]

    for cls in range(class_count):
        for day in range(day_count):
            row = tables[cls][day]
            for s in range(slot_count - 1):
                if row[s] != 0 and row[s] == row[s + 1]:
                    back2back += 1

    total = empty + clashes + back2back
    return {
        "empty_cells": empty,
        "teacher_clashes": clashes,
        "back_to_back": back2back,
        "total_violations": total,
    }
