import time
from base import fill_timetable

total_classes = 5
no_courses = 70
slots = 80
total_days = 150
population_size = 10
max_fitness = 100  # fixed
max_generations = 25
daily_repetition = 3
t0 = time.time()
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
print((t1 - t0) * 100)


for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")

