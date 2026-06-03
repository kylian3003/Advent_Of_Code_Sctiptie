import csv
import statistics
import subprocess
import time
from pathlib import Path

PATH_MAP_CSV = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\corpus\path_map.csv"
INPUT_DIR = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\input_files"
OUTPUT_CSV = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\runtimes.csv"

FIELDNAMES = ["username", "year", "day", "filename", "runtime"]

# years for which we have input files
SUPPORTED_YEARS = {2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024}

# max seconds to wait before killing the script
TIMEOUT = 10


def load_path_map(path_map_csv):
    '''Load the path map CSV into a dict keyed by corpus_file path.'''
    path_map = {}
    with open(path_map_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            path_map[row["corpus_file"]] = row
    return path_map


def run_once(original_file, original_dir, input_file):
    '''Run a solution script once and return (elapsed, reason).'''
    try:
        start = time.perf_counter()
        result = subprocess.run(
            ["python", str(original_file)],
            cwd=original_dir,
            stdin=open(input_file),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
        )
        elapsed = time.perf_counter() - start
 
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            reason = stderr.splitlines()[-1] if stderr else "non-zero exit code"
            return None, reason
        return round(elapsed, 4), "ok"

    except subprocess.TimeoutExpired:
        return None, f"timeout (>{TIMEOUT}s)"
    except Exception as e:
        return None, str(e)


def measure_runtime(original_file, original_dir, input_file):
    '''Run the script 3 times and return the median runtime.
    If any run fails, return None immediately with the reason.'''
    times = []
    for _ in range(3):
        elapsed, reason = run_once(original_file, original_dir, input_file)
        if elapsed is None:
            return None, reason
        times.append(elapsed)
    return round(statistics.median(times), 4), "ok"


def main():
    path_map = load_path_map(PATH_MAP_CSV)
    input_root = Path(INPUT_DIR)

    total = 0
    succeeded = 0
    no_input = 0 
    timed_out = 0
    error_counts = {}

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for corpus_file, paths in sorted(path_map.items()):
            corpus_path = Path(corpus_file)
            parts = corpus_path.parts
            username = parts[-4]
            year = int(parts[-3])
            day = int(parts[-2].replace("day", ""))
            filename = corpus_path.name

            # skip years we don't have input files for
            if year not in SUPPORTED_YEARS:
                continue

            total += 1 


            input_dir = input_root / str(year) / f"day{day:02d}"
            input_files = list(input_dir.glob("*.txt")) if input_dir.exists() else []
            if not input_files:
                no_input += 1
                print(f"SKIP (no input): {username}/{year}/day{day:02d}/{filename}")
                writer.writerow({"username": username, "year": year, "day": day, "filename": filename, "runtime": None})
                continue
            input_file = input_files[0]

            original_file = Path(paths["original_file"])
            original_dir = Path(paths["original_dir"])

            runtime, reason = measure_runtime(original_file, original_dir, input_file)

            if runtime is None:
                if reason.startswith("timeout"):
                    timed_out += 1
                else:
                    bucket = reason.split(":")[0].strip()
                    error_counts[bucket] = error_counts.get(bucket, 0) + 1
                print(f"FAIL ({reason}): {username}/{year}/day{day:02d}/{filename}")
            else:
                succeeded += 1
                print(f"OK ({runtime}s): {username}/{year}/day{day:02d}/{filename}")

            writer.writerow({"username": username, "year": year, "day": day, "filename": filename, "runtime": runtime})
    
    total_failed = total - succeeded - no_input
    print("\n" + "=" * 40)
    print(f"Total:          {total}")
    print(f"Succeeded:      {succeeded}")
    print(f"No input file:  {no_input}")
    print(f"Timed out:      {timed_out}")
    print(f"Failed:         {total_failed}")
    if error_counts:
        print("\nFailure reasons:")
        for reason, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"  {count:4d}  {reason}")


if __name__ == "__main__":
    main()
    