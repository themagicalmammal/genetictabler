from random import choice, choices

from genetictabler.timetable import *


def generate_population(size):
    # our population will be a list of genes
    initialize_gene()
    return [generate_gene() for _ in range(size)]


def single_point_crossover(gene_a, gene_b):
    c = choice([1, 2, 3])

    if c == 1:
        gene_c = gene_b[0:course_bits] + gene_a[course_bits:]
        gene_d = gene_a[0:course_bits] + gene_b[course_bits:]

    elif c == 2:
        gene_c = (gene_a[:course_bits] +
                  gene_b[course_bits:course_bits + slot_bits] +
                  gene_a[course_bits + slot_bits:])
        gene_d = (gene_b[:course_bits] +
                  gene_a[course_bits:course_bits + slot_bits] +
                  gene_b[course_bits + slot_bits:])

    else:
        gene_c = gene_a[:course_bits + slot_bits] + gene_b[course_bits +
                                                           slot_bits:]
        gene_d = gene_b[:course_bits + slot_bits] + gene_a[course_bits +
                                                           slot_bits:]

    return [gene_c, gene_d]


def multi_point_crossover(gene_a, gene_b, points):
    # We use the single point crossover, multiple times
    for _ in range(points):
        gene_a, gene_b = single_point_crossover(gene_a, gene_b)

    return gene_a, gene_b


def mutation(gene, course_bit_length, slot_bit_length):
    c = choice([1, 2, 3])
    if c == 1:
        c1 = encode_course()
        mutated_gene = c1 + gene[course_bit_length:]

    elif c == 2:
        d = encode_slot()
        mutated_gene = (gene[:course_bit_length] + d +
                        gene[course_bit_length + slot_bit_length:])
    else:
        e = encode_class()
        mutated_gene = gene[:course_bit_length + slot_bit_length] + e

    return mutated_gene


def selection_pair(population):
    return choices(
        population=population,
        weights=[calculate_fitness(gene) for gene in population],
        k=2,
    )


def sort_population(population):
    return sorted(population, key=calculate_fitness, reverse=True)


def run_evolution(
        course_bit_length,
        slot_bit_length,
        population_size,
        max_fitness,
        max_generations,
):
    population = generate_population(population_size)
    for _ in range(max_generations):
        population = sorted(population, key=calculate_fitness, reverse=True)

        if calculate_fitness(population[0]) >= max_fitness:
            return population[0]

        next_generation = population[0:2]

        for _ in range(len(population) // 2 - 1):
            parents = selection_pair(population)
            child_a = single_point_crossover(parents[0], parents[1])[0]
            child_b = single_point_crossover(parents[0], parents[1])[1]

            child_a_ = mutation(child_a, course_bit_length, slot_bit_length)
            child_b_ = mutation(child_b, course_bit_length, slot_bit_length)

            next_generation += [child_a_, child_b_]

        population = next_generation

    return 0

def generate_timetable(
        total_classes,
        no_courses,
        slots,
        total_days,
        daily_repetition,
        population_size=10,
        max_fitness=100,
        max_generations=25,
):

    course_bit_length, slot_bit_length, all_slots = initialize_genotype(
        no_courses, total_classes, slots, total_days, daily_repetition)
    generate_table_skeleton()
    while all_slots > 0:

        gene = run_evolution(
            course_bit_length,
            slot_bit_length,
            population_size,
            max_fitness,
            max_generations,
        )
        if gene != 0:
            fit_slot(gene)
            all_slots -= 1

    return tables
