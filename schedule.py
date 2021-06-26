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
class_count = 0


def initialize_genotype(
    classes,
    no_courses,
    slots=6,
    days=5,
):
    global course_count
    global daily_slots
    global working_days
    global class_count

    course_count = no_courses
    daily_slots = slots
    working_days = days
    class_count = classes


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


def encode_class():
    global class_count
    return bin(random.randint(1, class_count))[2:]


def encode_slot():
    global total_slots
    return bin(random.randint(1, total_slots))[2:]


def encode_module():
    global course_count
    return bin(random.randint(1, course_count))[2:]


def generate_gene():
    module_code = encode_module()
    class_code = encode_class()
    slot_code = encode_slot()

    return module_code + slot_code + class_code


def calculate_fitness(gene):
    fitness = 100

    return fitness


def generate_table_skeleton():

    global class_count
    global working_days
    global daily_slots

    tables = []
    for _ in range(class_count):
        class_table = []
        for _ in range(working_days):
            day = [0 for _ in range(daily_slots)]
            class_table.append(day)
        tables.append(class_table)

    return tables


def fit_slot(gene, table):
    course_bits = len(bin(course_count)) - 2
    slot_bits = len(bin(total_slots)) - 2

    module = gene[0:course_bits]
    class_slot = gene[course_bits:slot_bits]

    slot_no = int(class_slot, 2) % daily_slots
    day_no = int(class_slot, 2) // daily_slots

    if slot_no == 0:
        slot_no = daily_slots
        day_no -= 1

    class_no = gene[slot_bits:]

    table[class_no][day_no][slot_no] = int(module, 2)
