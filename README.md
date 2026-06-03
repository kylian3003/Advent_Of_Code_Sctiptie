# Code Efficiency vs. Readability in Python: An Analysis of Advent of Code GitHub Repositories

Bachelor's thesis project — BSc Information Science, University of Groningen, 2026.

This repository contains the data pipeline used to collect, normalise, and analyse Python solutions from public Advent of Code (AoC) GitHub repositories. The pipeline extracts static complexity metrics and produces the datasets used for the statistical analysis conducted in R.

---

## Project structure

```
.
├── extract_solutions.py   # Walk repos, normalise structure, wrap flat scripts
├── extract_features.py    # Compute static complexity metrics per file
├── main.py                # Run feature extraction over the full corpus
├── measure_runtime.py     # Benchmark solution runtime (median of 3 runs)
└── requirements.txt
```

The LLM annotation script (Gemini 2.5 Flash Lite, zero-shot) and the R analysis scripts are not included in this repository.

---

## Pipeline overview

### 1. Extract solutions — `extract_solutions.py`

This script walks all AoC repository folders and copies Python solution files into a normalised corpus structure:

```
corpus/
└── username/
    └── year/
        └── dayNN/
            └── solution.py
```

The year and puzzle day are inferred from folder names and filenames using regex patterns. Non-solution files such as tests, utilities, and templates are skipped. Within each day folder, files are deduplicated both by content and by part (Part 1 / Part 2).

Flat scripts without any top-level functions are wrapped in a synthetic `main()` before being copied. This ensures that cyclomatic and cognitive complexity can be computed for the full corpus rather than only the files that were already structured as functions.

The script writes an `extraction_log.txt` and a `path_map.csv` to the corpus root. The path map is used by `measure_runtime.py` to locate the original, unmodified files.

```bash
python extract_solutions.py --src /path/to/repos --dst /path/to/corpus
```

### 2. Extract features — `main.py` + `extract_features.py`

This script iterates over every `.py` file in the corpus and computes the following static metrics:

| Metric | Description |
|---|---|
| `cyclomatic_complexity` | Mean McCabe complexity across all functions |
| `cognitive_complexity` | Mean cognitive complexity across all top-level functions |
| `halstead_volume` | Halstead volume for the whole file |
| `halstead_difficulty` | Halstead difficulty for the whole file |
| `sloc` | Source lines of code, excluding blank lines and comments |
| `max_nesting_depth` | Maximum nesting depth of any block (`if`/`for`/`while`/`with`/`try`) |
| `comment_ratio` | Ratio of comment lines to total non-blank lines |
| `avg_identifier_length` | Mean length of all variable, function, and argument names |
| `heavy_library` | Whether the file imports a heavy-lifting library (`networkx`, `z3`, `sympy`, `scipy`) |

All metrics are computed statically from the source code without executing any files. Output is written to `dataset.csv`.

```bash
python main.py
```

Edit the `CORPUS_DIR` and `OUTPUT_CSV` paths at the top of `main.py` before running.

### 3. Measure runtime — `measure_runtime.py`

This script runs each solution script three times using the corresponding AoC puzzle input file and records the median wall-clock time. Scripts that exceed the 10-second timeout or exit with a non-zero return code are recorded as failed. Output is written to `runtimes.csv`.

```bash
python measure_runtime.py
```

This script requires a `path_map.csv` in the corpus root, produced by `extract_solutions.py`, and a directory of puzzle input files organised as `input_files/year/dayNN/*.txt`. Note that runtime is measured on the original unmodified files, not the wrapped corpus copies.

Edit the path constants at the top of `measure_runtime.py` before running.

---

## Installation

Python 3.10+ is required.

```bash
pip install -r requirements.txt
```

---

## Data

The raw corpus is not included in this repository. The contributor list is documented in the thesis appendix.

The following derived datasets are included:

- `dataset.csv` — static complexity metrics for 4,262 Python files across 43 contributors
- `dataset_readability.csv` — LLM-assigned readability scores (Gemini 2.5 Flash Lite, zero-shot) for the same files
- `human_readability_annotation.csv` — manual readability annotations for a random sample of 49 files, used for inter-annotator agreement validation (weighted Cohen's κ = 0.759)

The `wrap_in_main` step affects approximately 26% of files that were originally written as flat scripts. After this step, 586 files were found to have a source line count of zero and were removed as empty stubs, reducing the dataset from 4,848 to 4,262 files.