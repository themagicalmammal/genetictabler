from random import choice, choices
from schedule import *


def generate_population(size):
    # our population will be a list of genes
    initialize_gene()
    return [generate_gene() for _ in range(size)]


def single_point_crossover(gene_a, gene_b):
    # Now we choose the point/location for single point crossover which will be a random index
    # between 2nd element and the second last element.

    c = choice([1, 2, 3])
    if c == 1:
        gene_a[0:course_bits], gene_b[0:course_bits] = (
            gene_b[0:course_bits],
            gene_a[0:course_bits],
        )
    elif c == 2:
        gene_a[course_bits:slot_bits], gene_b[course_bits:slot_bits] = (
            gene_b[course_bits:slot_bits],
            gene_a[course_bits:slot_bits],
        )
    elif c == 3:
        gene_a[slot_bits:], gene_b[slot_bits:] = gene_b[slot_bits:], gene_a[
            slot_bits:]

    return gene_a, gene_b


def multi_point_crossover(gene_a, gene_b, points):
    # We use the single point crossover, multiple times
    for _ in range(points):
        gene_a, gene_b = single_point_crossover(gene_a, gene_b)

    return gene_a, gene_b


def mutation(gene):
    # global course_count
    # global total_slots

    c = choice([1, 2, 3])
    if c == 1:
        gene[0:course_bits] = encode_module()
    elif c == 2:
        gene[course_bits:slot_bits] = encode_slot()
    elif c == 3:
        gene[slot_bits:] = encode_class()

    return gene


def selection_pair(population):
    return choices(
        population=population,
        weights=[calculate_fitness(gene) for gene in population],
        k=2,
    )


def sort_population(population):
    return sorted(population, key=calculate_fitness, reverse=True)


def run_evolution(population_size, max_fitness, max_generations=100):
    population = generate_population(population_size)
    for _ in range(max_generations):
        population = sorted(population, key=calculate_fitness, reverse=True)

        if calculate_fitness(population[0]) >= max_fitness:
            return population[0]

        next_generation = population[0:2]

        for _ in range(len(population) // 2 - 1):
            parents = selection_pair(population)
            child_a, child_b = single_point_crossover(parents[0], parents[1])
            child_a, child_b = mutation(child_a), mutation(child_b)

            next_generation += [child_a, child_b]

        population = next_generation

    return 0


def fill_timetable(
    total_classes,
    no_courses,
    slots,
    total_days,
    population_size,
    max_fitness,
    max_generations,
    daily_repetition
):
    # initialize the genotype and a skeletal table
    initialize_genotype(no_courses, total_classes, slots, total_days, daily_repetition)
    generate_table_skeleton()

    # all_slots is the sum of total_slots in all the classes.
    all_slots = total_slots * class_count

    while all_slots > 0:

        gene = run_evolution(population_size, max_fitness, max_generations)
        if gene != 0:
            fit_slot(gene)
            all_slots -= 1

    return tables
