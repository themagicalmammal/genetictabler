# GeneticTabler
Time Table scheduling using genetic algorithm.

Developed by [Dipan Nanda](https://github.com/themagicalmammal) and [Ashish Shah](https://github.com/ash-R2D2) (c) 2021

## Example of Usage

```python
from genetictabler import generate_timetable

total_classes = 4
no_courses = 8
slots = 6
total_days = 7
daily_repetition = 3


"""
Variable Definitions:

-total_classes: It is the count of total number of
                timetables you want. Suppose If you
		4 batches/student groups for CS freshmen
		all studying the same courses/modules/subjects
		you can generate 4 different yet coherent
		yet timetables without having any clashes.

-no_courses: 	It is the count of total number of 
		courses/modules/subjects that a class
		or classes are going to be taught. 
		For example if a class is going to be 
		taught only maths, physics, chemistry and CS
		then total count will be 4.

-slots:		it is the count of total lectures that are 
		to be scheduled each day. 

-total_days:	It is the count of total number of days for 
		which you want to schedule the timetable. 
		For example a weekly timetable will have total
		5/6 days. A monthly schedule can be of 25 days.

-daily_repitition:
		It is the maximum allowed number of times a 
		course/subject/module can have lectures per day.
		It is used when the slots count is more than 
		no_courses 
"""


table = generate_timetable(
    total_classes,
    no_courses,
    slots,
    total_days,
    daily_repetition,
)

# The table returned by the above function call is a 3-dimensional list/array
# It is a list of timetables for each class which in itself are 2d arrays.


# Loop to print all the timetables. 
for i in table:
    for j in i:
        print(j)
    print("-----------------------------------")
```

## Changelog
Go [here](https://github.com/themagicalmammal/genetictabler/blob/default/CHANGELOG.md) to checkout the complete changelog.

## License
#### This is under GNU GPL v3.0 License
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/themagicalmammal/genetictabler/blob/default/LICENSE)
