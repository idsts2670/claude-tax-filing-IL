"""
Reference template for generating fill_YYYY.py. Copy this, replace PLACEHOLDER values,
fill in computed tax values. NOT meant to be run directly.

HOW TO USE:
  1. Copy this file to output/fill_YEAR.py (e.g. output/fill_2025.py)
  2. Replace all PLACEHOLDER strings with real values from work/computations.txt
  3. Remove comment lines that don't apply (e.g. crypto section if no digital assets)
  4. Run: uv run python output/fill_YEAR.py
  5. Verify output against verify_1040.json and verify_il1040.json (see below)
"""

# ---------------------------------------------------------------------------
# Personal info — replace all PLACEHOLDER values
# ---------------------------------------------------------------------------
FIRST_NAME       = "PLACEHOLDER_FIRST"        # taxpayer first name + middle initial
LAST_NAME        = "PLACEHOLDER_LAST"          # taxpayer last name
SSN              = "PLACEHOLDER_SSN"           # 9 digits, NO dashes (e.g. "123456789")
ADDRESS          = "PLACEHOLDER_ADDRESS"       # street address
CITY_STATE_ZIP   = "PLACEHOLDER_CITY_ST_ZIP"  # city, state ZIP
ROUTING_NUMBER   = "PLACEHOLDER_ROUTING"      # 9-digit ABA routing number
ACCOUNT_NUMBER   = "PLACEHOLDER_ACCOUNT"      # bank account number


# ---------------------------------------------------------------------------
# FILING STATUS REFERENCE — Form 1040 radio button c1_8
# Verified from 2025 Form 1040 PDF AP/N keys:
#
#   "/1" = Single
#   "/2" = Married Filing Jointly
#   "/3" = Married Filing Separately  <- WARNING: NOT Single
#   "/4" = Head of Household
#   "/5" = Qualifying Surviving Spouse
#
# COMMON BUG: guessing /3 for Single is WRONG. Single = /1.
# Always verify against the actual PDF's --compact field dump if uncertain.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DIGITAL ASSETS REFERENCE — Form 1040 radio button c1_10
#
#   "/1" = Yes  <- use if taxpayer had ANY crypto / NFT / digital asset transactions
#   "/2" = No
#
# NOTE: Stock trades (1099-B equity) are NOT digital assets. Only crypto/NFT/
# staking rewards/airdrops count as "digital assets" for this question.
# COMMON BUG: guessing /2 for Yes (or /1 for No) — always use /1=Yes, /2=No.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Form 1040 radio buttons
# Change each value to match the taxpayer's situation using the references above.
# ---------------------------------------------------------------------------
radio_values_1040 = {
    "c1_8":  "/1",      # CHANGE per filing status — see FILING STATUS REFERENCE above
    "c1_10": "/1",      # CHANGE: /1=Yes if crypto/NFT/digital assets, /2=No if none
    "c2_16": "/1",      # CHANGE: /1=checking, /2=savings (direct deposit account type)
}

# ---------------------------------------------------------------------------
# Form 1040 text fields (add_suffix() is applied automatically by fill_irs_pdf)
# Replace values with actual computed line amounts (integers, no commas, no $).
# ---------------------------------------------------------------------------
fields_1040 = {
    # Identification
    "f1_01": FIRST_NAME,
    "f1_02": LAST_NAME,
    "f1_03": SSN,
    "f1_04": ADDRESS,
    "f1_05": CITY_STATE_ZIP,

    # Income lines (replace with computed values from work/computations.txt)
    "f1_25": "PLACEHOLDER_WAGES",           # Line 1a: wages (W-2 Box 1)
    "f1_30": "PLACEHOLDER_TAX_EXEMPT_INT",  # Line 2a: tax-exempt interest
    "f1_31": "PLACEHOLDER_TAXABLE_INT",     # Line 2b: taxable interest
    "f1_33": "PLACEHOLDER_QUAL_DIV",        # Line 3a: qualified dividends
    "f1_34": "PLACEHOLDER_ORD_DIV",         # Line 3b: ordinary dividends
    "f1_39": "PLACEHOLDER_CAP_GAIN",        # Line 7: capital gain or (loss)
    "f1_55": "PLACEHOLDER_AGI",             # Line 11: adjusted gross income
    "f1_68": "PLACEHOLDER_STD_DED",         # Line 12: standard deduction
    "f1_72": "PLACEHOLDER_TAXABLE_INC",     # Line 15: taxable income
    "f1_75": "PLACEHOLDER_TAX",             # Line 16: tax
    "f1_86": "PLACEHOLDER_TOTAL_TAX",       # Line 24: total tax
    "f2_04": "PLACEHOLDER_FED_WITHHOLDING", # Line 25a: federal tax withheld (W-2)
    "f2_10": "PLACEHOLDER_TOTAL_PAYMENTS",  # Line 33: total payments
    "f2_13": "PLACEHOLDER_REFUND",          # Line 35a: refund amount

    # Direct deposit (only when taxpayer has a refund)
    "f2_14": ROUTING_NUMBER,               # Line 35b: routing number
    "f2_16": ACCOUNT_NUMBER,               # Line 35d: account number
}

# ---------------------------------------------------------------------------
# IL-1040 direct deposit — ALL four fields required when taxpayer has a refund
#
# These fields are separate from the IL-1040 text fields because they use
# fill_pdf() (not fill_irs_pdf()) and do NOT use add_suffix().
#
# COMMON BUG: omitting any of these four fields causes the direct deposit
# section to print blank on the return.
# ---------------------------------------------------------------------------
il_direct_deposit_fields = {
    "Routing number": ROUTING_NUMBER,
    "Account number": ACCOUNT_NUMBER,
}
il_direct_deposit_checkboxes = {
    "refund":       "/direct deposit",  # or "/paper check" if mailing a check
    "account_type": "/checking",        # or "/savings"
}

# ---------------------------------------------------------------------------
# IL-1040 text fields (use fill_pdf(), NOT fill_irs_pdf() or add_suffix())
# Field names come from work/il1040_fields.json discovered via --compact.
# ---------------------------------------------------------------------------
fields_il1040 = {
    # Identification — field names vary by year; always verify from --compact dump
    "Your SSN":        SSN,
    "First Name":      FIRST_NAME,
    "Last Name":       LAST_NAME,
    "Address":         ADDRESS,
    "City":            CITY_STATE_ZIP,

    # Income / tax lines (replace with computed values)
    "Step 2 - Line 1": "PLACEHOLDER_FED_AGI",         # Federal AGI
    "Step 2 - Line 11":"PLACEHOLDER_IL_BASE_INCOME",   # IL base income
    "Step 3 - Line 17":"PLACEHOLDER_IL_NET_INCOME",    # IL net income
    "Step 3 - Line 18":"PLACEHOLDER_IL_TAX",           # IL income tax (4.95%)
    "Step 3 - Line 24":"PLACEHOLDER_IL_NET_TAX",       # IL net income tax after credits

    # Payments
    "Step 4 - Line 29":"PLACEHOLDER_IL_WITHHOLDING",   # IL withholding (W-2 Box 17)

    # Refund / balance due
    "Refunded to you": "PLACEHOLDER_IL_REFUND",        # Line 36 refund amount
}

# ---------------------------------------------------------------------------
# IL-1040 filing status radio (field name varies by year; verify from --compact)
# Common values: "/single", "/married_filing_jointly", "/married_filing_separately"
# ---------------------------------------------------------------------------
il_radio_values = {
    "filing_status": "/single",  # CHANGE to match taxpayer's actual status
}

# ---------------------------------------------------------------------------
# Example fill calls (pseudocode — adapt to actual script imports)
# ---------------------------------------------------------------------------
# from scripts.fill_forms import add_suffix, fill_irs_pdf, fill_pdf
#
# # Form 1040
# fill_irs_pdf(
#     "forms/f1040_blank.pdf",
#     "output/f1040_filled.pdf",
#     fields=add_suffix(fields_1040),
#     checkboxes={},
#     radio_values=radio_values_1040,
# )
#
# # IL-1040 (note: fill_pdf, no add_suffix)
# all_il_fields = {**fields_il1040, **il_direct_deposit_fields}
# all_il_radios = {**il_radio_values, **il_direct_deposit_checkboxes}
# fill_pdf(
#     "forms/il1040_blank.pdf",
#     "output/il1040_filled.pdf",
#     fields=all_il_fields,
#     checkboxes=all_il_radios,
# )

# ---------------------------------------------------------------------------
# After generating filled PDFs — mandatory verification
# ---------------------------------------------------------------------------
# uv run python skills/tax-filing/scripts/verify_filled.py \
#     ../YYYY-source/outputs/f1040_filled.pdf \
#     skills/tax-filing/scripts/verify_1040.json
#
# uv run python skills/tax-filing/scripts/verify_filled.py \
#     ../YYYY-source/outputs/il1040_filled.pdf \
#     skills/tax-filing/scripts/verify_il1040.json
#
# Fix any MISMATCH or MISSING before presenting results to the user.
