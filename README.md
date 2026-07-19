# 🧬 genetictabler

> Generate conflict-free university and college timetables using genetic algorithms.
> Available as a **Python library** (`genetictabler`), a **TypeScript/React npm package** (sibling repo [`genetictabler-js`](https://github.com/themagicalmammal/genetictabler-js)), and a **Streamlit GUI**.

|                   |                                                                                                                                                                                                                                                                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Package**       | [![PyPI version](https://img.shields.io/pypi/v/genetictabler.svg)](https://pypi.org/project/genetictabler/) `@genetictabler/core`                                                                                                                                                                                                                                                                 |
| **Quality**       | [![Tests & Lint](https://github.com/themagicalmammal/genetictabler/actions/workflows/tests.yml/badge.svg)](https://github.com/themagicalmammal/genetictabler/actions/workflows/tests.yml) [![Type safety](https://img.shields.io/badge/types-mypy%20strict-blue.svg)](https://mypy.readthedocs.io/) [![Lint](https://img.shields.io/badge/lint-ruff-lightgray.svg)](https://docs.astral.sh/ruff/) |
| **Compatibility** | Python ≥ 3.12                                                                                                                                                                                                                                                                                                                                                                                     |
| **License**       | [![BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)                                                                                                                                                                                                                                                                                                          |

---

## Table of Contents

- [🧬 genetictabler](#-genetictabler)
  - [Table of Contents](#table-of-contents)
  - [Quick start](#quick-start)
    - [Python](#python)
    - [TypeScript](#typescript)
    - [Streamlit GUI](#streamlit-gui)
  - [Algorithm overview](#algorithm-overview)
  - [Configuration reference](#configuration-reference)
    - [Teacher system](#teacher-system)
      - [Simple mode (deprecated)](#simple-mode-deprecated)
      - [Explicit mode (recommended)](#explicit-mode-recommended)
      - [Real-world example](#real-world-example)
  - [Constraint system](#constraint-system)
  - [Python API reference](#python-api-reference)
    - [GenerateTimeTable](#generatetimetable)
      - [Core methods](#core-methods)
      - [Query helpers](#query-helpers)
      - [Export methods](#export-methods)
      - [Alternative constructor](#alternative-constructor)
    - [TeacherConfig](#teacherconfig)
    - [TimetableConfig](#timetableconfig)
  - [TypeScript API reference](#typescript-api-reference)
    - [TimetableEngine](#timetableengine)
    - [GeneEncoder](#geneencoder)
    - [FitnessEvaluator](#fitnessevaluator)
    - [GeneticOperators](#geneticoperators)
    - [React component](#react-component)
  - [Project structure](#project-structure)
  - [Testing](#testing)
    - [Python Tests](#python-tests)
  - [Contributing](#contributing)
  - [Contributors](#contributors)
  - [License](#license)

---

## Quick start

### Python

```bash
pip install genetictabler
```

```python
from genetictabler import GenerateTimeTable

scheduler = GenerateTimeTable(
    classes=4,
    courses=6,
    slots=6,
    days=5,
    seed=42,
    course_names=["Machine Learning", "Digital Design", "Data Structures",
                  "Linear Algebra", "Organic Chemistry", "World History",
                  "English Literature", "Computer Networks"],
    class_names=["CS 101", "CS 102", "CS 201", "CS 202",
                 "Math 101", "Physics 101"],
)
scheduler.run()
scheduler.pretty_print()
scheduler.export_html("timetable.html")
```

### TypeScript

```bash
npm install @genetictabler/core
```

```typescript
import { TimetableEngine } from "@genetictabler/core";

const engine = new TimetableEngine({
  classes: 4,
  courses: 6,
  slots: 6,
  days: 5,
  seed: 42,
  courseNames: ["Machine Learning", "Digital Design", "Data Structures",
                "Linear Algebra", "Organic Chemistry", "World History",
                "English Literature", "Computer Networks"],
  classNames: ["CS 101", "CS 102", "CS 201", "CS 202",
               "Math 101", "Physics 101"],
});

const timetable = engine.run();
const json = engine.toJSON();
const analytics = engine.analytics();
```

### Streamlit GUI

```bash
pip install genetictabler streamlit
streamlit run genetictabler_gui.py
```

A full-featured web app with parameter sliders, dark/light mode, colour-coded timetable display, analytics charts, and export buttons.

---

## Algorithm overview

The generator uses a **genetic algorithm** (GA) to fill each timetable cell one at a time:

1. **Gene encoding** — Each possible assignment ("course X in slot Y for class Z") is a binary string:

   ```md
   gene = <course_bits> + <slot_bits> + <class_bits>
   "010" + "00101" + "011"
   course 2 slot 5 class 3
   ```

2. **Population** — Spawn ~60 random candidate genes for the current cell.
3. **Fitness scoring** — Each gene is scored 0–100. The base score is 100; multiplicative penalties are applied for every constraint violation (clashes, quota exhaustion, back-to-back courses).
4. **Evolution** — Fittest genes survive (elitism), crossover to produce children, and some children mutate. Adaptive mutation kicks in if progress stalls.
5. **Commit** — Once a gene reaches the fitness threshold (~100), it is committed to the timetable and the process repeats for the next empty cell.
6. **Repeat** until all cells are filled.

See [Python API reference](#python-api-reference) and [TypeScript API reference](#typescript-api-reference) for full method documentation.

---

## Configuration reference

All parameters below are accepted by both Python's `GenerateTimeTable` constructor and TypeScript's `TimetableEngine` constructor.

| Parameter         | Type                  | Default | Description                                                          |
| ----------------- | --------------------- | ------- | -------------------------------------------------------------------- |
| `classes`         | `int`                 | `6`     | Number of distinct class groups                                      |
| `courses`         | `int`                 | `4`     | Number of distinct subjects                                          |
| `slots`           | `int`                 | `6`     | Time-slots (periods) per day                                         |
| `days`            | `int`                 | `5`     | School days per week                                                 |
| `repeat`          | `int \| List[int]`    | `2`     | Max times a course per day. Scalar or per-course list.               |
| `teachers`        | `int \| List[int]`    | `1`     | **Deprecated** — use `teachers_config` instead.                      |
| `teachers_config` | `List[TeacherConfig]` | `[]`    | Per-teacher definitions with course assignments and quotas.          |
| `population_size` | `int`                 | `60`    | GA population size per generation                                    |
| `max_fitness`     | `float`               | `100.0` | Early-stop threshold — a gene reaching this is committed immediately |
| `max_generations` | `int`                 | `80`    | Hard cap on GA iterations per cell                                   |
| `elite_ratio`     | `float`               | `0.10`  | Fraction of top genes carried unchanged into the next generation     |
| `mutation_rate`   | `float`               | `0.25`  | Probability (0–1) that a child gene is mutated                       |
| `adaptive`        | `bool`                | `True`  | Mutation rate triples if no improvement for 5+ generations           |
| `seed`            | `int \| None`         | `None`  | RNG seed for reproducible output                                     |
| `course_names`    | `List[str]`           | auto    | Human-readable course labels                                         |
| `class_names`     | `List[str]`           | auto    | Human-readable class labels                                          |
| `day_names`       | `List[str]`           | auto    | Human-readable day labels                                            |

---

### Teacher system

The teacher system lets you model **individual teachers** who are assigned to specific courses,
with per-course and total weekly quotas. This prevents:

1. **Teacher double-booking** — the same teacher teaching two different courses at the same time
2. **Quota exhaustion** — a teacher being assigned more classes than they can handle

Use the simple `teachers` parameter for quick prototypes, or `teachers_config` for realistic
scheduling where specific teachers are attached to specific courses.

#### Simple mode (deprecated)

```python
scheduler = GenerateTimeTable(
    classes=4,
    courses=4,
    slots=6,
    days=5,
    teachers=2,  # 2 teachers can teach course 1 at the same time
)
```

This only controls how many classes can share a course in the same slot.
It does **not** track which teacher teaches what.

#### Explicit mode (recommended)

Define each teacher with the courses they teach and their weekly quotas:

```python
from genetictabler import GenerateTimeTable, TeacherConfig

teachers = [
    TeacherConfig(
        name="Ms. Smith",
        courses=[1, 4],           # Teaches Maths (1) and Art (4)
        course_quota={4: 2},      # Max 2 classes/week of Art
        total_quota=12,           # Max 12 classes/week total
    ),
    TeacherConfig(
        name="Mr. Jones",
        courses=[4],              # Teaches Art (4)
        course_quota={4: 3},      # Max 3 classes/week of Art
        total_quota=0,            # No total cap
    ),
]

scheduler = GenerateTimeTable(
    classes=4,
    courses=6,
    slots=6,
    days=5,
    teachers_config=teachers,
)
```

How it works:

1. **Course → teacher mapping**: Each course is assigned to the **first** teacher in the list who teaches it. If two teachers both list course 4, the first one gets it.

2. **Double-booking check**: If the teacher for course 4 is already teaching another course in the same (day, slot), genes proposing that assignment are scored ×0.01.

3. **Per-course quota**: If "Ms. Smith" already teaches 2 classes of Art this week, her quota for Art is full — genes assigning her more Art are penalised.

4. **Total weekly cap**: If "Ms. Smith" reaches 12 total classes across all her subjects, any additional assignment is blocked.

#### Real-world example

A school with 4 Art classes (Years 6–9), 2 Art teachers, and a rule that no Art class repeats in a day:

```python
from genetictabler import GenerateTimeTable, TeacherConfig, TimetableConfig

art_teachers = [
    TeacherConfig(
        name="Ms. Smith",
        courses=[4],            # Art is course 4
        course_quota={4: 2},    # Each teacher handles max 2 Art classes
        total_quota=10,         # Reasonable teaching load
    ),
    TeacherConfig(
        name="Mr. Jones",
        courses=[4],            # Art is course 4
        course_quota={4: 2},
        total_quota=10,
    ),
]

cfg = TimetableConfig(
    classes=4,           # Year 6A, 6B, 7A, 7B
    courses=6,           # Maths, English, Science, History, PE, Art
    slots=6,
    days=5,
    repeat=[2, 2, 2, 2, 2, 1],  # Art only once per day
    teachers_config=art_teachers,
    seed=42,
)

scheduler = GenerateTimeTable.from_config(cfg)
scheduler.run()
```

---

## Constraint system

The fitness function starts at **100** and applies multiplicative penalties for each violated rule:

| Violation                                                         | Penalty | Type |
| ----------------------------------------------------------------- | ------- | ---- |
| Slot already occupied in this class                               | ×0.01   | Hard |
| Weekly course quota exhausted                                     | ×0.01   | Hard |
| Course appears ≥ 2 times today                                    | ×0.01   | Hard |
| Teacher capacity saturated for this slot                          | ×0.01   | Hard |
| Same course in the same slot across another class (teacher clash) | ×0.60   | Soft |
| Course is adjacent to itself in the same class/day                | ×0.60   | Soft |
| Daily repeat cap exceeded                                         | ×0.50   | Soft |
| Teacher double-booking (different course same slot)               | ×0.01   | Hard |
| Teacher weekly quota exceeded                                     | ×0.01   | Hard |

**Hard penalties** effectively zero out a gene's score (×0.01 = 1 %), making it extremely unlikely to be selected. **Soft penalties** stack gracefully — a gene with two soft violations scores 36 (0.6² × 100).

---

## Python API reference

### GenerateTimeTable

#### Core methods

```python
scheduler.run() -> list[list[list[int]]]
```

Execute the full scheduling algorithm. Returns a 3-D list `tables[class_idx][day_idx][slot_idx]` containing 1-based course numbers (`0` = unfilled).

```python
scheduler.pretty_print(class_idx: int | None = None)
```

Print a grid view to the terminal. Pass a 0-based index to print a single class.

```python
scheduler.validate() -> dict
```

Scan the completed timetable for constraint violations. Returns:

```python
{
    "empty_cells":      0,
    "teacher_clashes":  0,
    "back_to_back":     0,
    "total_violations": 0,
}
```

```python
scheduler.analytics() -> dict
```

Return a performance summary:

```python
{
    "runtime_s":          2.34,
    "genes_evaluated":    14520,
    "cache_hit_ratio":    0.9712,
    "course_frequency":   {"Maths": 12, "English": 10, ...},
    "validation":         { ... },       # as returned by validate()
    "slots_filled":       120,
    "generation_log_tail": [ ... ],      # last 5 generation stats
}
```

```python
scheduler.reset()
```

Wipe the timetable, quotas, cache, and telemetry so the scheduler can be run again.

#### Query helpers

```python
scheduler.get_class_timetable(class_name: str) -> list[list[int]] | None
```

Retrieve a single class's timetable as a 2-D list `[day][slot] = course_number`.

```python
scheduler.find_course_slots(course_name: str, class_name: str | None = None) -> list[tuple[str, str, str]]
```

Find all scheduled occurrences of a subject. Returns `(class_name, day_name, "Slot N")` tuples. Filter to one class with `class_name`.

```python
scheduler.get_teacher_schedule(course_name: str) -> dict[str, list[str]]
```

Build a teacher-eye view: `{"Mon Slot 2": ["Year 7A", "Year 8B"], ...}`.

#### Export methods

```python
scheduler.export_json(filepath: str)
scheduler.export_csv(filepath: str)
scheduler.export_html(filepath: str)
```

Save the timetable to disk.

**JSON** — Nested dict keyed by class name → day name → list of course names per slot:

```json
{
  "Year 7A": {
    "Mon": ["Maths", "English", "FREE", "Science", "PE", "Art"],
    "Tue": ["Science", "Maths", "Art", "English", "FREE", "History"]
  }
}
```

**CSV** — Flat table with four columns:

```md
Class,Day,Slot,Course
Year 7A,Mon,Slot 1,Maths
Year 7A,Mon,Slot 2,English
...
```

**HTML** — A styled, colour-coded webpage with one table per class. Each course gets a consistent pastel background. Open in any browser.

#### Alternative constructor

```python
scheduler = GenerateTimeTable.from_config(
    config=TimetableConfig(classes=3, courses=5, slots=6, days=5, seed=7),
    course_names=["Maths", "English", "Science", "History", "PE"],
)
```

### TeacherConfig

Defines a teacher with their course assignments and weekly quotas:

```python
from genetictabler import TeacherConfig

tc = TeacherConfig(
    name="Ms. Smith",
    courses=[1, 4],           # Teaches Maths (1) and Art (4)
    course_quota={4: 2},      # Max 2 Art classes per week
    total_quota=12,           # Max 12 classes total per week (0 = unlimited)
)
```

| Attribute      | Type             | Default  | Description                                                  |
| -------------- | ---------------- | -------- | ------------------------------------------------------------ |
| `name`         | `str`            | required | Human-readable name (e.g. "Ms. Smith")                       |
| `courses`      | `List[int]`      | required | 1-based course indices they teach                            |
| `course_quota` | `Dict[int, int]` | `{}`     | Per-course weekly limit: `{course_id: max_classes}`          |
| `total_quota`  | `int`            | `0`      | Total classes per week across all subjects (`0` = unlimited) |

### TimetableConfig

A frozen dataclass collecting all scheduling parameters:

```python
from genetictabler import TimetableConfig

cfg = TimetableConfig(
    classes=4,
    courses=6,
    slots=7,
    days=5,
    repeat=2,
    teachers=[2, 2, 1, 1, 1, 2],
    seed=42,
    course_names=["Maths", "English", "Science", "History", "PE", "Art"],
)
```

---

## TypeScript API reference

### TimetableEngine

```typescript
import { TimetableEngine, type TimetableConfig } from '@genetictabler/core';

const engine = new TimetableEngine(config: TimetableConfig);
```

| Method               | Return             | Description                                                                                                        |
| -------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `engine.run()`       | `Timetable`        | Execute scheduling. `Timetable` is `number[][][]` (`[class][day][slot]`).                                          |
| `engine.validate()`  | `ValidationResult` | `{ empty_cells, teacher_clashes, back_to_back, total_violations }`                                                 |
| `engine.analytics()` | `AnalyticsResult`  | `{ runtime_s, genes_evaluated, cache_hit_ratio, course_frequency, validation, slots_filled, generation_log_tail }` |
| `engine.reset()`     | `void`             | Wipe the engine for a fresh run.                                                                                   |
| `engine.toJSON()`    | `string`           | JSON string export.                                                                                                |
| `engine.toCSV()`     | `string`           | CSV string export.                                                                                                 |
| `engine.toHTML()`    | `string`           | Colour-coded HTML string export.                                                                                   |

### GeneEncoder

Binary encoding and decoding:

```typescript
import { GeneEncoder } from "@genetictabler/core";

const encoder = new GeneEncoder({ courses: 6, slots: 6, days: 5, classes: 4 });
encoder.courseBits = 3;
encoder.slotBits = 5;
encoder.classBits = 3;

encoder.toBinary(5, 4); // "0101"
encoder.generateGene(); // "01000101011"
encoder.decodeGene(gene); // [2, 3, 2, 3] — [course, slot, day, class]
encoder.extractSlotDay(gene); // [3, 2] — [slot_within_day, day_number]
```

### FitnessEvaluator

Score genes from 0 to 100:

```typescript
import { FitnessEvaluator } from "@genetictabler/core";

const evaluator = new FitnessEvaluator(state, cache);
const score = evaluator.calculate(gene); // 0–100
evaluator.invalidate(); // clear cache after committing a gene
```

Properties: `cacheHits: number`, `cacheMisses: number`.

### GeneticOperators

Genetic algorithm operators:

```typescript
import { GeneticOperators } from "@genetictabler/core";

const ops = new GeneticOperators(evaluator, eliteRatio, mutationRate, adaptive);
ops.geneLength = 16;

const [child1, child2] = ops.singlePointCrossover(geneA, geneB);
const [c1, c2] = ops.uniformCrossover(geneA, geneB);
const mutant = ops.mutation(gene);
const smart = ops.smartMutation(gene);
const winner = ops.tournamentSelection(population, (tournamentSize = 3));
const pair = ops.selectionPair(sortedPopulation);
const pop = ops.generatePopulation(60);
const sorted = ops.sortPopulation(population);
```

### React component

```typescript
import { TimetableRenderer } from '@genetictabler/core/react';

<TimetableRenderer
  timetable={timetable}
  config={engine.config}
  analytics={analytics}
  darkMode={true}
  className="my-custom-class"
/>
```

Props:

| Prop           | Type                           | Default         | Description                                   |
| -------------- | ------------------------------ | --------------- | --------------------------------------------- |
| `timetable`    | `number[][][]`                 | required        | `[class][day][slot] = courseNumber (1-based)` |
| `config`       | `TimetableConfig`              | required        | Configuration for labels and dimensions       |
| `analytics`    | `AnalyticsResult \| undefined` | `undefined`     | Optional analytics panel                      |
| `darkMode`     | `boolean`                      | `false`         | Dark colour scheme                            |
| `courseColors` | `Record<number, string>`       | default palette | Custom per-course colours                     |
| `className`    | `string`                       | `""`            | CSS class on root element                     |

---

## Project structure

```md
genetictabler/ # Python package
├── **init**.py # Re-exports: GenerateTimeTable, TimetableConfig, TeacherConfig, GenerationStats
├── config.py # TimetableConfig and TeacherConfig dataclasses
├── types.py # Type aliases, GenerationStats, ValidationResult, etc.
├── encoding.py # GeneEncoder — binary encode/decode
├── fitness.py # FitnessEvaluator — constraint scoring
├── genetic.py # GeneticOperators — crossover, mutation, selection
├── engine.py # GenerateTimeTable — core GA engine
├── export.py # pretty_print, export_json/csv/html (pure functions)
├── queries.py # get_class_timetable, find_course_slots, get_teacher_schedule
├── validation.py # validate_timetable (pure function)
├── utils.py # calc_course_quota, make_table_skeleton, quota builders
└── py.typed # mypy type-checking marker

genetictabler_gui.py # Streamlit GUI application

See the sibling [`genetictabler-js`](https://github.com/themagicalmammal/genetictabler-js)
repository for the TypeScript/React package.
```

---

## Testing

The project maintains **123 Python tests** (TypeScript tests are maintained in the
sibling [`genetictabler-js`](https://github.com/themagicalmammal/genetictabler-js) repo).

### Python Tests

```bash
# Install dev dependencies
uv sync --extra dev
# or: pip install pytest pytest-cov ruff mypy

# Run all tests
python -m pytest tests.py -v

# Type check
mypy genetictabler/

# Lint
ruff check genetictabler/
```

| Test class             | What's covered                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| `TestInitialisation`   | Constructor, `from_config`, bit-width computation, invalid inputs                         |
| `TestCourseQuota`      | Quota sum invariant, fair distribution, class independence                                |
| `TestEncoding`         | Binary encoding, encode functions, gene length, decode roundtrip                          |
| `TestFitness`          | Score range, every penalty type, cache hit/miss, `invalidate_cache`                       |
| `TestGeneticOperators` | Single/multi/uniform crossover, mutation, smart mutation, tournament & roulette selection |
| `TestTableAndFitSlot`  | Skeleton shape, all-zeros init, `fit_slot` writes/decrements/clears                       |
| `TestEvolutionLoop`    | Return type, gene length, max_fitness early-stop, generation log                          |
| `TestFullRun`          | Output dimensions, valid course values, slots-filled counter                              |
| `TestValidation`       | Key presence, sum invariant, back-to-back and teacher clash detection                     |
| `TestAnalytics`        | All keys present, cache ratio bounds, frequency total                                     |
| `TestExport`           | File creation, JSON structure, CSV header/row count, HTML content                         |
| `TestQueryHelpers`     | Class lookup, course slot search, teacher schedule                                        |
| `TestReset`            | Tables/cache/counters/log cleared, successful re-run                                      |
| `TestReproducibility`  | Same seed → same output, different seeds → different output                               |
| `TestInvariants`       | Gene length for any config, quota monotonicity, crossover length stability                |
| `TestEdgeCases`        | 1×1×1 grid, more courses than slots, excess teachers, degenerate populations              |

---

## Contributing

Contributions are welcome! Please ensure:

1. **Python code is fully typed** — every parameter and return value annotated.
2. **Python passes lint and type checks:** `ruff check genetictabler/` and `mypy genetictabler/`.
3. **All tests pass:** `python -m pytest tests.py -v`.
4. **Follow the existing code style** — Google docstrings, 100-char line length.

TypeScript/React changes should be made in the sibling [`genetictabler-js`](https://github.com/themagicalmammal/genetictabler-js) repository.

---

## Contributors

- **[Dipan Nanda](https://github.com/themagicalmammal)** — author, maintainer
- **[Ashish Shah](https://github.com/capriciousBoson)** — major contributor

---

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for details.
