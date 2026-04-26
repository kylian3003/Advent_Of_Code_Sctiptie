import re
from pathlib import Path
from radon.complexity import cc_visit, average_complexity

CORPUS_DIR = r"C:\Users\kylia\Documents\uni\Scriptie\corpus"


def get_part(filename):
    # try to figure out if this file is part 1 or 2 based on the filename
    if re.search(r"part[_\-]?1|p1\b|[_\-]1\.|[_\-]?a\.py", filename, re.IGNORECASE):
        return 1
    if re.search(r"part[_\-]?2|p2\b|[_\-]2\.|[_\-]?b\.py", filename, re.IGNORECASE):
        return 2
    return None


def get_cyclomatic_complexity(source):
    try:
        results = cc_visit(source)
        if not results:
            return None
        return round(average_complexity(results), 2)
    except Exception:
        return None


def extract_features(py_file):
    # folder structure is corpus/username/year/dayNN/file.py
    parts = py_file.parts
    username = parts[-4]
    year = int(parts[-3])
    day = int(parts[-2].replace("day", ""))
    part = get_part(py_file.name)

    source = py_file.read_text(encoding="utf-8", errors="replace")
    complexity = get_cyclomatic_complexity(source)

    return {
        "username": username,
        "year": year,
        "day": day,
        "part": part,
        "cyclomatic_complexity": complexity,
    }


def main():
    corpus = Path(CORPUS_DIR)

    for py_file in sorted(corpus.rglob("*.py")):
        features = extract_features(py_file)
        print(features)


if __name__ == "__main__":
    main()