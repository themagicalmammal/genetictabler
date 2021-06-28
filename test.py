from base import *
from schedule import *

table = fill_timetable(4, 5, 6, 5, 20, 100, 50, 2)

for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")
