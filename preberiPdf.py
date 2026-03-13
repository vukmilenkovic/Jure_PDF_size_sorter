import pdfplumber
import os
import shutil
import re

source_folder = r"C:\Users\vukmi\Downloads\Jure_pdfi\VSI_PDFJI"
destination_root = r"C:\Users\vukmi\Downloads\Jure_pdfi"

sizes = ["A0", "A1", "A2", "A3", "A4"]

for file in os.listdir(source_folder):
    if file.lower().endswith(".pdf"):
        file_path = os.path.join(source_folder, file)

        try:
            with pdfplumber.open(file_path) as pdf:
                text = pdf.pages[0].extract_text()

            if text:
                for size in sizes:
                    if re.search(rf"\b{size}\b", text):
                        destination_folder = os.path.join(destination_root, size)

                        os.makedirs(destination_folder, exist_ok = True)

                        shutil.move(file_path, os.path.join(destination_folder, file))

                        print(f"Moved {file} -> {size}")
                        break
        except Exception as e:
            print(f"Error reading {file}: {e}")