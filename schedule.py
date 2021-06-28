from random import randint

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
course_bits = 0
slot_bits = 0
class_bits = 0
tables = []
daily_rep = 2
total_fitness = 0


def initialize_genotype(
    no_courses,
    classes=4,
    slots=6,
    days=5,
    daily_repetition=2,
):
    global course_count
    global daily_slots
    global working_days
    global class_count
    global daily_rep
    global course_bits
    global total_slots
    global slot_bits
    global class_bits

    course_count = no_courses
    daily_slots = slots
    working_days = days
    class_count = classes
    daily_rep = daily_repetition

    course_bits = len(bin(course_count)) - 2
    total_slots = daily_slots * working_days
    slot_bits = len(bin(total_slots)) - 2
    class_bits = len(bin(course_count)) - 2

    initialize_gene()

    return [course_bits, slot_bits, daily_slots * working_days * class_count]


def initialize_gene():
    global course_quota

    q_max = total_slots // course_count
    if total_slots % course_count == 0:
        course_quota = [q_max] * course_count
    else:
        course_quota = [q_max + 1] * course_count

        extra_slots = (q_max + 1) * course_count - total_slots

        n = randint(1, course_count - extra_slots)
        for i in range(extra_slots):
            course_quota[n + i] -= 1

    course_quota = [course_quota for _ in range(class_count)]


def encode_class():
    class_code = bin(randint(1, class_count))[2:]
    class_code = "0" * (class_bits - len(class_code)) + class_code
    return class_code


def encode_slot():
    slot_code = bin(randint(1, total_slots))[2:]
    slot_code = "0" * (slot_bits - len(slot_code)) + slot_code
    return slot_code


def encode_module():
    module_code = bin(randint(1, course_count))[2:]
    module_code = "0" * (course_bits - len(module_code)) + module_code
    return module_code


def generate_gene():
    module_code = encode_module()
    class_code = encode_class()
    slot_code = encode_slot()

    # print(module_code, slot_code, class_code)
    return module_code + slot_code + class_code


def calculate_fitness(gene):
    """
    # START: Testing/ Debugging code
    if len(gene) != 11:
        print("ALERT : Variant gene detected , fitness cannot be identified, System failure Imminent !!.............")
        print(gene)
    # END Testing/ Debugging code
    """

    fitness = 100
    # print(gene)
    module = int(gene[0:course_bits], 2)
    class_slot = int(gene[course_bits:course_bits + slot_bits], 2)

    slot_no = class_slot % daily_slots
    day_no = class_slot // daily_slots

    if slot_no == 0:
        slot_no = daily_slots
        day_no -= 1

    class_no = int(gene[course_bits + slot_bits:], 2)

    # print(gene[0:course_bits], gene[course_bits:course_bits+slot_bits], gene[course_bits+slot_bits:])
    # print(module, class_slot, class_no)

    # Test: reduced all table indices by 1.
    if tables[class_no - 1][day_no - 1][slot_no - 1] != 0:
        fitness *= 0.1

    # Test: changed range(1, c.. +1) to range(c..)
    for i in range(class_count):
        if tables[i][day_no - 1][slot_no - 1] == module:
            fitness *= 0.6

    if slot_no != 1 and tables[class_no - 1][day_no - 1][(slot_no - 1) -
                                                         1] == module:
        fitness *= 0.6

    if (slot_no != daily_slots
            and tables[class_no - 1][day_no - 1][(slot_no - 1) + 1] == module):
        fitness *= 0.6

    if course_quota[class_no - 1][(module - 1) - 1] == 0:
        fitness *= 0

    if tables[class_no - 1][day_no - 1].count(module) >= daily_rep:
        fitness *= 0.6

    return fitness


def generate_table_skeleton():
    global tables

    for _ in range(class_count):
        class_table = []
        for _ in range(working_days):
            day = [0 for _ in range(daily_slots)]
            class_table.append(day)
        tables.append(class_table)

    return tables


def fit_slot(gene):
    global tables
    global course_quota
    global total_fitness

    total_fitness += calculate_fitness(gene)
    print(total_fitness)

    module = int(gene[0:course_bits], 2)
    class_slot = int(gene[course_bits:course_bits + slot_bits], 2)

    slot_no = class_slot % daily_slots
    day_no = class_slot // daily_slots

    if slot_no == 0:
        slot_no = daily_slots
        day_no -= 1

    class_no = int(gene[course_bits + slot_bits:], 2)

    tables[class_no - 1][day_no - 1][slot_no - 1] = module
    course_quota[class_no - 1][module - 1] -= 1
