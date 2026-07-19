"""Core scheduling engine: orchestrate encoding, fitness, genetic operators.

This is the main entry point for users. All other modules are called from here.

Lifecycle:
    1. ``GenerateTimeTable(...)`` or ``from_config(...)`` → set parameters
    2. ``run()``                                       → execute full scheduling
    3. ``validate()``                                  → check constraint violations
    4. ``analytics()``                                 → get performance summary
    5. ``export_*()``                                  → save results
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from genetictabler.config import TimetableConfig
from genetictabler.encoding import GeneEncoder
from genetictabler.fitness import FitnessEvaluator
from genetictabler.genetic import GeneticOperators
from genetictabler.types import (
    AnalyticsResult,
    FitnessCache,
    GenerationStats,
    Timetable,
    ValidationResult,
)
from genetictabler.utils import (
    build_repeat_quota,
    build_teacher_quota,
    calc_course_quota,
    make_table_skeleton,
)

if TYPE_CHECKING:
    pass


class EngineState:
    """Shared mutable state accessed by encoder, evaluator, and operators."""

    def __init__(self, encoder: GeneEncoder) -> None:
        self.encoder = encoder
        self.tables: Timetable = []
        self.course_quota: list[list[int]] = []
        self.teacher_quota: list[int] = []
        self.repeat_quota: list[list[int]] = []
        self.total_genes_eval: int = 0


class GenerateTimeTable:
    """Genetic algorithm timetable scheduler.

    Usage::

        scheduler = GenerateTimeTable(classes=4, courses=6, slots=6, days=5, seed=42)
        timetable = scheduler.run()
        scheduler.pretty_print()
    """

    # ── Construction ───────────────────────────────────────────────────────

    def __init__(
        self,
        classes: int = 6,
        courses: int = 4,
        slots: int = 6,
        days: int = 5,
        repeat: int | list[int] = 2,
        teachers: int | list[int] = 1,
        population_size: int = 60,
        max_fitness: float = 100.0,
        max_generations: int = 80,
        elite_ratio: float = 0.10,
        mutation_rate: float = 0.25,
        adaptive: bool = True,
        seed: int | None = None,
        course_names: list[str] | None = None,
        class_names: list[str] | None = None,
        day_names: list[str] | None = None,
    ) -> None:
        if seed is not None:
            import random as _random

            _random.seed(seed)

        self.classes = classes
        self.courses = courses
        self.slots = slots
        self.days = days
        self.repeat = repeat
        self.teachers = teachers
        self.population_size = population_size
        self.max_fitness = max_fitness
        self.max_generations = max_generations
        self.elite_ratio = elite_ratio
        self.mutation_rate = mutation_rate
        self.adaptive = adaptive
        self.seed = seed

        self.course_names: list[str] = course_names or [
            f"Course-{i + 1}" for i in range(courses)
        ]
        self.class_names: list[str] = class_names or [
            f"Class-{i + 1}" for i in range(classes)
        ]
        self.day_names: list[str] = (
            day_names
            or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sat"][:days]
        )

        self._config = TimetableConfig(
            classes=classes,
            courses=courses,
            slots=slots,
            days=days,
            repeat=repeat,
            teachers=teachers,
            population_size=population_size,
            max_fitness=max_fitness,
            max_generations=max_generations,
            elite_ratio=elite_ratio,
            mutation_rate=mutation_rate,
            adaptive=adaptive,
            seed=seed,
        )

        # Component instances (built in run())
        self._encoder: GeneEncoder | None = None
        self._evaluator: FitnessEvaluator | None = None
        self._genetic: GeneticOperators | None = None
        self._state: EngineState | None = None
        self._cache: FitnessCache = {}
        self._generation_log: list[GenerationStats] = []
        self._run_start_time: float = 0.0
        self._slots_filled: int = 0

    @property
    def tables(self) -> Timetable:
        """Access the 3-D timetable. Raises if run() has not been called."""
        if self._state is None:
            return []
        return self._state.tables

    @classmethod
    def from_config(
        cls, config: TimetableConfig, **kwargs
    ) -> GenerateTimeTable:
        """Construct from a TimetableConfig dataclass."""
        return cls(
            classes=config.classes,
            courses=config.courses,
            slots=config.slots,
            days=config.days,
            repeat=config.repeat,
            teachers=config.teachers,
            population_size=config.population_size,
            max_fitness=config.max_fitness,
            max_generations=config.max_generations,
            elite_ratio=config.elite_ratio,
            mutation_rate=config.mutation_rate,
            adaptive=config.adaptive,
            seed=config.seed,
            **kwargs,
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _build_components(self) -> tuple[int, int, int]:
        """Initialise encoding, quotas, and return (course_bits, slot_bits, total_cells)."""
        config = self._config
        encoder = GeneEncoder(config)
        encoder.course_bits = len(bin(config.courses)) - 2
        encoder.slot_bits = len(bin(config.slots * config.days)) - 2
        encoder.class_bits = len(bin(config.classes)) - 2

        # Quotas
        flat_quota = calc_course_quota(config.slots * config.days, config.courses)
        course_quota = [flat_quota[:] for _ in range(config.classes)]
        teacher_quota = build_teacher_quota(config.teachers, config.courses)
        repeat_quota = build_repeat_quota(config.repeat, config.courses, config.classes)

        state = EngineState(encoder)
        state.encoder = encoder
        state.course_quota = course_quota
        state.teacher_quota = teacher_quota
        state.repeat_quota = repeat_quota

        self._cache = {}
        self._encoder = encoder
        self._evaluator = FitnessEvaluator(state, self._cache)
        self._genetic = GeneticOperators(
            encoder, self._evaluator,
            self.elite_ratio, self.mutation_rate, self.adaptive,
        )
        self._state = state

        total_cells = config.slots * config.days * config.classes
        return encoder.course_bits, encoder.slot_bits, total_cells

    # ── Public API ─────────────────────────────────────────────────────────

    def run(self) -> Timetable:
        """Execute the full scheduling algorithm.

        Returns:
            3-D list ``tables[class][day][slot]`` containing 1-based course
            numbers (0 = unfilled).
        """
        if self.seed is not None:
            random.seed(self.seed)

        self._run_start_time = time.perf_counter()

        course_bits, slot_bits, total_cells = self._build_components()
        encoder = self._encoder  # type: ignore[assignment]
        state = self._state  # type: ignore[assignment]
        config = self._config

        # Generate blank timetable
        state.tables = make_table_skeleton(
            config.classes, config.days, config.slots
        )

        print(f"\nGenetictabler — {config.classes} classes, {config.courses} courses, "
              f"{config.slots} slots/day, {config.days} days")
        print(f"Gene encoding: {course_bits}+{encoder.slot_bits}+{encoder.class_bits} bits\n")

        remaining = total_cells
        while remaining > 0:
            gene = self._run_evolution(course_bits, slot_bits)
            if self._evaluator.calculate(gene) > 0:  # type: ignore[union-attr]
                self._fit_slot(gene)
                remaining -= 1
            else:
                gene = encoder.generate_gene()
                self._fit_slot(gene)
                remaining -= 1

            filled = total_cells - remaining
            if filled % max(1, total_cells // 10) == 0 or remaining == 0:
                pct = 100 * filled // total_cells
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                elapsed = time.perf_counter() - self._run_start_time
                print(f"  [{bar}] {pct:3d}% ({filled}/{total_cells}) {elapsed:.1f}s\r", end="")

        elapsed_total = time.perf_counter() - self._run_start_time
        print(f"\n\nScheduling complete in {elapsed_total:.2f}s  "
              f"({self._state.total_genes_eval:,} genes, "
              f"{self._evaluator.cache_hits:,} cache hits)\n")  # type: ignore[union-attr]

        return state.tables

    def validate(self) -> ValidationResult:
        """Scan the timetable for constraint violations."""
        from genetictabler.validation import validate as validate_mod

        if not self._state or not self._encoder:
            return {"empty_cells": 0, "teacher_clashes": 0, "back_to_back": 0, "total_violations": 0}
        return validate_mod(
            self._state.tables,
            self._encoder,
            self._state.teacher_quota,
            self._config.classes,
            self._config.days,
            self._config.slots,
        )

    def analytics(self) -> AnalyticsResult:
        """Return a performance summary of the last run."""
        runtime = time.perf_counter() - self._run_start_time
        total_evals = self._evaluator.cache_hits + self._evaluator.cache_misses  # type: ignore[union-attr]
        hit_ratio = self._evaluator.cache_hits / total_evals if total_evals else 0.0

        if not self._state:
            return {
                "runtime_s": 0.0,
                "genes_evaluated": 0,
                "cache_hit_ratio": 0.0,
                "course_frequency": {},
                "validation": {"empty_cells": 0, "teacher_clashes": 0, "back_to_back": 0, "total_violations": 0},
                "slots_filled": 0,
                "generation_log_tail": [],
            }

        encoder = self._encoder
        freq: dict[str, int] = {}
        for cls_idx in range(encoder.class_count):
            for day_idx in range(encoder.day_count):
                for slot_idx in range(encoder.slot_count):
                    cn = self._state.tables[cls_idx][day_idx][slot_idx]
                    if cn > 0:
                        label = self.course_names[cn - 1]
                        freq[label] = freq.get(label, 0) + 1

        validation = self.validate()
        tail = [vars(s) for s in self._generation_log[-5:]]

        return {
            "runtime_s": runtime,
            "genes_evaluated": self._state.total_genes_eval,
            "cache_hit_ratio": round(hit_ratio, 4),
            "course_frequency": freq,
            "validation": validation,
            "slots_filled": self._slots_filled,
            "generation_log_tail": tail,
        }

    def reset(self) -> None:
        """Reset the scheduler so it can be run again."""
        self._encoder = None
        self._evaluator = None
        self._genetic = None
        self._state = None
        self._cache.clear()
        self._generation_log.clear()
        self._slots_filled = 0
        self._run_start_time = 0.0
        if self.seed is not None:
            random.seed(self.seed)

    # ── Display / Export / Queries ─────────────────────────────────────────

    def pretty_print(self, class_idx: int | None = None) -> None:
        """Print timetable(s) to the terminal in a grid format."""
        assert self._encoder is not None
        from genetictabler.export import pretty_print as _pp

        _pp(
            self._state.tables,
            self.course_names,
            self.class_names,
            self.day_names,
            self._config.slots,
            self._config.days,
            class_idx,
        )

    def export_json(self, filepath: str = "timetable.json") -> None:
        """Save the completed timetable to a JSON file."""
        from genetictabler.export import export_json as _ej

        _ej(
            self._state.tables,
            self.class_names,
            self.day_names,
            self.course_names,
            self._config.slots,
            filepath,
        )

    def export_csv(self, filepath: str = "timetable.csv") -> None:
        """Save the timetable as a flat CSV file."""
        from genetictabler.export import export_csv as _ec

        _ec(
            self._state.tables,
            self.class_names,
            self.day_names,
            self.course_names,
            self._config.slots,
            filepath,
        )

    def export_html(self, filepath: str = "timetable.html") -> None:
        """Export a colour-coded HTML timetable."""
        from genetictabler.export import export_html as _eh

        _eh(
            self._state.tables,
            self.class_names,
            self.day_names,
            self.course_names,
            self._config.slots,
            self._config.courses,
            filepath,
        )

    def print_analytics(self) -> None:
        """Print a formatted analytics summary to the terminal."""
        a = self.analytics()
        v = a["validation"]
        print("┌─────────────────────────────────────────┐")
        print("│           RUN ANALYTICS                 │")
        print("├─────────────────────────────────────────┤")
        print(f"│  Runtime          : {a['runtime_s']:.2f}s")
        print(f"│  Genes evaluated  : {a['genes_evaluated']:,}")
        print(f"│  Cache hit ratio  : {a['cache_hit_ratio']*100:.1f}%")
        print(f"│  Slots filled     : {a['slots_filled']}")
        print("├─────────────────────────────────────────┤")
        print(f"│  Empty cells      : {v['empty_cells']}")
        print(f"│  Teacher clashes  : {v['teacher_clashes']}")
        print(f"│  Back-to-back     : {v['back_to_back']}")
        print(f"│  Total violations : {v['total_violations']}")
        print("├─────────────────────────────────────────┤")
        print("│  Course frequency:")
        for course, cnt in sorted(a["course_frequency"].items()):
            bar = "▓" * (cnt // 2)
            print(f"│    {course:<15} {cnt:3d}  {bar}")
        print("└─────────────────────────────────────────┘\n")

    def get_class_timetable(self, class_name: str) -> list[list[int]] | None:
        """Retrieve the timetable for a specific class by name."""
        assert self._encoder is not None
        from genetictabler.queries import get_class_timetable as _gct

        return _gct(self._state.tables, self.class_names, class_name)

    def find_course_slots(
        self, course_name: str, class_name: str | None = None
    ) -> list[tuple[str, str, str]]:
        """Find all scheduled occurrences of a course."""
        assert self._encoder is not None
        from genetictabler.queries import find_course_slots as _fcs

        return _fcs(
            self._state.tables,
            self.class_names,
            self.day_names,
            self.course_names,
            self._config.slots,
            course_name,
            class_name,
        )

    def get_teacher_schedule(self, course_name: str) -> dict[str, list[str]]:
        """Build a teacher-eye view for a subject."""
        assert self._encoder is not None
        from genetictabler.queries import get_teacher_schedule as _gts

        return _gts(
            self._state.tables,
            self.class_names,
            self.day_names,
            self.course_names,
            self._config.slots,
            course_name,
        )

    # ── Legacy public API (wrappers for test compatibility) ────────────────

    def initialize_genotype(
        self,
        courses: int,
        classes: int,
        slots: int,
        days: int,
        repeat: int | list[int],
        teachers: int | list[int],
    ) -> tuple[int, int, int]:
        """Initialise encoding constants, quotas, and component instances.

        Returns:
            ``(course_bits, slot_bits, total_cells)``
        """
        config = self._config
        encoder = GeneEncoder(config)
        encoder.course_bits = len(bin(courses)) - 2
        encoder.slot_bits = len(bin(slots * days)) - 2
        encoder.class_bits = len(bin(classes)) - 2
        encoder.course_count = courses
        encoder.slot_count = slots
        encoder.day_count = days
        encoder.class_count = classes
        encoder.total_slots = slots * days

        flat_quota = calc_course_quota(slots * days, courses)
        course_quota = [flat_quota[:] for _ in range(classes)]
        teacher_quota = build_teacher_quota(teachers, courses)
        repeat_quota = build_repeat_quota(repeat, courses, classes)

        state = EngineState(encoder)
        state.encoder = encoder
        state.course_quota = course_quota
        state.teacher_quota = teacher_quota
        state.repeat_quota = repeat_quota

        self._cache = {}
        self._encoder = encoder
        self._evaluator = FitnessEvaluator(state, self._cache)
        self._genetic = GeneticOperators(
            encoder, self._evaluator,
            self.elite_ratio, self.mutation_rate, self.adaptive,
        )
        self._state = state

        total_cells = slots * days * classes
        return encoder.course_bits, encoder.slot_bits, total_cells

    def generate_table_skeleton(self) -> None:
        """Create a blank 3-D timetable (all zeros)."""
        assert self._state is not None
        self._state.tables = make_table_skeleton(
            self._config.classes, self._config.days, self._config.slots,
        )

    @property
    def course_bits(self) -> int:
        """Width (in bits) of the course portion of a gene."""
        assert self._encoder is not None
        return self._encoder.course_bits

    @property
    def slot_bits(self) -> int:
        """Width (in bits) of the slot portion of a gene."""
        assert self._encoder is not None
        return self._encoder.slot_bits

    @property
    def class_bits(self) -> int:
        """Width (in bits) of the class portion of a gene."""
        assert self._encoder is not None
        return self._encoder.class_bits

    @property
    def gene_len(self) -> int:
        """Total length of a gene string in bits."""
        assert self._encoder is not None
        return self._encoder.course_bits + self._encoder.slot_bits + self._encoder.class_bits

    @property
    def total_slots(self) -> int:
        """Total number of slots across all days."""
        assert self._encoder is not None
        return self._encoder.total_slots

    @property
    def course_count(self) -> int:
        """Number of courses."""
        assert self._encoder is not None
        return self._encoder.course_count

    @property
    def _calc_course_quota(self) -> staticmethod:
        """Expose calc_course_quota for test compatibility."""
        return staticmethod(calc_course_quota)

    @property
    def _make_table_skeleton(self) -> staticmethod:
        """Expose make_table_skeleton for test compatibility."""
        return staticmethod(make_table_skeleton)

    @property
    def _build_repeat_quota(self) -> staticmethod:
        """Expose build_repeat_quota for test compatibility."""
        return staticmethod(build_repeat_quota)

    @property
    def _build_teacher_quota(self) -> staticmethod:
        """Expose build_teacher_quota for test compatibility."""
        return staticmethod(build_teacher_quota)

    # ── State accessors for test compatibility ─────────────────────────────

    @property
    def repeat_quota(self) -> list[list[int]]:
        """Repeat quota per class (accessed directly in tests)."""
        assert self._state is not None
        return self._state.repeat_quota

    @property
    def teacher_quota(self) -> list[int]:
        """Teacher quota per course (accessed directly in tests)."""
        assert self._state is not None
        return self._state.teacher_quota

    @property
    def course_quota(self) -> list[list[int]]:
        """Course quota per class (accessed directly in tests)."""
        assert self._state is not None
        return self._state.course_quota

    @property
    def _total_genes_eval(self) -> int:
        """Total genes evaluated (accessed directly in tests)."""
        if self._state is None:
            return 0
        return self._state.total_genes_eval

    @property
    def _cache_hits(self) -> int:
        """Number of fitness cache hits."""
        if self._evaluator is None:
            return 0
        return self._evaluator.cache_hits

    @_cache_hits.setter
    def _cache_hits(self, value: int) -> None:
        if self._evaluator is not None:
            self._evaluator.cache_hits = value

    @property
    def _cache_misses(self) -> int:
        """Number of fitness cache misses."""
        if self._evaluator is None:
            return 0
        return self._evaluator.cache_misses

    @_cache_misses.setter
    def _cache_misses(self, value: int) -> None:
        if self._evaluator is not None:
            self._evaluator.cache_misses = value

    # Additional aliases for test compatibility

    @property
    def _fitness_cache(self) -> FitnessCache:
        """Alias for the internal fitness cache dict (tests clear it directly)."""
        return self._cache

    @_fitness_cache.setter
    def _fitness_cache(self, value: FitnessCache) -> None:
        self._cache = value

    @property
    def slot_count(self) -> int:
        """Number of slots per day."""
        assert self._encoder is not None
        return self._encoder.slot_count

    @property
    def class_count(self) -> int:
        """Number of classes."""
        assert self._encoder is not None
        return self._encoder.class_count

    @property
    def day_count(self) -> int:
        """Number of days."""
        assert self._encoder is not None
        return self._encoder.day_count

    # Alias for _calc_course_quota
    @property
    def _calc_course_quota_alias(self) -> staticmethod:
        return staticmethod(calc_course_quota)

    def _to_binary(self, value: int, bit_length: int) -> str:
        """Convert an integer to a zero-padded binary string."""
        assert self._encoder is not None
        return self._encoder.to_binary(value, bit_length)

    def encode_course(self) -> str:
        """Encode a random course (1 … courses) as binary."""
        assert self._encoder is not None
        return self._encoder.encode_course()

    def encode_slot(self) -> str:
        """Encode a random cumulative slot (1 … total_slots) as binary."""
        assert self._encoder is not None
        return self._encoder.encode_slot()

    def encode_class(self) -> str:
        """Encode a random class (1 … classes) as binary."""
        assert self._encoder is not None
        return self._encoder.encode_class()

    def generate_gene(self) -> str:
        """Generate a complete random gene string."""
        assert self._encoder is not None
        return self._encoder.generate_gene()

    def decode_gene(self, gene: str) -> tuple[int, int, int, int]:
        """Decode a gene into ``(course_no, slot_no, day_no, class_no)``."""
        assert self._encoder is not None
        return self._encoder.decode_gene(gene)

    def extract_slot_day(self, gene: str) -> tuple[int, int]:
        """Extract ``(slot, day)`` from the slot portion of a gene."""
        assert self._encoder is not None
        return self._encoder.extract_slot_day(gene)

    def calculate_fitness(self, gene: str) -> float:
        """Calculate the fitness of a single gene."""
        assert self._evaluator is not None
        return self._evaluator.calculate(gene)

    def invalidate_cache(self) -> None:
        """Clear the fitness cache."""
        assert self._evaluator is not None
        self._evaluator.invalidate()

    def single_point_crossover(
        self, parent_a: str, parent_b: str
    ) -> list[str]:
        """Single-point crossover — return list of child genes."""
        assert self._genetic is not None
        return self._genetic.single_point_crossover(parent_a, parent_b)

    def multi_point_crossover(
        self, parent_a: str, parent_b: str, points: int = 2
    ) -> list[str]:
        """Multi-point crossover — return list of child genes."""
        assert self._genetic is not None
        return self._genetic.multi_point_crossover(parent_a, parent_b, points)

    def uniform_crossover(self, parent_a: str, parent_b: str) -> list[str]:
        """Uniform crossover — return list of child genes."""
        assert self._genetic is not None
        return self._genetic.uniform_crossover(parent_a, parent_b)

    def mutation(
        self, gene: str, course_bits: int, slot_bits: int
    ) -> str:
        """Random bit-flip mutation."""
        assert self._genetic is not None
        return self._genetic.mutation(gene)

    def smart_mutation(
        self,
        gene: str,
        course_bits: int,
        slot_bits: int,
        attempts: int = 10,
    ) -> str:
        """Mutation that tries multiple flips and keeps the best."""
        assert self._genetic is not None
        return self._genetic.smart_mutation(gene)

    def selection_pair(self, population: list[str]) -> tuple[str, str]:
        """Select two parents via roulette-wheel selection."""
        assert self._genetic is not None
        return self._genetic.selection_pair(population)

    def tournament_selection(
        self, population: list[str], tournament_size: int = 3
    ) -> str:
        """Select one winner via tournament selection."""
        assert self._genetic is not None
        return self._genetic.tournament_selection(population, tournament_size)

    def sort_population(self, population: list[str]) -> list[str]:
        """Return population sorted by fitness (descending)."""
        assert self._genetic is not None
        return self._genetic.sort_population(population)

    def generate_population(self, size: int) -> list[str]:
        """Generate a random initial population of genes."""
        assert self._genetic is not None
        return self._genetic.generate_population(size)

    def fit_slot(self, gene: str) -> None:
        """Commit a gene to the timetable."""
        self._fit_slot(gene)

    def run_evolution(
        self,
        course_bits: int,
        slot_bits: int,
        population_size: int = 60,
        max_fitness: float = 100.0,
        max_generations: int = 80,
    ) -> str:
        """Run the GA for one slot and return the best gene.

        This is the legacy public entry-point for slot-by-slot evolution.
        """
        assert self._encoder is not None
        assert self._evaluator is not None
        assert self._genetic is not None
        assert self._state is not None

        elite_count = max(2, int(population_size * self.elite_ratio))
        mut_rate = self.mutation_rate
        stale_count = 0
        prev_best = -1.0
        local_gen_log: list[GenerationStats] = []

        population = self._genetic.generate_population(population_size)

        for gen_idx in range(max_generations):
            t0 = time.perf_counter()
            population = self._genetic.sort_population(population)
            fitnesses = [self._evaluator.calculate(g) for g in population]
            best_f = fitnesses[0]
            avg_f = sum(fitnesses) / len(fitnesses)
            worst_f = fitnesses[-1]

            local_gen_log.append(GenerationStats(
                generation=gen_idx,
                best_fitness=best_f,
                avg_fitness=avg_f,
                worst_fitness=worst_f,
                mutation_rate=mut_rate,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
            ))

            if best_f >= max_fitness:
                self._generation_log.extend(local_gen_log)
                return population[0]

            if self.adaptive:
                if best_f <= prev_best + 0.001:
                    stale_count += 1
                    if stale_count >= 5:
                        mut_rate = min(0.95, self.mutation_rate * 3.0)
                else:
                    stale_count = 0
                    mut_rate = self.mutation_rate
            prev_best = best_f

            next_gen = population[:elite_count]
            remaining = population_size - elite_count
            pairs = remaining // 2

            for _ in range(pairs):
                if random.random() < 0.5:  # type: ignore[name-defined]
                    p_a = self._genetic.tournament_selection(population)
                    p_b = self._genetic.tournament_selection(population)
                else:
                    p_a, p_b = self._genetic.selection_pair(population)

                if random.random() < 0.15:  # type: ignore[name-defined]
                    children = self._genetic.uniform_crossover(p_a, p_b)
                else:
                    children = self._genetic.single_point_crossover(p_a, p_b)

                for child in children:
                    if random.random() < mut_rate:  # type: ignore[name-defined]
                        if gen_idx > max_generations // 2:
                            child = self._genetic.smart_mutation(child)
                        else:
                            child = self._genetic.mutation(child)
                    next_gen.append(child)

            if len(next_gen) < population_size:
                next_gen.append(self._encoder.generate_gene())

            population = next_gen

        self._generation_log.extend(local_gen_log)
        return self._genetic.sort_population(population)[0]

    # ── Internal ───────────────────────────────────────────────────────────

    def _fit_slot(self, gene: str) -> None:
        """Commit a gene to the timetable and decrement its quota."""
        encoder = self._encoder  # type: ignore[union-attr]
        state = self._state  # type: ignore[union-attr]

        course = int(gene[: encoder.course_bits], 2)
        slot_no, day_no = encoder.extract_slot_day(gene)
        class_no = int(gene[encoder.course_bits + encoder.slot_bits :], 2)

        state.tables[class_no - 1][day_no - 1][slot_no - 1] = course
        state.course_quota[class_no - 1][course - 1] -= 1
        self._evaluator.invalidate()  # type: ignore[union-attr]
        self._slots_filled += 1

    def _run_evolution(self, course_bits: int, slot_bits: int) -> str:
        """Run the GA for one slot and return the best gene found."""
        assert self._genetic is not None
        assert self._encoder is not None
        assert self._state is not None
        assert self._evaluator is not None

        population = self._genetic.generate_population(self.population_size)
        elite_count = max(2, int(self.population_size * self.elite_ratio))
        mut_rate = self.mutation_rate
        stale_count = 0
        prev_best = -1.0
        config = self._config

        for gen_idx in range(self.max_generations):
            t0 = time.perf_counter()
            population = self._genetic.sort_population(population)
            fitnesses = [self._evaluator.calculate(g) for g in population]
            best_f = fitnesses[0]
            avg_f = sum(fitnesses) / len(fitnesses)
            worst_f = fitnesses[-1]

            self._generation_log.append(GenerationStats(
                generation=gen_idx,
                best_fitness=best_f,
                avg_fitness=avg_f,
                worst_fitness=worst_f,
                mutation_rate=mut_rate,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
            ))

            if best_f >= config.max_fitness:
                return population[0]

            if self.adaptive:
                if best_f <= prev_best + 0.001:
                    stale_count += 1
                    if stale_count >= 5:
                        mut_rate = min(0.95, self.mutation_rate * 3.0)
                else:
                    stale_count = 0
                    mut_rate = self.mutation_rate
            prev_best = best_f

            next_gen = population[:elite_count]
            remaining = self.population_size - elite_count
            pairs = remaining // 2

            for _ in range(pairs):
                if random.random() < 0.5:  # type: ignore[name-defined]
                    p_a = self._genetic.tournament_selection(population)
                    p_b = self._genetic.tournament_selection(population)
                else:
                    p_a, p_b = self._genetic.selection_pair(population)

                if random.random() < 0.15:  # type: ignore[name-defined]
                    children = self._genetic.uniform_crossover(p_a, p_b)
                else:
                    children = self._genetic.single_point_crossover(p_a, p_b)

                for child in children:
                    if random.random() < mut_rate:  # type: ignore[name-defined]
                        if gen_idx > self.max_generations // 2:
                            child = self._genetic.smart_mutation(child)
                        else:
                            child = self._genetic.mutation(child)
                    next_gen.append(child)

            if len(next_gen) < self.population_size:
                next_gen.append(self._encoder.generate_gene())

            population = next_gen

        return self._genetic.sort_population(population)[0]
