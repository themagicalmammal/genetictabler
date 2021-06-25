import random

from schedule import *


def generate_population(size):
    # our population will be a list of genes
    gene_length = initialize_gene()
    return [generate_gene(gene_length) for _ in range(size)]


def single_point_crossover(gene_a, gene_b, gene_length):

    # Now we choose the point/location for single point crossover which will be a random index
    # between 2nd element and the second last element.
    p = random.randint(1, gene_length - 1)

    gene_a, gene_b = gene_a[0:p] + gene_b[p:], gene_b[0:p] + gene_a[p:]

    return gene_a, gene_b


def multi_point_crossover(gene_a, gene_b, gene_length, points):

    # We use the single point crossover, multiple times
    for _ in range(points):
        gene_a, gene_b = single_point_crossover(gene_a, gene_b, gene_length)

    return gene_a, gene_b


def mutation(gene, num=1, probability=0.5):
    for _ in range(num):

        # we choose a random position "p" in the gene which we will mutate.
        p = random.randrange(len(gene))

        if random.uniform(0, 1) > probability:
            gene[p] = gene[p]
        else:
            gene[p] = generate_courses()
    return gene


def selection_pair(population):
    return random.choices(
        population=population,
        weights=[calculate_fitness(gene) for gene in population],
        k=2,
    )


def sort_population(population):
    return sorted(population, key=calculate_fitness, reverse=True)


def run_evolution(
    total_days, slots, no_courses, population_size, max_fitness, max_generations=100
):

    initialize_genotype(no_courses, slots, total_days)
    population = generate_population(population_size)
    for i in range(max_generations):
        population = sorted(population, key=calculate_fitness, reverse=True)

        if calculate_fitness(population[0]) >= max_fitness:
            break

        next_generation = population[0:2]

        for j in range(len(population) // 2 - 1):
            parents = selection_pair(population)
            child_a, child_b = mutation(parents[0], parents[1])
            child_a, child_b = mutation(child_a), mutation(child_b)

            next_generation += [child_a, child_b]

        population = next_generation

    return population[0]
