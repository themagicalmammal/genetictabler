import time

from base import fill_timetable

t0 = time.time()

total_classes = 5
no_courses = 8
slots = 5
total_days = 6
population_size = 10
max_fitness = 100
max_generations = 20
daily_repetition = 2

table = fill_timetable(
    total_classes,
    no_courses,
    slots,
    total_days,
    population_size,
    max_fitness,
    max_generations,
    daily_repetition,
)

t1 = time.time()
for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")

print("time taken = ", t1 - t0)
