# AI Process Documentation — Submission Analyser

**Audience:** Developers and technical architects
**Scope:** The AI layer, its design rationale, and how to swap to a different LLM provider
**Last updated:** 2026-03-10

---

## Table of Contents

1. [Overview](#1-overview)
2. [AI Pipeline — End to End](#2-ai-pipeline--end-to-end)
3. [The Extraction Function — Core Contract](#3-the-extraction-function--core-contract)
4. [Prompt Design Principles](#4-prompt-design-principles)
5. [RAG Flag Pattern](#5-rag-flag-pattern)
6. [JSON Parsing Strategy](#6-json-parsing-strategy)
7. [Gap Analysis — Non-AI Component](#7-gap-analysis--non-ai-component)
8. [Session State and Caching](#8-session-state-and-caching)
9. [Cost Considerations](#9-cost-considerations)
10. [Swapping to a Different AI Provider](#10-swapping-to-a-different-ai-provider)
11. [Multi-Provider Architecture — Future Pattern](#11-multi-provider-architecture--future-pattern)
12. [What Never Changes](#12-what-never-changes)

---

## 1. Overview

Submission Analyser is a Python application that parses London Market broker submissions — composed of emails, PDFs, Excel spreadsheets, and Word documents — and extracts structured underwriting data from them using a large language model (LLM).

The AI layer has one job: given a block of unstructured text representing a full submission and a structured system prompt defining what to extract, return a populated JSON object matching a predefined schema.

The entire AI interface is deliberately isolated in a single function in `core/extractor.py`. Everything else in the codebase — UI, output formatting, gap analysis, report generation — is AI-provider-agnostic. Swapping to a different LLM requires changes to one file only.

**Current provider:** Anthropic Claude (`claude-sonnet-4-20250514`)

---

## 2. AI Pipeline — End to End

The following describes the full data flow from a folder of submission files to a structured output.

```
Submission folder (emails, PDFs, Excel, Word)
        |
        v
  core/processor.py
  - Iterates files in the folder
  - Calls file_parser.py for each file type
  - Concatenates extracted text into combined_text string
        |
        v
  skills/<class>/prompts.py
  - Selects SYSTEM_PROMPT based on chosen insurance class
  - Selects OUTPUT_SCHEMA defining the expected JSON keys
        |
        v
  core/extractor.call_claude_extraction()          <-- ONLY AI CALL
  - Sends combined_text (capped at 60,000 chars) + system_prompt to the LLM
  - Receives raw text response
  - Parses and validates JSON
  - Returns (parsed_dict, raw_text)
        |
        v
  core/analysis.run_gap_analysis()                 <-- PURE PYTHON
  - Compares parsed_dict keys against required_fields list
  - Returns data_quality_score, critical_gaps, advisory_gaps, present lists
        |
        v
  core/outputs.py  /  core/report.py
  - Formats results to CSV, Excel, and/or PDF report
  - _rag_colour() parses triage flag strings into RED/AMBER/GREEN counts
        |
        v
  ui/
  - Renders results in Streamlit, cached in st.session_state
```

There is exactly one API call per submission in single mode, or one per subfolder in batch mode.

---

## 3. The Extraction Function — Core Contract

**File:** `core/extractor.py`

The function signature is the stable contract that the rest of the application depends on. It must not change when swapping providers.

```python
def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `combined_text` | `str` | All text extracted from the submission files, concatenated. Passed to the LLM truncated at 60,000 characters. |
| `system_prompt` | `str` | The full skill system prompt defining the extraction task, output schema, and behaviour rules. |
| `api_key` | `str` | The provider API key. Passed through from application config — the function does not hard-code it. |
| `max_tokens` | `int` | Maximum output tokens. Defaults to 4,096. Controls response length, not input length. |

**Return value:** `Tuple[dict, str]`

- `dict` — The parsed JSON extraction result. On failure, contains `extraction_error` and `raw_snippet` keys rather than raising an exception.
- `str` — The raw, unprocessed text response from the LLM. Retained for audit logging and debugging.

**Current implementation:**

```python
import anthropic
import json
import re
from typing import Tuple

def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
    client = anthropic.Anthropic(api_key=api_key)

    user_msg = (
        "You are processing a broker submission. The content below has been extracted "
        "from multiple source files (emails, PDFs, Excel spreadsheets, Word documents). "
        "Read ALL of it carefully before extracting — later sections may correct or "
        "supplement earlier ones. Reconcile any conflicts as instructed.\n\n"
        "=== SUBMISSION CONTENT START ===\n\n"
        + combined_text[:60000]
        + "\n\n=== SUBMISSION CONTENT END ===\n\n"
        "Now extract all structured data and return the JSON as specified. "
        "Return ONLY the JSON object — no markdown fences, no explanation."
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = message.content[0].text

    # Strip markdown fences if present
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    clean = clean.strip()

    parsed = {}
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
        else:
            parsed = {"extraction_error": "No JSON found in response", "raw_snippet": clean[:500]}

    return parsed, raw
```

### Input token cap rationale

The submission text is truncated to 60,000 characters before being sent to the LLM. This is not an API restriction — it is an application-level safeguard.

- 60,000 characters equates to approximately 15,000–20,000 tokens (depending on content density).
- Claude's context window is 200,000 tokens, so this is well within limits.
- The cap ensures cost predictability and consistent latency across all providers (see [Section 10](#10-swapping-to-a-different-ai-provider) for per-provider context window details).
- The most material submission information almost always appears in the first 60,000 characters. Reconciliation rules in the system prompt instruct the model to prioritise later-appearing information where conflicts exist.

---

## 4. Prompt Design Principles

Each skill stores its system prompt in `skills/<class>/prompts.py` as a constant named `SYSTEM_PROMPT`. Every prompt follows the same eight-section structure, in order:

**Section 1 — Role definition**
Establishes the model's persona and domain authority.
Example: *"You are an expert London Market underwriter analysing a broker submission for Marine Cargo."*

**Section 2 — Task framing**
Describes what to extract and why. Sets the model's objective before it reads any data.

**Section 3 — Reconciliation rules**
Submission folders contain multiple documents that may conflict. This section defines the priority hierarchy — typically: policy schedule > slip > cover note > email > supporting attachments. The model is instructed to flag where it applied reconciliation rather than silently selecting a value.

**Section 4 — Quality checks**
Sense checks appropriate to the class of business. For example: premium vs. rate consistency, limit vs. deductible plausibility, known exclusions for the risk type, development year warnings, IBNR commentary requirements.

**Section 5 — UW analyst flag instructions**
Defines when to raise RED, AMBER, or INFO flags in designated flag fields. Criteria are explicit (e.g., "flag RED if there is no signed slip").

**Section 6 — RAG flag instructions (triage skills only)**
Provides explicit criteria for GREEN, AMBER, and RED ratings in the eight triage flag fields. See [Section 5](#5-rag-flag-pattern) for the string format.

**Section 7 — JSON output structure**
A complete template matching the keys in `OUTPUT_SCHEMA`. The model is shown the exact key names, types, and any enumerated value sets it must adhere to.

**Section 8 — Final instruction**
Always ends with: *"Return ONLY the JSON object — no markdown fences, no explanation."*
This instruction is duplicated in the user message inside `call_claude_extraction()` as a belt-and-braces measure.

### Why this structure works

The role-before-task ordering exploits instruction hierarchy — the model is primed with its persona before encountering any user data, which reduces hallucination on ambiguous fields. The reconciliation rules section is critical for multi-document submissions: without it, models will silently pick whichever value appears first. The redundant JSON-only instruction (in both system and user messages) significantly reduces the frequency of markdown-wrapped responses.

---

## 5. RAG Flag Pattern

Triage skills return eight structured flag fields in their JSON output. Each field is a string beginning with one of three prefixes:

```
🟢 GREEN — <reason text>
🟡 AMBER — <reason text>
🔴 RED — <reason text>
```

The prefix is set by the LLM based on the explicit criteria in Section 6 of the system prompt. The rest of the string is free-form reasoning generated by the model.

**Parsing:** `core/outputs.py` contains a `_rag_colour()` helper that reads the leading emoji character to determine the colour category. It counts RED, AMBER, and GREEN across all eight fields to produce summary metrics written to the CSV output.

The emoji prefix approach was chosen because:
- It is unambiguous — no risk of the model using "red" as a descriptive word being misclassified.
- It is human-readable in raw JSON before any processing.
- It is trivially parseable with a single character comparison.

When adapting prompts for a different provider, ensure the RAG prefix format is preserved exactly. If a provider's model struggles to produce emoji characters reliably, the `_rag_colour()` helper and the prompt criteria would need to be updated together to use a text prefix such as `RED:`, `AMBER:`, `GREEN:`.

---

## 6. JSON Parsing Strategy

The LLM is explicitly instructed to return only a raw JSON object. In practice, models occasionally wrap their response in markdown code fences (` ```json ... ``` `) despite the instruction, particularly when they have been RLHF-tuned to format code blocks in conversation.

The parsing logic applies two layers of defence:

**Layer 1 — Fence stripping**

```python
clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
clean = clean.strip()
```

This removes opening ` ```json ` or ` ``` ` fences and closing ` ``` ` fences from the beginning and end of the response.

**Layer 2 — JSON object extraction fallback**

If `json.loads()` fails after fence stripping, the code attempts to locate any JSON object within the response using a greedy regex:

```python
match = re.search(r"\{[\s\S]*\}", clean)
```

This handles cases where the model prepends a brief explanation before the JSON, or appends a note after it. If this extraction also fails to parse, the function returns a structured error dict rather than raising an exception:

```python
{"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
```

**Why errors are returned rather than raised**

The application needs to continue processing remaining submissions in batch mode even if one fails. Returning a dict with `extraction_error` means:
- Gap analysis still runs (everything will be a gap).
- The error is visible in the output CSV.
- The raw response is preserved for manual inspection.
- No unhandled exception crashes the batch.

**JSON reliability by provider**

Claude with explicit JSON-only instructions returns clean JSON in the large majority of cases. When evaluating alternative providers, test JSON output reliability with representative prompts before committing to a swap. GPT-4o's `response_format={"type": "json_object"}` parameter enforces structured output at the API level, which is more reliable than instruction-only approaches.

---

## 7. Gap Analysis — Non-AI Component

**File:** `core/analysis.py`
**Entry point:** `run_gap_analysis(extracted_dict, required_fields)`

Gap analysis is entirely deterministic Python — it does not call the LLM. It compares the extracted dict returned by the AI against the `required_fields` list defined per skill, and determines which fields are meaningfully populated.

### Presence rules

A field is considered **present** if its value meets all of the following:

- Is not `None`
- Is not an empty string `""`
- Is not one of the placeholder strings: `"null"`, `"none"`, `"unknown"`, `"n/a"` (case-insensitive)

Special cases:
- **Arrays** — present only if non-empty and contains at least one item that is itself not a placeholder value.
- **Booleans** — always considered present. `False` is a valid, informative value.

### Outputs

| Output | Description |
|--------|-------------|
| `data_quality_score` | Integer 0–100. Percentage of required fields that are present. |
| `critical_gaps` | List of required fields that are absent. These are fields marked as mandatory in the skill definition. |
| `advisory_gaps` | List of recommended fields that are absent. These affect the score but are not blockers. |
| `present` | List of all fields that passed the presence check. |

The score and gap lists are written to the output CSV and displayed in the Streamlit UI alongside the extracted data. They are not fed back to the LLM — gap analysis is always a post-processing step.

---

## 8. Session State and Caching

There is no server-side caching and no database. Results are cached in Streamlit's `st.session_state` for the duration of the browser session.

**Cache key format:**

```python
f"{folder_path}|{class_choice}"
```

For example: `"/submissions/acme_cargo_2024|Marine Cargo"`

When the user navigates to a submission that has already been processed in the current session, the cached result is returned immediately without making another API call. The cache is cleared when:

- The Streamlit app process restarts.
- The user clears session state explicitly.
- The browser session ends.

**Implications for development:**

- There is no risk of stale cache across deployments — each restart is a clean slate.
- In batch mode, each subfolder is processed sequentially and cached individually. If a batch run is interrupted, restarting will reprocess all subfolders (no partial resumption).
- If persistent caching is required in future (e.g., for a multi-user deployment), results would need to be written to a database or file store, keyed by a hash of `(folder_path, class_choice, prompt_version)`.

---

## 9. Cost Considerations

All costs are approximate and subject to Anthropic's current pricing at time of use.

**Per-submission cost breakdown:**

| Component | Typical value |
|-----------|---------------|
| Input tokens | ~15,000–20,000 (from 60,000 char text + system prompt) |
| Output tokens | Up to 4,096 (set by `max_tokens`) |
| API calls | 1 per submission (single mode) or 1 per subfolder (batch mode) |
| Estimated cost | $0.01–$0.05 per submission |

**Cost drivers:**

- **Input length** — The 60,000 character cap is the primary cost control. Raising this cap will increase costs proportionally. The system prompt also contributes to input tokens and is fixed per skill.
- **Output length** — `max_tokens=4096` is the ceiling. Actual output is usually shorter, but a complex extraction with many fields and flag reasoning can approach this limit. Reducing `max_tokens` reduces cost but risks truncated JSON.
- **Model selection** — `claude-sonnet-4-20250514` is a mid-tier model offering strong JSON reliability at moderate cost. Switching to a lighter model (e.g., Claude Haiku) would reduce cost but may reduce extraction accuracy. Switching to a heavier model (e.g., Claude Opus) would improve accuracy at higher cost.

**Batch mode cost note:** In batch mode, the application processes one subfolder per API call. If a submission folder contains 50 subfolders, expect 50 API calls. There is no batching at the API level — calls are made sequentially.

---

## 10. Swapping to a Different AI Provider

The entire AI interface is contained in one function in one file: `call_claude_extraction()` in `core/extractor.py`. No other file in the codebase imports from the Anthropic SDK or references any provider-specific object.

To swap providers, replace the body of `call_claude_extraction()` (and update imports) while keeping the function signature and return type identical. The JSON parsing and cleanup logic can be reused unchanged.

### Stable contract (must not change)

```python
def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
```

---

### Option A — OpenAI GPT-4o

**Install:** `pip install openai`

```python
from openai import OpenAI
import json
import re
from typing import Tuple

def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "You are processing a broker submission. The content below has been extracted "
                "from multiple source files (emails, PDFs, Excel spreadsheets, Word documents). "
                "Read ALL of it carefully before extracting — later sections may correct or "
                "supplement earlier ones. Reconcile any conflicts as instructed.\n\n"
                "=== SUBMISSION CONTENT START ===\n\n"
                + combined_text[:60000]
                + "\n\n=== SUBMISSION CONTENT END ===\n\n"
                "Now extract all structured data and return the JSON as specified. "
                "Return ONLY the JSON object — no markdown fences, no explanation."
            )},
        ],
        response_format={"type": "json_object"},  # Enforces JSON output at API level
    )

    raw = response.choices[0].message.content

    # Same JSON parsing logic as original
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    clean = clean.strip()

    parsed = {}
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
        else:
            parsed = {"extraction_error": "No JSON found in response", "raw_snippet": clean[:500]}

    return parsed, raw
```

**Notes for GPT-4o:**
- The `response_format={"type": "json_object"}` parameter enforces structured JSON output at the API level, making the fence-stripping logic largely redundant but harmless to keep.
- OpenAI's chat API takes the system prompt as `messages[0]` with `role="system"`, not as a separate `system=` parameter.
- GPT-4o context window is 128,000 tokens. The 60,000 character input cap remains safe.
- When using `response_format={"type": "json_object"}`, the model requires that the word "json" appear somewhere in the prompt — this is satisfied by the output instruction.

---

### Option B — Google Gemini 1.5 Pro

**Install:** `pip install google-generativeai`

```python
import google.generativeai as genai
import json
import re
from typing import Tuple

def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=system_prompt,
    )

    user_content = (
        "You are processing a broker submission. The content below has been extracted "
        "from multiple source files (emails, PDFs, Excel spreadsheets, Word documents). "
        "Read ALL of it carefully before extracting — later sections may correct or "
        "supplement earlier ones. Reconcile any conflicts as instructed.\n\n"
        "=== SUBMISSION CONTENT START ===\n\n"
        + combined_text[:60000]
        + "\n\n=== SUBMISSION CONTENT END ===\n\n"
        "Now extract all structured data and return the JSON as specified. "
        "Return ONLY the JSON object — no markdown fences, no explanation."
    )

    response = model.generate_content(
        user_content,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
        ),
    )

    raw = response.text

    # Same JSON parsing logic as original
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    clean = clean.strip()

    parsed = {}
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
        else:
            parsed = {"extraction_error": "No JSON found in response", "raw_snippet": clean[:500]}

    return parsed, raw
```

**Notes for Gemini:**
- The system prompt is passed via `system_instruction=` on the `GenerativeModel` constructor, not in the message content.
- Gemini 1.5 Pro has a 1,000,000 token context window — the 60,000 character cap is a non-issue.
- Gemini models may be less consistent at returning clean JSON without fences. Consider adding `response_mime_type="application/json"` to `GenerationConfig` if available in your SDK version, which enables JSON mode.
- The RAG emoji flags (🟢/🟡/🔴) should be tested explicitly — some model versions may substitute alternative unicode or describe the colour in text.

---

### Option C — Local model via Ollama

**Requires:** [Ollama](https://ollama.com) running locally with a suitable model pulled (e.g., `llama3.1:70b`).
**No pip install needed** — uses the standard `requests` library.

```python
import requests
import json
import re
from typing import Tuple

def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,  # Unused for Ollama — no API key required
    max_tokens: int = 4096,
) -> Tuple[dict, str]:
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.1:70b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    "You are processing a broker submission. The content below has been extracted "
                    "from multiple source files (emails, PDFs, Excel spreadsheets, Word documents). "
                    "Read ALL of it carefully before extracting — later sections may correct or "
                    "supplement earlier ones. Reconcile any conflicts as instructed.\n\n"
                    "=== SUBMISSION CONTENT START ===\n\n"
                    + combined_text[:60000]
                    + "\n\n=== SUBMISSION CONTENT END ===\n\n"
                    "Now extract all structured data and return the JSON as specified. "
                    "Return ONLY the JSON object — no markdown fences, no explanation."
                )},
            ],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            },
        },
        timeout=300,  # Local inference can be slow — 5 minute timeout
    )
    response.raise_for_status()

    raw = response.json()["message"]["content"]

    # Same JSON parsing logic as original
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    clean = clean.strip()

    parsed = {}
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
        else:
            parsed = {"extraction_error": "No JSON found in response", "raw_snippet": clean[:500]}

    return parsed, raw
```

**Notes for Ollama:**
- The `api_key` parameter is accepted but not used — Ollama has no authentication by default. Keep it in the signature to maintain the contract.
- Timeout is critical. Local inference on a 70B model can take 60–180 seconds per submission. Set the timeout accordingly.
- JSON output reliability varies significantly by model. Open-weight models are generally less disciplined about following JSON-only instructions than frontier models. Stricter prompting and the fence-stripping fallback become more important.
- Context window depends on the specific model and how Ollama was configured. Check `ollama show llama3.1:70b` for the model's context length. The 60,000 character cap remains the application-level safeguard.
- The `num_predict` option controls maximum output tokens. Naming varies by Ollama version — check the API reference if this key is not recognised.

---

### Provider comparison summary

| Consideration | Claude (current) | GPT-4o | Gemini 1.5 Pro | Ollama (local) |
|---------------|-----------------|--------|----------------|----------------|
| Context window | 200K tokens | 128K tokens | 1M tokens | Model-dependent |
| JSON reliability | High | Very high (JSON mode) | Medium–High | Low–Medium |
| System prompt parameter | `system=` (separate) | `messages[role=system]` | `system_instruction=` (constructor) | `messages[role=system]` |
| Structured output enforcement | Instruction-only | `response_format` JSON mode | `response_mime_type` (SDK-dependent) | Instruction-only |
| API key required | Yes | Yes | Yes | No |
| Cost | ~$0.01–0.05/submission | Comparable | Comparable | Zero (hardware cost only) |
| Latency | 5–20 seconds | 5–20 seconds | 5–30 seconds | 60–180 seconds (70B) |
| RAG emoji support | Confirmed | Confirmed | Test required | Test required |

---

## 11. Multi-Provider Architecture — Future Pattern

If the application needs to support multiple providers selectable at runtime (e.g., for cost comparison or provider resilience), the following pattern extends the current architecture without breaking any existing callers.

**UI change — `ui/pages/analyser.py` sidebar:**

```python
provider = st.selectbox(
    "AI Provider",
    ["Claude (Anthropic)", "GPT-4o (OpenAI)", "Gemini (Google)", "Llama (Local Ollama)"],
)
```

**Refactored `core/extractor.py`:**

```python
def call_claude_extraction(
    combined_text: str,
    system_prompt: str,
    api_key: str,
    max_tokens: int = 4096,
    provider: str = "claude",
) -> Tuple[dict, str]:
    """
    Public entry point — signature is the stable contract.
    provider defaults to "claude" so all existing callers continue to work unchanged.
    """
    if provider == "claude":
        return _call_claude(combined_text, system_prompt, api_key, max_tokens)
    elif provider == "openai":
        return _call_openai(combined_text, system_prompt, api_key, max_tokens)
    elif provider == "gemini":
        return _call_gemini(combined_text, system_prompt, api_key, max_tokens)
    elif provider == "ollama":
        return _call_ollama(combined_text, system_prompt, api_key, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _call_claude(combined_text, system_prompt, api_key, max_tokens):
    # Current implementation
    ...

def _call_openai(combined_text, system_prompt, api_key, max_tokens):
    # OpenAI implementation
    ...

def _call_gemini(combined_text, system_prompt, api_key, max_tokens):
    # Gemini implementation
    ...

def _call_ollama(combined_text, system_prompt, api_key, max_tokens):
    # Ollama implementation
    ...


def _parse_json(raw: str) -> dict:
    """
    Shared JSON parsing logic — call from each provider-specific function.
    """
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {"extraction_error": "JSON parse failed", "raw_snippet": clean[:500]}
```

**Key implementation notes for multi-provider:**
- The `provider` parameter is added with a default value so all existing call sites need no changes.
- `_parse_json()` is extracted as a shared helper to avoid duplicating the parsing logic across four implementations.
- Each provider function returns `(dict, str)` — the same contract as the public function.
- API key management becomes more complex: different providers use different keys. Consider passing a `config: dict` or a dedicated credentials object rather than a single `api_key` string in this scenario.

---

## 12. What Never Changes

Regardless of which AI provider is in use, the following components of the application are completely unaffected:

**Code that never touches the AI layer:**

| File / Module | Role |
|---------------|------|
| `core/analysis.py` | Gap analysis — pure Python comparison |
| `core/outputs.py` | CSV/Excel formatting, `_rag_colour()` parsing |
| `core/report.py` | PDF report generation |
| `core/processor.py` | File parsing and text concatenation |
| `ui/` (all files) | Streamlit UI rendering |
| `skills/` (all files) | System prompts and output schemas |
| `file_parser.py` | Document text extraction |

**Concepts that never change:**

- The function signature `(combined_text, system_prompt, api_key, max_tokens) -> (dict, str)` is the single integration point. Honour it and everything else works.
- The 60,000 character input cap is an application-level decision, not a provider constraint. It applies regardless of provider.
- The system prompt content and structure (the eight sections) are provider-agnostic. The same prompt string is passed to whichever model is in use.
- The JSON parsing and fence-stripping logic is defensive infrastructure. Keep it regardless of provider, even if the provider offers JSON mode — it costs nothing and handles edge cases.
- Gap analysis runs on the returned `dict`. As long as the dict is populated with the correct keys, gap analysis is unaffected by how the dict was produced.
- The `extraction_error` fallback pattern means the application never crashes on a bad LLM response. Preserve this in any replacement implementation.

---

*End of AI Process Documentation*
