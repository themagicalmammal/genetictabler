"""genetictabler — Genetic Algorithm Timetable Generator.

Generate conflict-free school and university timetables using
evolutionary computation (genetic algorithms).
"""

from genetictabler.config import TeacherConfig, TimetableConfig
from genetictabler.engine import GenerateTimeTable
from genetictabler.types import GenerationStats

__all__ = ["GenerateTimeTable", "TeacherConfig", "TimetableConfig", "GenerationStats"]
__version__ = "3.0.0"
