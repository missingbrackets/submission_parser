PINE WALK — SUBMISSION ANALYSER
================================
AI-powered submission extraction, gap analysis, and rating model data prep.
Built for London Market casualty (extensible to other classes).


QUICK START
-----------
1. Install Python 3.10+ from https://python.org  (tick "Add to PATH")
2. Copy this folder to your machine (e.g. T:\Tools\SubmissionAnalyser\)
3. Double-click  Launch_Analyser.bat
4. App opens in your browser at http://localhost:8501
5. Enter your Anthropic API key (get one at console.anthropic.com)
6. Paste in a case folder path and click Run Analysis


WHAT IT DOES
------------
Reads files from:
  <case_folder>\01_correspondence\   (emails, Word docs, PDFs)
  <case_folder>\02_data\             (Excel, PDFs, data files)

Produces:
  <case_folder>\01_correspondence\YYYYMMDD_AI_Summary.txt   — structured summary report
  <case_folder>\02_data\submission_data.csv                 — rating model data (appends each run)


ADDING A NEW CLASS / SKILL
---------------------------
1. Copy  skills/casualty.py  to  skills/your_class.py
2. Edit REQUIRED_FIELDS, CSV_SCHEMA, and SYSTEM_PROMPT for the new class
3. Open  skills/__init__.py  and add an import + entry to the SKILLS dict
4. The new class will appear in the app dropdown automatically


FOLDER STRUCTURE
----------------
submission_analyser/
  main.py                   Streamlit app
  file_parser.py            PDF / Excel / Word / .msg text extraction
  claude_caller.py          Claude API, gap analysis, CSV builder
  requirements.txt          Python dependencies
  Launch_Analyser.bat       Windows double-click launcher
  skills/
    __init__.py             Skills registry
    casualty.py             Casualty Liability template


API KEY NOTE
------------
Your Anthropic API key is entered in the app sidebar each session.
It is never stored to disk. For convenience you can set an environment
variable ANTHROPIC_API_KEY and the app will pick it up automatically
(edit main.py sidebar section to add: value=os.getenv("ANTHROPIC_API_KEY",""))


DEPENDENCIES
------------
streamlit, anthropic, pdfplumber, openpyxl, python-docx, extract-msg, pandas
All installed automatically by the .bat launcher.
