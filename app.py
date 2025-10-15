import sys
import os
import subprocess
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QPlainTextEdit, QLabel, QScrollArea,
    QDialog, QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QTextCursor, QGuiApplication
from PyQt6.QtCore import QThread, pyqtSignal


class InitialSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Initial Setup")
        self.setFixedSize(420, 260)
        self.center(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Domain
        self.domain_label = QLabel("Domain:")
        self.domain_input = QLineEdit()
        layout.addWidget(self.domain_label)
        layout.addWidget(self.domain_input)

        # Wordlist (file) + browse
        self.wordlist_label = QLabel("Path to wordlist (file):")
        wordlist_h = QHBoxLayout()
        self.wordlist_input = QLineEdit()
        self.wordlist_browse = QPushButton("Browse")
        self.wordlist_browse.clicked.connect(self.browse_wordlist)
        wordlist_h.addWidget(self.wordlist_input)
        wordlist_h.addWidget(self.wordlist_browse)
        layout.addWidget(self.wordlist_label)
        layout.addLayout(wordlist_h)

        # Output directory + browse
        self.output_dir_label = QLabel("Output directory:")
        output_h = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_browse = QPushButton("Browse")
        self.output_dir_browse.clicked.connect(self.browse_output_dir)
        output_h.addWidget(self.output_dir_input)
        output_h.addWidget(self.output_dir_browse)
        layout.addWidget(self.output_dir_label)
        layout.addLayout(output_h)

        # Output filename
        self.output_name_label = QLabel("Output filename (e.g. results.txt):")
        self.output_name_input = QLineEdit()
        layout.addWidget(self.output_name_label)
        layout.addWidget(self.output_name_input)

        # Buttons
        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self.on_submit)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_h.addWidget(self.cancel_btn)
        btn_h.addWidget(self.submit_btn)
        layout.addLayout(btn_h)

        # Result storage
        self.result = None

    def center(self, parent):
        """Center the dialog on parent if available, otherwise on primary screen."""
        if parent is not None:
            parent_rect = parent.frameGeometry()
            parent_center = parent_rect.center()
        else:
            screen = QGuiApplication.primaryScreen()
            parent_center = screen.availableGeometry().center()

        top_left = QPoint(parent_center.x() - self.width() // 2,
                          parent_center.y() - self.height() // 2)
        self.move(top_left)

    def browse_wordlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select wordlist file")
        if path:
            self.wordlist_input.setText(path)

    def browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select output directory")
        if path:
            self.output_dir_input.setText(path)

    def on_submit(self):
        domain = self.domain_input.text().strip()
        wordlist = self.wordlist_input.text().strip()
        outdir = self.output_dir_input.text().strip()
        outname = self.output_name_input.text().strip()

        if not domain:
            QMessageBox.warning(self, "Validation", "Domain is required.")
            return
        if not wordlist or not os.path.isfile(wordlist):
            QMessageBox.warning(self, "Validation", "Valid wordlist file is required.")
            return
        if not outdir or not os.path.isdir(outdir):
            QMessageBox.warning(self, "Validation", "Valid output directory is required.")
            return
        if not outname:
            QMessageBox.warning(self, "Validation", "Output filename is required.")
            return

        self.result = {
            "domain": domain,
            "wordlist": wordlist,
            "output_dir": outdir,
            "output_name": outname
        }
        self.accept()


class ModernDarkTerminalApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Show setup dialog first
        setup = InitialSetupDialog(self)
        if setup.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

        res = setup.result
        self.domain = res["domain"]
        self.wordlist_path = res["wordlist"]
        self.output_dir = res["output_dir"]
        self.output_filename = res["output_name"]

        # set cwd to output directory
        try:
            os.chdir(self.output_dir)
        except Exception:
            pass

        self.setWindowTitle("Modern Dark Terminal App")
        self.showFullScreen()
        self.full_screen = True

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Top bar: left domain, right window controls
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(40)
        self.top_bar.setStyleSheet("background-color: #1F1F2E;")
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(8, 0, 8, 0)
        self.top_bar.setLayout(top_layout)

        self.domain_label = QLabel(f"Domain: {self.domain}")
        self.domain_label.setStyleSheet("color: white; font-weight: bold;")
        top_layout.addWidget(self.domain_label)
        top_layout.addStretch()

        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("□")
        self.btn_close = QPushButton("✕")
        for btn in [self.btn_min, self.btn_max, self.btn_close]:
            btn.setFixedSize(35, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #7B61FF;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #9E7CFF;
                }
            """)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self.toggle_fullscreen)
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_min)
        top_layout.addWidget(self.btn_max)
        top_layout.addWidget(self.btn_close)

        # Container (sidebar + terminal)
        self.container = QFrame()
        self.container_layout = QHBoxLayout()
        self.container.setLayout(self.container_layout)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setStyleSheet("background-color: #1F1F2E;")
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout()
        self.sidebar.setLayout(self.sidebar_layout)

        # Toggle button
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #7B61FF;
                color: white;
                border: none;
                font-size: 20px;
                padding: 10px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #9E7CFF;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(self.toggle_btn)
        self.sidebar_layout.addSpacing(8)

        # Header label
        self.header_label = QLabel("")
        self.header_label.setStyleSheet("color: white; font-weight: bold; padding: 5px;")
        self.sidebar_layout.addWidget(self.header_label)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.sidebar_layout.addWidget(self.scroll_area)

        # Main menu buttons
        self.main_buttons = ["Fuzzer", "HTTPX", "Subfinder", "Nuclei", "DNSX"]
        self.add_main_buttons()
        self.container_layout.addWidget(self.sidebar)

        # Terminal
        self.main_content = QFrame()
        self.main_content.setStyleSheet("background-color: #2E2E3E;")
        self.main_layout_content = QVBoxLayout()
        self.main_content.setLayout(self.main_layout_content)

        self.terminal = QPlainTextEdit()
        self.terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #121212;
                color: #00FF00;
                font-family: "Courier New";
                font-size: 14px;
                border: none;
            }
        """)
        self.terminal.setReadOnly(False)
        self.terminal.installEventFilter(self)
        self.main_layout_content.addWidget(self.terminal)
        self.container_layout.addWidget(self.main_content)

        # Put together
        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.container)

        # Sidebar animation
        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_animation.setDuration(250)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.sidebar_expanded = True

        # Terminal data
        self.process = None
        self.history = []
        self.history_index = -1
        self.username = os.getlogin() if hasattr(os, "getlogin") else "user"
        self.cwd = os.getcwd()
        self.show_prompt()

    def add_main_buttons(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        for tool in self.main_buttons:
            btn = QPushButton(tool)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    font-size: 16px;
                    text-align: left;
                    padding: 10px 20px;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #7B61FF;
                }
            """)
            btn.clicked.connect(lambda checked, t=tool: self.open_subpage(t))
            self.scroll_layout.addWidget(btn)

    def toggle_fullscreen(self):
        if self.full_screen:
            self.showNormal()
            self.full_screen = False
        else:
            self.showFullScreen()
            self.full_screen = True

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar_animation.setStartValue(220)
            self.sidebar_animation.setEndValue(0)
        else:
            self.sidebar_animation.setStartValue(0)
            self.sidebar_animation.setEndValue(220)
        self.sidebar_animation.start()
        self.sidebar_expanded = not self.sidebar_expanded

    def show_prompt(self):
        self.cwd = os.getcwd()
        prompt = f"{self.username}@{self.domain}:{self.cwd}$ "
        self.terminal.appendPlainText(prompt)
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.terminal.setTextCursor(cursor)

    def eventFilter(self, source, event):
        if source == self.terminal and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return:
                cursor = self.terminal.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                last_line = self.terminal.document().toPlainText().split('\n')[-1]
                command = last_line.split('$')[-1].strip()
                if command:
                    self.history.append(command)
                    self.history_index = len(self.history)
                    self.terminal.appendPlainText("")  # blank line before output

                    # start worker to run command safely (non-blocking) and stream output
                    self.current_worker = CommandWorker(command, cwd=self.output_dir)
                    # append each emitted line to terminal in main thread
                    self.current_worker.output_signal.connect(lambda text: self.terminal.appendPlainText(text))
                    # when finished, show prompt again
                    self.current_worker.finished_signal.connect(self.show_prompt)
                    self.current_worker.start()
                return True

            if event.key() == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.terminal.clear()
                self.show_prompt()
                return True
            if event.key() == Qt.Key.Key_Return:
                cursor = self.terminal.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                last_line = self.terminal.document().toPlainText().split('\n')[-1]
                command = last_line.split('$')[-1].strip()
                if command:
                    self.history.append(command)
                    self.history_index = len(self.history)
                    self.terminal.appendPlainText("")  # new line before output

                    # Run command in QThread (safe, async)
                    self.worker = CommandWorker(command, self.output_dir)
                    self.worker.output_signal.connect(lambda text: self.terminal.appendPlainText(text))
                    self.worker.finished.connect(self.show_prompt)
                    self.worker.start()
                return True
        return False


    def replace_current_line(self, text):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self.cwd = os.getcwd()
        cursor.insertText(f"{self.username}@{self.domain}:{self.cwd}$ {text}")
        self.terminal.setTextCursor(cursor)

    def open_subpage(self, tool_name):
        self.header_label.setText(f"Now inside {tool_name}")
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        option_labels = [
            "FFUF Dirs",      # Option 1 — change this string to whatever name you want
            "Option 2",
            "Option 3",
            "Option 4",
            "Option 5",
            "Option 6",
            "Option 7",
            "Option 8",
            "Option 9",
            "Option 10"
        ]

        for idx, label in enumerate(option_labels, start=1):
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    font-size: 14px;
                    text-align: left;
                    padding: 8px 15px;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: #7B61FF;
                }
            """)
            # keep original binding: pass the option index and tool name to handler
            btn.clicked.connect(lambda checked, i=idx, t=tool_name: self.on_option_click(t, i))
            self.scroll_layout.addWidget(btn)
            back_btn = QPushButton("Back")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5555;
                color: white;
                font-size: 14px;
                border-radius: 12px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #FF7777;
            }
        """)
        back_btn.clicked.connect(self.back_to_main)
        self.scroll_layout.addWidget(back_btn)

    def on_option_click(self, tool_name, option_index):
        """
        If Fuzzer + Option 1 -> build ffuf command using setup values
        and insert it into the CLI (does NOT execute).
        For other options/tools, insert a template command into the prompt.
        """
        if tool_name.lower() == "fuzzer" and option_index == 1:
            domain = self.domain.strip().rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            # build the ffuf command (escaped/quoted)
            cmd = f'ffuf -u "{url}" -w "{wordlist}" -t 50 -o "{output_path}" -of json'

            # insert command into terminal input line (does not auto-run)
            self.replace_current_line(cmd)
        else:
            # default: prepare a template command and insert it
            if tool_name.lower() == "httpx":
                cmd = f'httpx -u {self.domain} -o {self.output_filename}'
            else:
                cmd = f'# {tool_name} option {option_index} (configure command)'
            self.replace_current_line(cmd)


    def back_to_main(self):
        self.header_label.setText("")
        self.add_main_buttons()
class CommandWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, command, cwd=None):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd
            )
            for line in iter(process.stdout.readline, ''):
                if line is None:
                    break
                self.output_signal.emit(line.rstrip('\n'))
            process.stdout.close()
            process.wait()
        except Exception as e:
            self.output_signal.emit(f"[Error] {str(e)}")
        finally:
            self.finished_signal.emit()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernDarkTerminalApp()
    window.show()
    sys.exit(app.exec())
