"""Genetic operators: crossover, mutation, and selection.

These stateless operators work on gene strings and use the shared encoder
to know bit-widths for semantic crossover.
"""

from __future__ import annotations

import random

from genetictabler.encoding import GeneEncoder
from genetictabler.fitness import FitnessEvaluator
from genetictabler.types import Gene


class GeneticOperators:
    """GA crossover, mutation, and selection operators."""

    def __init__(
        self,
        encoder: GeneEncoder,
        evaluator: FitnessEvaluator,
        elite_ratio: float,
        mutation_rate: float,
        adaptive: bool,
    ) -> None:
        self._encoder = encoder
        self._evaluator = evaluator
        self.elite_ratio = elite_ratio
        self.mutation_rate = mutation_rate
        self.adaptive = adaptive

    # ── Crossover ──────────────────────────────────────────────────────────

    def single_point_crossover(self, gene_a: Gene, gene_b: Gene) -> list[Gene]:
        """Swap one logical segment (course / slot / class) between two parents.

        Keeps crossover semantically meaningful — always swaps entire concepts.
        """
        c = random.choice([1, 2, 3])
        cb = self._encoder.course_bits
        sb = self._encoder.slot_bits

        if c == 1:
            # Swap course segment
            child_c = gene_b[:cb] + gene_a[cb:]
            child_d = gene_a[:cb] + gene_b[cb:]
        elif c == 2:
            # Swap slot segment
            child_c = gene_a[:cb] + gene_b[cb : cb + sb] + gene_a[cb + sb :]
            child_d = gene_b[:cb] + gene_a[cb : cb + sb] + gene_b[cb + sb :]
        else:
            # Swap class segment
            child_c = gene_a[: cb + sb] + gene_b[cb + sb :]
            child_d = gene_b[: cb + sb] + gene_a[cb + sb :]

        return [child_c, child_d]

    def multi_point_crossover(
        self, gene_a: Gene, gene_b: Gene, points: int = 2
    ) -> list[Gene]:
        """Apply single_point_crossover ``points`` times in sequence."""
        a, b = gene_a, gene_b
        for _ in range(points):
            a, b = self.single_point_crossover(a, b)
        return [a, b]

    def uniform_crossover(self, gene_a: Gene, gene_b: Gene) -> list[Gene]:
        """Bit-level uniform crossover: each bit independently drawn from either parent.

        Produces higher diversity than segment-level crossover.
        """
        length = len(gene_a)
        child_c = "".join(
            gene_a[i] if random.random() < 0.5 else gene_b[i] for i in range(length)
        )
        child_d = "".join(
            gene_b[i] if child_c[i] == gene_a[i] else gene_a[i]
            for i in range(length)
        )
        return [child_c, child_d]

    # ── Mutation ───────────────────────────────────────────────────────────

    def mutation(self, gene: Gene) -> Gene:
        """Randomly replace one segment with a freshly encoded value."""
        c = random.choice([1, 2, 3])
        cb = self._encoder.course_bits
        sb = self._encoder.slot_bits

        if c == 1:
            return self._encoder.encode_course() + gene[cb:]
        elif c == 2:
            return gene[:cb] + self._encoder.encode_slot() + gene[cb + sb :]
        else:
            return gene[: cb + sb] + self._encoder.encode_class()

    def smart_mutation(self, gene: Gene, attempts: int = 5) -> Gene:
        """Guided mutation: try ``attempts`` mutations, keep the best.

        A simple (1+λ) local search wrapped around standard mutation.
        Falls back to the original gene if none improve.
        """
        best_gene = gene
        best_fitness = self._evaluator.calculate(gene)

        for _ in range(attempts):
            candidate = self.mutation(gene)
            f = self._evaluator.calculate(candidate)
            if f > best_fitness:
                best_fitness = f
                best_gene = candidate

        return best_gene

    # ── Selection ──────────────────────────────────────────────────────────

    def selection_pair(self, population: list[Gene]) -> list[Gene]:
        """Fitness-proportionate (roulette wheel) selection of two parents."""
        weights = [self._evaluator.calculate(g) for g in population]
        return random.choices(population=population, weights=weights, k=2)

    def tournament_selection(
        self, population: list[Gene], tournament_size: int = 3
    ) -> Gene:
        """Pick ``tournament_size`` random genes, return the fittest."""
        contestants = random.sample(
            population, min(tournament_size, len(population))
        )
        return max(contestants, key=self._evaluator.calculate)

    def sort_population(self, population: list[Gene]) -> list[Gene]:
        """Sort genes in descending fitness order (best first)."""
        return sorted(population, key=self._evaluator.calculate, reverse=True)

    # ── Population ─────────────────────────────────────────────────────────

    def generate_population(self, size: int) -> list[Gene]:
        """Spawn ``size`` random genes to form the initial population."""
        return [self._encoder.generate_gene() for _ in range(size)]
