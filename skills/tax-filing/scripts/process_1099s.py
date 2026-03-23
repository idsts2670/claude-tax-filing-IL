#!/usr/bin/env python3
"""
Process 1099 forms (1099-B, 1099-DIV, 1099-INT) for tax filing.
Extracts key data and categorizes transactions for Form 8949 and Schedule B.

Usage with uv:
    uv run python scripts/process_1099s.py 2025-source/ --output work/1099_summary.json --verbose
"""

import sys
import json
import argparse
from pathlib import Path
import re

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not found. Install with: uv add pdfplumber pypdf pymupdf")
    sys.exit(1)


def extract_1099_int(pdf_path):
    """Extract data from 1099-INT form."""
    data = {
        'form_type': '1099-INT',
        'payer_name': '',
        'payer_tin': '',
        'recipient_name': '',
        'recipient_ssn': '',
        'taxable_interest': 0.0,  # Box 1
        'tax_exempt_interest': 0.0,  # Box 8
        'federal_tax_withheld': 0.0,  # Box 4
        'state_tax_withheld': 0.0,  # Box 17
        'state': ''
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    # Extract key fields using regex patterns
    patterns = {
        'taxable_interest': r'Box\s*1[^\d]*(\d+\.?\d*)',
        'tax_exempt_interest': r'Box\s*8[^\d]*(\d+\.?\d*)',
        'federal_tax_withheld': r'Box\s*4[^\d]*(\d+\.?\d*)',
        'state_tax_withheld': r'Box\s*17[^\d]*(\d+\.?\d*)'
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                data[field] = float(match.group(1))
            except ValueError:
                pass
    
    return data


def extract_1099_div(pdf_path):
    """Extract data from 1099-DIV form."""
    data = {
        'form_type': '1099-DIV',
        'payer_name': '',
        'payer_tin': '',
        'recipient_name': '',
        'recipient_ssn': '',
        'total_ordinary_dividends': 0.0,  # Box 1a
        'qualified_dividends': 0.0,  # Box 1b
        'capital_gain_distributions': 0.0,  # Box 2a
        'foreign_tax_paid': 0.0,  # Box 7
        'federal_tax_withheld': 0.0,  # Box 4
        'state_tax_withheld': 0.0,  # Box 16
        'state': ''
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    patterns = {
        'total_ordinary_dividends': r'Box\s*1a[^\d]*(\d+\.?\d*)',
        'qualified_dividends': r'Box\s*1b[^\d]*(\d+\.?\d*)',
        'capital_gain_distributions': r'Box\s*2a[^\d]*(\d+\.?\d*)',
        'foreign_tax_paid': r'Box\s*7[^\d]*(\d+\.?\d*)',
        'federal_tax_withheld': r'Box\s*4[^\d]*(\d+\.?\d*)',
        'state_tax_withheld': r'Box\s*16[^\d]*(\d+\.?\d*)'
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                data[field] = float(match.group(1))
            except ValueError:
                pass
    
    return data


def extract_1099_b(pdf_path):
    """Extract data from 1099-B form."""
    data = {
        'form_type': '1099-B',
        'payer_name': '',
        'payer_tin': '',
        'recipient_name': '',
        'recipient_ssn': '',
        'transactions': []
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    # For 1099-B, we need to extract individual transactions
    # This is a simplified version - real implementation would need more sophisticated parsing
    transaction = {
        'description': '',  # Box 1a
        'date_acquired': '',  # Box 1b
        'date_sold': '',  # Box 1c
        'proceeds': 0.0,  # Box 1d
        'cost_basis': 0.0,  # Box 1e
        'wash_sale_loss': 0.0,  # Box 1g
        'form_8949_code': '',  # Applicable checkbox (A, B, D, E)
        'short_term': None  # True/False when detectable from PDF text
    }

    # Form 8949 checkbox (brokers often say "Box A", "Part II, Box D", etc.)
    code_match = re.search(
        r'(?i)(?:form\s*8949|part\s*[ivx]+).*?box\s*([abde])\b',
        text,
    ) or re.search(r'(?i)box\s*([abde])\b(?:\s*checked)?', text)
    if code_match:
        transaction['form_8949_code'] = code_match.group(1).upper()

    if re.search(r'(?i)long[\s-]term', text):
        transaction['short_term'] = False
    elif re.search(r'(?i)short[\s-]term', text):
        transaction['short_term'] = True

    # Extract basic transaction data
    patterns = {
        'proceeds': r'Box\s*1d[^\d]*(\d+\.?\d*)',
        'cost_basis': r'Box\s*1e[^\d]*(\d+\.?\d*)',
        'wash_sale_loss': r'Box\s*1g[^\d]*(\d+\.?\d*)'
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                transaction[field] = float(match.group(1))
            except ValueError:
                pass

    data['transactions'].append(transaction)
    return data


def categorize_8949_transactions(transactions):
    """Categorize 1099-B transactions for Form 8949 using explicit checkbox codes only.

    If the PDF text does not include a reliable Box A/B/D/E indicator, transactions
    are placed in ``uncategorized`` for manual review (heuristics are error-prone).
    """
    categories = {
        'box_a': [],
        'box_b': [],
        'box_d': [],
        'box_e': [],
        'uncategorized': [],
    }

    for txn in transactions:
        code = (txn.get('form_8949_code') or '').strip().upper()
        if code == 'A':
            categories['box_a'].append(txn)
        elif code == 'B':
            categories['box_b'].append(txn)
        elif code == 'D':
            categories['box_d'].append(txn)
        elif code == 'E':
            categories['box_e'].append(txn)
        else:
            categories['uncategorized'].append(txn)

    return categories


def check_schedule_b_required(interest_total, dividend_total):
    """Check if Schedule B is required (combined interest or dividends > $1,500)."""
    return interest_total > 1500 or dividend_total > 1500


def main():
    parser = argparse.ArgumentParser(description='Process 1099 forms for tax filing')
    parser.add_argument('input_dir', help='Directory containing 1099 PDF files (e.g., 2025-source/inputs/)')
    parser.add_argument('--output', '-o', default='1099_summary.json', help='Output JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"Error: Input directory {input_path} does not exist")
        sys.exit(1)
    
    results = {
        'forms_processed': [],
        'schedule_b_required': False,
        'form_8949_categories': {
            'box_a': [],
            'box_b': [],
            'box_d': [],
            'box_e': [],
            'uncategorized': [],
        },
        'totals': {
            'total_interest': 0.0,
            'total_dividends': 0.0,
            'tax_exempt_interest': 0.0,
            'qualified_dividends': 0.0,
            'capital_gain_distributions': 0.0,
            'federal_withholding': 0.0,
            'state_withholding': 0.0
        }
    }
    
    # Process all PDF files in the input directory
    for pdf_file in input_path.glob('*.pdf'):
        if args.verbose:
            print(f"Processing {pdf_file.name}...")
        
        # Determine form type based on filename or content
        filename_lower = pdf_file.name.lower()
        
        try:
            if '1099-int' in filename_lower or '1099int' in filename_lower:
                data = extract_1099_int(pdf_file)
                results['forms_processed'].append(data)
                results['totals']['total_interest'] += data['taxable_interest']
                results['totals']['tax_exempt_interest'] += data['tax_exempt_interest']
                results['totals']['federal_withholding'] += data['federal_tax_withheld']
                results['totals']['state_withholding'] += data['state_tax_withheld']
                
            elif '1099-div' in filename_lower or '1099div' in filename_lower:
                data = extract_1099_div(pdf_file)
                results['forms_processed'].append(data)
                results['totals']['total_dividends'] += data['total_ordinary_dividends']
                results['totals']['qualified_dividends'] += data['qualified_dividends']
                results['totals']['capital_gain_distributions'] += data['capital_gain_distributions']
                results['totals']['federal_withholding'] += data['federal_tax_withheld']
                results['totals']['state_withholding'] += data['state_tax_withheld']
                
            elif '1099-b' in filename_lower or '1099b' in filename_lower:
                data = extract_1099_b(pdf_file)
                results['forms_processed'].append(data)
                
                # Categorize transactions for Form 8949
                categories = categorize_8949_transactions(data['transactions'])
                for category, transactions in categories.items():
                    results['form_8949_categories'][category].extend(transactions)
                    
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            continue
    
    # Check if Schedule B is required
    results['schedule_b_required'] = check_schedule_b_required(
        results['totals']['total_interest'],
        results['totals']['total_dividends']
    )
    
    # Write results to JSON file
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    if args.verbose:
        print(f"\nProcessing complete. Results saved to {args.output}")
        print(f"Schedule B required: {results['schedule_b_required']}")
        print(f"Total interest: ${results['totals']['total_interest']:,.2f}")
        print(f"Total dividends: ${results['totals']['total_dividends']:,.2f}")
        print(f"Forms processed: {len(results['forms_processed'])}")


if __name__ == '__main__':
    main()