from base import *
from schedule import *

t = initialize_genotype(5, 4, 6, 5, 2)
# print(t)
table = fill_timetable(t[0], t[1], t[2], 4, 5, 6, 5, 20, 100, 50, 2)

for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")
