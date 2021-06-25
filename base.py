#!/usr/bin/env python
# coding: utf-8

import random

from schedule import *


def generate_population(size):
    # our population will be a list of genomes.
    gene_length = initialize_genome()
    return [generate_genome(gene_length) for _ in range(size)]


def single_point_crossover(genome_a, genome_b):

    # Now we choose the point/location for single point crossover which will be a random index
    # between 2nd element and the second last element.
    p = random.randint(1, length - 1)

    genome_c = genome_a[0:p] + genome_b[p:]
    genome_d = genome_b[0:p] + genome_a[p:]

    return genome_c, genome_d


def mutation(genome, num=1, probability=0.5):
    for _ in range(num):

        # we choose a random position "p" in the genome which we will mutate.
        p = random.randrange(len(genome))

        if random.uniform(0, 1) > probability:
            genome[p] = genome[p]
        else:
            genome[p] = generate_courses()
    return genome


"""
def population_fitness(population):
    return sum([calculate_fitness(genome) for genome in population])
"""


def selection_pair(population):
    return random.choices(
        population=population,
        weights=[calculate_fitness(gene) for gene in population],
        k=2,
    )


def sort_population(population):
    return sorted(population, key=calculate_fitness, reverse=True)


def run_evolution(total_days,
                  slots,
                  no_courses,
                  population_size,
                  max_fitness,
                  max_generations=100):

    initialize_genotype(no_courses, slots, total_days)
    population = generate_population(population_size)
    for i in range(max_generations):
        population = sorted(population,
                            key=lambda genome: calculate_fitness(genome),
                            reverse=True)

        if calculate_fitness(population[0]) >= max_fitness:
            break

        next_generation = population[0:2]

        for j in range(len(population) // 2 - 1):
            parents = selection_pair(population)
            child_a, child_b = mutation(parents[0], parents[1])
            child_a, child_b = mutation(child_a), mutation(child_b)

            next_generation += [child_a, child_b]

        population = next_generation

    return population
