# GeneticTabler
Time Table scheduling using genetic algorithm.

Developed by [Dipan Nanda](https://github.com/themagicalmammal) and [Ashish Shah](https://github.com/capriciousBoson) (c) 2021

## Example of Usage

```python
from genetictabler import GenerateTimeTable

total_classes = 6
no_courses = 6
slots = 6
total_days = 7
daily_repetition = 3

"""
Variable Definitions:

:param total_classes: It is the count of total number of timetables you want. 
                      Suppose If you 4 batches/student groups for CS freshmen
                      all studying the same courses/modules/subjects you can 
                      generate 4 different yet coherent yet timetables without 
                      having any clashes.

:param no_courses: It is the count of total number of courses/modules/subjects 
                   that a class or classes are going to be taught. For example 
                   if a class is going to be taught only maths, physics, 
                   chemistry and CS then total count will be 4.

:param slots: It is the count of total lectures that are to be scheduled each 
              day. 

:param total_days: It is the count of total number of days for which you want 
                   to schedule the timetable. For example a weekly timetable 
                   will have total 5/6 days. A monthly schedule can be of 25 
                   days.

:param daily_repetition: It is the maximum allowed number of times a 
                         course/subject/module can have lectures per day. It 
                         is used when the slots count is more than no_courses.
                         
Note:- The table returned by the above function call is a 3-dimensional 
list/array. Which is a list of timetables for each class which in itself are 
2d arrays.
"""

table = GenerateTimeTable(total_classes, no_courses, slots, total_days, daily_repetition)
for single_table in table.run():
    for days in single_table:
        print(days)
    print("-----------------------------------")


```

## Changelog
Go [here](CHANGELOG.md) to checkout the complete changelog.

## License
#### This is under GNU GPL v3.0 License
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
