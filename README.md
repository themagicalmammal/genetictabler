# GeneticTabler
Time Table scheduling using genetic algorithm.

Developed by [Dipan Nanda](https://github.com/themagicalmammal) and [Ashish Shah](https://github.com/ash-R2D2) (c) 2021

## Example of Usage

```python
from genetictabler.genetic import fill_timetable

total_classes = 4
no_courses = 8
slots = 6
total_days = 7
daily_repetition = 3

table = fill_timetable(
    total_classes,
    no_courses,
    slots,
    total_days,
    daily_repetition,
)

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
