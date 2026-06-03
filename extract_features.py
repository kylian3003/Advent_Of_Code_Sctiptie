import re
import ast
import warnings
from radon.complexity import cc_visit, average_complexity
from radon.metrics import h_visit
from cognitive_complexity.api import get_cognitive_complexity as get_cognitive_complexity_for_function

# suppress SyntaxWarnings from solution files that use invalid escape sequences
warnings.filterwarnings("ignore", category=SyntaxWarning)

# libraries that are considered heavy lifting for AoC puzzles
HEAVY_LIBRARIES = {"networkx", "z3", "sympy", "scipy"}


def get_part(filename):
    """Try to figure out if this file is part 1 or 2 based on the filename.
    Returns None if it can't be determined."""
    if re.search(r"part[_\-]?1|p1\b|[_\-]1\.|[_\-]?a\.py|[qQ]1\b|solution1|sol1\b", filename, re.IGNORECASE):
        return 1
    if re.search(r"part[_\-]?2|p2\b|[_\-]2\.|[_\-]?b\.py|[qQ]2\b|solution2|sol2\b", filename, re.IGNORECASE):
        return 2
    return None




def get_cyclomatic_complexity(source):
    """Compute the average cyclomatic complexity of all functions in the file.
    Returns None if the file can't be parsed."""
    try:
        results = cc_visit(source)
        if not results:
            return None
        return round(average_complexity(results), 2)
    except Exception:
        return None
    
    
    
def get_cognitive_complexity(source):
    """Compute the average cognitive complexity across all top-level functions in the file.
    Cognitive complexity measures how hard code is to understand, rather than
    just counting paths like cyclomatic complexity does.
    Returns None if the file can't be parsed."""
    try:
        tree = ast.parse(source)
        scores = []
        # only iterate top-level nodes to avoid double-counting nested functions
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                score = get_cognitive_complexity_for_function(node)
                scores.append(score)
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)
    except Exception:
        return None
    


def get_halstead(source):
    """Compute Halstead volume and difficulty for the whole file.
    Volume measures the size of the implementation, difficulty measures how hard it is to write.
    Returns (None, None) if the file can't be parsed."""
    try:
        result = h_visit(source)
        volume = round(result.total.volume, 2)
        difficulty = round(result.total.difficulty, 2)
        return volume, difficulty
    except Exception:
        return None, None
    

def get_avg_identifier_length(source):
    """Compute the average length of all identifiers (variable, function, and argument names).
    Longer names tend to be more descriptive and readable, shorter names are more common
    in competitive/speed-focused code.
    Returns None if the file can't be parsed."""
    try:
        tree = ast.parse(source)
        lengths = []
        for node in ast.walk(tree):
            # function and argument names
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lengths.append(len(node.name))
                for arg in node.args.args:
                    lengths.append(len(arg.arg))
            # variable names from assignments
            elif isinstance(node, ast.Name):
                lengths.append(len(node.id))
        if not lengths:
            return None
        return round(sum(lengths) / len(lengths), 2)
    except Exception:
        return None


def get_sloc(source):
    """Count the number of Source Lines of Code (SLOC) — ignoring blank lines and comments."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            count += 1
    return count



def get_comment_ratio(source):
    """Compute the ratio of comment lines to total non-blank lines.
    A higher ratio means more of the code is commented/documented."""
    total = 0
    comments = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped:
            total += 1
            if stripped.startswith('#'):
                comments += 1
    if total == 0:
        return None
    return round(comments / total, 4)


def walk_depth(node, depth, nesting_nodes):
    """Recursively walk the AST and return the maximum nesting depth found."""
    max_depth = depth if isinstance(node, nesting_nodes) else 0
    for child in ast.iter_child_nodes(node):
        child_depth = walk_depth(child, depth + 1 if isinstance(node, nesting_nodes) else depth, nesting_nodes)
        max_depth = max(max_depth, child_depth)
    return max_depth


def get_max_nesting_depth(source):
    """Find the maximum nesting depth of any block in the file (if/for/while/with/try).
    Returns None if the file can't be parsed."""
    try:
        tree = ast.parse(source)
    except Exception:
        return None
    
    nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
    return walk_depth(tree, 0, nesting_nodes)


def get_heavy_library(source):
    """Check if the file imports any heavy lifting libraries.
    Returns True if a heavy library is found, False otherwise."""
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in HEAVY_LIBRARIES:
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in HEAVY_LIBRARIES:
                    return True
        return False
    except Exception:
        return False


def get_file_status(source):
    """Check whether a file has functions and whether it parses successfully.
    Returns one of: 'ok', 'no_functions', 'parse_error'"""
    try: 
        tree = ast.parse(source)
        has_functions = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in tree.body
        )
        if not has_functions:
            return "no_functions"
        return "ok"
    except Exception:
        return "parse_error"


def extract_features(py_file):
    """Extract all features from a single solution file.
    Metadata comes from the folder structure: corpus/username/year/dayNN/file.py"""
    parts = py_file.parts
    username = parts[-4]
    year = int(parts[-3])
    day = int(parts[-2].replace("day", ""))
    part = get_part(py_file.name)
    
    source = py_file.read_text(encoding="utf-8", errors="replace")
    halstead_volume, halstead_difficulty = get_halstead(source)
    
    return {
        "username": username,
        "filename": py_file.name,
        "year": year,
        "day": day,
        "part": part,
        "cyclomatic_complexity": get_cyclomatic_complexity(source),
        "cognitive_complexity": get_cognitive_complexity(source),
        "halstead_volume": halstead_volume,
        "halstead_difficulty": halstead_difficulty,
        "sloc": get_sloc(source),
        "max_nesting_depth": get_max_nesting_depth(source),
        "comment_ratio": get_comment_ratio(source),
        "avg_identifier_length": get_avg_identifier_length(source),
        "heavy_library": get_heavy_library(source),
        # status is used for the summary in main.py, not written to the csv
        "_status": get_file_status(source),
    }
