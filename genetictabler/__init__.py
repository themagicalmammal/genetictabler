"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                 TIMETABLE GENERATOR — GENETIC ALGORITHM ENGINE                   ║
║                                                                                  ║
║  Generates optimized school/university timetables using evolutionary computing.  ║
║  Features: elitism, adaptive mutation, multi-point crossover, fitness caching,   ║
║  analytics, visualisation, export, and full validation.                          ║
╚══════════════════════════════════════════════════════════════════════════════════╝

HOW IT WORKS (Overview):
────────────────────────
1.  Each possible course assignment (course + slot + class) is encoded as a binary
    "gene" string.
2.  A random "population" of genes is spawned.
3.  Each gene is scored with a fitness function (penalties for clashes, overuse, etc.)
4.  The fittest genes survive, reproduce (crossover), and occasionally mutate.
5.  After many generations the best gene for that slot is committed to the timetable.
6.  Steps 3-5 repeat until every slot in every class is filled.

ENCODING:
─────────
  Gene = <course_bits> + <slot_bits> + <class_bits>
  e.g.  "010" + "00101" + "011"  → course 2, slot 5, class 3

"""

import copy
import csv
import json
import math
import os
import random

# ─── Standard Library ────────────────────────────────────────────────────────
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union

# ─── Optional Rich terminal output (falls back to plain print gracefully) ────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text

    _RICH = True
    console = Console()
except ImportError:
    _RICH = False
    console = None  # plain print fallback

# ══════════════════════════════════════════════════════════════════════════════
#  DATA CLASSES — typed containers used throughout the engine
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class TimetableConfig:
    """
    All knobs exposed to the user collected in one clean container.

    Attributes:
        classes         – Number of distinct class groups (e.g. 6 year groups)
        courses         – Number of distinct subjects (e.g. Math, English …)
        slots           – Number of time-slots per day (e.g. 6 periods)
        days            – Number of school days per week (typically 5)
        repeat          – How many times per day a course may appear:
                            int  → same limit for every course
                            list → per-course limits, len must equal `courses`
        teachers        – How many teachers can teach a course simultaneously
                          (limits how many classes share the same slot):
                            int  → same for every course
                            list → per-course counts
        population_size – GA population per slot-filling generation
        max_fitness     – Early-stop threshold (100 = perfect gene)
        max_generations – Hard cap on GA iterations per gene
        elite_ratio     – Fraction of top genes carried into next generation
        mutation_rate   – Probability 0-1 that a child gene is mutated
        adaptive        – If True, mutation_rate rises when progress stalls
        seed            – Optional RNG seed for reproducibility
    """

    classes: int = 6
    courses: int = 4
    slots: int = 6
    days: int = 5
    repeat: Union[int, list] = 2
    teachers: Union[int, list] = 1
    population_size: int = 60
    max_fitness: float = 100.0
    max_generations: int = 80
    elite_ratio: float = 0.10  # top 10 % survive unchanged
    mutation_rate: float = 0.25  # 25 % of children are mutated
    adaptive: bool = True  # ramp mutation when stuck
    seed: Optional[int] = None


@dataclass
class GenerationStats:
    """
    Snapshot of one GA generation — collected for analytics / plotting.

    Attributes:
        generation   – Generation index (0-based)
        best_fitness – Highest fitness in this generation
        avg_fitness  – Mean fitness across population
        worst_fitness– Lowest fitness in this generation
        mutation_rate– Effective mutation rate this generation (may be adaptive)
        elapsed_ms   – Wall-clock time this generation took in milliseconds
    """

    generation: int
    best_fitness: float
    avg_fitness: float
    worst_fitness: float
    mutation_rate: float
    elapsed_ms: float


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENGINE CLASS
# ══════════════════════════════════════════════════════════════════════════════


class GenerateTimeTable:
    """
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  GENETIC ALGORITHM TIMETABLE SCHEDULER                                  │
    │                                                                         │
    │  Lifecycle:                                                             │
    │    1. __init__  / from_config  → set parameters                        │
    │    2. run()                    → execute full scheduling                │
    │    3. pretty_print()           → display in terminal                   │
    │    4. export_json / export_csv → save results                          │
    │    5. analytics()              → generation-by-generation stats        │
    └─────────────────────────────────────────────────────────────────────────┘
    """

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(
        self,
        classes: int = 6,
        courses: int = 4,
        slots: int = 6,
        days: int = 5,
        repeat: Union[int, list] = 2,
        teachers: Union[int, list] = 1,
        population_size: int = 60,
        max_fitness: float = 100.0,
        max_generations: int = 80,
        elite_ratio: float = 0.10,
        mutation_rate: float = 0.25,
        adaptive: bool = True,
        seed: Optional[int] = None,
        course_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        day_names: Optional[List[str]] = None,
    ):
        """
        Initialise the scheduler.  All parameters have sensible defaults so you
        can start with `GenerateTimeTable().run()` immediately.

        Extra cosmetic parameters (not in original):
            course_names – human-readable course labels, e.g. ["Math","PE",…]
            class_names  – human-readable class labels, e.g. ["Year 1","Year 2"]
            day_names    – human-readable day labels,   e.g. ["Mon","Tue",…]
        """
        # ── Seed RNG first so everything downstream is reproducible ──────────
        if seed is not None:
            random.seed(seed)

        # ── User-supplied parameters ─────────────────────────────────────────
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

        # ── Human-readable labels (auto-generated if not supplied) ───────────
        self.course_names = course_names or [
            f"Course-{i+1}" for i in range(courses)
        ]
        self.class_names = class_names or [
            f"Class-{i+1}" for i in range(classes)
        ]
        self.day_names = (day_names
                          or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sat"
                              ][:days])

        # ── Derived encoding constants (populated by initialize_genotype) ────
        self.course_count = 0  # validated copy of `courses`
        self.slot_count = 0  # validated copy of `slots`
        self.day_count = 0  # validated copy of `days`
        self.class_count = 0  # validated copy of `classes`
        self.course_bits = 0  # bits to encode a course number in binary
        self.slot_bits = 0  # bits to encode a cumulative slot number
        self.class_bits = 0  # bits to encode a class number
        self.total_slots = 0  # slot_count × day_count

        # ── Quota / constraint arrays (populated by initialize_genotype) ─────
        self.course_quota = []  # [class][course] remaining weekly occurrences
        self.teacher_quota = []  # [course] max simultaneous classes per slot
        self.repeat_quota = []  # [class][course] max daily occurrences

        # ── Output timetable: tables[class][day][slot] = course_number ───────
        self.tables: List[List[List[int]]] = []

        # ── Performance / telemetry ──────────────────────────────────────────
        self._fitness_cache: Dict[str,
                                  float] = {}  # gene → fitness memoisation
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_genes_eval = 0
        self._generation_log: List[GenerationStats] = []
        self._run_start_time: float = 0.0
        self._slots_filled = 0

    # ── Alternative constructor ───────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: TimetableConfig,
                    **kwargs) -> "GenerateTimeTable":
        """
        Construct from a TimetableConfig dataclass instead of raw kwargs.

        Example:
            cfg = TimetableConfig(classes=3, courses=5, slots=7, days=5)
            scheduler = GenerateTimeTable.from_config(cfg)
            result = scheduler.run()
        """
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

    # ══════════════════════════════════════════════════════════════════════════
    #  INITIALISATION HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def initialize_genotype(
        self,
        no_courses: int,
        classes: int,
        slots: int,
        days: int,
        daily_rep: Union[int, list],
        teachers: Union[int, list],
    ) -> List[int]:
        """
        Pre-compute every constant the GA needs and populate quota arrays.

        Binary encoding lengths explained:
          • course_bits = ⌈log₂(course_count + 1)⌉
              → enough bits to uniquely represent every course number
          • slot_bits   = ⌈log₂(total_slots + 1)⌉
              → enough bits for a cumulative slot index across all days
          • class_bits  = course_bits  (same magnitude as courses for simplicity)

        Returns:
            [course_bits, slot_bits, total_genes_needed]
            where total_genes_needed = slots × days × classes (one gene per cell)
        """
        # Store validated counts
        self.course_count = no_courses
        self.slot_count = slots
        self.day_count = days
        self.class_count = classes
        self.total_slots = self.slot_count * self.day_count

        # Compute bit-widths using Python's built-in bin() length trick.
        # bin(n) returns '0bXXX', so len - 2 strips the '0b' prefix.
        self.course_bits = len(bin(self.course_count)) - 2
        self.slot_bits = len(bin(self.total_slots)) - 2
        self.class_bits = len(bin(
            self.class_count)) - 2  # fixed: use class_count

        # Populate the weekly occurrence caps per course
        self._calc_course_quota()

        # ── daily_rep: how many times a course may appear on a single day ────
        if isinstance(daily_rep, int):
            # Same cap for every course
            flat_rep = [daily_rep] * self.course_count
        elif isinstance(daily_rep,
                        list) and len(daily_rep) == self.course_count:
            flat_rep = daily_rep
        else:
            raise ValueError(
                f"repeat must be an int OR a list of length {self.course_count}. "
                f"Got: {daily_rep!r}")
        # Each class gets its own copy so deductions are class-local
        self.repeat_quota = [flat_rep[:] for _ in range(self.class_count)]

        # ── teachers: how many simultaneous classes one teacher can cover ────
        if isinstance(teachers, int):
            self.teacher_quota = [teachers] * self.course_count
        elif isinstance(teachers, list) and len(teachers) == self.course_count:
            self.teacher_quota = teachers
        else:
            raise ValueError(
                f"teachers must be an int OR a list of length {self.course_count}. "
                f"Got: {teachers!r}")

        total_genes = self.slot_count * self.day_count * self.class_count
        return [self.course_bits, self.slot_bits, total_genes]

    # ──────────────────────────────────────────────────────────────────────────

    def _calc_course_quota(self):
        """
        Distribute the week's available slots as evenly as possible across
        all courses, giving each course a fair share.

        Algorithm:
          q_max = total_slots // course_count   (base allocation)

          If total_slots is perfectly divisible → every course gets q_max.
          Otherwise    → some courses get q_max+1, the rest q_max.
          The boundary is chosen randomly to avoid systematic bias.

        Result stored in self.course_quota[class_idx][course_idx].
        Each class gets an independent copy so deductions don't bleed across.
        """
        q_max = self.total_slots // self.course_count
        remainder = self.total_slots % self.course_count

        if remainder == 0:
            # Perfect split — all courses equal
            flat_quota = [q_max] * self.course_count
        else:
            # Give q_max+1 to most courses, reduce `extra_slots` courses by 1
            flat_quota = [q_max + 1] * self.course_count
            extra_slots = (q_max + 1) * self.course_count - self.total_slots

            # Random start index so the "shorted" courses rotate each run
            n = random.randint(1, self.course_count - extra_slots)
            for i in range(extra_slots):
                flat_quota[n + i] -= 1

        # One independent quota array per class
        self.course_quota = [flat_quota[:] for _ in range(self.class_count)]

    # ══════════════════════════════════════════════════════════════════════════
    #  BINARY ENCODING / DECODING
    # ══════════════════════════════════════════════════════════════════════════

    def _to_binary(self, value: int, bit_length: int) -> str:
        """
        Convert an integer to a zero-padded binary string of exactly `bit_length`.

        Example:
            _to_binary(5, 4) → '0101'
            _to_binary(1, 3) → '001'
        """
        raw = bin(value)[2:]  # strip '0b' prefix
        return raw.zfill(bit_length)  # left-pad with zeros

    def encode_course(self) -> str:
        """
        Pick a random course (1 … course_count) and encode it as binary.

        Example with 4 courses (needs 2 bits):
            encode_course() might return '10' (= course 2)
        """
        return self._to_binary(random.randint(1, self.course_count),
                               self.course_bits)

    def encode_slot(self) -> str:
        """
        Pick a random cumulative slot (1 … total_slots) and encode as binary.

        Cumulative slots count across all days:
            slot 1-6   = Monday   slots 1-6   (if 6 periods/day)
            slot 7-12  = Tuesday  slots 1-6
            etc.

        Example with 30 total slots (needs 5 bits):
            encode_slot() might return '01011' (= slot 11, i.e. Tue period 5)
        """
        return self._to_binary(random.randint(1, self.total_slots),
                               self.slot_bits)

    def encode_class(self) -> str:
        """
        Pick a random class (1 … class_count) and encode as binary.

        Example with 6 classes (needs 3 bits):
            encode_class() might return '100' (= class 4)
        """
        return self._to_binary(random.randint(1, self.class_count),
                               self.class_bits)

    def generate_gene(self) -> str:
        """
        Build a complete random gene = course_bits + slot_bits + class_bits.

        A gene is one candidate timetable entry:
          "which course is taught, in which slot, for which class?"

        Example (4 courses / 2bits, 30 slots / 5bits, 6 classes / 3bits):
            generate_gene() → '10' + '01011' + '100'
                            = '1001011100'
                             course=2, slot=11(Tue-P5), class=4
        """
        return self.encode_course() + self.encode_slot() + self.encode_class()

    def decode_gene(self, gene: str) -> Tuple[int, int, int, int]:
        """
        Fully decode a gene string back into human-readable components.

        Returns:
            (course_no, slot_no, day_no, class_no)
            All values are 1-based natural numbers.

        Example:
            decode_gene('1001011100')
            → (course=2, slot=5, day=2, class=4)
              i.e. Course-2 taught on Day-2 (Tue) period 5 for Class-4
        """
        course_no = int(gene[:self.course_bits], 2)
        slot_no, day_no = self.extract_slot_day(gene)
        class_no = int(gene[self.course_bits + self.slot_bits:], 2)
        return course_no, slot_no, day_no, class_no

    def extract_slot_day(self, gene: str) -> Tuple[int, int]:
        """
        Convert the cumulative slot number encoded in a gene into a
        (slot_within_day, day_number) pair.

        Maths:
          cumulative_slot = slot_within_day + (day_index × slots_per_day)
          → day_no   = cumulative_slot // slots_per_day
          → slot_no  = cumulative_slot  % slots_per_day

        Edge-case: when cumulative_slot is a perfect multiple of slot_count
          the raw modulo gives 0, so we adjust:  slot_no = slot_count, day_no -= 1

        Returns:
            (slot_no, day_no) both 1-based
        """
        raw_slot = int(
            gene[self.course_bits:self.course_bits + self.slot_bits], 2)
        slot_no = raw_slot % self.slot_count
        day_no = raw_slot // self.slot_count

        if slot_no == 0:  # perfect multiple → last slot of prev day
            slot_no = self.slot_count
            day_no -= 1

        return slot_no, day_no

    # ══════════════════════════════════════════════════════════════════════════
    #  FITNESS FUNCTION  — heart of the GA
    # ══════════════════════════════════════════════════════════════════════════

    def calculate_fitness(self, gene: str) -> float:
        """
        Score a gene from 0.0 (awful) to 100.0 (perfect).

        The score starts at 100 and is multiplied by penalty factors for each
        constraint violation.  Multiplicative penalties allow multiple soft
        constraints to stack gracefully rather than producing binary pass/fail.

        ┌──────────────────────────────────────────────────────────────────────┐
        │ Penalty catalogue                                                    │
        │                                                                      │
        │  × 0.01  HARD — slot already occupied in this class                 │
        │  × 0.60  SOFT — same course already in this slot (another class)    │
        │  × 0.60  SOFT — course appears in adjacent slot (same class/day)    │
        │  × 0.01  HARD — weekly quota exhausted for this course+class        │
        │  × 0.01  HARD — course appears ≥ 2 times today in this class        │
        │  × 0.50  SOFT — daily repeat cap exceeded                           │
        │  × 0.01  HARD — teacher capacity saturated for this slot            │
        └──────────────────────────────────────────────────────────────────────┘

        Uses an internal dict cache (_fitness_cache) so the same gene string
        is never evaluated twice — significant speedup for large populations.
        """
        # ── Cache lookup ─────────────────────────────────────────────────────
        if gene in self._fitness_cache:
            self._cache_hits += 1
            return self._fitness_cache[gene]
        self._cache_misses += 1
        self._total_genes_eval += 1

        fitness = 100.0

        # Decode gene components
        course = int(gene[:self.course_bits], 2)
        slot_no, day_no = self.extract_slot_day(gene)
        class_no = int(gene[self.course_bits + self.slot_bits:], 2)

        # Guard: encoded indices must be within valid range
        if (course < 1 or course > self.course_count or class_no < 1
                or class_no > self.class_count or day_no < 1
                or day_no > self.day_count or slot_no < 1
                or slot_no > self.slot_count):
            self._fitness_cache[gene] = 0.0
            return 0.0

        timetable = self.tables  # local alias for speed

        # ── 1. HARD: slot already occupied in target class ───────────────────
        if timetable[class_no - 1][day_no - 1][slot_no - 1] != 0:
            fitness *= 0.01

        # ── 2. SOFT: same course already in this slot (teacher clash) ────────
        for cls_idx in range(self.class_count):
            if timetable[cls_idx][day_no - 1][slot_no - 1] == course:
                fitness *= 0.60  # penalise once per offending class

        # ── 3. SOFT: course is adjacent to itself (bad for student attention) ─
        today_row = timetable[class_no - 1][day_no - 1]
        if slot_no > 1 and today_row[slot_no - 2] == course:
            fitness *= 0.60  # previous slot is same course
        if slot_no < self.slot_count and today_row[slot_no] == course:
            fitness *= 0.60  # next slot is same course

        # ── 4. HARD: weekly course quota depleted ────────────────────────────
        if self.course_quota[class_no - 1][course - 1] < 1:
            fitness *= 0.01

        # ── 5. HARD: course appears twice+ today (absolute daily cap) ────────
        if today_row.count(course) >= 2:
            fitness *= 0.01

        # ── 6. SOFT: exceeds per-course daily repeat allowance ───────────────
        if today_row.count(course) >= self.repeat_quota[class_no - 1][course -
                                                                      1]:
            fitness *= 0.50

        # ── 7. HARD: teacher at capacity this slot across all classes ─────────
        simultaneous = sum(1 for cls_idx in range(self.class_count)
                           if timetable[cls_idx][day_no - 1][slot_no -
                                                             1] == course)
        if simultaneous >= self.teacher_quota[course - 1]:
            fitness *= 0.01

        self._fitness_cache[gene] = fitness
        return fitness

    def invalidate_cache(self):
        """
        Clear the fitness cache.

        Must be called after fit_slot() commits a gene to the timetable,
        because existing cached scores may now be stale (the environment
        the scores were computed against has changed).
        """
        self._fitness_cache.clear()

    # ══════════════════════════════════════════════════════════════════════════
    #  GENETIC OPERATORS
    # ══════════════════════════════════════════════════════════════════════════

    def single_point_crossover(self, gene_a: str, gene_b: str) -> List[str]:
        """
        Swap one of the three gene segments (course / slot / class) between
        two parent genes to produce two children.

        Randomly picks which segment to swap:
            1 → swap course codes   (changes what subject is taught)
            2 → swap slot codes     (changes when it is taught)
            3 → swap class codes    (changes who it is taught to)

        This keeps crossover semantically meaningful — we always swap entire
        logical units rather than arbitrary bit positions.

        Example (swapping slot, c=2):
            parent A: [crs_A][slot_A][cls_A]
            parent B: [crs_B][slot_B][cls_B]
            child  C: [crs_A][slot_B][cls_A]   ← slot from B
            child  D: [crs_B][slot_A][cls_B]   ← slot from A
        """
        c = random.choice([1, 2, 3])
        cb = self.course_bits
        sb = self.slot_bits

        if c == 1:
            # Swap course segment
            child_c = gene_b[:cb] + gene_a[cb:]
            child_d = gene_a[:cb] + gene_b[cb:]
        elif c == 2:
            # Swap slot segment
            child_c = gene_a[:cb] + gene_b[cb:cb + sb] + gene_a[cb + sb:]
            child_d = gene_b[:cb] + gene_a[cb:cb + sb] + gene_b[cb + sb:]
        else:
            # Swap class segment
            child_c = gene_a[:cb + sb] + gene_b[cb + sb:]
            child_d = gene_b[:cb + sb] + gene_a[cb + sb:]

        return [child_c, child_d]

    def multi_point_crossover(self,
                              gene_a: str,
                              gene_b: str,
                              points: int = 2) -> List[str]:
        """
        Apply single_point_crossover `points` times in sequence.

        Each successive crossover uses the children of the last, producing
        more thorough genetic mixing than a single swap.

        With points=2 the operator is equivalent to 2-point crossover.
        With points=3 all three segments can independently be exchanged.

        Args:
            gene_a, gene_b – parent genes
            points         – number of successive single-point crossovers

        Returns:
            [offspring_a, offspring_b]
        """
        a, b = gene_a, gene_b
        for _ in range(points):
            a, b = self.single_point_crossover(a, b)
        return [a, b]

    def uniform_crossover(self, gene_a: str, gene_b: str) -> List[str]:
        """
        Bit-level uniform crossover: each bit independently drawn from either
        parent with equal probability.

        Produces higher diversity than segment-level crossover but may destroy
        meaningful segment structures.  Used as an occasional diversity injection.

        Returns:
            [offspring_a, offspring_b]
        """
        length = len(gene_a)
        child_c = "".join(gene_a[i] if random.random() < 0.5 else gene_b[i]
                          for i in range(length))
        # child_d is the bitwise complement selection of child_c
        child_d = "".join(gene_b[i] if child_c[i] == gene_a[i] else gene_a[i]
                          for i in range(length))
        return [child_c, child_d]

    def mutation(self, gene: str, course_bit_length: int,
                 slot_bit_length: int) -> str:
        """
        Randomly replace one segment of the gene with a freshly encoded value.

        Mutation introduces new genetic material that crossover alone cannot
        create, preventing the population from converging prematurely.

        Strategy chosen uniformly at random:
            1 → replace course code  (try a different subject)
            2 → replace slot code    (try a different time)
            3 → replace class code   (try a different class)

        Args:
            gene              – the gene to mutate
            course_bit_length – bit-width of the course segment
            slot_bit_length   – bit-width of the slot segment

        Returns:
            mutated gene string (same length as input)
        """
        c = random.choice([1, 2, 3])
        cb = course_bit_length
        sb = slot_bit_length

        if c == 1:
            return self.encode_course() + gene[cb:]
        elif c == 2:
            return gene[:cb] + self.encode_slot() + gene[cb + sb:]
        else:
            return gene[:cb + sb] + self.encode_class()

    def smart_mutation(
        self,
        gene: str,
        course_bit_length: int,
        slot_bit_length: int,
        attempts: int = 5,
    ) -> str:
        """
        Guided mutation: try up to `attempts` mutations, keep the one with
        the highest fitness.  Falls back to the original gene if none improve.

        This is a simple (1+λ) local search wrapped around standard mutation.
        It costs more evaluations per child but produces better offspring,
        especially late in evolution when random drift is wasteful.

        Args:
            gene              – gene to mutate
            course_bit_length – encoding constant
            slot_bit_length   – encoding constant
            attempts          – how many random mutations to trial

        Returns:
            best mutant (or original gene if no improvement found)
        """
        best_gene = gene
        best_fitness = self.calculate_fitness(gene)

        for _ in range(attempts):
            candidate = self.mutation(gene, course_bit_length, slot_bit_length)
            f = self.calculate_fitness(candidate)
            if f > best_fitness:
                best_fitness = f
                best_gene = candidate

        return best_gene

    # ══════════════════════════════════════════════════════════════════════════
    #  SELECTION
    # ══════════════════════════════════════════════════════════════════════════

    def selection_pair(self, population: List[str]) -> List[str]:
        """
        Fitness-proportionate (roulette wheel) selection of two parents.

        Each gene's probability of being chosen equals its fitness divided by
        the population's total fitness.  High-scoring genes are picked more
        often but low-scoring ones still have a chance — maintaining diversity.

        Uses random.choices() with fitness weights for efficiency.

        Returns:
            [parent_a, parent_b]
        """
        weights = [self.calculate_fitness(g) for g in population]
        return random.choices(population=population, weights=weights, k=2)

    def tournament_selection(self,
                             population: List[str],
                             tournament_size: int = 3) -> str:
        """
        Tournament selection: pick `tournament_size` random genes, return
        the one with the highest fitness.

        Advantages over roulette wheel:
          • Works even when fitnesses are negative or zero
          • Selection pressure tunable via tournament_size
          • Faster (no need to sum all weights)

        Args:
            population      – current gene pool
            tournament_size – contestants per tournament (default 3)

        Returns:
            single winning gene
        """
        contestants = random.sample(population,
                                    min(tournament_size, len(population)))
        return max(contestants, key=self.calculate_fitness)

    def sort_population(self, population: List[str]) -> List[str]:
        """
        Sort genes in descending fitness order (best first).

        Cached fitness lookups make repeated sorting cheap.
        """
        return sorted(population, key=self.calculate_fitness, reverse=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  POPULATION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def generate_population(self, size: int) -> List[str]:
        """
        Spawn `size` random genes to form the initial population.

        Each gene is fully random — no prior knowledge is injected.  The GA
        will quickly weed out the worst and keep the best within a few
        generations.

        Returns:
            list of `size` random gene strings
        """
        return [self.generate_gene() for _ in range(size)]

    def generate_table_skeleton(self):
        """
        Allocate the output timetable as a 3-D array of zeros.

        Structure: tables[class_idx][day_idx][slot_idx] = course_number
        Initially all zeros (= unscheduled).

        The array is mutated in-place by fit_slot() as genes are committed.
        """
        self.tables = []
        for _ in range(self.class_count):
            class_table = [[0] * self.slot_count
                           for _ in range(self.day_count)]
            self.tables.append(class_table)
        return self.tables

    def fit_slot(self, gene: str):
        """
        Commit a gene to the timetable and decrement its course quota.

        Called once per iteration of the outer scheduling loop when the GA
        has found a gene with fitness ≥ max_fitness (or the best it could
        find after max_generations).

        After committing, we MUST invalidate the fitness cache because all
        future fitness evaluations now see a different timetable state.
        """
        course = int(gene[:self.course_bits], 2)
        slot_no, day_no = self.extract_slot_day(gene)
        class_no = int(gene[self.course_bits + self.slot_bits:], 2)

        # Write to timetable (1-based indices → 0-based array indices)
        self.tables[class_no - 1][day_no - 1][slot_no - 1] = course

        # Decrement weekly occurrence quota for this course in this class
        self.course_quota[class_no - 1][course - 1] -= 1

        # Stale cache must be cleared — the scoring environment has changed
        self.invalidate_cache()
        self._slots_filled += 1

    # ══════════════════════════════════════════════════════════════════════════
    #  CORE EVOLUTION LOOP
    # ══════════════════════════════════════════════════════════════════════════

    def run_evolution(
        self,
        course_bit_length: int,
        slot_bit_length: int,
        population_size: int,
        max_fitness: float,
        max_generations: int,
    ) -> str:
        """
        Run the GA for one slot and return the best gene found.

        Algorithm per generation:
          1. Sort by fitness (best first)
          2. Early-stop if best ≥ max_fitness
          3. Elitism: copy top `elite_ratio` fraction directly to next gen
          4. Fill remainder via crossover + mutation pairs
          5. Repeat until max_generations exhausted

        Adaptive mutation:
          If no improvement after 5 consecutive generations, temporarily
          triple the mutation rate to escape local optima.  Rate resets once
          improvement resumes.

        Args:
            course_bit_length – encoding constant
            slot_bit_length   – encoding constant
            population_size   – number of individuals
            max_fitness       – early-stop threshold
            max_generations   – hard iteration cap

        Returns:
            Best gene string found (may not be perfect if GA stalls)
        """
        population = self.generate_population(population_size)
        elite_count = max(2, int(population_size * self.elite_ratio))
        mut_rate = self.mutation_rate
        stale_count = 0  # consecutive gens with no improvement
        prev_best = -1.0

        for gen_idx in range(max_generations):
            t0 = time.perf_counter()

            # ── Sort population by fitness (best first) ──────────────────────
            population = self.sort_population(population)
            fitnesses = [self.calculate_fitness(g) for g in population]
            best_f = fitnesses[0]
            avg_f = sum(fitnesses) / len(fitnesses)
            worst_f = fitnesses[-1]

            # ── Record telemetry ─────────────────────────────────────────────
            self._generation_log.append(
                GenerationStats(
                    generation=gen_idx,
                    best_fitness=best_f,
                    avg_fitness=avg_f,
                    worst_fitness=worst_f,
                    mutation_rate=mut_rate,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                ))

            # ── Early-stop if a perfect gene is found ────────────────────────
            if best_f >= max_fitness:
                return population[0]

            # ── Adaptive mutation: increase rate if GA is stalling ───────────
            if self.adaptive:
                if best_f <= prev_best + 0.001:
                    stale_count += 1
                    if stale_count >= 5:
                        # Crank up mutation to blast out of the local optimum
                        mut_rate = min(0.95, self.mutation_rate * 3.0)
                else:
                    stale_count = 0
                    mut_rate = self.mutation_rate  # reset to normal
            prev_best = best_f

            # ── Elitism: top genes survive unchanged ─────────────────────────
            next_gen = population[:elite_count]

            # ── Crossover + mutation to fill the rest ────────────────────────
            remaining = population_size - elite_count
            pairs = remaining // 2

            for _ in range(pairs):
                # Parent selection: mix of tournament and roulette for diversity
                if random.random() < 0.5:
                    p_a = self.tournament_selection(population)
                    p_b = self.tournament_selection(population)
                else:
                    p_a, p_b = self.selection_pair(population)

                # Crossover strategy: occasionally use uniform crossover
                if random.random() < 0.15:
                    children = self.uniform_crossover(p_a, p_b)
                else:
                    children = self.single_point_crossover(p_a, p_b)

                # Mutation pass
                for child in children:
                    if random.random() < mut_rate:
                        # Smart mutation late in evolution; random early on
                        if gen_idx > max_generations // 2:
                            child = self.smart_mutation(
                                child, course_bit_length, slot_bit_length)
                        else:
                            child = self.mutation(child, course_bit_length,
                                                  slot_bit_length)
                    next_gen.append(child)

            # Handle odd population sizes
            if len(next_gen) < population_size:
                next_gen.append(self.generate_gene())

            population = next_gen

        # Return best of final generation even if imperfect
        return self.sort_population(population)[0]

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC ENTRY POINT
    # ══════════════════════════════════════════════════════════════════════════

    def run(self) -> List[List[List[int]]]:
        """
        Execute the full timetable scheduling algorithm.

        Outer loop: iterate over every cell in the timetable (class × day × slot)
        Inner loop: run the GA to find the best gene for that cell, then commit it.

        Returns:
            tables: 3-D list  tables[class][day][slot] = course_number (1-based)
                    Shape: (classes, days, slots)

        Usage:
            scheduler = GenerateTimeTable(classes=3, courses=4, slots=5, days=5)
            timetable = scheduler.run()
        """
        self._run_start_time = time.perf_counter()
        print("\n🧬  Initialising genetic algorithm engine …")

        # ── Step 1: compute encoding constants and quota arrays ───────────────
        course_bits, slot_bits, total_cells = self.initialize_genotype(
            self.courses,
            self.classes,
            self.slots,
            self.days,
            self.repeat,
            self.teachers,
        )

        # ── Step 2: allocate blank timetable ─────────────────────────────────
        self.generate_table_skeleton()

        print(
            f"   Classes: {self.class_count}  |  Courses: {self.course_count}  "
            f"|  Slots/day: {self.slot_count}  |  Days: {self.day_count}")
        print(f"   Total cells to fill: {total_cells}")
        print(
            f"   Gene encoding: {course_bits}+{slot_bits}+{self.class_bits} bits\n"
        )

        # ── Step 3: fill every cell one by one ───────────────────────────────
        remaining = total_cells
        while remaining > 0:
            gene = self.run_evolution(
                course_bits,
                slot_bits,
                self.population_size,
                self.max_fitness,
                self.max_generations,
            )
            # Only commit if gene is plausibly valid (fitness > 0)
            if self.calculate_fitness(gene) > 0:
                self.fit_slot(gene)
                remaining -= 1
            else:
                # Gene is zero-fitness; generate fresh random gene to unstick
                gene = self.generate_gene()
                self.fit_slot(gene)
                remaining -= 1

            # Progress display every 10 % of cells
            filled = total_cells - remaining
            if filled % max(1, total_cells // 10) == 0 or remaining == 0:
                pct = 100 * filled // total_cells
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                elapsed = time.perf_counter() - self._run_start_time
                print(
                    f"   [{bar}] {pct:3d}%  ({filled}/{total_cells} cells)  "
                    f"{elapsed:.1f}s elapsed",
                    end="\r",
                )

        elapsed_total = time.perf_counter() - self._run_start_time
        print(f"\n\n✅  Scheduling complete in {elapsed_total:.2f}s  "
              f"({self._total_genes_eval:,} genes evaluated, "
              f"{self._cache_hits:,} cache hits)\n")

        return self.tables

    # ══════════════════════════════════════════════════════════════════════════
    #  VALIDATION
    # ══════════════════════════════════════════════════════════════════════════

    def validate(self) -> Dict[str, int]:
        """
        Scan the completed timetable for constraint violations and return a
        summary dict.

        Checks performed:
          • Empty cells (unfilled slots — should be zero after a full run)
          • Double-booked slots (same class, same slot, used twice — impossible
            given our structure but checked for integrity)
          • Teacher clashes (same course in the same slot across too many classes)
          • Back-to-back repetitions (same course in consecutive slots, same class)

        Returns:
            {
                "empty_cells":      int,
                "teacher_clashes":  int,
                "back_to_back":     int,
                "total_violations": int,
            }
        """
        empty = 0
        clashes = 0
        back2back = 0

        for day in range(self.day_count):
            for slot in range(self.slot_count):
                # Count how many classes have each course in this slot
                slot_courses = Counter(self.tables[cls][day][slot]
                                       for cls in range(self.class_count))
                for course, count in slot_courses.items():
                    if course == 0:
                        empty += count
                    elif count > self.teacher_quota[course - 1]:
                        clashes += count - self.teacher_quota[course - 1]

        for cls in range(self.class_count):
            for day in range(self.day_count):
                row = self.tables[cls][day]
                for s in range(self.slot_count - 1):
                    if row[s] != 0 and row[s] == row[s + 1]:
                        back2back += 1

        total = empty + clashes + back2back
        return {
            "empty_cells": empty,
            "teacher_clashes": clashes,
            "back_to_back": back2back,
            "total_violations": total,
        }

    # ══════════════════════════════════════════════════════════════════════════
    #  DISPLAY / EXPORT
    # ══════════════════════════════════════════════════════════════════════════

    def pretty_print(self, class_idx: Optional[int] = None):
        """
        Print timetable(s) to the terminal in a human-readable grid format.

        Args:
            class_idx – 0-based index of the class to print, or None to print all.

        Output example:
            ═══ Class-1 ═══
                     Mon   Tue   Wed   Thu   Fri
            Period 1 │Math │PE   │Eng  │Math │Sci
            Period 2 │Eng  │Math │PE   │Sci  │Math
            ...
        """
        classes_to_print = range(
            self.class_count) if class_idx is None else [class_idx]

        col_w = max(len(n) for n in self.course_names) + 2

        for cls in classes_to_print:
            print(f"\n{'═'*50}")
            print(f"  📚  {self.class_names[cls]}")
            print(f"{'═'*50}")

            # Header row with day names
            header = " " * 10
            for day_name in self.day_names:
                header += day_name.center(col_w)
            print(header)
            print(" " * 10 + ("─" * col_w * self.day_count))

            # One row per slot
            for s in range(self.slot_count):
                row_label = f"  Slot {s+1}  │"
                row_str = row_label
                for d in range(self.day_count):
                    course_no = self.tables[cls][d][s]
                    if course_no == 0:
                        label = "FREE"
                    else:
                        label = self.course_names[course_no - 1]
                    row_str += label.center(col_w)
                print(row_str)

        print()

    def analytics(self) -> Dict:
        """
        Return a summary of the GA run's performance.

        Includes:
          • Total wall-clock time
          • Total genes evaluated
          • Cache hit/miss ratio
          • Per-course frequency in the final timetable
          • Validation results
          • Last-generation stats from each slot-filling run

        Returns:
            dict with keys: runtime_s, genes_evaluated, cache_hit_ratio,
                            course_frequency, validation, generation_log_tail
        """
        runtime = time.perf_counter() - self._run_start_time
        total_evals = self._cache_hits + self._cache_misses
        hit_ratio = self._cache_hits / total_evals if total_evals else 0.0

        # Count course appearances across the entire timetable
        freq: Dict[str, int] = Counter()
        for cls in range(self.class_count):
            for day in range(self.day_count):
                for slot in range(self.slot_count):
                    cn = self.tables[cls][day][slot]
                    if cn > 0:
                        freq[self.course_names[cn - 1]] += 1

        validation = self.validate()

        return {
            "runtime_s":
            runtime,
            "genes_evaluated":
            self._total_genes_eval,
            "cache_hit_ratio":
            round(hit_ratio, 4),
            "course_frequency":
            dict(freq),
            "validation":
            validation,
            "slots_filled":
            self._slots_filled,
            "generation_log_tail": [
                vars(s) for s in self._generation_log[-5:]  # last 5 snapshots
            ],
        }

    def export_json(self, filepath: str = "timetable.json"):
        """
        Save the completed timetable to a JSON file.

        Output structure:
            {
              "Class-1": {
                "Mon": ["Course-2", "Course-1", …],
                "Tue": […],
                …
              },
              "Class-2": { … },
              …
            }

        Args:
            filepath – destination path (default: 'timetable.json')
        """
        output: Dict = {}

        for cls_idx, cls_name in enumerate(self.class_names):
            output[cls_name] = {}
            for day_idx, day_name in enumerate(self.day_names):
                slots_list = []
                for s in range(self.slot_count):
                    cn = self.tables[cls_idx][day_idx][s]
                    slots_list.append(self.course_names[cn - 1] if cn >
                                      0 else "FREE")
                output[cls_name][day_name] = slots_list

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        print(f"💾  Timetable exported → {filepath}")

    def export_csv(self, filepath: str = "timetable.csv"):
        """
        Save the timetable as a flat CSV file with columns:
            Class, Day, Slot, Course

        Useful for importing into Excel or other tools.

        Args:
            filepath – destination path (default: 'timetable.csv')
        """
        rows = [["Class", "Day", "Slot", "Course"]]

        for cls_idx, cls_name in enumerate(self.class_names):
            for day_idx, day_name in enumerate(self.day_names):
                for s in range(self.slot_count):
                    cn = self.tables[cls_idx][day_idx][s]
                    course_label = self.course_names[cn -
                                                     1] if cn > 0 else "FREE"
                    rows.append(
                        [cls_name, day_name, f"Slot {s+1}", course_label])

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"📊  Timetable exported → {filepath}")

    def export_html(self, filepath: str = "timetable.html"):
        """
        Export a colour-coded HTML timetable — one table per class, each
        course gets a consistent background colour for easy visual scanning.

        Args:
            filepath – destination path (default: 'timetable.html')
        """

        # Build a colour palette (pastel HSL colours cycling across courses)
        def course_colour(course_no: int) -> str:
            hue = int((course_no - 1) * 360 / self.course_count)
            return f"hsl({hue}, 60%, 80%)"

        lines = [
            "<!DOCTYPE html><html><head>",
            "<meta charset='utf-8'>",
            "<title>Timetable</title>",
            "<style>",
            "  body { font-family: Arial, sans-serif; padding: 20px; }",
            "  table { border-collapse: collapse; margin-bottom: 30px; }",
            "  th, td { border: 1px solid #999; padding: 8px 14px; text-align:center; }",
            "  th { background: #444; color: #fff; }",
            "  h2 { margin-top: 40px; }",
            "</style></head><body>",
            "<h1>🗓️ Generated Timetable</h1>",
        ]

        for cls_idx, cls_name in enumerate(self.class_names):
            lines.append(f"<h2>{cls_name}</h2>")
            lines.append("<table>")

            # Header: days
            header_cells = "<th>Slot</th>" + "".join(f"<th>{d}</th>"
                                                     for d in self.day_names)
            lines.append(f"<tr>{header_cells}</tr>")

            for s in range(self.slot_count):
                cells = f"<td><b>Slot {s+1}</b></td>"
                for d in range(self.day_count):
                    cn = self.tables[cls_idx][d][s]
                    label = self.course_names[cn - 1] if cn > 0 else "FREE"
                    colour = course_colour(cn) if cn > 0 else "#eee"
                    cells += f"<td style='background:{colour}'>{label}</td>"
                lines.append(f"<tr>{cells}</tr>")

            lines.append("</table>")

        lines.append("</body></html>")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"🌐  Timetable exported → {filepath}")

    def print_analytics(self):
        """
        Print a formatted analytics summary to the terminal.

        Includes runtime, cache efficiency, constraint violations,
        and course-frequency distribution.
        """
        a = self.analytics()
        v = a["validation"]

        print("┌─────────────────────────────────────────┐")
        print("│           📈  RUN ANALYTICS             │")
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

    # ══════════════════════════════════════════════════════════════════════════
    #  UTILITY / HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def get_class_timetable(self,
                            class_name: str) -> Optional[List[List[int]]]:
        """
        Retrieve the timetable for a specific class by name.

        Args:
            class_name – must match one of self.class_names exactly

        Returns:
            2-D list [day][slot] = course_number, or None if not found.

        Example:
            tt = scheduler.get_class_timetable("Year 3")
            monday_slots = tt[0]   # list of course numbers for Monday
        """
        if class_name not in self.class_names:
            print(f"⚠️  Class '{class_name}' not found.  "
                  f"Available: {self.class_names}")
            return None
        idx = self.class_names.index(class_name)
        return self.tables[idx]

    def find_course_slots(
            self,
            course_name: str,
            class_name: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Find all scheduled occurrences of a course.

        Args:
            course_name – must match one of self.course_names
            class_name  – optional filter; if None, searches all classes

        Returns:
            list of (class_name, day_name, "Slot N") tuples

        Example:
            scheduler.find_course_slots("Mathematics")
            → [("Class-1", "Mon", "Slot 2"),
               ("Class-2", "Tue", "Slot 4"), …]
        """
        if course_name not in self.course_names:
            print(f"⚠️  Course '{course_name}' not found.")
            return []

        course_no = self.course_names.index(course_name) + 1
        results = []

        class_range = ([self.class_names.index(class_name)]
                       if class_name else range(self.class_count))

        for cls_idx in class_range:
            for day_idx in range(self.day_count):
                for s in range(self.slot_count):
                    if self.tables[cls_idx][day_idx][s] == course_no:
                        results.append((
                            self.class_names[cls_idx],
                            self.day_names[day_idx],
                            f"Slot {s+1}",
                        ))
        return results

    def get_teacher_schedule(self, course_name: str) -> Dict[str, List[str]]:
        """
        Build a schedule view from a teacher's perspective — which classes
        they are teaching in each slot.

        Args:
            course_name – the subject this teacher teaches

        Returns:
            dict: { "Mon Slot 1": ["Class-2", "Class-5"], … }

        Example:
            scheduler.get_teacher_schedule("Mathematics")
        """
        if course_name not in self.course_names:
            print(f"⚠️  Course '{course_name}' not found.")
            return {}

        course_no = self.course_names.index(course_name) + 1
        schedule: Dict[str, List[str]] = defaultdict(list)

        for day_idx, day_name in enumerate(self.day_names):
            for s in range(self.slot_count):
                for cls_idx, cls_name in enumerate(self.class_names):
                    if self.tables[cls_idx][day_idx][s] == course_no:
                        key = f"{day_name} Slot {s+1}"
                        schedule[key].append(cls_name)

        return dict(schedule)

    def reset(self):
        """
        Reset the scheduler to a clean state so it can be run again with
        different parameters or for benchmarking.

        Clears timetable, quotas, caches, and telemetry.
        """
        self.tables = []
        self.course_quota = []
        self.repeat_quota = []
        self._fitness_cache.clear()
        self._generation_log.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_genes_eval = 0
        self._slots_filled = 0
        self._run_start_time = 0.0
        if self.seed is not None:
            random.seed(self.seed)


# ══════════════════════════════════════════════════════════════════════════════
#  BENCHMARK UTILITY
# ══════════════════════════════════════════════════════════════════════════════


def benchmark(
    configurations: List[Dict],
    runs_per_config: int = 1,
    verbose: bool = True,
) -> List[Dict]:
    """
    Run the scheduler against multiple configurations and report timing + quality.

    Useful for:
      • Comparing how parameter choices affect speed / constraint satisfaction
      • Profiling before deploying to production
      • Regression testing after code changes

    Args:
        configurations  – list of dicts; each dict is passed as **kwargs to
                          GenerateTimeTable()
        runs_per_config – how many independent runs to average over
        verbose         – print results table to stdout

    Returns:
        list of result dicts with keys: config, avg_time_s, avg_violations

    Example:
        results = benchmark([
            {"classes": 3, "courses": 4, "slots": 5, "days": 5},
            {"classes": 6, "courses": 6, "slots": 6, "days": 5},
        ])
    """
    results = []

    for cfg_idx, cfg in enumerate(configurations):
        times = []
        violations = []

        for run in range(runs_per_config):
            scheduler = GenerateTimeTable(**cfg)
            t0 = time.perf_counter()
            scheduler.run()
            elapsed = time.perf_counter() - t0
            v = scheduler.validate()["total_violations"]
            times.append(elapsed)
            violations.append(v)

        avg_t = sum(times) / len(times)
        avg_v = sum(violations) / len(violations)
        result = {
            "config": cfg,
            "avg_time_s": round(avg_t, 3),
            "avg_violations": round(avg_v, 2),
        }
        results.append(result)

        if verbose:
            print(f"Config {cfg_idx+1}: {avg_t:.2f}s avg, "
                  f"{avg_v:.1f} avg violations  {cfg}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  EXAMPLE USAGE SUITE
# ══════════════════════════════════════════════════════════════════════════════


def example_minimal():
    """
    ─────────────────────────────────────────────────────────────
    EXAMPLE 1: Minimal — one-liner defaults
    ─────────────────────────────────────────────────────────────
    Uses all default parameters.  4 courses, 6 classes, 5-day week
    with 6 periods per day.  Quick smoke-test that everything works.
    ─────────────────────────────────────────────────────────────
    """
    print("=" * 60)
    print("EXAMPLE 1: Minimal (all defaults)")
    print("=" * 60)

    scheduler = GenerateTimeTable()
    timetable = scheduler.run()

    # Print just the first class
    scheduler.pretty_print(class_idx=0)
    print(f"Validation: {scheduler.validate()}\n")


def example_named_courses():
    """
    ─────────────────────────────────────────────────────────────
    EXAMPLE 2: Named courses and classes
    ─────────────────────────────────────────────────────────────
    Demonstrates custom course/class/day labels, making the
    output immediately readable without decoding numbers.
    ─────────────────────────────────────────────────────────────
    """
    print("=" * 60)
    print("EXAMPLE 2: Named Courses & Classes")
    print("=" * 60)

    scheduler = GenerateTimeTable(
        classes=3,
        courses=5,
        slots=6,
        days=5,
        repeat=2,
        teachers=2,
        seed=42,  # Reproducible output
        course_names=["Mathematics", "English", "Physics", "Art", "PE"],
        class_names=["Year 7A", "Year 7B", "Year 7C"],
        day_names=["Mon", "Tue", "Wed", "Thu", "Fri"],
        population_size=50,
        max_generations=60,
    )

    scheduler.run()
    scheduler.pretty_print()  # print all classes

    # Show where Mathematics is scheduled
    math_slots = scheduler.find_course_slots("Mathematics")
    print("📐  Mathematics slots:")
    for entry in math_slots:
        print(f"     {entry[0]} | {entry[1]} | {entry[2]}")

    # Teacher's schedule view
    print("\n👩‍🏫  PE teacher's schedule:")
    pe_schedule = scheduler.get_teacher_schedule("PE")
    for slot_key, classes in sorted(pe_schedule.items()):
        print(f"     {slot_key}: {', '.join(classes)}")

    scheduler.print_analytics()


def example_large_school():
    """
    ─────────────────────────────────────────────────────────────
    EXAMPLE 3: Large secondary school — stress test
    ─────────────────────────────────────────────────────────────
    10 classes, 8 subjects, 8 periods/day, 5-day week.
    Per-course teacher counts reflect reality (e.g. more Maths
    teachers than Drama teachers).
    ─────────────────────────────────────────────────────────────
    """
    print("=" * 60)
    print("EXAMPLE 3: Large School (stress test)")
    print("=" * 60)

    scheduler = GenerateTimeTable(
        classes=10,
        courses=8,
        slots=8,
        days=5,
        repeat=[2, 2, 2, 1, 1, 1, 2, 1],  # per-course daily max
        teachers=[3, 3, 2, 2, 1, 1, 2, 1],  # per-course teacher count
        population_size=80,
        max_generations=100,
        elite_ratio=0.15,
        mutation_rate=0.30,
        adaptive=True,
        course_names=[
            "Maths",
            "English",
            "Science",
            "History",
            "Geography",
            "Art",
            "PE",
            "Drama",
        ],
        class_names=[f"Form {i+1}" for i in range(10)],
    )

    scheduler.run()
    scheduler.export_json("/mnt/user-data/outputs/large_school_timetable.json")
    scheduler.export_csv("/mnt/user-data/outputs/large_school_timetable.csv")
    scheduler.export_html("/mnt/user-data/outputs/large_school_timetable.html")
    scheduler.print_analytics()


def example_config_dataclass():
    """
    ─────────────────────────────────────────────────────────────
    EXAMPLE 4: Using TimetableConfig dataclass
    ─────────────────────────────────────────────────────────────
    Shows the alternative constructor for cleaner config management,
    handy when loading settings from a file or CLI argument parser.
    ─────────────────────────────────────────────────────────────
    """
    print("=" * 60)
    print("EXAMPLE 4: Config dataclass constructor")
    print("=" * 60)

    config = TimetableConfig(
        classes=4,
        courses=6,
        slots=5,
        days=5,
        repeat=1,
        teachers=2,
        population_size=40,
        max_generations=70,
        seed=7,
    )

    scheduler = GenerateTimeTable.from_config(
        config,
        course_names=["Maths", "English", "Science", "History", "PE", "Art"],
        class_names=["Alpha", "Beta", "Gamma", "Delta"],
    )

    timetable = scheduler.run()
    scheduler.pretty_print()
    v = scheduler.validate()
    print(f"Total violations: {v['total_violations']}\n")


def example_reproducibility():
    """
    ─────────────────────────────────────────────────────────────
    EXAMPLE 5: Reproducibility with seed
    ─────────────────────────────────────────────────────────────
    Demonstrate that two schedulers with the same seed produce
    identical timetables — useful for unit testing and demos.
    ─────────────────────────────────────────────────────────────
    """
    print("=" * 60)
    print("EXAMPLE 5: Reproducibility (seed=99)")
    print("=" * 60)

    def make_scheduler():
        return GenerateTimeTable(
            classes=2,
            courses=3,
            slots=4,
            days=3,
            repeat=1,
            teachers=1,
            seed=99,
            population_size=30,
            max_generations=40,
        )

    run_a = make_scheduler().run()
    run_b = make_scheduler().run()

    identical = run_a == run_b
    print(
        f"Run A == Run B: {identical}  ({'✅ Reproducible' if identical else '❌ Differs'})\n"
    )


def example_analytics_deep_dive():
    """
    ─────────────────────────────────────────────────────────────
    EXAMPLE 6: Deep analytics dive
    ─────────────────────────────────────────────────────────────
    Run a small schedule and print detailed analytics including
    generation-by-generation convergence data.
    ─────────────────────────────────────────────────────────────
    """
    print("=" * 60)
    print("EXAMPLE 6: Analytics Deep Dive")
    print("=" * 60)

    scheduler = GenerateTimeTable(
        classes=2,
        courses=4,
        slots=5,
        days=4,
        repeat=2,
        teachers=1,
        seed=77,
        population_size=40,
        max_generations=50,
        course_names=["Maths", "English", "Science", "Art"],
    )
    scheduler.run()
    stats = scheduler.analytics()

    print(f"Runtime          : {stats['runtime_s']:.3f}s")
    print(f"Genes evaluated  : {stats['genes_evaluated']:,}")
    print(f"Cache hit ratio  : {stats['cache_hit_ratio']*100:.1f}%")
    print(f"Violations       : {stats['validation']}")
    print(f"Course frequency : {stats['course_frequency']}")
    print()

    # Print last-5-generation snapshot
    print("Last 5 generation snapshots:")
    for snap in stats["generation_log_tail"]:
        print(f"  Gen {snap['generation']:3d} | "
              f"best={snap['best_fitness']:6.2f}  "
              f"avg={snap['avg_fitness']:6.2f}  "
              f"mut_rate={snap['mutation_rate']:.2f}  "
              f"time={snap['elapsed_ms']:.1f}ms")
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Run all six examples in sequence.

    Each example is isolated and self-contained.  Adjust the list below
    to run only the ones you care about.
    """
    examples = [
        example_minimal,
        example_named_courses,
        example_config_dataclass,
        example_reproducibility,
        example_analytics_deep_dive,
        # example_large_school,   # ← uncomment for stress test (slowest)
    ]

    for fn in examples:
        fn()
        print()

    print("🏁  All examples complete.")
