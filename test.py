import time

from base import fill_timetable

total_classes = 4
no_courses = 8
slots = 6
total_days = 7
daily_repetition = 3
t0 = time.time()
table = fill_timetable(
    total_classes,
    no_courses,
    slots,
    total_days,
    daily_repetition,
)
t1 = time.time()
print((t1 - t0) * 100)

'''
for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")
'''