"""Shared helper utilities for quota calculation and table generation."""

from __future__ import annotations

import random


def calc_course_quota(total_slots: int, course_count: int) -> list[int]:
    """Distribute the week's available slots evenly across all courses.

    If total_slots is perfectly divisible → every course gets ``total_slots // course_count``.
    Otherwise → some courses get ``+1`` slot, chosen randomly to avoid systematic bias.
    """
    q_max = total_slots // course_count
    remainder = total_slots % course_count

    if remainder == 0:
        return [q_max] * course_count

    flat_quota = [q_max + 1] * course_count
    extra_slots = (q_max + 1) * course_count - total_slots
    n = random.randint(1, course_count - extra_slots)
    for i in range(extra_slots):
        flat_quota[n + i] -= 1

    return flat_quota


def make_table_skeleton(
    class_count: int, day_count: int, slot_count: int
) -> list[list[list[int]]]:
    """Allocate the output timetable as a 3-D array of zeros.

    Structure: ``tables[class_idx][day_idx][slot_idx] = course_number``
    """
    return [[ [0] * slot_count for _ in range(day_count) ] for _ in range(class_count)]


def build_repeat_quota(
    repeat: int | list[int], course_count: int, class_count: int
) -> list[list[int]]:
    """Build per-class, per-course repeat quota arrays.

    ``repeat`` may be an int (same cap for every course) or a list of length ``course_count``.
    Each class gets its own independent copy.
    """
    if isinstance(repeat, int):
        flat_rep = [repeat] * course_count
    elif isinstance(repeat, list) and len(repeat) == course_count:
        flat_rep = list(repeat)
    else:
        raise ValueError(
            f"repeat must be an int OR a list of length {course_count}. "
            f"Got: {repeat!r}"
        )
    return [flat_rep[:] for _ in range(class_count)]


def build_teacher_quota(
    teachers: int | list[int], course_count: int
) -> list[int]:
    """Build per-course teacher quota array.

    ``teachers`` may be an int (same for every course) or a list of length ``course_count``.
    """
    if isinstance(teachers, int):
        return [teachers] * course_count
    elif isinstance(teachers, list) and len(teachers) == course_count:
        return list(teachers)
    else:
        raise ValueError(
            f"teachers must be an int OR a list of length {course_count}. "
            f"Got: {teachers!r}"
        )
