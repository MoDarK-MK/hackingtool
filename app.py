import sys
import signal
import platform
import os
import html
import subprocess
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QPlainTextEdit, QLabel, QScrollArea,
    QDialog, QLineEdit, QFileDialog, QMessageBox , QTextEdit
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QTextCursor, QGuiApplication
from PyQt6.QtCore import QThread, pyqtSignal

ANSI_SGR_COLORS = {
        30: "black", 31: "red", 32: "green", 33: "orange", 34: "blue",
        35: "magenta", 36: "cyan", 37: "lightgray", 90: "gray",
        91: "lightcoral", 92: "lightgreen", 93: "yellow", 94: "lightskyblue",
        95: "plum", 96: "paleturquoise", 97: "white"
    }

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
        self._last_was_output_line = False
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

        self.terminal = QTextEdit()
        self.terminal.setAcceptRichText(True)
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


    def ansi_to_html(text: str) -> str:
        """
        Very small ANSI SGR -> HTML converter.
        Handles sequences like \x1b[31m (red) and \x1b[0m (reset) and bold (1).
        Other sequences are removed.
        """
        # escape html first
        text = html.escape(text)
        # regex to find SGR params
        sgr_re = re.compile(r'\\x1B\\[([0-9;]*)m')
        parts = []
        last_pos = 0
        open_spans = []

        for m in sgr_re.finditer(text):
            start, end = m.span()
            params = m.group(1)
            # append text before this escape
            parts.append(text[last_pos:start])
            last_pos = end

            if params == '' or params == '0':
                # reset -> close all open spans
                while open_spans:
                    parts.append("</span>")
                    open_spans.pop()
            else:
                attrs = params.split(';')
                style_attrs = []
                for a in attrs:
                    try:
                        ai = int(a)
                    except:
                        continue
                    if ai == 1:
                        style_attrs.append("font-weight:700")
                    elif 30 <= ai <= 37 or 90 <= ai <= 97:
                        color = ANSI_SGR_COLORS.get(ai, None)
                        if color:
                            style_attrs.append(f"color:{color}")
                    elif ai == 39:
                        # default fg
                        pass
                if style_attrs:
                    parts.append(f"<span style=\"{';'.join(style_attrs)}\">")
                    open_spans.append(True)

        parts.append(text[last_pos:])
        # close any remaining spans
        while open_spans:
            parts.append("</span>")
            open_spans.pop()
        return ''.join(parts).replace('\\n', '<br/>').replace('  ', '&nbsp;&nbsp;')

    def show_prompt(self):
        """Append a prompt line using HTML so colors/formatting can be used."""
        self.cwd = os.getcwd()
        prompt = f'<span style="color:#9EA7FF;font-weight:600;">{html.escape(self.username)}</span>' \
                f'@<span style="color:#7B61FF;font-weight:600;">{html.escape(self.domain)}</span>:' \
                f'<span style="color:#A6A6A6;">{html.escape(self.cwd)}</span>$ '
        # ensure cursor at end then insert prompt as HTML block
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        self.terminal.insertHtml(prompt)
        self.terminal.insertPlainText('')  # keep cursor after HTML
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        
        self._last_was_output_line = False
        
    def replace_current_line(self, text):
        """
        Replace current input area (last block) with the provided text (keeps prompt).
        Works by selecting the last block and replacing it.
        """
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # select last block
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        # get current block text to detect prompt boundary if present
        block_text = cursor.selectedText()
        # If prompt visible in block, we will replace after prompt; otherwise replace whole block
        if '$' in block_text:
            # split at last $ to preserve prompt
            idx = block_text.rfind('$')
            prompt_part = block_text[:idx+1]
            # replace: set the block to prompt_part + our text (escape HTML)
            new_block = html.escape(prompt_part) + ' ' + html.escape(text)
            cursor.removeSelectedText()
            cursor.insertHtml(new_block)
        else:
            cursor.removeSelectedText()
            cursor.insertHtml(html.escape(text))
        self.terminal.setTextCursor(cursor)
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def eventFilter(self, source, event):
        if source == self.terminal and event.type() == event.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()
            
            # Enter: پردازش فرمان
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                cursor = self.terminal.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                block_text = cursor.selectedText()
                if '$' in block_text:
                    command = block_text.split('$')[-1].strip()
                else:
                    command = block_text.strip()

                if command:
                    self.history.append(command)
                    self.history_index = len(self.history)
                    
                    # جداسازی دستور اصلی
                    cmd_parts = command.strip().split()
                    cmd_base = cmd_parts[0].lower()
                    
                    # دستورات شبیه‌سازی‌شده
                    if cmd_base == "clear":
                        self.terminal.clear()
                        self.show_prompt()
                    elif cmd_base == "pwd":
                        self.handle_output(self.cwd)
                        self.show_prompt()
                    elif cmd_base == "ls":
                        try:
                            items = os.listdir(self.cwd)
                            self.handle_output('\n'.join(items))
                        except Exception as e:
                            self.handle_output(f"[Error] {str(e)}")
                        self.show_prompt()
                    elif cmd_base == "cd":
                        if len(cmd_parts) > 1:
                            path = os.path.abspath(os.path.join(self.cwd, cmd_parts[1]))
                            if os.path.isdir(path):
                                os.chdir(path)
                                self.cwd = path
                            else:
                                self.handle_output(f"[Error] Directory not found: {path}")
                        self.show_prompt()
                    elif cmd_base == "history":
                        hist_text = '\n'.join(self.history)
                        self.handle_output(hist_text)
                        self.show_prompt()
                    elif cmd_base == "echo":
                        self.handle_output(' '.join(cmd_parts[1:]))
                        self.show_prompt()
                    elif cmd_base == "exit":
                        self.close()
                    else:
                        # دستور واقعی: استفاده از CommandWorker
                        self.terminal.append("")
                        self.current_worker = CommandWorker(command, cwd=self.output_dir)
                        self.current_worker.output_signal.connect(self.handle_output)
                        self.current_worker.finished_signal.connect(self.show_prompt)
                        self.current_worker.start()
                return True
            
            # Ctrl+L: پاک کردن ترمینال
            if key == Qt.Key.Key_L and mods == Qt.KeyboardModifier.ControlModifier:
                self.terminal.clear()
                self.show_prompt()
                return True
            
            # Ctrl+C: copy یا interrupt پروسه جاری
            if key == Qt.Key.Key_C and mods == Qt.KeyboardModifier.ControlModifier:
                cursor = self.terminal.textCursor()
                has_selection = cursor.hasSelection()
                if has_selection:
                    self.terminal.copy()
                else:
                    worker = getattr(self, "current_worker", None)
                    if worker is not None and isinstance(worker, QThread):
                        try:
                            if hasattr(worker, "interrupt"):
                                worker.interrupt()
                        except Exception:
                            pass
                    else:
                        self.terminal.copy()
                return True
            
            # Ctrl+V: paste
            if key == Qt.Key.Key_V and mods == Qt.KeyboardModifier.ControlModifier:
                self.terminal.paste()
                return True
            
            # Arrow Up: فرمان قبلی
            if key == Qt.Key.Key_Up:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.replace_current_line(self.history[self.history_index])
                return True
            
            # Arrow Down: فرمان بعدی یا خط خالی
            if key == Qt.Key.Key_Down:
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.replace_current_line(self.history[self.history_index])
                elif self.history_index == len(self.history) - 1:
                    self.history_index += 1
                    self.replace_current_line('')
                return True

        return False


    def ansi_to_html(self, text: str) -> str:
        ANSI_SGR_COLORS = {
            30: "black", 31: "red", 32: "green", 33: "orange", 34: "blue",
            35: "magenta", 36: "cyan", 37: "lightgray", 90: "gray",
            91: "lightcoral", 92: "lightgreen", 93: "yellow", 94: "lightskyblue",
            95: "plum", 96: "paleturquoise", 97: "white"
        }

        text = html.escape(text)
        sgr_re = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        parts = []
        last_pos = 0
        open_spans = []

        for m in sgr_re.finditer(text):
            start, end = m.span()
            parts.append(text[last_pos:start])
            last_pos = end

            params = m.group()[2:-1]  # remove \x1b[ and m
            if params == '' or params == '0':
                while open_spans:
                    parts.append("</span>")
                    open_spans.pop()
            else:
                attrs = params.split(';')
                style_attrs = []
                for a in attrs:
                    try:
                        ai = int(a)
                    except:
                        continue
                    if ai == 1:
                        style_attrs.append("font-weight:700")
                    elif 30 <= ai <= 37 or 90 <= ai <= 97:
                        color = ANSI_SGR_COLORS.get(ai, None)
                        if color:
                            style_attrs.append(f"color:{color}")
                if style_attrs:
                    parts.append(f"<span style=\"{';'.join(style_attrs)}\">")
                    open_spans.append(True)

        parts.append(text[last_pos:])
        while open_spans:
            parts.append("</span>")
            open_spans.pop()
        return ''.join(parts).replace('\n', '<br/>').replace('  ', '&nbsp;&nbsp;')


    def handle_output(self, raw_text):
        """
        Robust output handler:
        - '\n' -> append new output line (never overwrite previous lines)
        - '\r' -> update last output line (or update text after prompt if prompt is present)
        - '\x1b[2K' -> clear last output line
        - other ANSI escapes (colors) are stripped here to avoid raw escape printing;
            if you want colors later we can add safe html-rendering.
        Uses self._last_was_output_line to know whether last block is an output line or a prompt.
        """
        if raw_text is None:
            return

        text = raw_text.replace('\t', '    ')

        def strip_ansi_except_controls(s):
            return re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', s)

        text = text.replace('\x1b[2K', '[ESC_CLEAR_LINE]')

        parts = re.split(r'(\r|\n|\[ESC_CLEAR_LINE\])', text)

        def append_output_line(s):
            # append plain text + newline
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
            # insertText on cursor is more reliable in PyQt6
            cur = self.terminal.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.insertText(s + '\n')
            self.terminal.setTextCursor(cur)
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
            self._last_was_output_line = True

        def replace_last_output_line(s):
            """
            Replace the last output line. If the last block is a prompt (contains '$'),
            preserve prompt part and replace only after it.
            """
            cur = self.terminal.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.select(QTextCursor.SelectionType.BlockUnderCursor)
            block_text = cur.selectedText()

            if '$' in block_text and not self._last_was_output_line:
                # there's a prompt in the block — preserve up to last '$'
                idx = block_text.rfind('$')
                prompt_part = block_text[:idx+1]  # include $
                new_block = prompt_part + ' ' + s
                cur.removeSelectedText()
                cur.insertText(new_block)
            else:
                # last block is an output line (or no prompt found) -> replace whole block
                cur.removeSelectedText()
                cur.insertText(s)
            self.terminal.setTextCursor(cur)
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
            self._last_was_output_line = True

        def clear_last_output_line():
            # remove the last block (output or prompt line). If it's a prompt, leave prompt only.
            cur = self.terminal.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.select(QTextCursor.SelectionType.BlockUnderCursor)
            block_text = cur.selectedText()
            if '$' in block_text and not self._last_was_output_line:
                # keep prompt only
                idx = block_text.rfind('$')
                prompt_part = block_text[:idx+1]  # include $
                cur.removeSelectedText()
                cur.insertText(prompt_part + ' ')
            else:
                # remove whole block (makes it empty)
                cur.removeSelectedText()
            self.terminal.setTextCursor(cur)
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
            self._last_was_output_line = False

        # iterate parts and process
        buffer = ""
        last_was_newline = False
        last_was_progress = False

        for token in parts:
            if token == '' or token is None:
                continue
            if token == '\n':
                # finish current buffer as appended line
                if buffer != "":
                    # strip ANSI colors from buffer (so control sequences don't show up)
                    clean = strip_ansi_except_controls(buffer)
                    append_output_line(clean)
                    buffer = ""
                else:
                    append_output_line('')
                last_was_newline = True
                last_was_progress = False
                continue

            if token == '\r':
                if buffer != "":
                    clean = strip_ansi_except_controls(buffer)
                    replace_last_output_line(clean)
                    buffer = ""
                last_was_progress = True
                last_was_newline = False
                continue

            if token == '[ESC_CLEAR_LINE]':
                # clear last output line
                clear_last_output_line()
                buffer = ""
                last_was_progress = False
                last_was_newline = False
                continue

            buffer += token

        if buffer != "":
            clean = strip_ansi_except_controls(buffer)
            if last_was_progress or (not last_was_newline and self._last_was_output_line):
                replace_last_output_line(clean)
            else:
                append_output_line(clean)

    def open_subpage(self, tool_name):
        self.header_label.setText(f"Now inside {tool_name}")
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        option_labels = [
            "Fuzz Dirs",      # Option 1 — change this string to whatever name you want
            "Fuzz extensions",
            "Query Fuzz",
            "Subdomain Fuzz",
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
        if tool_name.lower() == "fuzzer" and option_index == 1:
            domain = self.domain.strip().rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f'ffuf -u "{url}" -w "{wordlist}" -t 50 -o "{output_path}" -of json'
            self.replace_current_line(cmd)
        elif option_index == 2:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            extensions = ".php,.bak,.old"
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f'ffuf -u "{url}" -w "{wordlist}" -e {extensions} -t 40 -o "{output_path}" -mc 200-500'
            self.replace_current_line(cmd)
        elif option_index == 3:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/search.php?FUZZ=1"
            params_file = "params.txt"
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u '{url}' -w {params_file} -t 40 -mc 200-500 -o {output_path} "
            self.replace_current_line(cmd)
        elif option_index == 4:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/"
            subdomains_file = "subdomains.txt"
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u {url} -H 'Host: FUZZ.{domain}' -w {subdomains_file} -t 80 -mc 200 -o {output_path}"
            self.replace_current_line(cmd)
 
        else:
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
        self.process = None

    def run(self):
        try:
            # اجرا در یک process group جدید تا بتونیم سیگنال به گروه ارسال کنیم
            is_windows = platform.system() == "Windows"
            if is_windows:
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
                self.process = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.cwd,
                    creationflags=creationflags
                )
            else:
                # preexec_fn=os.setsid باعث میشه پروسه فرزند ریشه‌ی یک گروه جدید باشه
                self.process = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.cwd,
                    preexec_fn=os.setsid
                )

            # خواندن خروجی خط به خط
            for line in iter(self.process.stdout.readline, ''):
                if line is None:
                    break
                # ارسال هر خط به UI
                self.output_signal.emit(line.rstrip('\n'))
            if self.process.stdout:
                self.process.stdout.close()
            self.process.wait()
        except Exception as e:
            self.output_signal.emit(f"[Error] {str(e)}")
        finally:
            self.finished_signal.emit()
            # پس از اتمام، null کردن مرجع پروسه
            try:
                self.process = None
            except Exception:
                pass

    def interrupt(self):
        """
        سعی می‌کنیم SIGINT یا معادلش رو به پروسه/گروه پروسه بفرستیم.
        اگر نشد، fallback به terminate.
        """
        if not self.process:
            return

        try:
            is_windows = platform.system() == "Windows"
            if is_windows:
                # ارسال CTRL_BREAK_EVENT به گروه پروسه (نیاز به CREATE_NEW_PROCESS_GROUP)
                try:
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    # fallback: terminate
                    try:
                        self.process.terminate()
                    except Exception:
                        pass
            else:
                # POSIX: سیگنال به whole process group
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
                except Exception:
                    try:
                        self.process.terminate()
                    except Exception:
                        pass
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernDarkTerminalApp()
    window.show()
    sys.exit(app.exec())