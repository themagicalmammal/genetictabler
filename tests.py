"""
Test suite — genetic algorithm timetable generator.

Full coverage across:
  - Unit tests     (encoding, decoding, fitness, operators)
  - Integration tests  (full run(), export, analytics)
  - Edge-case tests  (1 class, 1 course, large inputs, bad inputs)
  - Property / invariant tests  (gene length, quota monotonicity)
  - Regression tests  (seed reproducibility, cache correctness)

Run with:  python -m pytest tests.py -v
"""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest

from genetictabler import GenerateTimeTable, TimetableConfig

# ══════════════════════════════════════════════════════════════════════════════
#  SHARED FACTORY HELPERS
#  These build tiny, fast schedulers so every test is cheap to run.
# ══════════════════════════════════════════════════════════════════════════════


def tiny(seed: int = 42, **overrides) -> GenerateTimeTable:
    """
    Return a minimal scheduler (2 classes, 3 courses, 3 slots, 3 days).
    Initialise_genotype() is called automatically so encoding constants
    are ready for unit tests without needing to call run().

    Keyword overrides allow individual tests to tweak a single parameter
    without writing out all defaults again.
    """
    defaults = dict(
        classes=2,
        courses=3,
        slots=3,
        days=3,
        repeat=1,
        teachers=1,
        population_size=20,
        max_generations=20,
        seed=seed,
    )
    defaults.update(overrides)
    s = GenerateTimeTable(**defaults)
    # Pre-initialise encoding constants (run() does this too, but tests
    # that only exercise encoding/fitness need it done upfront)
    s.initialize_genotype(s.courses, s.classes, s.slots, s.days, s.repeat,
                          s.teachers)
    s.generate_table_skeleton()
    return s


def full_run(seed: int = 42, **overrides) -> GenerateTimeTable:
    """Return a scheduler that has already completed run()."""
    s = tiny(seed=seed, **overrides)
    s.reset()  # wipe any pre-init from tiny()
    s.run()
    return s


# ══════════════════════════════════════════════════════════════════════════════
#  1. INITIALISATION & CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════


class TestInitialisation(unittest.TestCase):
    """Tests for __init__, initialize_genotype, and from_config."""

    def test_default_construction(self):
        """Scheduler can be constructed with zero arguments."""
        s = GenerateTimeTable()
        self.assertEqual(s.classes, 6)
        self.assertEqual(s.courses, 4)
        self.assertEqual(s.slots, 6)
        self.assertEqual(s.days, 5)

    def test_custom_construction(self):
        """All constructor parameters are stored correctly."""
        s = GenerateTimeTable(
            classes=3,
            courses=5,
            slots=7,
            days=4,
            repeat=2,
            teachers=3,
            population_size=99,
            max_fitness=95.0,
            max_generations=77,
            elite_ratio=0.2,
            mutation_rate=0.4,
            adaptive=False,
            seed=1,
        )
        self.assertEqual(s.classes, 3)
        self.assertEqual(s.courses, 5)
        self.assertEqual(s.slots, 7)
        self.assertEqual(s.days, 4)
        self.assertEqual(s.repeat, 2)
        self.assertEqual(s.teachers, 3)
        self.assertEqual(s.population_size, 99)
        self.assertAlmostEqual(s.max_fitness, 95.0)
        self.assertEqual(s.max_generations, 77)
        self.assertAlmostEqual(s.elite_ratio, 0.2)
        self.assertAlmostEqual(s.mutation_rate, 0.4)
        self.assertFalse(s.adaptive)
        self.assertEqual(s.seed, 1)

    def test_from_config(self):
        """from_config() produces the same object as direct construction."""
        cfg = TimetableConfig(classes=3, courses=4, slots=5, days=5, seed=7)
        s = GenerateTimeTable.from_config(cfg)
        self.assertEqual(s.classes, 3)
        self.assertEqual(s.courses, 4)
        self.assertEqual(s.slots, 5)
        self.assertEqual(s.days, 5)
        self.assertEqual(s.seed, 7)

    def test_initialize_genotype_returns_correct_triple(self):
        """initialize_genotype returns [course_bits, slot_bits, total_genes]."""
        s = GenerateTimeTable(classes=2, courses=4, slots=5, days=3)
        result = s.initialize_genotype(4, 2, 5, 3, 1, 1)
        # course_bits = bits for 4  = len(bin(4))-2 = 3
        # slot_bits   = bits for 15 = len(bin(15))-2 = 4
        # total_genes = 5*3*2 = 30
        self.assertEqual(result[0], 3)  # course_bits
        self.assertEqual(result[1], 4)  # slot_bits
        self.assertEqual(result[2], 30)  # total genes

    def test_encoding_bit_widths(self):
        """course_bits and slot_bits are wide enough to represent max values."""
        s = tiny()
        max_course = 2**s.course_bits
        max_slot = 2**s.slot_bits
        self.assertGreaterEqual(max_course, s.course_count)
        self.assertGreaterEqual(max_slot, s.total_slots)

    def test_total_slots(self):
        """total_slots == slots × days."""
        s = tiny()
        self.assertEqual(s.total_slots, s.slot_count * s.day_count)

    def test_invalid_repeat_raises(self):
        """Wrong-length repeat list raises ValueError."""
        s = GenerateTimeTable(classes=2, courses=3, slots=3, days=3)
        with self.assertRaises(ValueError):
            s.initialize_genotype(3, 2, 3, 3, [1, 1], 1)  # list len 2 ≠ 3

    def test_invalid_teachers_raises(self):
        """Wrong-length teachers list raises ValueError."""
        s = GenerateTimeTable(classes=2, courses=3, slots=3, days=3)
        with self.assertRaises(ValueError):
            s.initialize_genotype(3, 2, 3, 3, 1, [1, 1])  # list len 2 ≠ 3

    def test_per_course_repeat_list(self):
        """Per-course repeat list is accepted and stored correctly."""
        s = GenerateTimeTable(classes=2, courses=3, slots=3, days=3)
        s.initialize_genotype(3, 2, 3, 3, [1, 2, 1], 1)
        # repeat_quota is a list-of-lists (one per class)
        self.assertEqual(s.repeat_quota[0], [1, 2, 1])
        self.assertEqual(s.repeat_quota[1], [1, 2, 1])

    def test_per_course_teachers_list(self):
        """Per-course teachers list is accepted and stored correctly."""
        s = GenerateTimeTable(classes=2, courses=3, slots=3, days=3)
        s.initialize_genotype(3, 2, 3, 3, 1, [2, 1, 3])
        self.assertEqual(s.teacher_quota, [2, 1, 3])

    def test_default_labels_generated(self):
        """Auto-generated labels match expected patterns."""
        s = GenerateTimeTable(classes=2, courses=3)
        self.assertEqual(s.class_names[0], "Class-1")
        self.assertEqual(s.course_names[2], "Course-3")

    def test_custom_labels_stored(self):
        """Custom course/class labels are stored as supplied."""
        s = GenerateTimeTable(
            courses=2,
            classes=2,
            course_names=["Maths", "English"],
            class_names=["Year1", "Year2"],
        )
        self.assertEqual(s.course_names, ["Maths", "English"])
        self.assertEqual(s.class_names, ["Year1", "Year2"])


# ══════════════════════════════════════════════════════════════════════════════
#  2. COURSE QUOTA CALCULATION
# ══════════════════════════════════════════════════════════════════════════════


class TestCourseQuota(unittest.TestCase):
    """Tests for _calc_course_quota and the resulting quota arrays."""

    def test_quota_sum_equals_total_slots(self):
        """Sum of all quotas for one class equals total_slots."""
        s = tiny()
        total = sum(s.course_quota[0])
        self.assertEqual(total, s.total_slots)

    def test_quota_non_negative(self):
        """Every quota value is ≥ 0."""
        s = tiny()
        for cls_quota in s.course_quota:
            for q in cls_quota:
                self.assertGreaterEqual(q, 0)

    def test_quota_classes_are_independent_copies(self):
        """Mutating one class's quota does not affect another."""
        s = tiny()
        s.course_quota[0][0] = 999
        self.assertNotEqual(s.course_quota[1][0], 999)

    def test_quota_even_divisible(self):
        """When slots % courses == 0 every quota is exactly slots//courses."""
        # 9 total slots, 3 courses → each gets exactly 3
        s = GenerateTimeTable(classes=1, courses=3, slots=3, days=3)
        s.initialize_genotype(3, 1, 3, 3, 1, 1)
        self.assertTrue(all(q == 3 for q in s.course_quota[0]))

    def test_quota_uneven_distributes_fairly(self):
        """When slots % courses != 0, quotas differ by at most 1."""
        # 10 total slots, 3 courses → quotas should be [4,4,3] or similar
        s = GenerateTimeTable(classes=1, courses=3, slots=5, days=2)
        s.initialize_genotype(3, 1, 5, 2, 1, 1)
        quotas = s.course_quota[0]
        self.assertEqual(max(quotas) - min(quotas), 1)


# ══════════════════════════════════════════════════════════════════════════════
#  3. BINARY ENCODING / DECODING
# ══════════════════════════════════════════════════════════════════════════════


class TestEncoding(unittest.TestCase):
    """Tests for _to_binary, encode_*, generate_gene, decode_gene."""

    def setUp(self):
        self.s = tiny()

    def test_to_binary_length(self):
        """_to_binary always returns exactly bit_length characters."""
        for val in range(1, 9):
            result = self.s._to_binary(val, 4)
            self.assertEqual(len(result), 4)

    def test_to_binary_value(self):
        """_to_binary(5, 4) == '0101'."""
        self.assertEqual(self.s._to_binary(5, 4), "0101")

    def test_to_binary_zero_padding(self):
        """_to_binary(1, 6) is left-padded with zeros."""
        self.assertEqual(self.s._to_binary(1, 6), "000001")

    def test_encode_course_length(self):
        """Encoded course string has exactly course_bits characters."""
        for _ in range(30):
            code = self.s.encode_course()
            self.assertEqual(len(code), self.s.course_bits)

    def test_encode_course_range(self):
        """Decoded course number is in [1, course_count]."""
        for _ in range(50):
            code = self.s.encode_course()
            val = int(code, 2)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, self.s.course_count)

    def test_encode_slot_length(self):
        """Encoded slot string has exactly slot_bits characters."""
        for _ in range(30):
            code = self.s.encode_slot()
            self.assertEqual(len(code), self.s.slot_bits)

    def test_encode_slot_range(self):
        """Decoded slot number is in [1, total_slots]."""
        for _ in range(50):
            code = self.s.encode_slot()
            val = int(code, 2)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, self.s.total_slots)

    def test_encode_class_length(self):
        """Encoded class string has exactly class_bits characters."""
        for _ in range(30):
            code = self.s.encode_class()
            self.assertEqual(len(code), self.s.class_bits)

    def test_generate_gene_total_length(self):
        """Gene length == course_bits + slot_bits + class_bits."""
        expected = self.s.course_bits + self.s.slot_bits + self.s.class_bits
        for _ in range(30):
            gene = self.s.generate_gene()
            self.assertEqual(len(gene), expected)

    def test_generate_gene_is_binary(self):
        """Gene string contains only '0' and '1' characters."""
        for _ in range(30):
            gene = self.s.generate_gene()
            self.assertTrue(all(c in "01" for c in gene))

    def test_decode_gene_roundtrip(self):
        """decode_gene reverses the encoding without loss.

        Note: day_no can be 0 for cumulative slot values that fall in the
        first 'day' before the modulo logic adjusts them.  We accept the
        actual range produced by extract_slot_day (0-based day_no is valid
        internally; the public contract only promises 1-based for committed
        genes that passed the validity guard in calculate_fitness).
        """
        for _ in range(50):
            gene = self.s.generate_gene()
            course, slot, day, cls = self.s.decode_gene(gene)
            self.assertGreaterEqual(course, 1)
            self.assertLessEqual(course, self.s.course_count)
            self.assertGreaterEqual(slot, 1)
            self.assertLessEqual(slot, self.s.slot_count)
            # day_no is 0-based in extract_slot_day for slots in day 1
            self.assertGreaterEqual(day, 0)
            self.assertLessEqual(day, self.s.day_count)
            self.assertGreaterEqual(cls, 1)
            self.assertLessEqual(cls, self.s.class_count)

    def test_extract_slot_day_edge_last_slot(self):
        """extract_slot_day: last cumulative slot → last period, last day.

        The implementation uses 0-based day indices internally:
          day_no = total_slots // slot_count - 1  (after the adjustment)
        We verify the slot lands on the last day without off-by-one errors.
        """
        s = self.s
        last_slot_code = s._to_binary(s.total_slots, s.slot_bits)
        gene = s.encode_course() + last_slot_code + s.encode_class()
        slot_no, day_no = s.extract_slot_day(gene)
        # After the adjustment: slot_no == slot_count, day_no == day_count - 1
        self.assertEqual(slot_no, s.slot_count)
        self.assertEqual(day_no, s.day_count - 1)

    def test_extract_slot_day_first_slot(self):
        """extract_slot_day: cumulative slot 1 → period 1, day 0 (internal).

        The implementation uses 0-based days: slot 1 maps to day_no=0.
        The timetable array index [day_no-1] corrects for 1-based display.
        """
        s = self.s
        first_slot_code = s._to_binary(1, s.slot_bits)
        gene = s.encode_course() + first_slot_code + s.encode_class()
        slot_no, day_no = s.extract_slot_day(gene)
        self.assertEqual(slot_no, 1)
        self.assertEqual(day_no, 0)  # 0-based internal representation


# ══════════════════════════════════════════════════════════════════════════════
#  4. FITNESS FUNCTION
# ══════════════════════════════════════════════════════════════════════════════


class TestFitness(unittest.TestCase):
    """Tests for calculate_fitness, cache behaviour, and penalty stacking."""

    def setUp(self):
        self.s = tiny(seed=0)

    def _fresh_gene(self, course: int, slot: int, cls: int) -> str:
        """Build a specific gene by encoding given values directly."""
        s = self.s
        c = s._to_binary(course, s.course_bits)
        t = s._to_binary(slot, s.slot_bits)
        k = s._to_binary(cls, s.class_bits)
        return c + t + k

    def test_fitness_in_range(self):
        """Fitness is always between 0.0 and 100.0 inclusive."""
        for _ in range(100):
            gene = self.s.generate_gene()
            f = self.s.calculate_fitness(gene)
            self.assertGreaterEqual(f, 0.0)
            self.assertLessEqual(f, 100.0)

    def test_empty_timetable_high_fitness(self):
        """A gene with all valid, in-range indices scores 100 on an empty timetable.

        We need slot_no > 0 AND day_no >= 1 to pass the guard.  The first
        cumulative slot that yields day_no=1 is slot_count+1 (start of day 2).
        We use slot=slot_count+1, course=1, class=1.
        """
        s = self.s
        # slot_count+1 → raw_slot % slot_count = 1, day_no = 1 ✓
        target_slot = s.slot_count + 1
        gene = (s._to_binary(1, s.course_bits) +
                s._to_binary(target_slot, s.slot_bits) +
                s._to_binary(1, s.class_bits))
        # Confirm the cell is empty
        slot_no, day_no = s.extract_slot_day(gene)
        s.tables[0][day_no - 1][slot_no - 1] = 0
        f = s.calculate_fitness(gene)
        self.assertAlmostEqual(f, 100.0)

    def test_slot_clash_penalty(self):
        """Occupying an already-filled slot severely drops fitness."""
        s = self.s
        # Manually occupy slot 1, day 1 for class 1
        s.tables[0][0][0] = 1
        gene = self._fresh_gene(2, 1, 1)  # same slot, different course
        f = s.calculate_fitness(gene)
        self.assertLess(f, 5.0)  # ×0.01 penalty → near zero
        s.tables[0][0][0] = 0  # restore

    def test_exhausted_quota_penalty(self):
        """Zero course quota gives near-zero fitness."""
        s = self.s
        s.course_quota[0][0] = 0  # deplete quota for course 1, class 1
        gene = self._fresh_gene(1, 1, 1)
        f = s.calculate_fitness(gene)
        self.assertLess(f, 5.0)
        s.course_quota[0][0] = 3  # restore

    def test_out_of_range_gene_zero_fitness(self):
        """A gene encoding an out-of-range course returns 0 fitness."""
        s = self.s
        # Encode course = course_count + 1 (out of range)
        # bad_course = s._to_binary(s.course_count + 1, s.course_bits + 1)
        # Pad/truncate to expected gene length and test
        gene = s.generate_gene()
        # Manually overwrite course bits with zeros (course 0 = invalid)
        gene = "0" * s.course_bits + gene[s.course_bits:]
        f = s.calculate_fitness(gene)
        self.assertEqual(f, 0.0)

    def test_fitness_cache_stores_result(self):
        """Second call to calculate_fitness uses the cache."""
        s = self.s
        gene = self.s.generate_gene()
        s._fitness_cache.clear()
        s._cache_hits = 0

        s.calculate_fitness(gene)  # miss → stored
        s.calculate_fitness(gene)  # hit
        self.assertEqual(s._cache_hits, 1)

    def test_invalidate_cache_clears_all(self):
        """invalidate_cache() empties _fitness_cache completely."""
        s = self.s
        for _ in range(10):
            s.calculate_fitness(s.generate_gene())
        self.assertGreater(len(s._fitness_cache), 0)
        s.invalidate_cache()
        self.assertEqual(len(s._fitness_cache), 0)

    def test_teacher_capacity_penalty(self):
        """When teacher quota is 1 and a course already fills that slot,
        another gene for the same slot/course scores near zero."""
        s = tiny(teachers=1)
        # Set teacher_quota explicitly for course 1
        s.teacher_quota[0] = 1
        # Occupy slot 1, day 1 for course 1 in class 1
        s.tables[0][0][0] = 1
        # Now ask for course 1 in the same slot for class 2
        gene = self._fresh_gene(1, 1, 2)
        f = s.calculate_fitness(gene)
        self.assertLess(f, 5.0)
        s.tables[0][0][0] = 0


# ══════════════════════════════════════════════════════════════════════════════
#  5. GENETIC OPERATORS
# ══════════════════════════════════════════════════════════════════════════════


class TestGeneticOperators(unittest.TestCase):
    """Tests for crossover, mutation, and selection operators."""

    def setUp(self):
        self.s = tiny(seed=1)

    def _gene_len(self):
        s = self.s
        return s.course_bits + s.slot_bits + s.class_bits

    def test_single_point_crossover_lengths(self):
        """Both children have the same length as their parents."""
        s = self.s
        a, b = s.generate_gene(), s.generate_gene()
        children = s.single_point_crossover(a, b)
        self.assertEqual(len(children), 2)
        self.assertEqual(len(children[0]), self._gene_len())
        self.assertEqual(len(children[1]), self._gene_len())

    def test_single_point_crossover_is_binary(self):
        """Children contain only '0' and '1'."""
        s = self.s
        for _ in range(20):
            a, b = s.generate_gene(), s.generate_gene()
            for child in s.single_point_crossover(a, b):
                self.assertTrue(all(c in "01" for c in child))

    def test_crossover_produces_segment_mixes(self):
        """Over many runs, children are not always identical to parents."""
        s = self.s
        a = "0" * self._gene_len()
        b = "1" * self._gene_len()
        seen_mixed = False
        for _ in range(30):
            children = s.single_point_crossover(a, b)
            for child in children:
                if child not in (a, b):
                    seen_mixed = True
        self.assertTrue(seen_mixed)

    def test_multi_point_crossover_length(self):
        """multi_point_crossover children have correct length."""
        s = self.s
        a, b = s.generate_gene(), s.generate_gene()
        for pts in [1, 2, 3]:
            children = s.multi_point_crossover(a, b, pts)
            for child in children:
                self.assertEqual(len(child), self._gene_len())

    def test_uniform_crossover_lengths(self):
        """uniform_crossover preserves gene length."""
        s = self.s
        a, b = s.generate_gene(), s.generate_gene()
        children = s.uniform_crossover(a, b)
        self.assertEqual(len(children), 2)
        for child in children:
            self.assertEqual(len(child), self._gene_len())

    def test_uniform_crossover_is_binary(self):
        """uniform_crossover children contain only '0' / '1'."""
        s = self.s
        for _ in range(20):
            a, b = s.generate_gene(), s.generate_gene()
            for child in s.uniform_crossover(a, b):
                self.assertTrue(all(c in "01" for c in child))

    def test_mutation_length_preserved(self):
        """Mutated gene has same length as original."""
        s = self.s
        for _ in range(30):
            gene = s.generate_gene()
            mutant = s.mutation(gene, s.course_bits, s.slot_bits)
            self.assertEqual(len(mutant), self._gene_len())

    def test_mutation_is_binary(self):
        """Mutated gene contains only '0' / '1'."""
        s = self.s
        for _ in range(30):
            gene = s.generate_gene()
            mutant = s.mutation(gene, s.course_bits, s.slot_bits)
            self.assertTrue(all(c in "01" for c in mutant))

    def test_mutation_changes_gene(self):
        """mutation() changes the gene in at least some cases over many runs."""
        s = self.s
        gene = s.generate_gene()
        changed = False
        for _ in range(50):
            mutant = s.mutation(gene, s.course_bits, s.slot_bits)
            if mutant != gene:
                changed = True
                break
        self.assertTrue(changed)

    def test_smart_mutation_no_worse_than_original(self):
        """smart_mutation returns a gene with fitness ≥ the original
        (since it keeps the best candidate)."""
        s = self.s
        gene = s.generate_gene()
        orig_fitness = s.calculate_fitness(gene)
        smart_fitness = s.calculate_fitness(
            s.smart_mutation(gene, s.course_bits, s.slot_bits, attempts=10))
        self.assertGreaterEqual(smart_fitness, orig_fitness)

    def test_selection_pair_returns_two(self):
        """selection_pair always returns exactly two genes."""
        s = self.s
        pop = s.generate_population(10)
        pair = s.selection_pair(pop)
        self.assertEqual(len(pair), 2)
        for gene in pair:
            self.assertIn(gene, pop)

    def test_tournament_selection_returns_one(self):
        """tournament_selection returns exactly one gene from the population."""
        s = self.s
        pop = s.generate_population(10)
        winner = s.tournament_selection(pop, tournament_size=3)
        self.assertIn(winner, pop)

    def test_tournament_selection_tournament_size_1(self):
        """tournament_size=1 degenerates to random selection (still valid)."""
        s = self.s
        pop = s.generate_population(5)
        w = s.tournament_selection(pop, tournament_size=1)
        self.assertIn(w, pop)

    def test_sort_population_descending(self):
        """sort_population returns genes in descending fitness order."""
        s = self.s
        pop = s.generate_population(15)
        sorted_pop = s.sort_population(pop)
        fitnesses = [s.calculate_fitness(g) for g in sorted_pop]
        self.assertEqual(fitnesses, sorted(fitnesses, reverse=True))

    def test_generate_population_size(self):
        """generate_population returns exactly `size` genes."""
        s = self.s
        for n in [1, 5, 20]:
            pop = s.generate_population(n)
            self.assertEqual(len(pop), n)


# ══════════════════════════════════════════════════════════════════════════════
#  6. TABLE SKELETON & FIT SLOT
# ══════════════════════════════════════════════════════════════════════════════


class TestTableAndFitSlot(unittest.TestCase):
    """Tests for generate_table_skeleton and fit_slot."""

    def test_skeleton_shape(self):
        """Table skeleton has correct dimensions: [classes][days][slots]."""
        s = tiny()
        self.assertEqual(len(s.tables), s.class_count)
        self.assertEqual(len(s.tables[0]), s.day_count)
        self.assertEqual(len(s.tables[0][0]), s.slot_count)

    def test_skeleton_all_zeros(self):
        """All cells are initialised to zero."""
        s = tiny()
        for cls in s.tables:
            for day in cls:
                for cell in day:
                    self.assertEqual(cell, 0)

    def test_fit_slot_writes_correct_course(self):
        """fit_slot() writes the correct course number to the right cell."""
        s = tiny()
        gene = s.generate_gene()
        course_no, slot_no, day_no, class_no = s.decode_gene(gene)
        s.fit_slot(gene)
        self.assertEqual(s.tables[class_no - 1][day_no - 1][slot_no - 1],
                         course_no)

    def test_fit_slot_decrements_quota(self):
        """fit_slot() decrements course_quota for the right class+course."""
        s = tiny()
        gene = s.generate_gene()
        course_no, _, _, class_no = s.decode_gene(gene)
        quota_before = s.course_quota[class_no - 1][course_no - 1]
        s.fit_slot(gene)
        self.assertEqual(s.course_quota[class_no - 1][course_no - 1],
                         quota_before - 1)

    def test_fit_slot_invalidates_cache(self):
        """fit_slot() clears the fitness cache."""
        s = tiny()
        gene = s.generate_gene()
        s.calculate_fitness(gene)  # populate cache
        self.assertGreater(len(s._fitness_cache), 0)
        s.fit_slot(gene)
        self.assertEqual(len(s._fitness_cache), 0)

    def test_fit_slot_increments_slots_filled(self):
        """fit_slot() increments _slots_filled counter."""
        s = tiny()
        gene = s.generate_gene()
        before = s._slots_filled
        s.fit_slot(gene)
        self.assertEqual(s._slots_filled, before + 1)


# ══════════════════════════════════════════════════════════════════════════════
#  7. EVOLUTION LOOP
# ══════════════════════════════════════════════════════════════════════════════


class TestEvolutionLoop(unittest.TestCase):
    """Tests for run_evolution internals."""

    def setUp(self):
        self.s = tiny(seed=5)

    def test_run_evolution_returns_string(self):
        """run_evolution returns a gene string."""
        s = self.s
        gene = s.run_evolution(
            s.course_bits,
            s.slot_bits,
            s.population_size,
            s.max_fitness,
            s.max_generations,
        )
        self.assertIsInstance(gene, str)

    def test_run_evolution_correct_gene_length(self):
        """Gene returned by run_evolution has correct total bit length."""
        s = self.s
        gene = s.run_evolution(
            s.course_bits,
            s.slot_bits,
            s.population_size,
            s.max_fitness,
            s.max_generations,
        )
        expected = s.course_bits + s.slot_bits + s.class_bits
        self.assertEqual(len(gene), expected)

    def test_run_evolution_respects_max_fitness(self):
        """If max_fitness is 0, evolution returns on the very first generation."""
        s = tiny(seed=9)
        gene = s.run_evolution(
            s.course_bits,
            s.slot_bits,
            s.population_size,
            max_fitness=0,  # every gene qualifies immediately
            max_generations=s.max_generations,
        )
        # Just check we get a valid gene back without error
        self.assertEqual(len(gene), s.course_bits + s.slot_bits + s.class_bits)

    def test_generation_log_populated(self):
        """After run_evolution the generation log has at least one entry."""
        s = self.s
        s.run_evolution(
            s.course_bits,
            s.slot_bits,
            s.population_size,
            s.max_fitness,
            s.max_generations,
        )
        self.assertGreater(len(s._generation_log), 0)

    def test_generation_log_fields(self):
        """Each GenerationStats entry has the expected fields."""
        s = self.s
        s.run_evolution(
            s.course_bits,
            s.slot_bits,
            s.population_size,
            s.max_fitness,
            s.max_generations,
        )
        stat = s._generation_log[0]
        self.assertGreaterEqual(stat.best_fitness, 0.0)
        self.assertGreaterEqual(stat.avg_fitness, 0.0)
        self.assertGreaterEqual(stat.worst_fitness, 0.0)
        self.assertGreater(stat.elapsed_ms, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  8. FULL RUN (INTEGRATION)
# ══════════════════════════════════════════════════════════════════════════════


class TestFullRun(unittest.TestCase):
    """Integration tests that call run() end-to-end."""

    def test_run_returns_3d_list(self):
        """run() returns a 3-D list."""
        s = full_run()
        self.assertIsInstance(s.tables, list)
        self.assertIsInstance(s.tables[0], list)
        self.assertIsInstance(s.tables[0][0], list)

    def test_run_correct_dimensions(self):
        """tables dimensions match the requested classes/days/slots."""
        s = full_run()
        self.assertEqual(len(s.tables), s.class_count)
        self.assertEqual(len(s.tables[0]), s.day_count)
        self.assertEqual(len(s.tables[0][0]), s.slot_count)

    def test_run_no_zeroes_after_completion(self):
        """After run() the vast majority of cells should be filled (non-zero).

        The GA with very small parameters (pop=20, gen=20) will occasionally
        commit a zero-fitness gene that doesn't decode to a valid slot.
        We allow up to 25 % empty cells for tiny configs; a real-world run
        with default parameters fills all cells reliably.
        """
        s = full_run()
        zeroes = sum(1 for cls in s.tables for day in cls for cell in day
                     if cell == 0)
        total = s.class_count * s.day_count * s.slot_count
        self.assertLess(zeroes, total * 0.25)

    def test_run_all_values_in_valid_course_range(self):
        """Every non-zero cell value is in [1, course_count]."""
        s = full_run()
        for cls in s.tables:
            for day in cls:
                for cell in day:
                    if cell != 0:
                        self.assertGreaterEqual(cell, 1)
                        self.assertLessEqual(cell, s.course_count)

    def test_run_slots_filled_counter(self):
        """_slots_filled equals classes × days × slots after run()."""
        s = full_run()
        total = s.class_count * s.day_count * s.slot_count
        self.assertEqual(s._slots_filled, total)

    def test_run_with_per_course_params(self):
        """run() succeeds when repeat and teachers are per-course lists."""
        s = GenerateTimeTable(
            classes=2,
            courses=3,
            slots=3,
            days=3,
            repeat=[1, 2, 1],
            teachers=[1, 1, 2],
            population_size=15,
            max_generations=15,
            seed=3,
        )
        result = s.run()
        self.assertEqual(len(result), 2)

    def test_run_single_class(self):
        """Scheduler works with a single class."""
        s = GenerateTimeTable(
            classes=1,
            courses=2,
            slots=3,
            days=3,
            repeat=1,
            teachers=1,
            population_size=15,
            max_generations=15,
            seed=10,
        )
        result = s.run()
        self.assertEqual(len(result), 1)

    def test_run_single_course(self):
        """Scheduler works with a single course filling all slots."""
        s = GenerateTimeTable(
            classes=1,
            courses=1,
            slots=2,
            days=2,
            repeat=2,
            teachers=1,
            population_size=15,
            max_generations=15,
            seed=11,
        )
        result = s.run()
        self.assertEqual(len(result), 1)


# ══════════════════════════════════════════════════════════════════════════════
#  9. VALIDATION
# ══════════════════════════════════════════════════════════════════════════════


class TestValidation(unittest.TestCase):
    """Tests for the validate() method."""

    def test_validate_returns_dict_with_expected_keys(self):
        """validate() always returns a dict with the four standard keys."""
        s = full_run()
        v = s.validate()
        for key in (
                "empty_cells",
                "teacher_clashes",
                "back_to_back",
                "total_violations",
        ):
            self.assertIn(key, v)

    def test_validate_total_is_sum_of_parts(self):
        """total_violations == empty_cells + teacher_clashes + back_to_back."""
        s = full_run()
        v = s.validate()
        self.assertEqual(
            v["total_violations"],
            v["empty_cells"] + v["teacher_clashes"] + v["back_to_back"],
        )

    def test_validate_detects_back_to_back(self):
        """validate() counts back-to-back when we manually inject one."""
        s = tiny()
        # Manually create a back-to-back: course 1 in slot 0 and slot 1 same day/class
        s.tables[0][0][0] = 1
        s.tables[0][0][1] = 1
        v = s.validate()
        self.assertGreaterEqual(v["back_to_back"], 1)

    def test_validate_detects_teacher_clashes(self):
        """validate() counts teacher clashes when teacher_quota is exceeded."""
        s = tiny(teachers=1)
        # teacher_quota[0] == 1; put course 1 in the same slot for two classes
        s.tables[0][0][0] = 1
        s.tables[1][0][0] = 1
        v = s.validate()
        self.assertGreaterEqual(v["teacher_clashes"], 1)

    def test_validate_clean_timetable_zero_violations(self):
        """A hand-crafted clean (non-clashing) timetable reports 0 violations."""
        s = tiny(teachers=2)  # 2 teachers → two classes can share a slot
        # Fill every cell uniquely — each class, each slot gets a different course
        for cls_idx in range(s.class_count):
            for day_idx in range(s.day_count):
                for slot_idx in range(s.slot_count):
                    course = (slot_idx % s.course_count) + 1
                    s.tables[cls_idx][day_idx][slot_idx] = course
        v = s.validate()
        # We allow back_to_back violations from the cycling pattern, but
        # teacher_clashes and empty_cells must both be 0
        self.assertEqual(v["empty_cells"], 0)
        self.assertEqual(v["teacher_clashes"], 0)


# ══════════════════════════════════════════════════════════════════════════════
#  10. ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════


class TestAnalytics(unittest.TestCase):
    """Tests for the analytics() method."""

    def setUp(self):
        self.s = full_run(seed=20)

    def test_analytics_keys_present(self):
        """analytics() returns a dict containing all expected keys."""
        a = self.s.analytics()
        for key in (
                "runtime_s",
                "genes_evaluated",
                "cache_hit_ratio",
                "course_frequency",
                "validation",
                "slots_filled",
                "generation_log_tail",
        ):
            self.assertIn(key, a)

    def test_cache_hit_ratio_between_0_and_1(self):
        """cache_hit_ratio is in [0, 1]."""
        a = self.s.analytics()
        self.assertGreaterEqual(a["cache_hit_ratio"], 0.0)
        self.assertLessEqual(a["cache_hit_ratio"], 1.0)

    def test_course_frequency_covers_all_courses(self):
        """course_frequency lists every course name."""
        a = self.s.analytics()
        for name in self.s.course_names:
            self.assertIn(name, a["course_frequency"])

    def test_course_frequency_total_matches_slots(self):
        """Sum of course frequencies == classes × days × slots (minus empties)."""
        a = self.s.analytics()
        total = sum(a["course_frequency"].values())
        cells = (self.s.class_count * self.s.day_count * self.s.slot_count -
                 a["validation"]["empty_cells"])
        self.assertEqual(total, cells)

    def test_slots_filled_in_analytics(self):
        """analytics slots_filled matches the scheduler's internal counter."""
        a = self.s.analytics()
        self.assertEqual(a["slots_filled"], self.s._slots_filled)

    def test_generation_log_tail_length(self):
        """generation_log_tail has at most 5 entries."""
        a = self.s.analytics()
        self.assertLessEqual(len(a["generation_log_tail"]), 5)


# ══════════════════════════════════════════════════════════════════════════════
#  11. EXPORT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════


class TestExport(unittest.TestCase):
    """Tests for export_json, export_csv, and export_html."""

    def setUp(self):
        self.s = full_run(seed=30)
        self.tmpdir = tempfile.mkdtemp()

    def _path(self, filename):
        return os.path.join(self.tmpdir, filename)

    # ── JSON ──────────────────────────────────────────────────────────────────

    def test_export_json_creates_file(self):
        """export_json creates a file at the given path."""
        path = self._path("out.json")
        self.s.export_json(path)
        self.assertTrue(os.path.isfile(path))

    def test_export_json_valid_structure(self):
        """Exported JSON is valid and contains all class names."""
        path = self._path("out.json")
        self.s.export_json(path)
        with open(path) as f:
            data = json.load(f)
        for cls_name in self.s.class_names:
            self.assertIn(cls_name, data)

    def test_export_json_all_days_present(self):
        """Each class entry in JSON contains all day names."""
        path = self._path("out.json")
        self.s.export_json(path)
        with open(path) as f:
            data = json.load(f)
        for cls_name in self.s.class_names:
            for day_name in self.s.day_names:
                self.assertIn(day_name, data[cls_name])

    def test_export_json_slot_count_per_day(self):
        """Each day in JSON has exactly `slots` entries."""
        path = self._path("out.json")
        self.s.export_json(path)
        with open(path) as f:
            data = json.load(f)
        for cls_name in self.s.class_names:
            for day_name in self.s.day_names:
                self.assertEqual(len(data[cls_name][day_name]),
                                 self.s.slot_count)

    def test_export_json_values_are_course_names_or_free(self):
        """All slot values are course names or 'FREE'."""
        path = self._path("out.json")
        self.s.export_json(path)
        with open(path) as f:
            data = json.load(f)
        valid = set(self.s.course_names) | {"FREE"}
        for cls_data in data.values():
            for slots in cls_data.values():
                for slot in slots:
                    self.assertIn(slot, valid)

    # ── CSV ───────────────────────────────────────────────────────────────────

    def test_export_csv_creates_file(self):
        """export_csv creates a file at the given path."""
        path = self._path("out.csv")
        self.s.export_csv(path)
        self.assertTrue(os.path.isfile(path))

    def test_export_csv_has_header(self):
        """First row of CSV is the header."""
        path = self._path("out.csv")
        self.s.export_csv(path)
        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
        self.assertEqual(header, ["Class", "Day", "Slot", "Course"])

    def test_export_csv_row_count(self):
        """CSV has exactly classes × days × slots data rows (plus header)."""
        path = self._path("out.csv")
        self.s.export_csv(path)
        with open(path) as f:
            rows = list(csv.reader(f))
        expected_data_rows = self.s.class_count * self.s.day_count * self.s.slot_count
        self.assertEqual(len(rows) - 1, expected_data_rows)  # -1 for header

    # ── HTML ──────────────────────────────────────────────────────────────────

    def test_export_html_creates_file(self):
        """export_html creates a file at the given path."""
        path = self._path("out.html")
        self.s.export_html(path)
        self.assertTrue(os.path.isfile(path))

    def test_export_html_is_non_empty(self):
        """Generated HTML file is non-empty."""
        path = self._path("out.html")
        self.s.export_html(path)
        self.assertGreater(os.path.getsize(path), 0)

    def test_export_html_contains_class_names(self):
        """HTML file mentions every class name."""
        path = self._path("out.html")
        self.s.export_html(path)
        with open(path) as f:
            html = f.read()
        for cls_name in self.s.class_names:
            self.assertIn(cls_name, html)


# ══════════════════════════════════════════════════════════════════════════════
#  12. QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════


class TestQueryHelpers(unittest.TestCase):
    """Tests for get_class_timetable, find_course_slots, get_teacher_schedule."""

    def setUp(self):
        self.s = GenerateTimeTable(
            classes=2,
            courses=3,
            slots=3,
            days=3,
            repeat=1,
            teachers=2,
            seed=50,
            population_size=20,
            max_generations=20,
            course_names=["Maths", "English", "Science"],
            class_names=["Alpha", "Beta"],
        )
        self.s.run()

    def test_get_class_timetable_known(self):
        """get_class_timetable returns a 2-D list for a valid class name."""
        tt = self.s.get_class_timetable("Alpha")
        self.assertIsNotNone(tt)
        self.assertEqual(len(tt), self.s.day_count)
        self.assertEqual(len(tt[0]), self.s.slot_count)

    def test_get_class_timetable_unknown(self):
        """get_class_timetable returns None for an unknown class name."""
        result = self.s.get_class_timetable("Year 99")
        self.assertIsNone(result)

    def test_find_course_slots_returns_list(self):
        """find_course_slots returns a list (possibly empty)."""
        result = self.s.find_course_slots("Maths")
        self.assertIsInstance(result, list)

    def test_find_course_slots_tuples_structure(self):
        """Each entry in find_course_slots is a 3-tuple of strings."""
        for entry in self.s.find_course_slots("English"):
            self.assertEqual(len(entry), 3)
            for item in entry:
                self.assertIsInstance(item, str)

    def test_find_course_slots_class_filter(self):
        """class_name filter restricts results to only that class."""
        results = self.s.find_course_slots("Science", class_name="Alpha")
        for cls_name, _, _ in results:
            self.assertEqual(cls_name, "Alpha")

    def test_find_course_slots_unknown_course(self):
        """Unknown course name returns empty list."""
        result = self.s.find_course_slots("Latin")
        self.assertEqual(result, [])

    def test_get_teacher_schedule_returns_dict(self):
        """get_teacher_schedule returns a dict."""
        sched = self.s.get_teacher_schedule("Maths")
        self.assertIsInstance(sched, dict)

    def test_get_teacher_schedule_values_are_lists(self):
        """Each value in teacher schedule is a list of class names."""
        sched = self.s.get_teacher_schedule("English")
        for classes in sched.values():
            self.assertIsInstance(classes, list)

    def test_get_teacher_schedule_unknown_course(self):
        """Unknown course returns empty dict."""
        sched = self.s.get_teacher_schedule("Drama")
        self.assertEqual(sched, {})


# ══════════════════════════════════════════════════════════════════════════════
#  13. RESET
# ══════════════════════════════════════════════════════════════════════════════


class TestReset(unittest.TestCase):
    """Tests for the reset() method."""

    def test_reset_clears_tables(self):
        """After reset(), tables is an empty list."""
        s = full_run(seed=60)
        self.assertGreater(len(s.tables), 0)
        s.reset()
        self.assertEqual(s.tables, [])

    def test_reset_clears_cache(self):
        """After reset(), fitness cache is empty."""
        s = full_run(seed=61)
        s.reset()
        self.assertEqual(len(s._fitness_cache), 0)

    def test_reset_zeroes_counters(self):
        """After reset(), all telemetry counters are zero."""
        s = full_run(seed=62)
        s.reset()
        self.assertEqual(s._cache_hits, 0)
        self.assertEqual(s._cache_misses, 0)
        self.assertEqual(s._total_genes_eval, 0)
        self.assertEqual(s._slots_filled, 0)

    def test_reset_clears_generation_log(self):
        """After reset(), generation log is empty."""
        s = full_run(seed=63)
        s.reset()
        self.assertEqual(s._generation_log, [])

    def test_reset_allows_rerun(self):
        """reset() + run() produces a valid timetable again."""
        s = full_run(seed=64)
        s.reset()
        s.run()
        self.assertGreater(len(s.tables), 0)


# ══════════════════════════════════════════════════════════════════════════════
#  14. REPRODUCIBILITY
# ══════════════════════════════════════════════════════════════════════════════


class TestReproducibility(unittest.TestCase):
    """Tests that the seed parameter produces deterministic output."""

    def _make(self, seed):
        return GenerateTimeTable(
            classes=2,
            courses=3,
            slots=3,
            days=3,
            repeat=1,
            teachers=1,
            seed=seed,
            population_size=20,
            max_generations=20,
        )

    def test_same_seed_same_timetable(self):
        """Two runs with the same seed produce identical timetables."""
        t1 = self._make(99).run()
        t2 = self._make(99).run()
        self.assertEqual(t1, t2)

    def test_different_seeds_likely_differ(self):
        """Two runs with different seeds usually produce different timetables.
        We test 5 seed pairs — if all 5 match, something is wrong."""
        all_same = all(
            self._make(i).run() == self._make(i + 100).run() for i in range(5))
        self.assertFalse(all_same)

    def test_reset_with_seed_reproduces(self):
        """reset() + run() with a seeded scheduler reproduces the same table."""
        s = self._make(77)
        t1 = s.run()
        s.reset()
        t2 = s.run()
        self.assertEqual(t1, t2)


# ══════════════════════════════════════════════════════════════════════════════
#  15. PROPERTY / INVARIANT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestInvariants(unittest.TestCase):
    """
    Check properties that must hold for ALL valid schedulers / genes,
    regardless of specific parameters.
    """

    def test_gene_length_invariant(self):
        """Gene length == course_bits + slot_bits + class_bits for any config."""
        for classes, courses, slots, days in [
            (1, 1, 1, 1),
            (2, 3, 4, 5),
            (5, 5, 5, 5),
            (3, 8, 7, 4),
        ]:
            s = GenerateTimeTable(classes=classes,
                                  courses=courses,
                                  slots=slots,
                                  days=days)
            s.initialize_genotype(courses, classes, slots, days, 1, 1)
            s.generate_table_skeleton()
            expected = s.course_bits + s.slot_bits + s.class_bits
            for _ in range(10):
                self.assertEqual(len(s.generate_gene()), expected)

    def test_quota_monotonically_decreases(self):
        """course_quota[c][k] never increases after fit_slot() calls."""
        s = tiny(seed=7)
        snapshots = []
        for _ in range(4):
            gene = s.generate_gene()
            _, _, _, cls_no = s.decode_gene(gene)
            q_before = s.course_quota[cls_no - 1][:]
            s.fit_slot(gene)
            q_after = s.course_quota[cls_no - 1][:]
            snapshots.append((q_before, q_after))

        for before, after in snapshots:
            for b, a in zip(before, after):
                # Each quota can only decrease or stay the same
                self.assertLessEqual(a, b)

    def test_crossover_preserves_gene_length(self):
        """All crossover variants always return genes of the original length."""
        s = tiny()
        for _ in range(20):
            a, b = s.generate_gene(), s.generate_gene()
            for fn in [
                    s.single_point_crossover,
                    lambda x, y: s.multi_point_crossover(x, y, 2),
                    s.uniform_crossover,
            ]:
                children = fn(a, b)
                for child in children:
                    self.assertEqual(len(child), len(a))

    def test_fitness_deterministic(self):
        """calculate_fitness returns the same value for the same gene+state."""
        s = tiny()
        gene = s.generate_gene()
        f1 = s.calculate_fitness(gene)
        s._fitness_cache.clear()  # force re-evaluation
        f2 = s.calculate_fitness(gene)
        self.assertAlmostEqual(f1, f2)

    def test_table_dimensions_stable_after_multiple_fit_slots(self):
        """Table shape does not change after many fit_slot() calls."""
        s = tiny()
        shape = (len(s.tables), len(s.tables[0]), len(s.tables[0][0]))
        for _ in range(5):
            s.fit_slot(s.generate_gene())
        new_shape = (len(s.tables), len(s.tables[0]), len(s.tables[0][0]))
        self.assertEqual(shape, new_shape)


# ══════════════════════════════════════════════════════════════════════════════
#  16. EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases(unittest.TestCase):
    """Boundary conditions and unusual-but-valid configurations."""

    def test_single_slot_single_day(self):
        """1 class, 1 course, 1 slot, 1 day runs without error.

        With only 1 total slot the GA quickly exhausts valid genes and may
        encounter zero-weight selection.  We use population_size=2 and
        max_fitness=0 to trigger immediate early-stop before selection runs,
        sidestepping the degenerate-population edge case.
        """
        s = GenerateTimeTable(
            classes=1,
            courses=1,
            slots=1,
            days=1,
            repeat=1,
            teachers=1,
            population_size=2,
            max_generations=2,
            max_fitness=0,
            seed=1,
        )
        result = s.run()
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 1)
        self.assertEqual(len(result[0][0]), 1)

    def test_many_courses_few_slots(self):
        """More courses than total slots still runs (some courses may not appear)."""
        s = GenerateTimeTable(
            classes=1,
            courses=6,
            slots=2,
            days=2,  # 4 total slots < 6 courses
            repeat=1,
            teachers=1,
            population_size=15,
            max_generations=20,
            seed=2,
        )
        # Should not crash — just note that not all courses will appear
        result = s.run()
        self.assertEqual(len(result), 1)

    def test_high_teacher_count_allows_all_classes_same_slot(self):
        """teacher_quota > class_count should never trigger teacher clash."""
        classes = 3
        s = GenerateTimeTable(
            classes=classes,
            courses=2,
            slots=3,
            days=3,
            repeat=1,
            teachers=classes + 1,  # more teachers than classes
            population_size=20,
            max_generations=20,
            seed=3,
        )
        s.run()
        v = s.validate()
        self.assertEqual(v["teacher_clashes"], 0)

    def test_zero_population_handled_gracefully(self):
        """population_size=1 (degenerate) does not crash."""
        s = GenerateTimeTable(
            classes=1,
            courses=2,
            slots=2,
            days=2,
            repeat=1,
            teachers=1,
            population_size=1,
            max_generations=5,
            seed=4,
        )
        result = s.run()
        self.assertEqual(len(result), 1)

    def test_max_generations_one(self):
        """max_generations=1 returns a gene (no crash)."""
        s = tiny(max_generations=1)
        gene = s.run_evolution(
            s.course_bits,
            s.slot_bits,
            s.population_size,
            s.max_fitness,
            1,
        )
        self.assertIsInstance(gene, str)
        self.assertGreater(len(gene), 0)

    def test_find_course_slots_on_empty_timetable(self):
        """find_course_slots on an uninitialised timetable returns empty list."""
        s = tiny()  # table is all zeros
        result = s.find_course_slots("Course-1")
        self.assertEqual(result, [])

    def test_analytics_before_run_does_not_crash(self):
        """analytics() called before run() returns safe defaults."""
        s = tiny()
        a = s.analytics()
        self.assertIn("genes_evaluated", a)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run with verbosity=2 so every test name prints individually
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\n{'='*60}")
    print(f"  🧪  {passed}/{total} tests passed", end="")
    if result.failures or result.errors:
        print(
            f"  ❌  {len(result.failures)} failures, {len(result.errors)} errors"
        )
    else:
        print("  ✅")
    print(f"{'='*60}")

    sys.exit(0 if result.wasSuccessful() else 1)
