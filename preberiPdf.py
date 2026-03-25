import pdfplumber
from pathlib import Path
import shutil
import os
import re
from tkinter import Tk
from tkinter.filedialog import askdirectory

Tk().withdraw()

source_folder = askdirectory(title="Select the folder with PDFs")
if not source_folder:
    print("No folder selected. Exiting...")
    exit()

destination_root = askdirectory(title="Select the folder where sorted PDFs should be placed")
if not destination_root:
    print("No destination folder selected. Exiting...")
    exit()

sizes = ["A0", "A1", "A2", "A3", "A4"]

for file in os.listdir(source_folder):
    if file.lower().endswith(".pdf"):
        file_path = os.path.normpath(os.path.join(source_folder, file))

        try:
            with pdfplumber.open(file_path) as pdf:
                sheet_size = None

                for page in pdf.pages:
                    text = page.extract_text()
                     
                    if not text:
                        continue

                    match = re.search(
                        r"\bA[0-4]\b",
                        text,
                    )

                    if match:
                        print(match)
                        sheet_size = f"A{match.group()}"
                        break
 
            if sheet_size:
                destination_folder = os.path.join(destination_root, sheet_size)
                os.makedirs(destination_folder, exist_ok=True)

                shutil.move(file_path, os.path.join(destination_folder, file))

                print(f"Moved {file} -> {sheet_size}")
            else:
                print(f"No size found in {file}")

        except Exception as e:
            print(f"Error reading {file}: {e}")