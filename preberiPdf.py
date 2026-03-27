import pdfplumber
import shutil
import os
import re
import sys
import fitz

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QTextEdit, QScrollArea,

)


from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import ( QImage, QPixmap, QPainter, QPen )


class PDFViewer(QLabel):
    def __init__(self, pdf_path):
        super().__init__()

        self.doc = fitz.open(pdf_path)
        self.page = self.doc[0]

        pix = self.page.get_pixmap()

        img = QImage.fromData(pix.tobytes("png"))

        self.image = QPixmap.fromImage(img)
       

        self.setPixmap(self.image)

        self.start = QPoint()
        self.end = QPoint()
        self.drawing = False

    def mousePressEvent(self, event):
        self.start = event.pos()
        self.end = event.pos()
        self.drawing = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()
        self.drawing = False

        x0 = min(self.start.x(), self.end.x())
        y0 = min(self.start.y(), self.end.y())
        x1 = max(self.start.x(), self.end.x())
        y1 = max(self.start.y(), self.end.y())

        print(f"SELECTED RECT: ({x0}, {y0}, {x1}, {y1})")

        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.drawing:
            painter = QPainter(self)
            pen = QPen(Qt.GlobalColor.red, 2)
            painter.setPen(pen)
            painter.drawRect(self.start.x(), self.start.y(),
                             self.end.x() - self.start.x(),
                             self.end.y() - self.start.y())


class PDFSorterApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bralec PDF formata")
        self.setGeometry(300, 300, 600, 500)

        self.source_folder = ""
        self.destination_folder = ""

        self.overlays = {
            "A4": [(55, 730, 173, 813)],
            "A3": [(650, 730, 762, 813)],
            "A2": [(1145, 1075, 1260, 1161)],
            "A1": [(1845, 1575, 1961, 1655)],
            "A0": [(2832, 2273, 2940, 2357)],
        }

        layout = QVBoxLayout()

        self.source_label = QLabel("Izvorna mapa: ni izbrana")
        self.dest_label = QLabel("Ciljna mapa: ni izbrana")

        self.source_btn = QPushButton("Izberi izvorno mapo")
        
        self.dest_btn = QPushButton("Izberi ciljno mapo")
        self.start_btn = QPushButton("Začni sortiranje")
        self.inspect_btn = QPushButton("Izberi PDF za koordinate")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)
        self.log.setStyleSheet("""
            QTextEdit {
            font-size: 12px;
            }
        """)

        layout.addWidget(self.source_label)
        layout.addWidget(self.source_btn)

        layout.addWidget(self.dest_label)
        layout.addWidget(self.dest_btn)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.log)

        layout.addWidget(self.log, 1)

        layout.addWidget(self.inspect_btn)


        self.setLayout(layout)

        self.source_btn.clicked.connect(self.select_source)
        self.dest_btn.clicked.connect(self.select_destination)
        self.start_btn.clicked.connect(self.sort_pdfs)
        self.inspect_btn.clicked.connect(self.open_pdf_viewer)

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
        self.log_message("Začetek sortiranja ⌛⏳")
        if not self.source_folder or not self.destination_folder:
            self.log_message("Prosim prvo izberite dve mapi!")
            return 

        for file in os.listdir(self.source_folder):
            QApplication.processEvents()
            if file.lower().endswith(".pdf"):
                file_path = os.path.join(self.source_folder, file)

                try:
                    with pdfplumber.open(file_path) as pdf:
                        self.log_message(f"Odprl PDF: { file }")

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

                        output_path = os.path.join(dest_folder, file)

                        self.overlay_and_save_pdf(file_path, output_path, sheet_size)

                        self.log_message(f"Obdelan {file} -> {sheet_size}")
                    else:
                        self.log_message(f"Velikost ni bila najdena v datoteki: {file}")

                except Exception as e:
                    self.log_message(f"Napaka pri branju... {file}: {e}")

        self.log_message("✅ Končano! Vse datoteke obdelane.")
        print("DONE: All files processed")

    def open_pdf_viewer(self):
        file, _ = QFileDialog.getOpenFileName(self, "Izberi PDF", "", "PDF Files (*.pdf)")
        if file:
            self.viewer = PDFViewer(file)

            self.scroll = QScrollArea()
            self.scroll.setWidget(self.viewer)
            self.scroll.setWidgetResizable(True)

            self.scroll.setWindowTitle("Izberi območje (klik + povleci)")
            self.scroll.showMaximized()

    # Exits full window on escape
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    
    def overlay_and_save_pdf(self, input_path, output_path, sheet_size):
        import fitz

        doc = fitz.open(input_path)

        rectangles = self.overlays.get(sheet_size, [])

        for page in doc:
            for coords in rectangles:
                rect = fitz.Rect(coords)
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        doc.save(output_path)
        doc.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFSorterApp()
    window.show()
    sys.exit(app.exec())

