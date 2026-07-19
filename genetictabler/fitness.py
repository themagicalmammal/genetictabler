"""Fitness calculation for GA genes.

The fitness function starts at 100 and applies multiplicative penalties
for each constraint violation.  Hard penalties (×0.01) effectively zero out
a gene, while soft penalties (×0.60, ×0.50) stack gracefully.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from genetictabler.types import FitnessCache, Gene

if TYPE_CHECKING:
    from genetictabler.engine import EngineState


class FitnessEvaluator:
    """Stateless fitness calculator that reads from shared EngineState."""

    def __init__(self, state: EngineState, cache: FitnessCache) -> None:
        self._state = state
        self._cache = cache
        self.cache_hits = 0
        self.cache_misses = 0

    def calculate(self, gene: Gene) -> float:
        """Score a gene from 0.0 (awful) to 100.0 (perfect).

        Penalty catalogue:

        │ × 0.01  HARD — slot already occupied in this class
        │ × 0.60  SOFT — same course in this slot (another class)
        │ × 0.60  SOFT — course adjacent to self (same class/day)
        │ × 0.01  HARD — weekly quota exhausted
        │ × 0.01  HARD — course ≥ 2 times today
        │ × 0.50  SOFT — daily repeat cap exceeded
        │ × 0.01  HARD — teacher capacity saturated
        """
        # ── Cache lookup ─────────────────────────────────────────────────────
        if gene in self._cache:
            self.cache_hits += 1
            return self._cache[gene]
        self.cache_misses += 1
        self._state.total_genes_eval += 1

        fitness = 100.0

        # Decode gene components
        course = int(gene[: self._state.encoder.course_bits], 2)
        slot_no, day_no = self._state.encoder.extract_slot_day(gene)
        class_no = int(gene[self._state.encoder.course_bits + self._state.encoder.slot_bits :], 2)

        # Guard: encoded indices must be within valid range
        if (
            course < 1
            or course > self._state.encoder.course_count
            or class_no < 1
            or class_no > self._state.encoder.class_count
            or day_no < 1
            or day_no > self._state.encoder.day_count
            or slot_no < 1
            or slot_no > self._state.encoder.slot_count
        ):
            self._cache[gene] = 0.0
            return 0.0

        timetable = self._state.tables

        # ── 1. HARD: slot already occupied in target class ───────────────────
        if timetable[class_no - 1][day_no - 1][slot_no - 1] != 0:
            fitness *= 0.01

        # ── 2. SOFT: same course already in this slot (teacher clash) ────────
        for cls_idx in range(self._state.encoder.class_count):
            if timetable[cls_idx][day_no - 1][slot_no - 1] == course:
                fitness *= 0.60

        # ── 3. SOFT: course is adjacent to itself (bad for student attention) ─
        today_row = timetable[class_no - 1][day_no - 1]
        if slot_no > 1 and today_row[slot_no - 2] == course:
            fitness *= 0.60
        if slot_no < self._state.encoder.slot_count and today_row[slot_no] == course:
            fitness *= 0.60

        # ── 4. HARD: weekly course quota depleted ────────────────────────────
        if self._state.course_quota[class_no - 1][course - 1] < 1:
            fitness *= 0.01

        # ── 5. HARD: course appears twice+ today ─────────────────────────────
        if today_row.count(course) >= 2:
            fitness *= 0.01

        # ── 6. SOFT: exceeds per-course daily repeat allowance ───────────────
        if today_row.count(course) >= self._state.repeat_quota[class_no - 1][course - 1]:
            fitness *= 0.50

        # ── 7. HARD: teacher at capacity this slot across all classes ────────
        simultaneous = sum(
            1
            for cls_idx in range(self._state.encoder.class_count)
            if timetable[cls_idx][day_no - 1][slot_no - 1] == course
        )
        if simultaneous >= self._state.teacher_quota[course - 1]:
            fitness *= 0.01

        self._cache[gene] = fitness
        return fitness

    def invalidate(self) -> None:
        """Clear the fitness cache.

        Must be called after a gene is committed to the timetable,
        because existing cached scores may now be stale.
        """
        self._cache.clear()
