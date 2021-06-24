#!/usr/bin/env python
# coding: utf-8

import random

# The generate_courses() generates random binary strings representing different
# courses based on the total number of courses specified.
# IF total courses are 8 then it will generate 4 bit numbers. If 17 courses then it generates
# 5 bit numbers but none of them will have value more than 17 or less than 1.

course_count = 0
daily_slots = 0
working_days = 0


def initialize_genotype(no_courses, slots=6, days=5):
    global course_count
    global daily_slots
    global working_days

    course_count = no_courses
    daily_slots = slots
    working_days = days


def generate_courses():
    global course_count
    bit_length = len(bin(course_count)) - 2

    n = random.randint(1, course_count)
    course = bin(n)[2:]
    course = "0" * (bit_length - len(course)) + course

    return course


# A function that generates the genome of specified length using generate courses function.
def generate_genome():
    global daily_slots
    global working_days

    total_slots = daily_slots * working_days
    q_max = total_slots // course_count
    if total_slots % course_count == 0:
        course_quota = [q_max] * course_count
    else:
        course_qouta =[q_max + 1] * course_count

        extra_slots = total_slots - (q_max * course_count)



    for _ in range():

    genome_length = daily_slots * working_days
    return [generate_courses() for i in range(genome_length)]


def calculate_fitness(genome):
    fitness = 0

    # First we create a dictionary (courses) of subjects to store counting of how many times
    # a course appears in a genome.
    courses = {}
    for i in range(1, course_count + 1):
        bit_length = len(bin(course_count)) - 2
        c = bin(i)[2:]
        c = "0" * (bit_length - len(c)) + c
        courses[c] = 0

    # We count the occurrences of each subject and update it in the dictionary.
    for j in genome:
        courses[j] += 1

    # Logic to decrease fitness if a course appears too many times.
    if max(courses.values()) > len(genome) // course_count + 1:
        fitness -= 2
    if min(courses.values()) < 1:
        fitness -= 4
    if max(courses.values()) == len(genome) // course_count + 1:
        fitness += 6

    return fitness


# x = generate_genome(5,2,17),
# print(x)
