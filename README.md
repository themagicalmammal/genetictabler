# Genetic Scheduler
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://github.com/DevilDipan/timetable_geneticalgo/blob/master/LICENSE)
Time Table scheduing done using [mutation](https://en.wikipedia.org/wiki/Mutation_(genetic_algorithm)) and [crossover](https://en.wikipedia.org/wiki/Crossover_(genetic_algorithm)) in [genetic algorithms](https://en.wikipedia.org/wiki/Genetic_algorithm) using python.

## Logic
```atom
* SubjectCode, Time Day, Batch (Code not involving genetic algorithm gets some logic and code)
* Subject Code = { 000 Subject1 , .............. 110 Subject7} --- There is no 111
* Time Day = 30 total = ( 00000 Monday First lec. ,       11101 Friday Sixth lec. ) Day -> Mon to Fri , Lect -> One to Six. --- There is no 11111 or 11110
* The population cannot be changed
* There should be no 11111111 or 11111110
* If the chromosome generated is same as before the generation cannot be changed
* If the result you want is 01011101 then it would be a stored 101011101 where the first is protective so that the zero doesnt go away or the output is
* 1011101 which would result in bad computation
* uap for represenation of respective maximum can be 5
```

## Mechanism
The working structure of solving the problem is represented [here](https://github.com/DevilDipan/timetable_geneticalgo/blob/master/info.txt).
