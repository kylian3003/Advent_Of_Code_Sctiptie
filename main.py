import csv
from pathlib import Path
from extract_features import extract_features

CORPUS_DIR = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\corpus"
OUTPUT_CSV = r"C:\Users\kylia\Documents\uni\Advent_Of_Code_Sctiptie\dataset.csv"

# _status is excluded from the csv, it's only used for the summary below
FIELDNAMES = ["username", "year", "day", "part", "cyclomatic_complexity", "cognitive_complexity", "halstead_volume", "halstead_difficulty", "sloc", "max_nesting_depth", "comment_ratio", "avg_identifier_length"]


def main():
    corpus = Path(CORPUS_DIR)
    
    # counters for the summary
    total = 0 
    has_cc = 0
    has_cog = 0
    no_functions = 0
    parse_errors = 0 
    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for py_file in sorted(corpus.rglob("*.py")):
            features = extract_features(py_file)
            total += 1
            
            # track why files return None
            status = features.pop("_status")
            if status == "no_functions":
                no_functions += 1
            elif status == "parse_error":
                parse_errors += 1
                
            if features["cyclomatic_complexity"] is not None:
                has_cc += 1
            if features["cognitive_complexity"] is not None:
                has_cog += 1
                
            writer.writerow(features)
            print(features)

    # print summary after all files are processed
    print("\n" + "=" * 40)
    print(f"Total files:         {total}")
    print(f"Has CC score:        {has_cc}")
    print(f"Has cognitive score: {has_cog}")
    print(f"No functions found:  {no_functions}")
    print(f"Parse errors:        {parse_errors}")
    

if __name__ == "__main__":
    main()
