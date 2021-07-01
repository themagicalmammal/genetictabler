from random import randint

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


# The initialize_genotype() initializes and stores important data relevant to
# the the user defined timetable(s)'s design in global variables so that they
# can be easily used multiple times throughout the program as per requirement.
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

    total_slots = daily_slots * working_days
    course_bits = len(bin(course_count)) - 2
    slot_bits = len(bin(total_slots)) - 2
    class_bits = len(bin(course_count)) - 2
    """
    Course_bits, slot_bits and class bits are the lengths of binary string needed to
    represent them respectively. For example if course_count is 8, then the maximum course
    number will be 8 which requires 4 bits, hence course_bits will be equal to 4.
    """

    calc_course_quota()

    return [course_bits, slot_bits, daily_slots * working_days * class_count]


# Below function calculates an array course_quota which stores the maximum allowed
# occurrence of a a course/subject/module in a week/scheduled number of days.


def calc_course_quota():
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


# The encode_class() function generates random binary strings whose
# integer values represent a course/module/subject
def encode_class():
    class_code = bin(randint(1, class_count))[2:]

    # Left padding of random binary strings with 0 is done to ensure each string
    # is of same consistent length.
    class_code = "0" * (class_bits - len(class_code)) + class_code
    return class_code


# The encode_slot() function generates random binary strings whose integer
# values represent slot number for a day.
def encode_slot():
    slot_code = bin(randint(1, total_slots))[2:]
    slot_code = "0" * (slot_bits - len(slot_code)) + slot_code
    return slot_code


# The encode_slot() function generates random binary strings whose integer
# values represents a course/module/subject.
def encode_course():
    course_code = bin(randint(1, course_count))[2:]
    course_code = "0" * (course_bits - len(course_code)) + course_code
    return course_code


def generate_gene():
    course_code = encode_course()
    class_code = encode_class()
    slot_code = encode_slot()

    return course_code + slot_code + class_code


def extract_slot_day(gene):
    # The class_slot is a cumulative class slot number, we calculate day number
    # and slot number for that day for a gene using this class_slot number.

    class_slot = int(gene[course_bits:course_bits + slot_bits], 2)
    slot_no = class_slot % daily_slots
    day_no = class_slot // daily_slots

    if slot_no == 0:
        slot_no = daily_slots
        day_no -= 1
    class_no = int(gene[course_bits + slot_bits:], 2)

    return slot_no, day_no


""" 
The calculate_fitness() function determines fitness_score of a gene(course schedule) 
by checking few things:-
1)   If there already exists a course schedule for the same slot of the same or different class,
    fitness_score of the gene is decreased.
2)   If the same course is scheduled for any of the adjacent slots in the same class, 
    fitness_score of that gene is reduced.
3)   If a course is occurring more han a fixed number of times, the fitness_score of 
    that gene is reduced.
"""


def calculate_fitness(gene):
    fitness_score = 100
    course = int(gene[0:course_bits], 2)

    slot_no, day_no = extract_slot_day(gene)
    class_no = int(gene[course_bits + slot_bits:], 2)

    if tables[class_no - 1][day_no - 1][slot_no - 1] != 0:
        fitness_score *= 0.1

    for i in range(class_count):
        if tables[i][day_no - 1][slot_no - 1] == course:
            fitness_score *= 0.6

    if slot_no != 1 and tables[class_no - 1][day_no - 1][(slot_no - 1) -
                                                         1] == course:
        fitness_score *= 0.6

    if (slot_no != daily_slots
            and tables[class_no - 1][day_no - 1][(slot_no - 1) + 1] == course):
        fitness_score *= 0.6

    if course_quota[class_no - 1][(course - 1) - 1] == 0:
        fitness_score *= 0

    if tables[class_no - 1][day_no - 1].count(course) >= daily_rep:
        fitness_score *= 0.6

    return fitness_score


# This function returns an 3d array with 0 value for all positions.
# We use this array to store the schedules and the timetables.
def generate_table_skeleton():
    global tables

    for _ in range(class_count):
        class_table = []
        for _ in range(working_days):
            day = [0 for _ in range(daily_slots)]
            class_table.append(day)
        tables.append(class_table)
    return tables


# The fit_slot() function fills the tables array with fit course schedules that
# are returned by run_evolution().
def fit_slot(gene):
    global tables
    global course_quota

    course = int(gene[0:course_bits], 2)

    slot_no, day_no = extract_slot_day(gene)
    class_no = int(gene[course_bits + slot_bits:], 2)

    # Python list indexing starts from 0, hence we subtract 1 from class_no, day_no,
    # slot_no which are natural numbers.
    tables[class_no - 1][day_no - 1][slot_no - 1] = course
    course_quota[class_no - 1][course - 1] -= 1
