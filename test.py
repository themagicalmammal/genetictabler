from base import fill_timetable
from statistics import mean
import time
t= []
for _ in range(10):
    t0 = time.time()

    total_classes = 5
    no_courses = 8
    slots = 5
    total_days = 6
    population_size = 10
    max_fitness = 100
    max_generations = 20
    daily_repetition = 2

    table = fill_timetable(total_classes,
        no_courses,
        slots,
        total_days,
        population_size,
        max_fitness,
        max_generations,
        daily_repetition,)

    t1 = time.time()
    print(t1 -t0)
    t.append(t1 -t0)
for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")

print("average time taken = ", mean(t))