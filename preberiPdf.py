import pdfplumber
from pathlib import Path
import shutil
import os
import re
from tkinter import Tk
from tkinter.filedialog import askdirectory

# Hide the root Tkinter window
Tk().withdraw()

# Ask user for the source folder
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
        file_path = os.path.normpath(os.path.join(source_folder, file))  # <- FIXED

        try:
            with pdfplumber.open(file_path) as pdf:
                text = pdf.pages[0].extract_text()

            if text:
                for size in sizes:
                    if re.search(rf"\b{size}\b", text):
                        destination_folder = os.path.join(destination_root, size)
                        os.makedirs(destination_folder, exist_ok=True)
                        shutil.move(file_path, os.path.join(destination_folder, file))
                        print(f"Moved {file} -> {size}")
                        break
        except Exception as e:
            print(f"Error reading {file}: {e}")