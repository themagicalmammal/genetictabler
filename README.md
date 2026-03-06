# 🧬 Genetic Algorithm Timetable Generator

A Python engine that builds conflict-free school and university timetables using an evolutionary algorithm. Drop in your number of classes, subjects, periods, and teachers — the GA handles the rest.

---

## Table of Contents

- [🧬 Genetic Algorithm Timetable Generator](#-genetic-algorithm-timetable-generator)
  - [Table of Contents](#table-of-contents)
  - [How it works](#how-it-works)
  - [Requirements](#requirements)
  - [Quick start](#quick-start)
  - [Configuration reference](#configuration-reference)
  - [Constraint system](#constraint-system)
  - [API reference](#api-reference)
    - [`GenerateTimeTable`](#generatetimetable)
      - [Core methods](#core-methods)
      - [Query helpers](#query-helpers)
      - [Export methods](#export-methods)
      - [Alternative constructor](#alternative-constructor)
  - [Export formats](#export-formats)
    - [JSON](#json)
    - [CSV](#csv)
    - [HTML](#html)
  - [Running the tests](#running-the-tests)
  - [Project structure](#project-structure)
  - [Algorithm deep-dive](#algorithm-deep-dive)
    - [Gene encoding](#gene-encoding)
    - [Selection](#selection)
    - [Crossover](#crossover)
    - [Mutation](#mutation)
    - [Adaptive mutation](#adaptive-mutation)
    - [Fitness caching](#fitness-caching)
    - [Elitism](#elitism)
  - [Performance notes](#performance-notes)

---

## How it works

Each possible timetable entry — _"course X is taught to class Y in slot Z"_ — is encoded as a short binary string called a **gene**:

```
gene = <course_bits> + <slot_bits> + <class_bits>
       "010"         + "00101"     + "011"
        course 2       slot 5        class 3
```

The algorithm fills one timetable cell at a time:

1. Spawn a random **population** of candidate genes for the current cell.
2. Score every gene with the **fitness function** (100 = perfect, penalties for clashes).
3. The fittest genes survive, **crossover** to produce children, some children **mutate**.
4. Repeat until a gene scores 100 or `max_generations` is exhausted.
5. Commit the best gene to the timetable and move to the next cell.

---

## Requirements

- Python 3.9+
- No mandatory third-party packages — the standard library is all you need.
- `rich` is optional. If installed it enables prettier terminal output:

```bash
pip install rich        # optional
```

---

## Quick start

```python
from timetable_generator import GenerateTimeTable

# Defaults: 6 classes, 4 courses, 6 periods/day, 5-day week
scheduler = GenerateTimeTable()
timetable = scheduler.run()

# timetable[class_idx][day_idx][slot_idx] = course_number (1-based)
print(timetable[0])   # Class 1's full week
```

**Realistic school example with named labels:**

```python
scheduler = GenerateTimeTable(
    classes  = 4,
    courses  = 6,
    slots    = 7,        # 7 periods per day
    days     = 5,
    repeat   = 2,        # each course may appear at most twice per day
    teachers = [2, 2, 1, 1, 1, 2],   # per-subject teacher counts
    seed     = 42,       # reproducible output
    course_names = ["Maths", "English", "Science", "History", "PE", "Art"],
    class_names  = ["Year 7A", "Year 7B", "Year 8A", "Year 8B"],
    day_names    = ["Mon", "Tue", "Wed", "Thu", "Fri"],
)

scheduler.run()
scheduler.pretty_print()       # grid view in the terminal
scheduler.export_html("timetable.html")   # colour-coded HTML
scheduler.print_analytics()    # runtime, violations, course frequency
```

**Using a config dataclass** (handy when loading settings from files or CLI parsers):

```python
from timetable_generator import GenerateTimeTable, TimetableConfig

cfg = TimetableConfig(classes=3, courses=5, slots=6, days=5, seed=7)
scheduler = GenerateTimeTable.from_config(cfg, course_names=["Maths", ...])
scheduler.run()
```

---

## Configuration reference

All parameters can be passed to `GenerateTimeTable(...)` directly or via `TimetableConfig`.

| Parameter         | Type                 | Default | Description                                                                                                                     |
| ----------------- | -------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `classes`         | `int`                | `6`     | Number of distinct class groups                                                                                                 |
| `courses`         | `int`                | `4`     | Number of distinct subjects                                                                                                     |
| `slots`           | `int`                | `6`     | Time-slots (periods) per day                                                                                                    |
| `days`            | `int`                | `5`     | School days per week                                                                                                            |
| `repeat`          | `int` or `list[int]` | `2`     | Max times a course may appear on a single day. Pass a list of length `courses` for per-course limits.                           |
| `teachers`        | `int` or `list[int]` | `1`     | How many teachers cover each course simultaneously (caps how many classes can share a slot). Pass a list for per-course values. |
| `population_size` | `int`                | `60`    | GA population size per generation                                                                                               |
| `max_fitness`     | `float`              | `100.0` | Early-stop threshold — a gene reaching this score is immediately committed                                                      |
| `max_generations` | `int`                | `80`    | Hard cap on GA iterations per cell                                                                                              |
| `elite_ratio`     | `float`              | `0.10`  | Fraction of top genes carried unchanged into the next generation (elitism)                                                      |
| `mutation_rate`   | `float`              | `0.25`  | Probability that a child gene is mutated                                                                                        |
| `adaptive`        | `bool`               | `True`  | When `True`, mutation rate automatically triples if the GA stalls for 5+ generations                                            |
| `seed`            | `int \| None`        | `None`  | RNG seed for reproducible output                                                                                                |
| `course_names`    | `list[str]`          | auto    | Human-readable course labels                                                                                                    |
| `class_names`     | `list[str]`          | auto    | Human-readable class labels                                                                                                     |
| `day_names`       | `list[str]`          | auto    | Human-readable day labels                                                                                                       |

---

## Constraint system

The fitness function starts at 100 and applies multiplicative penalties for each violated rule:

| Violation                                                         | Penalty | Type |
| ----------------------------------------------------------------- | ------- | ---- |
| Slot already occupied in this class                               | ×0.01   | Hard |
| Weekly course quota exhausted                                     | ×0.01   | Hard |
| Course appears ≥ 2 times today                                    | ×0.01   | Hard |
| Teacher capacity saturated for this slot                          | ×0.01   | Hard |
| Same course in the same slot across another class (teacher clash) | ×0.60   | Soft |
| Course is adjacent to itself in the same class/day                | ×0.60   | Soft |
| Daily repeat cap exceeded                                         | ×0.50   | Soft |

Hard penalties effectively zero out a gene's score (×0.01 = 1 %), making it extremely unlikely to be selected. Soft penalties stack gracefully — a gene with two soft violations scores 36 (0.6²×100).

---

## API reference

### `GenerateTimeTable`

#### Core methods

```python
scheduler.run() -> list[list[list[int]]]
```

Execute the full scheduling algorithm. Returns a 3-D list `tables[class][day][slot]` containing 1-based course numbers (0 = unfilled).

```python
scheduler.pretty_print(class_idx=None)
```

Print a grid view to the terminal. Pass a 0-based index to print a single class.

```python
scheduler.validate() -> dict
```

Scan the completed timetable for violations. Returns:

```python
{
    "empty_cells":      int,
    "teacher_clashes":  int,
    "back_to_back":     int,
    "total_violations": int,
}
```

```python
scheduler.analytics() -> dict
```

Return a performance summary including runtime, genes evaluated, cache hit ratio, per-course frequency, and validation results.

```python
scheduler.reset()
```

Wipe the timetable, quotas, cache, and telemetry so the scheduler can be run again.

#### Query helpers

```python
scheduler.get_class_timetable("Year 7A") -> list[list[int]] | None
```

Retrieve a single class's timetable as a 2-D list `[day][slot]`.

```python
scheduler.find_course_slots("Mathematics", class_name=None) -> list[tuple]
```

Find all scheduled occurrences of a subject. Returns a list of `(class_name, day_name, "Slot N")` tuples. Filter to one class with `class_name`.

```python
scheduler.get_teacher_schedule("Mathematics") -> dict
```

Build a teacher-eye view: `{"Mon Slot 2": ["Year 7A", "Year 8B"], ...}`.

#### Export methods

```python
scheduler.export_json("timetable.json")
scheduler.export_csv("timetable.csv")
scheduler.export_html("timetable.html")
```

See [Export formats](#export-formats) for output structure details.

#### Alternative constructor

```python
GenerateTimeTable.from_config(config: TimetableConfig, **kwargs)
```

---

## Export formats

### JSON

Nested dictionary keyed by class name → day name → list of course names per slot:

```json
{
  "Year 7A": {
    "Mon": ["Maths", "English", "FREE", "Science", "PE", "Art"],
    "Tue": [...]
  }
}
```

### CSV

Flat table with four columns, one row per cell:

```
Class,Day,Slot,Course
Year 7A,Mon,Slot 1,Maths
Year 7A,Mon,Slot 2,English
...
```

### HTML

A styled webpage with one colour-coded table per class. Each course gets a consistent pastel background colour across all tables for easy visual scanning. Open directly in any browser.

---

## Running the tests

```bash
python -m pytest test_timetable_generator.py -v
# or without pytest:
python test_timetable_generator.py
```

The suite contains **123 tests** across 16 test classes covering unit, integration, edge-case, property, and regression scenarios.

| Test class             | What's covered                                                                               |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| `TestInitialisation`   | Constructor, `from_config`, bit-width computation, invalid-input errors                      |
| `TestCourseQuota`      | Quota sum invariant, fair distribution, class independence                                   |
| `TestEncoding`         | `_to_binary`, all encode functions, gene length, binary-only output, decode roundtrip        |
| `TestFitness`          | Score range, every penalty type, cache hit/miss, `invalidate_cache`                          |
| `TestGeneticOperators` | Single/multi/uniform crossover, mutation, smart mutation, tournament & roulette selection    |
| `TestTableAndFitSlot`  | Skeleton shape, all-zeros init, `fit_slot` writes/decrements/clears/counts                   |
| `TestEvolutionLoop`    | Return type, gene length, max_fitness early-stop, generation log                             |
| `TestFullRun`          | Output dimensions, valid course values, slots-filled counter, per-course lists, edge configs |
| `TestValidation`       | Key presence, sum invariant, injected back-to-back and teacher clash detection               |
| `TestAnalytics`        | All keys present, cache ratio bounds, frequency total                                        |
| `TestExport`           | File creation, JSON structure, CSV header/row count, HTML content                            |
| `TestQueryHelpers`     | Class lookup, course slot search with filter, teacher schedule                               |
| `TestReset`            | Tables/cache/counters/log cleared, successful re-run                                         |
| `TestReproducibility`  | Same seed → same output, different seeds → different output                                  |
| `TestInvariants`       | Gene length for any config, quota monotonicity, crossover length stability                   |
| `TestEdgeCases`        | 1×1×1 grid, more courses than slots, excess teachers, degenerate populations                 |

---

## Project structure

```
timetable_generator.py     # Main engine — all classes and examples
test_timetable_generator.py  # 123-test suite
README.md                  # This file
```

`timetable_generator.py` also contains six runnable examples at the bottom, executed when the file is run directly:

```bash
python timetable_generator.py
```

| Example                       | What it demonstrates                                                       |
| ----------------------------- | -------------------------------------------------------------------------- |
| `example_minimal`             | One-liner default run                                                      |
| `example_named_courses`       | Custom labels, `find_course_slots`, `get_teacher_schedule`                 |
| `example_large_school`        | 10 classes, 8 subjects, per-course teacher/repeat lists, all three exports |
| `example_config_dataclass`    | `TimetableConfig` + `from_config` constructor                              |
| `example_reproducibility`     | Seed-based determinism check                                               |
| `example_analytics_deep_dive` | Generation-by-generation convergence data                                  |

---

## Algorithm deep-dive

### Gene encoding

Binary encoding allows the GA to operate on simple strings rather than structured objects. Bit-widths are computed automatically from the input parameters:

```
course_bits = ⌈log₂(courses + 1)⌉
slot_bits   = ⌈log₂(slots × days + 1)⌉
class_bits  = ⌈log₂(classes + 1)⌉
```

A gene for 4 courses / 30 total slots / 6 classes would be `3 + 5 + 3 = 11 bits`.

### Selection

Two strategies are mixed per generation to balance exploitation and diversity:

- **Roulette-wheel selection** — probability proportional to fitness; preserves diversity.
- **Tournament selection** — pick the best of `k` random contestants; computationally cheap and pressure-tunable.

### Crossover

Three operators are available, chosen probabilistically each generation:

- **Single-point (segment) crossover** — swap one of the three logical segments (course, slot, or class) between two parents. Semantically meaningful — always exchanges whole concepts.
- **Multi-point crossover** — apply segment crossover `n` times in sequence.
- **Uniform crossover** — swap each bit independently with 50 % probability. Higher diversity, used 15 % of the time as a diversity injection.

### Mutation

- **Random mutation** — replace one randomly chosen segment with a fresh random encoding.
- **Smart mutation** — trial `k` random mutations and keep the one with the highest fitness. Used in the second half of evolution when random drift is wasteful.

### Adaptive mutation

If best fitness does not improve by more than 0.001 for five consecutive generations, the mutation rate is temporarily tripled (capped at 0.95). This blasts the population out of local optima. The rate resets to its original value as soon as improvement resumes.

### Fitness caching

`calculate_fitness` memoises results in a plain Python `dict` keyed by gene string. Typical runs achieve cache hit ratios above 97 %, reducing redundant evaluation by a factor of ~30–50×. The cache is invalidated whenever a gene is committed to the timetable, since the scoring environment changes.

### Elitism

The top `elite_ratio` fraction (default 10 %) of each generation is copied unchanged into the next generation, guaranteeing the best-found solution is never lost to random genetic drift.

---

## Performance notes

- **Tiny config** (2 classes, 3 courses, 3 slots, 3 days): ~0.02 s
- **Default config** (6 classes, 4 courses, 6 slots, 5 days): ~1–3 s
- **Large config** (10 classes, 8 courses, 8 slots, 5 days): ~10–30 s

Runtime scales roughly with `classes × days × slots × population_size × max_generations`. The fastest levers to pull if scheduling is too slow:

1. Reduce `max_generations` (e.g. 40 → 20). Quality degrades slightly.
2. Reduce `population_size` (e.g. 60 → 30). Same trade-off.
3. Raise `max_fitness` threshold slightly below 100 to accept near-perfect genes earlier.
4. Increase `elite_ratio` to preserve more good solutions between generations.
