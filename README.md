# Jure_PDF_size_sorter
Simple Python script that goes thru a specific directory, scans the pdf files that it contains and sorts them in their respected directories.

This script scans a folder of PDFs and sorts them by sheet size (A0–A4).

## Requirements
- Python 3
- pdfplumber

Install dependencies:

pip install -r requirements.txt

## Usage

1. Put PDFs in the input folder
2. Edit paths in sort_pdfs.py
3. Run:

python sort_pdfs.py

The script will create folders (A0, A1, A2, A3, A4) and move files accordingly.
