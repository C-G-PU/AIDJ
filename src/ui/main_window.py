import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QLineEdit,
                               QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                               QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

from src.core.db import Database
from src.core.analyzer import Analyzer
from src.core.audio_engine import AudioEngine
from src.core.ai_brain import AIBrain

class DJWorker(QThread):
    finished_action = Signal(dict)

    def __init__(self, ai_brain, prompt):
        super().__init__()
        self.ai_brain = ai_brain
        self.prompt = prompt

    def run(self):
        result = self.ai_brain.generate_next_action(self.prompt)
        self.finished_action.emit(result)

class AIDJWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI DJ Controller")
        self.resize(1000, 700)

        # Core modules
        self.db = Database("library.db")
        self.analyzer = Analyzer(self.db)
        self.audio_engine = AudioEngine()
        self.ai_brain = AIBrain(self.db)

        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Panel (Chat & Controls)
        left_panel = QVBoxLayout()

        title = QLabel("🤖 AI DJ Controller")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        left_panel.addWidget(title)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.append("Welcome! Scan a directory or enter a prompt to let the AI start mixing.")
        left_panel.addWidget(self.chat_log)

        input_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Tell the AI what to play... (e.g. 'Play something energetic')")
        self.prompt_input.returnPressed.connect(self._handle_prompt)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._handle_prompt)
        input_layout.addWidget(self.prompt_input)
        input_layout.addWidget(self.send_btn)

        left_panel.addLayout(input_layout)
        main_layout.addLayout(left_panel, 1) # proportion 1

        # Right Panel (Database & Settings)
        right_panel = QVBoxLayout()

        db_controls = QHBoxLayout()
        scan_btn = QPushButton("Scan Folder for Tracks")
        scan_btn.clicked.connect(self._scan_folder)
        import_btn = QPushButton("Import Metadata (CSV/JSON)")
        import_btn.clicked.connect(self._import_metadata)
        db_controls.addWidget(scan_btn)
        db_controls.addWidget(import_btn)
        right_panel.addLayout(db_controls)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "BPM", "Key", "Mood", "Energy"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        right_panel.addWidget(self.table)

        main_layout.addLayout(right_panel, 2) # proportion 2

    def _refresh_table(self):
        tracks = self.db.get_all_tracks()
        self.table.setRowCount(len(tracks))
        for row_idx, track in enumerate(tracks):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(track['id'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(track['title']))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(track['bpm'])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(track['key_tag'] or '')))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(track['mood'] or '')))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(track['energy'] or '')))

    def _scan_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Audio Files")
        if folder:
            self.chat_log.append(f"[System] Scanning {folder}...")

            # Using QTimer for non-blocking single-shot execution is tricky with long loops,
            # but since scan_directory is synchronous and blocks, doing it directly here
            # is bad practice. We will use a minimal thread to prevent UI freeze.
            import threading
            def scan_task():
                self.analyzer.scan_directory(folder)
                # Note: QTableWidget updates must technically happen on the main thread,
                # but for simplicity we invoke refresh after thread join via signal or just wait.
                # In production, we'd use a QThread for this too.

            self.scan_thread = threading.Thread(target=scan_task)
            self.scan_thread.start()

            # Since QTableWidget must be updated in main thread, we'll schedule a periodic check
            from PySide6.QtCore import QTimer
            self.scan_timer = QTimer()
            self.scan_timer.timeout.connect(self._check_scan_finished)
            self.scan_timer.start(500)

    def _check_scan_finished(self):
        if not self.scan_thread.is_alive():
            self.scan_timer.stop()
            self._refresh_table()
            self.chat_log.append(f"[System] Scan complete.")

    def _import_metadata(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Metadata File", "", "JSON/CSV Files (*.json *.csv)")
        if file_path:
            self.analyzer.import_external_metadata(file_path)
            self._refresh_table()
            self.chat_log.append(f"[System] Metadata imported from {file_path}")

    def _handle_prompt(self):
        prompt = self.prompt_input.text().strip()
        if not prompt: return

        self.chat_log.append(f"<b>You:</b> {prompt}")
        self.prompt_input.clear()
        self.send_btn.setEnabled(False)
        self.chat_log.append("<i>AI is thinking...</i>")

        # Run AI generation in thread
        self.worker = DJWorker(self.ai_brain, prompt)
        self.worker.finished_action.connect(self._process_ai_response)
        self.worker.start()

    def _process_ai_response(self, result):
        self.send_btn.setEnabled(True)

        if "error" in result:
            self.chat_log.append(f"<font color='red'><b>AI:</b> Error - {result['error']}</font>")
            return

        track_id = result.get('next_track_id')
        duration = result.get('transition_duration', 5)
        explanation = result.get('explanation', "Here is the next track.")

        self.chat_log.append(f"<b>AI DJ:</b> {explanation}")

        track = self.db.get_track_by_id(track_id)
        if track:
            self.chat_log.append(f"[System] Transitioning to: {track['title']} over {duration} seconds.")
            # Execute transition in audio engine
            self.audio_engine.execute_plan(track['file_path'], duration)
        else:
            self.chat_log.append(f"<font color='red'>[System] AI requested invalid track ID {track_id}.</font>")

    def closeEvent(self, event):
        self.audio_engine.cleanup()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AIDJWindow()
    window.show()
    sys.exit(app.exec())
