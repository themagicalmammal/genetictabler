import random

# The generate_courses() generates random binary strings representing different
# courses based on the total number of courses specified.
# IF total courses are 8 then it will generate 4 bit numbers. If 17 courses then it generates
# 5 bit numbers but none of them will have value more than 17 or less than 1.

course_count = 0
daily_slots = 0
working_days = 0
total_slots = 0
course_quota = []


def initialize_genotype(no_courses, slots=6, days=5):
    global course_count
    global daily_slots
    global working_days

    course_count = no_courses
    daily_slots = slots
    working_days = days


def initialize_gene():
    global daily_slots
    global working_days
    global total_slots
    global course_quota

    total_slots = daily_slots * working_days
    # First we create a dictionary (courses) of subjects to store counting of how many times
    # a course appears in a gene.
    q_max = total_slots // course_count
    if total_slots % course_count == 0:
        course_quota = [q_max] * course_count
    else:
        course_quota = [q_max + 1] * course_count

        extra_slots = (q_max + 1) * course_count - total_slots

        n = random.randint(1, course_count - extra_slots)
        for i in range(extra_slots):
            course_quota[n + i] -= 1

    course_bit_len = len(bin(course_count)) - 2
    slot_bit_len = len(bin(total_slots)) - 2
    gene_length = slot_bit_len + course_bit_len

    return gene_length


def generate_gene(gene_length):
    gene = ""
    for _ in range(gene_length):
        gene += random.choice(["0", "1"])

    return gene


def calculate_fitness(gene):
    fitness = 100

    return fitness
