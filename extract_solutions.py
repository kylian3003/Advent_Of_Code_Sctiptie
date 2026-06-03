"""
AoC Solution Extractor

Walks all 46 GitHub repos and copies Python solution files into a
normalized structure: corpus/username/year/day/

It also skips non-solution files (tests, utils, templates, helpers)
and logs anything it could not confidently classify so you can review
those manually.

Usage:
    python extract_solutions.py --src "C:/path/to/your/repos" --dst "C:/path/to/corpus"

Or edit the SRC_DIR / DST_DIR defaults below and just run:
    python extract_solutions.py
"""

import os
import re
import ast
import csv
import shutil
import argparse
from pathlib import Path


# Edit these defaults if you don't want to pass CLI arguments
SRC_DIR = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\data"
DST_DIR = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\corpus"


# Files whose names strongly suggest they are NOT puzzle solutions
SKIP_NAME_PATTERNS = [
    r"^test_",               # test_aoc2017xx.py
    r"_test\.py$",           # aoc2017xx_test.py
    r"^conftest\.py$",
    r"^setup\.py$",
    r"^__init__\.py$",
    r"^create_template",
    r"^new_day",
    r"^update_benchmark",
    r"^runner\.py$",
    r"^bench\.py$",
    r"^collect\.py$",
    r"^template",
    r"^plot_",
]

# Folder names that are clearly not puzzle-day folders.
# NOTE: keep this list tight — "old", "solutions", "python", "py", "src"
# are NOT here because many repos use them as valid wrapper folders.
SKIP_FOLDER_NAMES = {
    "utils", "common", "helpers", "tools", "scripts",
    "resources", "docs", "tests", "test",
    "template", "templates", "benches", "bench", "include",
    "__pycache__", ".git", ".vscode", "node_modules",
    "media", "img", "images", "assets",
    ".aoc_dataset",          # puzzle metadata repo, not solutions
}

# Year extraction
# Handles: 2024, y2024, year_2024, aoc2024, AOC 24 (short year → expand)
YEAR_PATTERNS = [
    re.compile(r"\b(20\d{2})\b"),                        # 2015 … 2030
    re.compile(r"(?:y|year[_\-]?)(20\d{2})\b", re.IGNORECASE),  # y2024, year_2024
    re.compile(r"(?:aoc)[_\-\s]?(20\d{2})\b", re.IGNORECASE),   # aoc2024, AOC 2024
    re.compile(r"(?:aoc)[_\-\s]?(\d{2})\b", re.IGNORECASE),     # AOC 24
]

def extract_year(path_parts: list[str]) -> str | None:
    """Try to find a 4-digit AoC year in the path components."""
    for part in reversed(path_parts):
        for pat in YEAR_PATTERNS:
            m = pat.search(part)
            if m:
                raw = m.group(1)
                yr = int(raw)
                # Expand 2-digit short years: "24" → 2024
                if yr < 100:
                    yr += 2000
                if 2015 <= yr <= 2030:
                    return str(yr)
    return None

# Day extraction
# Handles folder names and filenames:
#   day01, day-1, day_01, Day-04         from folder or filename
#   d01, d1_                             abbreviated prefix
#   19.py, 03-1.py, 04A.py, 16a.py       bare number (possibly with part suffix)
#   day16p1.py                           day+part in filename
#   advent16.py                          advent prefix
#   part_one.py inside day_1/            day from parent folder
#   aoc201801                            year+day in name

DAY_FOLDER_PATTERNS = [
    re.compile(r"day[_\-]?0*(\d{1,2})", re.IGNORECASE),      # day01, Day-04
    re.compile(r"\bday_0*(\d{1,2})\b", re.IGNORECASE),        # day_1
    re.compile(r"(?:^|[_\-])d0*(\d{1,2})(?:[_\-]|$)", re.IGNORECASE),  # d01_, _d1
    re.compile(r"year[_\-]\d{4}[_\-]day[_\-]?0*(\d{1,2})", re.IGNORECASE),  # year_2018_day_1
    re.compile(r"^0*(\d{1,2})[_\-]", re.IGNORECASE),          # 04_ or 03-
    re.compile(r"^0*(\d{1,2})$"),                              # folder is just "1" or "01"
]

DAY_FILENAME_PATTERNS = [
    re.compile(r"day[_\-]?0*(\d{1,2})(?:p\d+)?", re.IGNORECASE),  # day16p1, day_01
    re.compile(r"advent0*(\d{1,2})\b", re.IGNORECASE),             # advent16
    re.compile(r"(?:aoc\d{4})0*(\d{2})\b", re.IGNORECASE),         # aoc201801
    re.compile(r"^0*(\d{1,2})[a-z]?(?:[_\-]\d)?\.", re.IGNORECASE), # 04A.py, 16a.py, 03-1.py, 19.py
]


def extract_day(path_parts: list[str]) -> str | None:
    """
    Try to find a day number (1-25) in folder names first,
    then fall back to the filename itself.
    """
    filename = path_parts[-1]
    folders  = path_parts[:-1]

    # 1. Search folder names (deepest first)
    for part in reversed(folders):
        for pat in DAY_FOLDER_PATTERNS:
            m = pat.search(part)
            if m:
                day = int(m.group(1))
                if 1 <= day <= 25:
                    return f"{day:02d}"

    # 2. Fall back to filename patterns
    for pat in DAY_FILENAME_PATTERNS:
        m = pat.search(filename)
        if m:
            day = int(m.group(1))
            if 1 <= day <= 25:
                return f"{day:02d}"

    return None


# In filenames like aoc_2015_01.py or aoc201501.py the year+day are both present
FILENAME_YEAR_DAY = re.compile(
    r"(?:aoc[_\-]?)?(20\d{2})[_\-]?0*(\d{1,2})", re.IGNORECASE
)

def extract_year_day_from_filename(filename: str):
    """For files like aoc_2015_01.py where year+day are both in the name."""
    m = FILENAME_YEAR_DAY.search(filename)
    if m:
        yr  = int(m.group(1))
        day = int(m.group(2))
        if 2015 <= yr <= 2030 and 1 <= day <= 25:
            return str(yr), f"{day:02d}"
    return None, None


def is_skip_file(filename: str) -> bool:
    for pat in SKIP_NAME_PATTERNS:
        if re.search(pat, filename, re.IGNORECASE):
            return True
    return False


def should_skip_folder(folder_name: str) -> bool:
    return folder_name.lower() in SKIP_FOLDER_NAMES or folder_name.startswith(".")


def wrap_in_main(source: str) -> str:
    """If the source has no top-level functions, wrap the non-import code in a main() function.
    This allows cyclomatic and cognitive complexity to be computed for flat scripts."""
    try:
        tree = ast.parse(source)
    except Exception:
        return source

    # check if there are already any functions defined
    has_functions = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in tree.body
    )
    if has_functions:
        return source

    lines = source.splitlines(keepends=True)
    import_types = (ast.Import, ast.ImportFrom)

    # collect line numbers of import statements (1-indexed)
    import_lines = set()
    for node in tree.body:
        if isinstance(node, import_types):
            for lineno in range(node.lineno, node.end_lineno + 1):
                import_lines.add(lineno)

    # split lines into imports (stay at top level) and body (go inside main)
    top_lines = []
    body_lines = []
    for i, line in enumerate(lines, start=1):
        if i in import_lines:
            top_lines.append(line)
        else:
            body_lines.append('    ' + line)

    # only wrap if there is actually something to put inside main
    if not any(l.strip() for l in body_lines):
        return source

    wrapped = top_lines + ['\n', 'def main():\n'] + body_lines
    wrapped += ['\n', "\nif __name__ == '__main__':\n", '    main()\n']
    return ''.join(wrapped)


def get_part_from_filename(filename):
    """Detect part 1 or 2 from a filename. Returns None if it can't be determined."""
    if re.search(r"part[_\-]?1|p1\b|[_\-]1\.|[_\-]?a\.py|[qQ]1\b|solution1|sol1\b", filename, re.IGNORECASE):
        return 1
    if re.search(r"part[_\-]?2|p2\b|[_\-]2\.|[_\-]?b\.py|[qQ]2\b|solution2|sol2\b", filename, re.IGNORECASE):
        return 2
    return None


def copy_solution(src_file: Path, dst_dir: Path, new_name: str, log: list, path_map: list):
    dst_dir.mkdir(parents=True, exist_ok=True)
    src_content = src_file.read_text(encoding="utf-8", errors="replace")

    # skip if a file with identical content already exists in the destination folder
    for existing_file in dst_dir.glob("*.py"):
        existing_content = existing_file.read_text(encoding="utf-8", errors="replace")
        if src_content == existing_content:
            log.append(f"  SKIPPED (duplicate content): {src_file}")
            return

    # skip if a file for the same part already exists (or both are unknown part)
    incoming_part = get_part_from_filename(new_name)
    for existing_file in dst_dir.glob("*.py"):
        existing_part = get_part_from_filename(existing_file.name)
        if incoming_part == existing_part:
            log.append(f"  SKIPPED (part {incoming_part} already exists): {src_file}")
            return

    # wrap flat scripts in main() so complexity metrics can be computed
    src_content = wrap_in_main(src_content)

    dst_file = dst_dir / new_name
    dst_file.write_text(src_content, encoding="utf-8")
    path_map.append({"corpus_file": str(dst_file), "original_file": str(src_file), "original_dir": str(src_file.parent)})
    log.append(f"  COPIED  {src_file}  →  {dst_file}")




def process_repos(src_root: Path, dst_root: Path):
    copied = 0
    skipped_files = []
    unresolved = []
    path_map = []

    repo_dirs = sorted([d for d in src_root.iterdir() if d.is_dir()])

    for repo_dir in repo_dirs:
        username = repo_dir.name
        if should_skip_folder(username):
            continue

        print(f"\n── Repo: {username}")
        log = []

        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if not should_skip_folder(d)]

            root_path = Path(root)
            py_files  = [f for f in files if f.endswith(".py")]

            for fname in py_files:
                src_file = root_path / fname


                if is_skip_file(fname):
                    skipped_files.append(str(src_file))
                    continue

                rel   = src_file.relative_to(repo_dir)
                parts = list(rel.parts)   # e.g. ['2024', 'Day-04', 'solution1.py']

                # Strategy 1: year+day both embedded in filename (e.g. aoc_2024_01.py)
                year, day = extract_year_day_from_filename(fname)

                # Strategy 2: extract from path components
                if not year:
                    year = extract_year(parts)
                if not day:
                    day = extract_day(parts)

                if year and day:
                    dst_dir = dst_root / username / year / f"day{day}"
                    copy_solution(src_file, dst_dir, fname, log, path_map)
                    copied += 1
                else:
                    unresolved.append(str(src_file))
                    log.append(f"  UNRESOLVED (year={year}, day={day}): {src_file}")

        for line in log:
            print(line)


    # Summary
    print("\n" + "=" * 60)
    print(f"Done. {copied} files copied to {dst_root}")
    print(f"{len(skipped_files)} files skipped (tests/utils/templates)")
    print(f"{len(unresolved)} files could NOT be resolved — review manually:") 
    for f in unresolved:
        print(f"  !! {f}")

    log_path = dst_root / "extraction_log.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(f"Copied: {copied}\n")
        fh.write(f"Skipped (non-solutions): {len(skipped_files)}\n")
        fh.write(f"Unresolved: {len(unresolved)}\n\n")
        fh.write("=== UNRESOLVED ===\n")
        fh.write("\n".join(unresolved) + "\n\n")
        fh.write("=== SKIPPED ===\n")
        fh.write("\n".join(skipped_files) + "\n")
    print(f"\nFull log written to: {log_path}")

    # write the path map so measure_runtime.py can find original file locations
    map_path = dst_root / "path_map.csv"
    with open(map_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["corpus_file", "original_file", "original_dir"])
        writer.writeheader()
        writer.writerows(path_map)
    print(f"Path map written to: {map_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract AoC Python solutions into a normalised corpus.")
    parser.add_argument("--src", default=SRC_DIR, help="Root folder containing all repo folders")
    parser.add_argument("--dst", default=DST_DIR, help="Destination corpus folder")
    args = parser.parse_args()


    src = Path(args.src)
    dst = Path(args.dst)

    if not src.exists():
        print(f"ERROR: Source folder not found: {src}")
        exit(1)

    print(f"Source : {src}")
    print(f"Dest   : {dst}")
    process_repos(src, dst)
    