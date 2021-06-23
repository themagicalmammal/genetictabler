#!/usr/bin/env python
# coding: utf-8


import random

# The generate_courses() generates random binary strings representing different
# courses based on the total number of courses specified.
# IF total courses are 8 then it will generate 4 bit numbers. If 17 courses then it generates 
# 5 bit numbers but none of them will have value more than 17 or less than 1.

course_count = 0


def generate_courses():
    global course_count
    bit_length = len(bin(course_count)) - 2

    n = random.randint(1, course_count)
    course = bin(n)[2:]
    course = "0" * (bit_length - len(course)) + course

    return course


# A function that generates the genome of specified length using generate courses function.
def generate_genome(genome_length, no_courses):
    global course_count
    course_count = no_courses
    return [generate_courses() for i in range(genome_length)]


def calculate_fitness(genome):

    fitness = 0

    # First we create a dictionary (courses) of subjects to store counting of how many times
    # a course appears in a genome.
    courses = {}
    for i in range(1, course_count+1):
        bit_length = len(bin(course_count)) -2
        c = bin(i)[2:]
        c = "0" * (bit_length - len(c)) + c
        courses[c] = 0

    # We count the occurrences of each subject and update it in the dictionary.
    for j in genome:
        courses[j] += 1

    # Logic to decrease fitness if a course appears too many times.
    if max(courses.values()) > (int(len(genome)/course_count) + 1):
        fitness -= 2
    if min(courses.values()) < 1:
        fitness -= 4
    if max(courses.values()) == int(len(genome) / course_count) + 1:
        fitness += 6

    return fitness

# x = generate_genome(5,2,17),
# print(x)
