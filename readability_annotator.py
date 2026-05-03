import os
import sys
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


PROMPT = '''You are an expert software engineer and code reviewer specializing in Python.
Your task is to evaluate the human readability of the Python script provided below.
Act as a strict, consistent zero-shot annotator. Do NOT consider runtime efficiency.
Focus solely on how easy it is for a human developer to read, understand, and maintain this script.

Evaluate the script across these five dimensions:
1. Variable & function naming - Are identifiers descriptive and consistent?
   Penalise single-letter names, cryptic abbreviations, or misleading names.
2. Modularity & structure - Is the code broken into logical, reusable units?
   Penalise monolithic blocks or deeply nested logic.
3. Control flow clarity - Are conditionals and loops straightforward to follow?
   Penalise deeply nested conditions or overly clever one-liners.
4. Comments & documentation - Are non-obvious sections explained?
   Penalise the complete absence of comments on complex logic.
5. Pythonic style & consistency - Does the code follow PEP 8 and idiomatic Python?
   Penalise inconsistent formatting or anti-patterns.

Scoring scale (1-10):
  1-2  : Nearly unreadable. Extremely cryptic, no structure, no naming conventions.
  3-4  : Poor readability. Some structure but major clarity issues throughout.
  5-6  : Average readability. Readable with effort, a mix of good and poor practices.
  7-8  : Good readability. Mostly clear, minor issues only.
  9-10 : Excellent readability. Clean, well-named, well-structured, immediately understandable.

PYTHON SCRIPT TO ANNOTATE:
{code}

Respond with ONLY a valid JSON object, no markdown, no preamble, no extra text.
Use this exact schema:
{{
  "readability_score": <integer 1-10>,
  "naming": {{"score": <integer 1-10>, "comment": "<one sentence>"}},
  "modularity": {{"score": <integer 1-10>, "comment": "<one sentence>"}},
  "control_flow": {{"score": <integer 1-10>, "comment": "<one sentence>"}},
  "comments_docs": {{"score": <integer 1-10>, "comment": "<one sentence>"}},
  "pythonic_style": {{"score": <integer 1-10>, "comment": "<one sentence>"}},
  "summary": "<two to three sentences explaining the overall readability score>"
}}'''


def read_file(filepath):
    '''
    This function reads a Python file and returns its contents as a string.
    '''
    if not os.path.isfile(filepath): 
        print('File not found: {}'.format(filepath), file=sys.stderr)
        exit(-1)
    with open(filepath, 'r') as f:
        code = f.read()
    if not code.strip():
        print('The file is empty: {}'.format(filepath), file=sys.stderr)
        exit(-1)
    return code


def call_gemini(code, api_key):
    '''
    This function sends the code to the Gemini API and returns the raw response text.
    '''
    client = genai.Client(api_key=api_key) 
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=PROMPT.format(code=code),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type='application/json'
        )
    )
    return response.text.strip()



def parse_response(raw):
    '''
    This function parses the JSON response from Gemini and returns it as a dict.
    '''
    try:
        result = json.loads(raw) 
    except json.JSONDecodeError:
        print('Could not parse Gemini response as JSON.', file=sys.stderr)
        exit(-1)
    return result


def annotate(filepath):
    '''
    This function ties together reading, calling the API and printing the result.
    '''
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print('No API key found. Add GEMINI_API_KEY to your .env file.', file=sys.stderr)
        exit(-1)

    code = read_file(filepath)
    raw = call_gemini(code, api_key)
    result = parse_response(raw)
    result['annotated_file'] = os.path.basename(filepath)
    print(json.dumps(result, indent=2))

    
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, 'test.py')
    annotate(filepath)

    
if __name__ == '__main__':
    main()
