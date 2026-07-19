"""Type aliases and shared data structures."""

from __future__ import annotations

from dataclasses import dataclass

# Domain types for readability
Gene = str
CourseNumber = int
SlotNumber = int
DayNumber = int
ClassNumber = int

# The 3-D timetable: tables[class_idx][day_idx][slot_idx] = course_number (1-based; 0 = unfilled)
Timetable = list[list[list[CourseNumber]]]

# Fitness cache: gene string → fitness score
FitnessCache = dict[Gene, float]


@dataclass
class GenerationStats:
    """Snapshot of one GA generation — collected for analytics / plotting.

    Attributes:
        generation:    Generation index (0-based).
        best_fitness:  Highest fitness in this generation.
        avg_fitness:   Mean fitness across the population.
        worst_fitness: Lowest fitness in this generation.
        mutation_rate: Effective mutation rate this generation (may be adaptive).
        elapsed_ms:    Wall-clock time this generation took in milliseconds.
    """

    generation: int
    best_fitness: float
    avg_fitness: float
    worst_fitness: float
    mutation_rate: float
    elapsed_ms: float


# Validation result structure
ValidationResult = dict[str, int]

# Analytics result structure
AnalyticsResult = dict[
    str,
    float | int | dict[str, int] | ValidationResult | list[dict[str, object]],
]
