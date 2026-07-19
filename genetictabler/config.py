"""
Timetable configuration dataclass.

All scheduling parameters collected in one clean container.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimetableConfig:
    """All knobs for the timetable generator.

    Attributes:
        classes: Number of distinct class groups (e.g. 6 year groups).
        courses: Number of distinct subjects (e.g. Math, English, ...).
        slots: Number of time-slots per day (e.g. 6 periods).
        days: Number of school days per week (typically 5).
        repeat: How many times per day a course may appear.
            ``int`` — same limit for every course.
            ``list[int]`` — per-course limits; length must equal ``courses``.
        teachers: How many teachers can teach a course simultaneously.
            This caps how many classes can share the same time slot.
            ``int`` — same for every course.
            ``list[int]`` — per-course counts.
        population_size: GA population size per slot-filling generation.
        max_fitness: Early-stop threshold (100.0 = perfect gene).
        max_generations: Hard cap on GA iterations per gene.
        elite_ratio: Fraction of top genes carried into the next generation.
        mutation_rate: Probability (0-1) that a child gene is mutated.
        adaptive: If ``True``, mutation rate rises when progress stalls.
        seed: Optional RNG seed for reproducibility.
    """

    classes: int = 6
    courses: int = 4
    slots: int = 6
    days: int = 5
    repeat: int | list[int] = 2
    teachers: int | list[int] = 1
    population_size: int = 60
    max_fitness: float = 100.0
    max_generations: int = 80
    elite_ratio: float = 0.10
    mutation_rate: float = 0.25
    adaptive: bool = True
    seed: int | None = None
