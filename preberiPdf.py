import os
import re
import shutil
import sys

import fitz
import pdfplumber
from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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
            painter.drawRect(
                self.start.x(),
                self.start.y(),
                self.end.x() - self.start.x(),
                self.end.y() - self.start.y(),
            )


class PDFSorterApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF Size Sorter")
        self.setGeometry(250, 180, 980, 760)

        self.source_folder = ""
        self.destination_folder = ""
        self.combined_output_folder = "Izbrisane glave"
        self.unsorted_output_folder = "neuvr\u0161\u010deni"

        self.is_running = False
        self.cancel_requested = False
        self.stats = {"processed": 0, "matched": 0, "unsorted": 0, "errors": 0}

        self.overlays = {
            "A4": [(55, 730, 173, 813)],
            "A3": [(650, 730, 762, 813)],
            "A2": [(1145, 1075, 1260, 1161)],
            "A1": [(1845, 1575, 1961, 1655)],
            "A0": [(2832, 2273, 2940, 2357)],
        }

        self.build_ui()
        self.update_button_states()

    def build_ui(self):
        layout = QVBoxLayout()

        self.source_btn = QPushButton("Select source folder")
        self.source_btn.clicked.connect(self.select_source)
        self.source_label = QLabel("Source folder: not selected")
        self.source_label.setWordWrap(True)

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_btn, 0)
        source_row.addWidget(self.source_label, 1)
        layout.addLayout(source_row)

        self.dest_btn = QPushButton("Select destination folder")
        self.dest_btn.clicked.connect(self.select_destination)
        self.dest_label = QLabel("Destination folder: not selected")
        self.dest_label.setWordWrap(True)

        dest_row = QHBoxLayout()
        dest_row.addWidget(self.dest_btn, 0)
        dest_row.addWidget(self.dest_label, 1)
        layout.addLayout(dest_row)

        self.start_btn = QPushButton("Start sorting")
        self.start_btn.clicked.connect(self.sort_pdfs)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_sorting)

        self.open_sorted_btn = QPushButton("Open processed folder")
        self.open_sorted_btn.clicked.connect(self.open_processed_folder)

        self.open_unsorted_btn = QPushButton("Open unsorted folder")
        self.open_unsorted_btn.clicked.connect(self.open_unsorted_folder)

        self.inspect_btn = QPushButton("Inspect PDF coordinates")
        self.inspect_btn.clicked.connect(self.open_pdf_viewer)

        action_row = QHBoxLayout()
        action_row.addWidget(self.start_btn)
        action_row.addWidget(self.stop_btn)
        action_row.addWidget(self.open_sorted_btn)
        action_row.addWidget(self.open_unsorted_btn)
        action_row.addWidget(self.inspect_btn)
        layout.addLayout(action_row)

        self.progress_label = QLabel("Progress: 0 / 0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_label, 0)
        progress_row.addWidget(self.progress_bar, 1)
        layout.addLayout(progress_row)

        self.summary_label = QLabel("Ready.")
        layout.addWidget(self.summary_label)

        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(
            ["File", "Detected Size", "Status", "Output Path"]
        )
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.results_table, 1)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(145)
        self.log.setStyleSheet(
            """
            QTextEdit {
                font-size: 12px;
            }
            """
        )
        layout.addWidget(self.log)

        self.setLayout(layout)

    def update_button_states(self):
        can_start = bool(self.source_folder and self.destination_folder) and not self.is_running
        self.start_btn.setEnabled(can_start)
        self.stop_btn.setEnabled(self.is_running)
        self.source_btn.setEnabled(not self.is_running)
        self.dest_btn.setEnabled(not self.is_running)
        self.inspect_btn.setEnabled(not self.is_running)

        combined_folder, unsorted_folder = self.get_output_paths()
        self.open_sorted_btn.setEnabled(
            (not self.is_running)
            and bool(combined_folder)
            and os.path.isdir(combined_folder)
        )
        self.open_unsorted_btn.setEnabled(
            (not self.is_running)
            and bool(unsorted_folder)
            and os.path.isdir(unsorted_folder)
        )

    def get_output_paths(self):
        if not self.destination_folder:
            return "", ""

        combined_folder = os.path.join(self.destination_folder, self.combined_output_folder)
        unsorted_folder = os.path.join(self.destination_folder, self.unsorted_output_folder)
        return combined_folder, unsorted_folder

    def select_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select source folder")
        if folder:
            self.source_folder = folder
            self.source_label.setText(f"Source folder: {folder}")
            self.update_button_states()

    def select_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Select destination folder")
        if folder:
            self.destination_folder = folder
            self.dest_label.setText(f"Destination folder: {folder}")
            self.update_button_states()

    def log_message(self, message):
        self.log.append(message)

    def reset_run_ui(self, total_files):
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(max(1, total_files))
        self.progress_label.setText(f"Progress: 0 / {total_files}")
        self.stats = {"processed": 0, "matched": 0, "unsorted": 0, "errors": 0}
        self.summary_label.setText("Running...")

    def stop_sorting(self):
        if self.is_running:
            self.cancel_requested = True
            self.log_message("Stop requested. Finishing current file...")

    def sort_pdfs(self):
        if not self.source_folder or not self.destination_folder:
            self.log_message("Please select source and destination folders first.")
            return

        pdf_files = sorted(
            file for file in os.listdir(self.source_folder) if file.lower().endswith(".pdf")
        )
        total_files = len(pdf_files)
        self.reset_run_ui(total_files)

        if total_files == 0:
            self.summary_label.setText("No PDF files found in source folder.")
            self.log_message("No PDF files found in source folder.")
            self.update_button_states()
            return

        combined_folder, unsorted_folder = self.get_output_paths()
        os.makedirs(combined_folder, exist_ok=True)
        os.makedirs(unsorted_folder, exist_ok=True)

        self.is_running = True
        self.cancel_requested = False
        self.update_button_states()
        self.log_message(f"Started sorting {total_files} PDF file(s).")

        for file in pdf_files:
            QApplication.processEvents()
            if self.cancel_requested:
                self.log_message("Sorting stopped by user.")
                break

            file_path = os.path.join(self.source_folder, file)
            detected_size = "-"
            status = ""
            output_path = ""

            try:
                with pdfplumber.open(file_path) as pdf:
                    detected_size = self.detect_sheet_size(pdf)

                if detected_size:
                    output_path = self.get_unique_output_path(combined_folder, file)
                    self.overlay_and_save_pdf(file_path, output_path, detected_size)
                    status = "Matched"
                    self.stats["matched"] += 1
                    self.log_message(f"Processed: {file} ({detected_size})")
                else:
                    output_path = self.copy_to_unsorted(file_path, file, unsorted_folder)
                    status = "Unsorted (size not found)"
                    self.stats["unsorted"] += 1
                    self.log_message(f"Size not found: {file}. Copied to unsorted.")

            except Exception as e:
                output_path = self.copy_to_unsorted(file_path, file, unsorted_folder)
                status = "Error -> unsorted"
                self.stats["errors"] += 1
                self.log_message(f"Read error in {file}: {e}. Copied to unsorted.")

            self.stats["processed"] += 1
            self.add_result_row(file, detected_size, status, output_path)
            self.update_progress(self.stats["processed"], total_files)

        self.finish_run(total_files)

    def finish_run(self, total_files):
        self.is_running = False
        self.update_button_states()

        summary = (
            f"Processed {self.stats['processed']}/{total_files} | "
            f"Matched: {self.stats['matched']} | "
            f"Unsorted: {self.stats['unsorted']} | "
            f"Errors: {self.stats['errors']}"
        )
        self.summary_label.setText(summary)
        self.log_message(summary)

    def detect_sheet_size(self, pdf):
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            match = re.search(r"\bA\s*[-]?\s*([0-4])\b", text, re.IGNORECASE)
            if match:
                return f"A{match.group(1)}"

        return None

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Progress: {current} / {total}")
        QApplication.processEvents()

    def add_result_row(self, file_name, detected_size, status, output_path):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(file_name))
        self.results_table.setItem(row, 1, QTableWidgetItem(detected_size))
        self.results_table.setItem(row, 2, QTableWidgetItem(status))
        self.results_table.setItem(row, 3, QTableWidgetItem(output_path))

    def open_folder(self, folder_path):
        if not folder_path or not os.path.isdir(folder_path):
            self.log_message("Folder does not exist yet.")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def open_processed_folder(self):
        combined_folder, _ = self.get_output_paths()
        self.open_folder(combined_folder)

    def open_unsorted_folder(self):
        _, unsorted_folder = self.get_output_paths()
        self.open_folder(unsorted_folder)

    def open_pdf_viewer(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if file:
            self.viewer = PDFViewer(file)

            self.scroll = QScrollArea()
            self.scroll.setWidget(self.viewer)
            self.scroll.setWidgetResizable(True)
            self.scroll.setWindowTitle("Select area (click + drag)")
            self.scroll.showMaximized()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def overlay_and_save_pdf(self, input_path, output_path, sheet_size):
        doc = fitz.open(input_path)
        rectangles = self.overlays.get(sheet_size, [])

        for page in doc:
            for coords in rectangles:
                rect = fitz.Rect(coords)
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        doc.save(output_path)
        doc.close()

    def copy_to_unsorted(self, file_path, filename, unsorted_folder):
        unsorted_output_path = self.get_unique_output_path(unsorted_folder, filename)
        shutil.copy2(file_path, unsorted_output_path)
        return unsorted_output_path

    def get_unique_output_path(self, target_folder, filename):
        base, ext = os.path.splitext(filename)
        candidate_path = os.path.join(target_folder, filename)
        counter = 1

        while os.path.exists(candidate_path):
            candidate_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
            counter += 1

        return candidate_path


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFSorterApp()
    window.show()
    sys.exit(app.exec())
