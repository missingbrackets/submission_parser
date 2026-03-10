# Submission Analyser — User Guide

**Audience:** Underwriters and pricing analysts in the London Market
**Application:** Submission Analyser (Streamlit)
**Purpose:** Automated extraction, gap analysis, and CSV output from broker submission files

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Folder Structure](#3-folder-structure)
4. [The Submission Analyser Page](#4-the-submission-analyser-page)
   - 4.1 [Sidebar Inputs](#41-sidebar-inputs)
   - 4.2 [Running an Analysis](#42-running-an-analysis)
   - 4.3 [Reading Submission Files](#43-reading-submission-files)
   - 4.4 [AI Extraction](#44-ai-extraction)
   - 4.5 [Gap Analysis](#45-gap-analysis)
   - 4.6 [Extracted Data Tabs](#46-extracted-data-tabs)
   - 4.7 [Saving Outputs](#47-saving-outputs)
5. [Batch Mode — Multiple Submissions](#5-batch-mode--multiple-submissions)
6. [Output Files Reference](#6-output-files-reference)
7. [The Skill Viewer Page](#7-the-skill-viewer-page)
8. [Supported File Formats](#8-supported-file-formats)
9. [Classes of Business (Skills)](#9-classes-of-business-skills)
10. [Tips and Best Practices](#10-tips-and-best-practices)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Overview

The Submission Analyser reads broker submission documents from a local folder, sends them to Claude AI for structured data extraction, and returns:

- A gap analysis score showing how complete the submission is against your class-of-business requirements
- Tabbed views of all extracted fields organised by section (insured details, limits, loss history, and so on)
- Ready-to-export CSV files for pricing models and portfolio tracking
- A plain-text summary report for the underwriting file

The application is designed for day-to-day use by underwriters and pricing analysts. No coding or technical knowledge is required to operate it.

---

## 2. Quick Start

### Prerequisites

- You have been given an Anthropic API key by your team administrator
- The application has been installed on your machine (contact your support team if not)
- Your submission documents are in a folder on your local drive or a mapped network drive

### Launching the Application

**On Windows:**

Double-click `Launch_Analyser.bat` in the application folder.

**Alternative (any platform):**

Open a terminal in the application folder and run:

```
streamlit run main.py
```

The application opens automatically in your default web browser at:

```
http://localhost:8501
```

If the browser does not open automatically, copy and paste that address into your browser manually.

### First Analysis in Five Steps

1. Enter your Anthropic API key in the sidebar
2. Paste the path to your case folder
3. Select the correct Class of Business
4. Click **Run Analysis**
5. Review the gap analysis score and extracted data, then click **Save Summary Report + CSV**

---

## 3. Folder Structure

The application expects your case files to follow this folder layout:

```
case_folder/
├── 01_correspondence/        # Emails, Word documents, PDFs from the broker
└── 02_data/                  # Excel files, data attachments, SOV files
```

The application creates its output folder automatically on first save:

```
case_folder/
├── 01_correspondence/
├── 02_data/
└── submission_tool_auto_outputs/     # Created automatically
    ├── YYYYMMDD_AI_Summary.txt
    ├── submission_data.csv
    ├── claims_data.csv               # Present if skill includes loss history
    ├── locations_data.csv            # Present if skill includes SOV data
    ├── triage_matrix.csv             # PV Triage skill only
    └── triage_direct.csv             # PV Direct Triage skill only
```

The application never modifies files in `01_correspondence/` or `02_data/`. All writes go exclusively to `submission_tool_auto_outputs/`.

### Naming Conventions

There are no strict requirements on what you name your case folder. The subfolder names `01_correspondence` and `02_data` are the expected defaults; you select which subfolders to include in the sidebar before running.

---

## 4. The Submission Analyser Page

The sidebar on the left contains all configuration inputs. The main panel displays results after the analysis runs.

### 4.1 Sidebar Inputs

#### Anthropic API Key

Enter your Anthropic API key in the password field at the top of the sidebar. The key is masked on screen and is **never written to disk** — it exists only in memory for the duration of your browser session. You will need to re-enter it each time you restart the application.

If you do not have an API key, contact your team administrator.

#### Case Folder Path

Paste the full path to the root of your submission folder. Examples:

```
C:\Submissions\2026\ABC_Corp_GL
\\server\submissions\ABC_Corp_GL
/Users/jsmith/submissions/ABC_Corp_GL
```

The folder must contain at least one of the expected subfolders (`01_correspondence` or `02_data`) with readable files inside them.

#### Class of Business

Select the class of business that matches this submission. The class determines:

- Which fields Claude is asked to extract
- Which gap analysis checks are applied (and which are flagged as critical)
- Which output CSV columns are produced
- Which data tabs appear in the results panel

Available classes are listed in [Section 9](#9-classes-of-business-skills).

#### Source Subfolders

Two checkboxes control which parts of the case folder are read:

| Checkbox | Reads from | Typical contents |
|---|---|---|
| `01_correspondence` | `case_folder/01_correspondence/` | Broker emails, cover notes, Word documents, PDFs |
| `02_data` | `case_folder/02_data/` | Excel schedules, SOV files, data attachments |

Tick both unless you have a specific reason to exclude one. If you are re-running an analysis because new data has arrived in only one subfolder, you can limit reading to save time — but note that the AI extraction uses all files that are read, so excluding a subfolder means its content will not be sent to Claude.

#### Submission Mode

The default is single-submission mode. Toggle **Multiple Submissions** to process a parent folder containing several submission subfolders in one batch run. See [Section 5](#5-batch-mode--multiple-submissions) for full details.

#### Display Tabs

A set of checkboxes controls which data tabs appear in the results panel after analysis. By default, the tabs appropriate for the selected Class of Business are pre-selected. You can deselect tabs you do not need to reduce visual clutter. The underlying extraction is not affected — only the display changes.

#### Run Analysis

The blue **Run Analysis** button starts the process. The button is only active when an API key, a valid folder path, and a Class of Business have been provided.

---

### 4.2 Running an Analysis

When you click **Run Analysis**, the main panel works through four stages in sequence. A status indicator appears at the top of each stage.

| Stage | What happens |
|---|---|
| Reading Submission Files | All readable files in the selected subfolders are loaded into memory |
| AI Extraction | The combined document text is sent to Claude; extracted fields are returned as structured JSON |
| Gap Analysis | The extracted fields are scored against the class-of-business requirements |
| Extracted Data | Results are displayed in tabs |

---

### 4.3 Reading Submission Files

The application lists every file it finds, showing:

- File name
- File size in KB
- Read status (success or error message)

If a file cannot be read (for example, a password-protected PDF), it is skipped and an error note is shown on its card. The remaining files are still processed.

Large documents are truncated at 60,000 characters before being sent to Claude. This limit exists to keep API costs and response times manageable. For most submission documents this limit is not reached, but very large Excel files or lengthy SOV schedules may be partially truncated. If you suspect truncation is causing missed data, consider splitting large files or removing irrelevant tabs before running.

---

### 4.4 AI Extraction

A spinner is shown while Claude processes the documents. Extraction typically takes between 15 and 60 seconds depending on the volume of text.

When complete, a confirmation message — "Extraction complete" — is shown.

#### Result Caching

The application caches the extraction result for each unique combination of case folder and Class of Business. If you click **Run Analysis** again without changing any inputs, the cached result is returned instantly without a new API call, and without any additional charge.

The cache is cleared and a fresh API call is made when you:

- Change the case folder path
- Change the Class of Business
- Tick the **Re-run all (ignore cache)** checkbox (batch mode only)

This means you can freely switch between the data tabs, adjust which tabs are displayed, or review the gap analysis as many times as you like without incurring further costs.

---

### 4.5 Gap Analysis

The gap analysis panel shows a score and a breakdown of missing fields.

#### Score

The score is a number from 0 to 100, reflecting the percentage of required fields that were successfully extracted. The colour band indicates overall submission quality:

| Score range | Rating | Meaning |
|---|---|---|
| 75 – 100 | GOOD | Most required fields are present; submission is workable |
| 50 – 74 | MODERATE | Several fields are missing; follow-up with broker likely needed |
| 0 – 49 | POOR | Material gaps; submission may not be ready for pricing |

#### Critical Gaps (RED)

Fields marked in red are blocking gaps — data points that are required before a risk can be underwritten. Examples include insured name, premium, and policy limits. A POOR score is almost always driven by multiple critical gaps.

#### Advisory Gaps (AMBER)

Fields marked in amber are useful but not strictly blocking. Their absence may warrant a question to the broker but does not prevent initial assessment.

#### Fields Present

The panel also shows a count of how many expected fields were successfully populated, giving a quick sense of submission completeness.

---

### 4.6 Extracted Data Tabs

Results are presented in tabs. The tabs available depend on the Class of Business and the Display Tabs selection in the sidebar.

#### Insured & Exposure 🏢

Core insured details: insured name, broker name, annual revenue, employee count, and similar exposure metrics. This is the first check to confirm the AI has correctly identified the risk.

#### Policy Structure 📄

Policy dates, trigger basis, jurisdiction, retroactive date, and other structural terms.

#### Limits & Structure 🔢

Limit of indemnity, excess point, deductible, and sublimit details.

#### Coverage Lines 🏷

A yes/no flag table showing which coverage extensions or exclusions were found in the submission documents. Flags are shown with colour-coded icons for quick scanning.

#### Premium Analytics 💷

Premium, brokerage percentage, net premium, and rate metrics where extractable.

#### Loss History 📉

A year-by-year table of prior losses with summary metrics (total incurred, largest single loss, loss ratio where calculable). Large individual losses are highlighted.

#### Risk Flags ⚠️

Free-text extractions relating to litigation history, prior declinatures, regulatory issues, or other risk-quality indicators found in the documents.

#### Underwriter Analytics 🚩

Flags raised by the AI for the underwriter's attention, sorted by severity. This tab also surfaces data conflicts (where different documents disagree on the same field) and suggested questions for the broker.

#### Locations & SOV 📍

A schedule of values table extracted from SOV or location schedule files. Populated for terror and political violence skills where location data is expected.

#### Triage Flags 🚦

RAG-rated (Red / Amber / Green) flags specific to the PV Direct Triage skill. Each flag indicates whether a screening criterion is met, partially met, or failed.

#### Summary 📋

A preview of the full narrative summary report that will be saved as a `.txt` file. You can read it here before saving.

#### Claims CSV 📊

A preview of the rows that will be written to `claims_data.csv`. Verify the table looks correct before saving.

#### Raw JSON 🔍

The complete extraction output in JSON format, alongside the skill schema documentation. This tab is primarily for checking what the AI returned in full and for diagnosing unexpected gaps. It is not needed for routine use.

---

### 4.7 Saving Outputs

When you are satisfied with the extraction, click **Save Summary Report + CSV** in the results panel.

This single button writes all applicable output files to `submission_tool_auto_outputs/` inside the case folder. See [Section 6](#6-output-files-reference) for a description of each file.

#### Important Behaviour: Append, Not Overwrite

The Save action **appends** new rows to existing CSV files rather than overwriting them. This means you can process multiple submissions into the same output CSV to build up a portfolio-level dataset. If you re-save the same submission after a re-run, a duplicate row will be added — delete the duplicate manually in Excel if needed.

#### CSV Row Preview

An expandable section beneath the Save button shows a preview of the row that will be written to `submission_data.csv`. Review this before saving if you want to confirm the key fields.

---

## 5. Batch Mode — Multiple Submissions

Batch mode processes several submissions in a single run. It is useful for onboarding a book of business, processing end-of-month bordereaux, or re-processing a portfolio after a skills update.

### Setting Up Batch Mode

1. Toggle **Multiple Submissions** in the sidebar
2. Set the Case Folder Path to the **parent** folder that contains your individual submission subfolders. For example:

```
Parent folder (point app here in batch mode):
  renewals_2026/
  ├── ABC_Corp/
  │   ├── 01_correspondence/
  │   └── 02_data/
  ├── DEF_Ltd/
  │   ├── 01_correspondence/
  │   └── 02_data/
  └── GHI_PLC/
      ├── 01_correspondence/
      └── 02_data/
```

3. Select Class of Business and Source Subfolders as normal
4. Click **Run Analysis**

### What Happens During a Batch Run

- Each submission subfolder is processed in turn
- A progress bar tracks completion
- A results table is built up showing all submissions with their gap analysis scores
- If a subfolder fails (unreadable files, empty folder), it is noted in the results table and processing continues

### Batch Output Files

**Per-submission outputs** — written to each subfolder's own `submission_tool_auto_outputs/`:

```
renewals_2026/
└── ABC_Corp/
    └── submission_tool_auto_outputs/
        ├── YYYYMMDD_AI_Summary.txt
        ├── submission_data.csv
        └── claims_data.csv
```

**Consolidated outputs** — written to the parent folder's `submission_tool_auto_outputs/`:

```
renewals_2026/
└── submission_tool_auto_outputs/
    ├── submission_data.csv      # All submissions combined
    └── claims_data.csv          # All claims rows combined
```

The consolidated CSVs are particularly useful for importing into a portfolio pricing model or risk management system.

### Re-running Batch Extractions

Tick **Re-run all (ignore cache)** before clicking Run Analysis to force fresh API calls for every submission, regardless of whether a cached result exists. Use this when you have updated the skill configuration or want to ensure the latest Claude model is used.

---

## 6. Output Files Reference

All output files are written to `submission_tool_auto_outputs/` inside the case folder (or parent folder for consolidated batch outputs).

### YYYYMMDD_AI_Summary.txt

A plain-text narrative summary of the submission, dated with the run date. Suitable for pasting into an underwriting system or attaching to the underwriting file. The date prefix means multiple runs produce separate summary files; old summaries are not overwritten.

### submission_data.csv

The primary structured output. One row per submission run. Columns correspond to the fields defined in the skill schema for the selected Class of Business. This file is the main input for pricing models and portfolio trackers.

Key column groups present in most skills:

| Column group | Example columns |
|---|---|
| Identification | insured_name, broker, reference |
| Dates | inception_date, expiry_date |
| Exposure | revenue, employees, territory |
| Limits | limit, excess, deductible |
| Premium | gross_premium, brokerage_pct, net_premium |
| Scoring | gap_score, critical_gaps_count, advisory_gaps_count |

### claims_data.csv

One row per policy year of loss history. Columns typically include year, number of claims, total incurred, largest loss, and loss ratio. Present only for skills that include a loss history extraction section.

### locations_data.csv

One row per location from the schedule of values. Columns typically include location name, address, TIV, and occupancy. Present only for skills with SOV extraction (terror and political violence skills).

### triage_matrix.csv

A structured triage output for the PV Triage (Quick) skill. Each row represents a triage criterion with its RAG rating.

### triage_direct.csv

The triage output for the PV Direct Triage skill. Similar structure to `triage_matrix.csv` but with criteria specific to direct (non-facultative) placements.

---

## 7. The Skill Viewer Page

Navigate to the **Skill Viewer** 📖 page using the sidebar navigation. This page is a reference tool — it lets you inspect any skill's configuration without running an analysis.

### Output Schema Tab

A table listing every field the skill attempts to extract. Columns in the schema table:

| Column | Meaning |
|---|---|
| Field | The field name as it appears in the CSV output |
| Section | Which results tab the field appears in |
| Type | Data type (text, number, date, boolean, list) |
| Critical | Whether this field triggers a RED gap if missing |
| Gap Check | Whether this field is included in the gap analysis score |

Use this tab to understand exactly what the AI will look for in a submission, and to explain to brokers which data points are needed.

### CSV Outputs Tab

Shows the full column list for `submission_data.csv` and any skill-specific CSVs (claims, locations, triage). Use this when setting up a downstream model to confirm expected column names and order.

### System Prompt Tab

Displays the full prompt that is sent to Claude for this skill. This is a read-only view intended for those who want to understand exactly how the AI is instructed. For guidance on modifying or creating skills, see the separate `adding_skills.md` document.

---

## 8. Supported File Formats

The application reads the following file types automatically. No conversion is needed before placing files in the case folder.

| Extension | Format | Library used |
|---|---|---|
| `.pdf` | PDF documents | pdfplumber |
| `.xlsx`, `.xls`, `.xlsm` | Excel workbooks | openpyxl / xlrd |
| `.docx`, `.doc` | Word documents | python-docx |
| `.msg` | Outlook email messages | extract-msg |
| `.txt` | Plain text | built-in |
| `.csv` | Comma-separated values | built-in |

### Notes on Specific Formats

**PDF:** Text is extracted from selectable text layers. Scanned PDFs (image-only) cannot be read and will show an error on the file card. If you have scanned documents, ask for an OCR-processed version from the broker.

**Excel:** All sheets in a workbook are read. Hidden sheets and very wide sheets are included. Formatting and colours are not extracted — only cell values.

**MSG:** The email body and any plain-text content are extracted. Attachments inside MSG files are not recursively unpacked; if an email contains an important PDF attachment, save the attachment separately into the folder.

**Password-protected files:** These cannot be read. The file card will show an error. Remove the password protection before placing the file in the case folder.

---

## 9. Classes of Business (Skills)

Each Class of Business (referred to internally as a "skill") defines a bespoke extraction schema, gap analysis criteria, and output format.

| Skill name | Intended use |
|---|---|
| Casualty Liability | General liability, products liability, and related casualty lines |
| Political Violence & Terrorism | Full PV/T submissions with SOV and location data |
| PV Triage (Quick) | Rapid screening of PV/T submissions against a triage matrix |
| PV Direct Triage | Triage for direct PV/T placements |
| My New Class | Placeholder / example for custom skill development |

If your class of business is not listed, contact your team administrator to request a new skill. Refer to `adding_skills.md` for the technical process.

---

## 10. Tips and Best Practices

### Organise Files Before Running

- Remove irrelevant files from the case folder before running — marketing materials, blank templates, or superseded versions add noise without improving extraction
- Place the most informative documents in `01_correspondence/` (cover letters, MRCs, slip drafts) and structured data in `02_data/`

### Use the Cache

The extraction cache is your friend. Once an extraction has run, you can:
- Change the Display Tabs selection to explore different data views at no cost
- Return to the analysis at any time during the same session without re-running
- Re-save outputs if you accidentally closed the results panel

Only click **Re-run all (ignore cache)** if new documents have arrived or you want to try a different Class of Business against the same folder.

### Check the Gap Analysis Before Saving

A high gap score does not guarantee accuracy — the AI extracts what it finds in the documents. Review the critical fields (Insured & Exposure 🏢 and Limits & Structure 🔢 tabs) before saving to catch obvious errors, such as a limit extracted from a prior year's policy rather than the current one.

### Use the Underwriter Analytics Tab

The Underwriter Analytics 🚩 tab surfaces data conflicts between documents. If two documents give different premium figures, the AI notes the discrepancy here. Check this tab before relying on extracted premium or limit figures.

### Building a Portfolio CSV

Because saves append rather than overwrite, you can accumulate a portfolio-level `submission_data.csv` by pointing the application at each case folder in turn and saving. Batch mode does this automatically and also produces a pre-consolidated file in the parent folder.

To start fresh and avoid duplicates, delete or rename `submission_data.csv` in `submission_tool_auto_outputs/` before processing a new set of submissions.

### API Key Management

- Do not share your API key with colleagues via email or chat — each user should have their own key
- The key is not stored by the application; you must re-enter it each session
- If you suspect your key has been compromised, rotate it in the Anthropic Console immediately

---

## 11. Troubleshooting

### The application does not open

- Confirm the `Launch_Analyser.bat` is in the correct folder
- Check that no other application is using port 8501; if so, close it or ask your support team to change the port
- If you see a Python error in the terminal, contact your support team with the full error text

### "No files found" error after clicking Run Analysis

- Check that the case folder path is correct and that the folder exists
- Confirm the `01_correspondence/` and/or `02_data/` subfolders exist inside the case folder
- Verify that the Source Subfolders checkboxes match the subfolders that actually contain files

### Extraction returns mostly empty fields

Possible causes:

| Cause | What to check |
|---|---|
| Wrong Class of Business selected | Does the skill match the type of risk in the documents? |
| Files not being read | Are all file cards showing green status? |
| Documents are image-only PDFs | Check for scanned PDFs; these cannot be read |
| Text is in tables the AI cannot parse | Try exporting the relevant Excel sheet as a flat `.csv` and re-running |
| Documents are encrypted | Check for password-protected files |

### Gap score is unexpectedly low despite good documents

- Open the Raw JSON 🔍 tab and check that the documents were received with meaningful content
- Confirm the correct Class of Business is selected — a Casualty skill applied to a PV submission will produce a low score
- Check whether the 60,000 character limit has truncated the most relevant document (the file card shows KB size; very large files may be cut off)

### API errors during extraction

| Error message | Likely cause | Action |
|---|---|---|
| Authentication error / Invalid API key | Key is incorrect or has been revoked | Re-enter or rotate the key |
| Rate limit exceeded | Too many requests in a short period | Wait one to two minutes and try again |
| Context length exceeded | Document text is unusually large after truncation | Remove the largest files from the folder and re-run; check which files are largest on the file cards |
| Timeout | Network issue or very slow response | Retry; if persistent, contact support |

### Saved CSV has duplicate rows

This occurs if **Save Summary Report + CSV** was clicked more than once for the same submission. Open `submission_data.csv` in Excel, identify and delete the duplicate row (the `run_date` column and all field values will be identical), and save the file.

### Batch mode skips some subfolders

- Each subfolder must contain at least one of the expected subfolders (`01_correspondence/` or `02_data/`) with at least one readable file
- Subfolders that contain only other subfolders (nested structure) are not recursed into
- Check the results table in the main panel — skipped submissions are listed with an explanation

### The Skill Viewer page shows no skills

This indicates a configuration issue with the skills directory. Contact your support team.

---

## Appendix: Folder Path Examples

The following examples show correct case folder path formats for common environments.

**Local Windows drive:**
```
C:\Submissions\2026\Risks\ABC_Corp_Liability
```

**Mapped network drive (Windows):**
```
Z:\London_Market\Submissions\2026\ABC_Corp
```

**UNC path (Windows):**
```
\\fileserver01\submissions\2026\ABC_Corp
```

**macOS / Linux local path:**
```
/Users/jsmith/submissions/ABC_Corp
/home/jsmith/submissions/ABC_Corp
```

Paths with spaces are supported — paste them in directly without quotation marks.

---

*For technical issues, contact your support team. For questions about skill configuration or adding new classes of business, refer to `adding_skills.md` in the documentation folder.*
