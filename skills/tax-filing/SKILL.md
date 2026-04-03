---
name: tax-filing
description: Prepare and fill federal and state tax return PDF forms
user_invocable: true
triggers:
  - do my taxes
  - prepare tax return
  - fill tax forms
  - file taxes
  - tax preparation
---

# Tax Filing Skill

Prepare federal and state income tax returns: read source documents, compute taxes, fill official PDF forms.

**Year-agnostic** — always look up current-year brackets, deductions, and credits. Never reuse prior-year values.

## Folder Structure

Organize all work into subfolders of the working directory:

```
working_dir/
  YYYY-source/         ← source document folder
    inputs/            ← user's source documents (W-2, 1099s, prior return, CSVs)
  work/                ← ALL intermediate files (extracted data, field maps, computations)
    tax_data.txt       ← extracted figures from source docs
    computations.txt   ← all tax math (federal, state, capital gains)
    1099_summary.json  ← processed 1099 data and categorization
    f1040_fields.json  ← field discovery dumps
    f8949_fields.json
    f1040sd_fields.json
    scheduleb_fields.json ← Schedule B field mappings
    il1040_fields.json
    il_wit_fields.json ← Schedule IL-WIT field mappings
    expected_*.json    ← verification expected values
  forms/               ← blank downloaded PDF forms
    f1040_blank.pdf
    f8949_blank.pdf
    f1040sd_blank.pdf
    scheduleb_blank.pdf
    il1040_blank.pdf
    il_wit_blank.pdf
  output/              ← final filled PDFs + fill script
    fill_YEAR.py       ← the fill script
    f1040_filled.pdf
    f8949_filled.pdf
    f1040sd_filled.pdf
    scheduleb_filled.pdf
    il1040_filled.pdf
    il_wit_filled.pdf
```

Create these folders at the start. Keep the working directory clean — no loose files.

**Important:** Replace `YYYY` with the actual tax year (e.g., `2025-source` for 2025 tax year). This prevents confusion between different tax years and keeps documents organized chronologically.

## Environment Setup

**Use `uv` for Python environment management** — it's 10-100x faster than pip and keeps your system Python clean.

**Install uv (if not already installed):**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Initialize project environment:**
```bash
# Option 1: Use existing pyproject.toml (recommended)
uv sync

# Option 2: Manual setup
uv venv tax-env
source tax-env/bin/activate  # On Windows: tax-env\Scripts\activate
uv add pdfplumber pypdf pymupdf

# Verify installation
uv run python -c "import pdfplumber, pypdf, fitz; print('All dependencies installed successfully')"
```

**All Python commands in this skill use `uv run` for automatic environment management.**

**Working directory for script paths:**
- **Claude skill root** (`skills/tax-filing/`): use `scripts/…` as shown below.
- **Repository root** (after `git clone`, where `pyproject.toml` lives): prefix paths with `skills/tax-filing/`, e.g. `uv run python skills/tax-filing/scripts/process_1099s.py …`.

**Quick Start:**
```bash
# 1. Initialize environment (from repository root)
uv sync

# 2. Create working directories  
mkdir -p 2025-source/inputs work forms output

# 3. Place your tax documents in 2025-source/inputs/
# 4. Run: "Do my taxes using this skill"
```

## Context Budget Rules

These rules prevent context blowouts that cause compaction:

1. **NEVER read PDFs with the Read tool.** Each page becomes ~250KB of base64 images (a 9-page return = 1.8 MB). Extract text instead:
   ```bash
   uv run python -c "
   import pdfplumber
   with pdfplumber.open('2025-source/inputs/document.pdf') as pdf:
       for p in pdf.pages: print(p.extract_text())
   "
   ```
2. **NEVER read the same document twice.** Save extracted figures to `work/tax_data.txt` on first read.
3. **Run field discovery ONCE per form** as a bulk JSON dump to `work/`. Do NOT use `--search` repeatedly.
4. **Save all computed values to `work/computations.txt`** so they survive compaction.

## Workflow

### Step 1: Gather Source Documents

Ask the user what documents they have. Read files from `YYYY-source/inputs/` (move them there if needed). Use pdfplumber for PDFs, Read tool for CSVs.

**Investment Document Processing:**
For 1099-B, 1099-DIV, and 1099-INT forms, extract the following data systematically:

**1099-INT (Interest Income):**
- Box 1: Taxable interest → Schedule B Part I + Form 1040 Line 2b
- Box 8: Tax-exempt interest → Form 1040 Line 2a (informational only)
- Box 4: Federal tax withheld → Form 1040 Line 25b
- Box 17: State tax withheld → IL Schedule IL-WIT (if applicable)

**1099-DIV (Dividends):**
- Box 1a: Total ordinary dividends → Schedule B Part II + Form 1040 Line 3b
- Box 1b: Qualified dividends → Form 1040 Line 3a (preferential tax rates)
- Box 2a: Capital gain distributions → Schedule D Line 13
- Box 7: Foreign tax paid → Form 1116 (if >$300 or election made)
- Box 16: State tax withheld → IL Schedule IL-WIT (if applicable)

**1099-B (Broker Transactions):**
- Box 1a: Description of property
- Box 1b: Date acquired
- Box 1c: Date sold
- Box 1d: Proceeds (gross sales price)
- Box 1e: Cost basis (if reported to IRS)
- Box 2: Gain/loss classification (short-term vs long-term)
- Applicable checkbox: Determines Form 8949 category (A, B, D, or E)

Save all extracted figures to `work/tax_data.txt` immediately — one section per document with every relevant number.

### Step 2: Confirm Filing Details — MANDATORY

**You MUST ask the user every one of these questions and WAIT for answers before proceeding.** Do NOT skip this step even if you think you know the answers from memory or source documents. Tax returns are legal documents.

- Filing status (Single, MFJ, MFS, HOH, QSS)
- Dependents (number, names)
- State of residence
- Standard vs. itemized deduction preference
- Digital asset / cryptocurrency transactions (Yes/No) — stock trades are NOT digital assets
- Full-year Illinois resident? (Yes/No — determines if IL-1040 is required)
- Any Illinois additions to income? (e.g., state tax refund deducted federally, tax-exempt interest excluded federally)
- Any Illinois subtractions? (e.g., retirement income, U.S. government obligation interest, Social Security)
- Any Illinois estimated tax payments made (IL-1040-ES)?
- Any other credits or adjustments (e.g., Illinois Property Tax Credit, Education Expense Credit)
- **If W-2 Box 12W (HSA) is present and exceeds the annual limit:** Was the excess contribution returned by the HSA custodian before April 15? If yes, obtain and review the custodian's distribution statement (letter, check stub, or account record) to confirm (a) the withdrawal actually completed, (b) the exact amount returned, and (c) the date. The amount returned will typically exceed the calculated excess because the custodian also returns earnings — note the earnings separately (they are income on the *following* year's return, not the current year).

**Do NOT proceed to Step 3 until the user has answered.** "Same as last year" counts as confirmation.

### Step 3: Look Up Year-Specific Values

Research from IRS.gov and tax.illinois.gov:
- Federal tax brackets, standard deduction, QDCG 0%/15%/20% thresholds
- Illinois flat tax rate (currently 4.95% — verify current year at tax.illinois.gov)
- Illinois personal exemption allowance for the filing status (e.g., $2,425 single — always look up; changes annually)
- Illinois Schedule M additions/subtractions that apply to the taxpayer's situation

**Standard deduction — verify from the actual Form 1040 PDF, not from memory or IRS Rev. Proc. alone.** Open the blank `f1040_blank.pdf` (once downloaded in Step 7) and read the field tooltip for the standard deduction line. The tooltip shows the exact dollar amount printed on the form for that year. Rev. Proc. values can differ from the final printed form; the form controls.

Save to `work/computations.txt`.

### Rounding Rule — Apply Everywhere

**IRS and Illinois both require whole-dollar rounding on all return line values:**
- Drop cents below $0.50 (e.g., $75,531.32 → $75,531)
- Round up at $0.50 or higher (e.g., $26.50 → $27)

Apply this rule to **every** number entered on Form 1040, Schedule D, Form 8949 totals, Schedule 3, and IL-1040 — including income, deductions, tax, payments, and refund/owed amounts. Source document figures (W-2, 1099) are extracted at full precision for intermediate math; round only the **final** value written to each form line.

### Step 4: Compute Federal Return

**4A: Process Investment Income Forms**

**Schedule B (Interest and Dividends) — Required if combined interest OR dividends >$1,500:**
1. **Part I (Interest):** List each 1099-INT payer and Box 1 amount
   - Total → Form 1040 Line 2b
   - Tax-exempt interest (Box 8) → Form 1040 Line 2a
2. **Part II (Dividends):** List each 1099-DIV payer and Box 1a amount
   - Total ordinary dividends → Form 1040 Line 3b
   - Qualified dividends (Box 1b) → Form 1040 Line 3a

**4B: Process Brokerage Transactions (1099-B)**

**Form 8949 Categories (sort all transactions):**
- **Box A:** Short-term, basis reported to IRS (Code A on 1099-B)
- **Box B:** Short-term, basis NOT reported to IRS (Code B on 1099-B)  
- **Box D:** Long-term, basis reported to IRS (Code D on 1099-B)
- **Box E:** Long-term, basis NOT reported to IRS (Code E on 1099-B)

**For 10+ transactions:** Use substitute statement method — attach broker's detailed 1099-B summary instead of listing each trade. Write "See attached statement" on Form 8949 and enter only column totals.

**Schedule D:** Carry Form 8949 totals to Schedule D, apply $3,000 loss limitation, calculate carryovers.

**4C: Main Form 1040 Assembly**

1. Gross Income: W-2 wages (1a) + interest (2b) + dividends (3b) + capital gain/loss (7)
2. Adjustments → AGI (Line 11)
3. Deductions → Taxable Income (Line 15)
4. Tax: use QDCG worksheet if qualified dividends/capital gains exist
5. Credits, other taxes → Total Tax (Line 24)
6. Payments (withholding, estimated) → Refund/Owed
7. If refund: collect direct deposit info (routing, account, type)

Save all line values to `work/computations.txt`.

### Step 5: Compute Capital Gains (if applicable)

1. Form 8949: individual transactions (Part I short-term, Part II long-term)
2. Schedule D: totals, $3,000 loss limitation, carryover calculation
3. Net gain/loss → 1040 Line 7

### Step 6: Compute State Return (IL Form IL-1040)

Illinois taxes full-year residents on worldwide income at a **flat rate** — no brackets.

**6A: Process Investment Income for Illinois**

**Key Illinois Rules:**
- **Interest & Dividends:** Already included in Federal AGI, automatically flows to IL-1040 Line 1
- **Capital Gains:** Taxed as ordinary income at 4.95% flat rate (no preferential treatment)
- **Tax-Exempt Interest:** Federally tax-exempt interest (Form 1040 Line 2a) must be ADDED BACK on IL-1040 Line 2
- **US Treasury Interest:** Must be SUBTRACTED on Schedule M (Illinois does not tax federal obligations)

**6B: Illinois Withholding (Schedule IL-WIT)**
Only complete if any 1099 forms show Illinois withholding (Box 16/17). For each form with IL withholding:
- Form type code (W=W-2, A=1099-B, B=1099-DIV, C=1099-INT, etc.)
- Payer TIN
- Federal amount
- Illinois amount  
- Illinois tax withheld

**6C: Main IL-1040 Calculation**

1. **IL base income** (IL-1040 Line 11)
   - Start: Federal AGI (IL-1040 Line 1)
   - + IL additions (Lines 2–5): federally deducted IL tax refunds, non-IL tax-exempt bond interest, lump-sum distributions, etc. Use Schedule M if any additions apply.
   - − IL subtractions (Lines 6–9): retirement/pension income exclusions, U.S. government obligation interest, Social Security (if included in AGI), military pay, etc. Use Schedule M if any subtractions apply.
   - For a W-2-only filer with no adjustments, IL base income = Federal AGI.

2. **IL exemption allowance** (IL-1040 Lines 12–15)
   - Personal exemption for filing status (look up current-year amount — e.g., $2,425 single for 2025)
   - + $1,000 for each dependent claimed on federal return
   - + Age 65 / blindness additions if applicable

3. **IL net income** (IL-1040 Line 17) = IL base income − total exemption allowance
   - If Line 17 ≤ $0, Illinois tax is $0. Stop here.

4. **IL income tax** (IL-1040 Line 18) = IL net income × 4.95%
   - Always verify the current flat rate at tax.illinois.gov before computing.

5. **Credits** (IL-1040 Lines 19–23)
   - Illinois Earned Income Credit: 20% of federal EITC (if eligible)
   - Illinois Property Tax Credit: 5% of IL property taxes paid (if homeowner/renter with Certificate of Rent Paid)
   - Education Expense Credit (K-12): up to $750 (if applicable)
   - Pass-through entity credit (if applicable)

6. **Net IL income tax** (Line 24) = Line 18 − credits

7. **Payments** (Lines 29–34)
   - IL withholding from W-2 Box 17 (state income tax withheld)
   - Any IL-1040-ES estimated payments made during the year

8. **Refund or balance due** (Lines 36–43)
   - Refund = payments − total tax (Line 28)
   - Balance due = total tax − payments

Save all line values to `work/computations.txt`.

### Step 6A: Process 1099 Forms (Investment Income)

**Automated 1099 Processing:**
```bash
uv run python scripts/process_1099s.py 2025-source/inputs/ --output work/1099_summary.json --verbose
```
*Replace `2025` with the actual tax year being processed.*

This script will:
- Extract data from all 1099-INT, 1099-DIV, and 1099-B forms in `YYYY-source/inputs/`
- Determine if Schedule B is required (interest or dividends >$1,500)
- Categorize 1099-B transactions for Form 8949 when Box A/B/D/E appears clearly in extracted text; otherwise lists them under `uncategorized` for manual assignment
- Calculate totals for federal and state withholding
- Generate `work/1099_summary.json` with all extracted data

**Manual Verification Steps:**
1. Review `work/1099_summary.json` for accuracy
2. Confirm Schedule B requirement with user
3. Resolve any `form_8949_categories.uncategorized` entries against the broker PDF or substitute statement
4. For 10+ brokerage transactions, ask user if they prefer substitute statement method
5. Verify Illinois withholding amounts for Schedule IL-WIT

### Step 7: Download Blank PDF Forms

Save to `forms/` directory.

**IRS**: Use `/irs-prior/` for prior-year forms (`/irs-pdf/` is always current year):
```
https://www.irs.gov/pub/irs-prior/f1040--YEAR.pdf
https://www.irs.gov/pub/irs-prior/f8949--YEAR.pdf
https://www.irs.gov/pub/irs-prior/f1040sd--YEAR.pdf
https://www.irs.gov/pub/irs-prior/f1040sb--YEAR.pdf
```

**IL**: Navigate to `https://tax.illinois.gov/forms/incometax/currentyear/individual.html` to find the current-year IL-1040 PDF. Download the fillable version:
```
https://tax.illinois.gov/content/dam/soi/en/web/tax/forms/incometax/docs/currentyear/individual/il-1040.pdf
```
If that URL 404s (path changes yearly), fetch the forms index page and find the direct PDF link.
Also download **Schedule M** if the taxpayer has any IL additions or subtractions:
```
https://tax.illinois.gov/content/dam/soi/en/web/tax/forms/incometax/docs/currentyear/individual/il-1040-schedulem.pdf
```

Download **Schedule IL-WIT** if the taxpayer has Illinois withholding from 1099 forms:
```
https://tax.illinois.gov/content/dam/soi/en/web/tax/forms/incometax/docs/currentyear/individual/il-1040-schedule-il-wit.pdf
```

Verify each download has `%PDF-` header (not an HTML error page).

### Step 8: Discover Field Names & Fill Forms

#### Discovery — ONCE per form, use `--compact`

```bash
uv run python scripts/discover_fields.py forms/f1040_blank.pdf --compact > work/f1040_fields.json
uv run python scripts/discover_fields.py forms/f8949_blank.pdf --compact > work/f8949_fields.json
uv run python scripts/discover_fields.py forms/f1040sd_blank.pdf --compact > work/f1040sd_fields.json
uv run python scripts/discover_fields.py forms/f1040sb_blank.pdf --compact > work/scheduleb_fields.json
uv run python scripts/discover_fields.py forms/il1040_blank.pdf --compact > work/il1040_fields.json
uv run python scripts/discover_fields.py forms/il_wit_blank.pdf --compact > work/il_wit_fields.json
```

`--compact` outputs a minimal `{field_name: description}` mapping — each field name is paired with its tooltip/speak description so you can map line numbers to field names directly without manual inspection. Radio buttons include their option values (e.g. `{"/2": "Single", "/1": "MFJ"}`).

Do NOT use `--search` repeatedly or `--json` (which dumps raw metadata and wastes context).

**HARD FAIL**: If discovery returns 0 human-readable descriptions, STOP. Do not guess field names.

#### Fill Script

Write `output/fill_YEAR.py` using `scripts/fill_forms.py`:

- **`add_suffix(d)`** — appends `[0]` to text field keys. Required for IRS forms.
- **`fill_irs_pdf(in, out, fields, checkboxes, radio_values)`** — IRS forms. `radio_values` for filing status, yes/no, checking/savings.
- **`fill_pdf(in, out, fields, checkboxes)`** — IL-1040 and other state forms. Matches by `/Parent` chain + `/AP/N` keys. IL-1040 is a standard AcroForm (not XFA) — do NOT use `add_suffix()` or `fill_irs_pdf()` for IL forms.

Output filled PDFs to `output/`.

**After generating filled PDFs — mandatory verification:**
```bash
uv run python skills/tax-filing/scripts/verify_filled.py ../YYYY-source/outputs/f1040_filled.pdf skills/tax-filing/scripts/verify_1040.json
uv run python skills/tax-filing/scripts/verify_filled.py ../YYYY-source/outputs/il1040_filled.pdf skills/tax-filing/scripts/verify_il1040.json
```
Fix any MISMATCH or MISSING before presenting results to the user.

### Step 9: Verify

```bash
uv run python scripts/verify_filled.py output/f1040_filled.pdf work/expected_f1040.json
```

Fix any failures, re-run fill script.

### Step 10: Present Results

Show a summary table, verification checklist, capital loss carryover (if any), then:

- **Sign your returns** — unsigned returns are rejected
- **Payment instructions** (if owed):
  - Federal: IRS Direct Pay at irs.gov/payments — deadline April 15
  - Illinois: MyTax Illinois at mytax.illinois.gov → "Make a Payment" — deadline April 15
  - IL mail: check payable to "Illinois Department of Revenue", include IL-1040-V payment voucher
- **Direct deposit** — recommend it for both refunds; ask for bank routing + account number
- **Filing options**:
  - Federal: IRS Free File (free at irs.gov/freefile) or mail to IRS address on 1040 instructions
  - Illinois: MyTax Illinois (free e-file at mytax.illinois.gov — no login required) or mail IL-1040 to:
    - Refund/zero balance: Illinois Department of Revenue, P.O. Box 19041, Springfield IL 62794-9041
    - Balance due: Illinois Department of Revenue, P.O. Box 19027, Springfield IL 62794-9027

## Key Gotchas

### Context
- NEVER use Read tool on PDFs — use pdfplumber
- NEVER read same document twice — save to `work/tax_data.txt`
- Field discovery once per form with `--compact` — no `--json` (wastes context), no repeated `--search`

### Field Discovery
- Field names change between years — always discover fresh
- XFA template is in `/AcroForm` → `/XFA` array, NOT from brute-force xref scanning
- Do NOT use `xml.etree` for XFA — use regex (IRS XML has broken namespaces)

### PDF Filling
- Remove XFA from AcroForm, set NeedAppearances=True, use auto_regenerate=False
- Checkboxes: set both `/V` and `/AS` to `/1` or `/Off`
- IRS fields need `[0]` suffix — use `add_suffix()`
- IRS checkboxes match by `/T` directly; radio groups match by `/AP/N` key via `radio_values`

### HSA Excess Contributions (W-2 Box 12W)

If Box 12W exceeds the annual HSA limit (self-only or family — look up each year):

| Situation | Income inclusion | 6% excise (Form 5329) | Earnings |
|-----------|-----------------|----------------------|----------|
| Excess NOT withdrawn by deadline | Include excess on Schedule 1 / Line 8 | Yes | N/A |
| Excess withdrawn by April 15 (timely) | **No income inclusion** | **No** | Report on *next* year's return |

- Timely withdrawal = returned by the due date of the return (April 15, or October 15 if extended).
- The custodian returns the excess **plus earnings**. The excess itself drops out of income; the earnings go on the following year's return as Other Income.
- Always obtain custodian documentation before applying the timely-withdrawal treatment. The check/statement amount will exceed your calculated excess by the earnings; record both figures separately.
- Do NOT assume a timely withdrawal occurred based on the taxpayer's recollection alone — require documentary proof (custodian letter, check stub, or account transaction record).

### Fill Script Generation
When generating `fill_YYYY.py`, always reference `skills/tax-filing/scripts/fill_template.py` for correct radio button AP/N values. Never guess these values. Key rules:
- Form 1040 filing status (`c1_8`): `/1`=Single, `/2`=MFJ, `/3`=MFS, `/4`=HOH, `/5`=QSS
- Form 1040 digital assets (`c1_10`): `/1`=Yes, `/2`=No
- IL-1040 direct deposit: always include all four fields (`Routing number`, `Account number`, `refund` radio, `account_type` radio) when the taxpayer has a refund
- **All string values passed to PDF fields must be whole-dollar amounts** (no cents). Apply the IRS rounding rule before writing any value: drop cents below $0.50, round up at $0.50 or higher. Example: `"75531"` not `"75531.32"`; `"27"` not `"26.50"`.

### Form-Specific
- **1040**: First few fields (`f1_01`-`f1_03`) are fiscal year headers, not name fields. SSN = 9 digits, no dashes. Digital assets = crypto only, not stocks.
- **8949**: Box A/B/C checkboxes are 3-way radio buttons. Totals at high field numbers (e.g. `f1_115`-`f1_119`), not after last data row. Schedule D lines 1b/8b (from 8949), not 1a/8a.
- **Schedule D**: Some fields have `_RO` suffix (read-only) — skip those.
- **IL-1040**: Standard AcroForm — use `fill_pdf()`, NOT `fill_irs_pdf()` or `add_suffix()`. Field names discovered via `--compact` will match IL line numbers. IL-1040 PDF URLs change every year; always navigate the IDOR forms index page to find the current fillable PDF rather than hardcoding the URL. If Schedule M is needed (any additions/subtractions), download and fill it separately, then carry totals back to IL-1040 Lines 4 and 9.
- **Downloads**: Prior-year IRS = `irs.gov/pub/irs-prior/`, current = `irs.gov/pub/irs-pdf/`
