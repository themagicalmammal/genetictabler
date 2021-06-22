#!/usr/bin/env python
# coding: utf-8

import random
from TimeTable_Problem import *


def generate_population(size, genome_length):
    # our population will be a list of genomes.
    return [generate_genome(genome_length) for _ in range(size)]

def single_point_crossover(genome_a, genome_b):
    if len(genome_a) != len(genome_b):
        raise ValueError("Parent genomes must be of same length for crossover")
    
    length = len(genome_a)
    
    if length < 2:
        return genome_a, genome_b
    
    # Now we choose the point/location for single point crossover which will be a random index 
    # between 2nd element and the second last element.
    p = random.randint(1, length-1)
    
    genome_c = genome_a[0:p] + genome_b[p:]
    genome_d = genome_b[0:p] + genome_a[p:]
    
    return genome_c, genome_d

def mutation(genome, num=1, probability=0.5):
    for _ in range(num):
    
        # we choose a random position "p" in the genome which we will mutate.
        p = random.randrange(len(genome))

        x = random.uniform(0, 1)
        if x > probability:
            
            genome[p] = genome[p]
        else:
            genome[p] = generate_courses()
    return genome

def population_fitness(population, fitness_func):
    return sum([fitness_func(genome) for genome in population])


def selection_pair(population, fitness_func):
    return random.choices(population=population, weights=[fitness_func(gene) for gene in population], k=2)
    
def sort_population(population, fitness_func):
    return sorted(population, key=fitness_func, reverse=True)
   
    
def run_evolution(fitness_func, max_fitness, populate_func=generate_population, selection_func=selection_pair,
                  mate_func=single_point_crossover, mutate_func=mutation, max_generations=100):
    
    population = populate_func()
    for i in range(max_generations):
        population = sorted(population, key=lambda genome: fitness_func(genome), reverse=True)
        
        if fitness_func(population[0]) >= max_fitness:
            break
        
        next_generation = population[0:2]
        
        for j in range(int(len(population)/2)-1):
            parents = selection_func(population, fitness_func)
            child_a, child_b = mate_func(parents[0], parents[1])
            
            child_a = mutate_func(child_a)
            child_b = mutate_func(child_b)
            
            next_generation += [child_a, child_b]
            
        population = next_generation
        
    return population
