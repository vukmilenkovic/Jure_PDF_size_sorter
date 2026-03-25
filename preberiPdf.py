import pdfplumber
import shutil
import os
import re
import sys

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QTextEdit
)


class PDFSorterApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF bralec")
        self.setGeometry(200, 200, 500, 400)

        self.source_folder = ""
        self.destination_folder = ""

        layout = QVBoxLayout()

        self.source_label = QLabel("Izvorna mapa: ni izbrana")
        self.dest_label = QLabel("Ciljna mapa: ni izbrana")

        self.source_btn = QPushButton("Izberi izvorno mapo")
        self.dest_btn = QPushButton("Izberi ciljno mapo")
        self.start_btn = QPushButton("Začni sortiranje")

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout.addWidget(self.source_label)
        layout.addWidget(self.source_btn)

        layout.addWidget(self.dest_label)
        layout.addWidget(self.dest_btn)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.log)

        self.setLayout(layout)

        self.source_btn.clicked.connect(self.select_source)
        self.dest_btn.clicked.connect(self.select_destination)
        self.start_btn.clicked.connect(self.sort_pdfs)

    def select_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Izberi izvorno mapo")
        if folder:
            self.source_folder = folder
            self.source_label.setText(f"Izvor: {folder}")

    def select_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Izberi ciljno mapo")
        if folder:
            self.destination_folder = folder
            self.dest_label.setText(f"Ciljna mapa: {folder}")

    def log_message(self, message):
        self.log.append(message)

    def sort_pdfs(self):
        print("Start button clicked")
        if not self.source_folder or not self.destination_folder:
            self.log_message("Prosim prvo izberite dve mapi!")
            return 

        for file in os.listdir(self.source_folder):
            if file.lower().endswith(".pdf"):
                file_path = os.path.join(self.source_folder, file)

                try:
                    with pdfplumber.open(file_path) as pdf:
                        sheet_size = None

                        for page in pdf.pages:
                            text = page.extract_text()

                            if not text:
                                continue

                            match = re.search(
                                # Looking for sizes = ["A0", "A1", "A2", "A3", "A4"]
                                r"\bA[0-4]\b",
                                text,
                            )

                            if match:
                                print(match.group())
                                sheet_size = match.group()
                                break
                    
                    if sheet_size:
                        dest_folder = os.path.join(self.destination_folder, sheet_size)
                        os.makedirs(dest_folder, exist_ok=True)

                        shutil.move(file_path, os.path.join(dest_folder, file))
                        self.log_message(f"Premaknil {file} -> {sheet_size}")
                    else:
                        self.log_message(f"Velikost ni bila najdena v datoteki: {file}")

                except Exception as e:
                    self.log_message(f"Napaka pri branju... {file}: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFSorterApp()
    window.show()
    sys.exit(app.exec())

