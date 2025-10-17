import sys
import signal
import platform
import os
import html
import subprocess
import re
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QScrollArea,
    QDialog, QLineEdit, QFileDialog, QMessageBox , QTextEdit,
    QLabel, QPlainTextEdit,QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QTextCursor, QGuiApplication
from PyQt6.QtCore import QThread, pyqtSignal
from command_worker import CommandWorker
from utils import ANSI_SGR_COLORS, ansi_to_html
from setup_dialog import InitialSetupDialog

class ModernDarkTerminalApp(QMainWindow):
    def __init__(self):
        self._last_was_output_line = False
        super().__init__()

        setup = InitialSetupDialog(self)
        if setup.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

        res = setup.result
        self.domain = res["domain"]
        self.wordlist_path = res["wordlist"]
        self.output_dir = res["output_dir"]
        self.output_filename = res["output_name"]

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

        self.container = QFrame()
        self.container_layout = QHBoxLayout()
        self.container.setLayout(self.container_layout)

        self.sidebar = QFrame()
        self.sidebar.setStyleSheet("background-color: #1F1F2E;")
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout()
        self.sidebar.setLayout(self.sidebar_layout)

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

        self.header_label = QLabel("")
        self.header_label.setStyleSheet("color: white; font-weight: bold; padding: 5px;")
        self.sidebar_layout.addWidget(self.header_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.sidebar_layout.addWidget(self.scroll_area)

        self.main_buttons = ["Fuzzer", "HTTPX", "Subfinder", "Nuclei", "DNSX"]
        self.add_main_buttons()
        self.container_layout.addWidget(self.sidebar)

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
        self.button_bar_frame = QFrame()
        self.button_bar_frame.setFixedHeight(56)
        self.button_bar_frame.setStyleSheet("background-color: #1B1B2B;")
        button_bar_layout = QHBoxLayout()
        button_bar_layout.setContentsMargins(10, 8, 10, 8)
        button_bar_layout.setSpacing(8)
        self.button_bar_frame.setLayout(button_bar_layout)

        btn_clear = QPushButton("Clear")
        btn_copy = QPushButton("Copy")
        btn_change_wordlist = QPushButton("Change Wordlist")
        btn_back_menu = QPushButton("Back")

        for b in (btn_clear, btn_copy, btn_change_wordlist, btn_back_menu):
            b.setFixedHeight(40)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #7B61FF;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #9E7CFF;
                }
            """)
            button_bar_layout.addWidget(b)

        button_bar_layout.addStretch()

        btn_clear.clicked.connect(lambda: (self.terminal.clear(), self.show_prompt()))
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(self.terminal.toPlainText()))
        btn_back_menu.clicked.connect(self.back_to_main)
        btn_change_wordlist.clicked.connect(self.change_wordlist)

        self.main_layout_content.addWidget(self.button_bar_frame)

        self.container_layout.addWidget(self.main_content)

        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.container)

        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_animation.setDuration(250)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.sidebar_expanded = True

        self.process = None
        self.history = []
        self.history_index = -1
        self.username = os.getlogin() if hasattr(os, "getlogin") else "user"
        self.cwd = os.getcwd()
        self.show_prompt()
        
    def change_wordlist(self):
        """
        Let the user pick a new wordlist file and update self.wordlist_path.
        Shows a confirmation message on success.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Select new wordlist file",
                                            "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        if not os.path.isfile(path):
            QMessageBox.warning(self, "Invalid File", "Selected file does not exist.")
            return
        self.wordlist_path = path
        self.terminal.append("")
        self.terminal.insertPlainText(f"[info] wordlist updated: {self.wordlist_path}\n")
        QMessageBox.information(self, "Wordlist Updated", f"New wordlist set to:\n{self.wordlist_path}")

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
        """Append a prompt line using HTML so colors/formatting can be used."""
        self.cwd = os.getcwd()
        prompt = f'<span style="color:#9EA7FF;font-weight:600;">{html.escape(self.username)}</span>' \
                f'@<span style="color:#7B61FF;font-weight:600;">{html.escape(self.domain)}</span>:' \
                f'<span style="color:#A6A6A6;">{html.escape(self.cwd)}</span>$ '
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        self.terminal.insertHtml(prompt)
        self.terminal.insertPlainText('')
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        
        self._last_was_output_line = False
        
    def replace_current_line(self, text):
        """
        Replace current input area (last block) with the provided text (keeps prompt).
        Works by selecting the last block and replacing it.
        """
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        block_text = cursor.selectedText()
        if '$' in block_text:
            idx = block_text.rfind('$')
            prompt_part = block_text[:idx+1]
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

                    cmd_parts = command.strip().split()
                    cmd_base = cmd_parts[0].lower()

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
                        self.terminal.append("")
                        self.current_worker = CommandWorker(command, cwd=self.output_dir)
                        self.current_worker.output_signal.connect(self.handle_output)
                        self.current_worker.finished_signal.connect(self.show_prompt)
                        self.current_worker.start()
                return True
            
            if key == Qt.Key.Key_L and mods == Qt.KeyboardModifier.ControlModifier:
                self.terminal.clear()
                self.show_prompt()
                return True

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

            if key == Qt.Key.Key_V and mods == Qt.KeyboardModifier.ControlModifier:
                self.terminal.paste()
                return True

            if key == Qt.Key.Key_Up:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.replace_current_line(self.history[self.history_index])
                return True

            if key == Qt.Key.Key_Down:
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.replace_current_line(self.history[self.history_index])
                elif self.history_index == len(self.history) - 1:
                    self.history_index += 1
                    self.replace_current_line('')
                return True

        return False


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
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
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
                idx = block_text.rfind('$')
                prompt_part = block_text[:idx+1]
                new_block = prompt_part + ' ' + s
                cur.removeSelectedText()
                cur.insertText(new_block)
            else:
                cur.removeSelectedText()
                cur.insertText(s)
            self.terminal.setTextCursor(cur)
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
            self._last_was_output_line = True

        def clear_last_output_line():

            cur = self.terminal.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.select(QTextCursor.SelectionType.BlockUnderCursor)
            block_text = cur.selectedText()
            if '$' in block_text and not self._last_was_output_line:
                idx = block_text.rfind('$')
                prompt_part = block_text[:idx+1]
                cur.removeSelectedText()
                cur.insertText(prompt_part + ' ')
            else:
                cur.removeSelectedText()
            self.terminal.setTextCursor(cur)
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)
            self._last_was_output_line = False

        buffer = ""
        last_was_newline = False
        last_was_progress = False

        for token in parts:
            if token == '' or token is None:
                continue
            if token == '\n':
                if buffer != "":
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

        t = tool_name.lower()
        if t == "httpx":
            option_labels = [
                "Basic Probe",
                "List from File",
                "Title Extract",
                "Status Codes",
                "Headers Grab",
                "HTTP Methods",
                "Follow Redirects",
                "Timeout & Retries",
                "Concurrency Scan",
                "Custom Template"
            ]
        elif t == "subfinder":
            option_labels = [
                "Passive Scan",         
                "Recursive Scan",       
                "Brute (wordlist)",     
                "Use Custom Resolvers", 
                "Timeout Tuning",       
                "Threads (concurrency)",
                "All Sources",          
                "Cert-based Scan",      
                "Save JSON",            
                "Custom Template"       
            ]
        elif t == "dnsx":
            option_labels = [
                "Basic DNS Lookup",      
                "A + AAAA Records",      
                "CNAME Lookup",          
                "MX / TXT Records",      
                "Use Custom Resolvers",  
                "Wildcard Detection",   
                "Brute (wordlist)",      
                "Port/Service Probe",    
                "Save JSON",             
                "Custom Template"        
            ]
        else:
            option_labels = [
                "Fuzz Dirs",
                "Fuzz extensions",
                "Query Fuzz",
                "subdomain Fuzz",
                "Packet Fuzz",
                "Depth Fuzz",
                "Human Fuzz",
                "Regex Fuzz",
                "Multi Fuzz",
                "Suggested Command"
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

        elif tool_name.lower() == "fuzzer" and option_index == 2:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            extensions = ".php,.bak,.old"
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f'ffuf -u "{url}" -w "{wordlist}" -e {extensions} -t 40 -o "{output_path}" -mc 200-500 -of json'
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 3:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/search.php?FUZZ=1"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u '{url}' -w {wordlist} -t 40 -mc 200-500 -o {output_path} -of json"
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 4:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u {url} -H 'Host: FUZZ.{domain}' -w {wordlist} -t 80 -mc 200 -o {output_path} -of json"
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 5:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/login"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u {url} -d 'username=admin&password=FUZZ' -X POST -w {wordlist} -H 'Content-Type: application/x-www-form-urlencoded' -t 30 -mc 200,302 -o {output_path} -of json"
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 6:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            extensions = ".php,.html"
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u '{url}' -w '{wordlist}' -recursion -recursion-depth 2 -t 50 -e '{extensions}' -o '{output_path}' -of json"
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 7:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u '{url}' -w '{wordlist}' -t 30 -rate 50 -timeout 10 -o '{output_path}' -of json"
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 8:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            url = f"https://{domain}/FUZZ"
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f'ffuf -u "{url}" -w "{wordlist}" -fs 0 -fw 5 -mr "index of|Directory listing" -o "{output_path}" -of json'
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 9:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -u 'https://{domain}/FUZZ' -H 'X-Api-Token: FUZZ2' -w '{self.wordlist_path}':FUZZ -w '{self.wordlist_path}':FUZZ2 -t 60 -mc 200 -o '{output_path}' -of json"
            self.replace_current_line(cmd)

        elif tool_name.lower() == "fuzzer" and option_index == 10:
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            wordlist = self.wordlist_path
            output_path = os.path.join(self.output_dir, self.output_filename)
            cmd = f"ffuf -c -w {wordlist}  -u http://{domain}/FUZZ -of json"
            self.replace_current_line(cmd)
        

        elif tool_name.lower() == "httpx":
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            output_base = f"https://{domain}"
            
            if option_index == 1:
                out = os.path.join(self.output_dir, f"httpx_basic_{domain}.txt")
                cmd = f'httpx -u {output_base} -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 2:
                out = os.path.join(self.output_dir, f"httpx_list_{domain}.txt")
                cmd = f'httpx -l "{self.wordlist_path}" -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 3:
                out = os.path.join(self.output_dir, f"httpx_title_{domain}.txt")
                cmd = f'httpx -u {output_base} -title -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 4:
                out = os.path.join(self.output_dir, f"httpx_status_{domain}.txt")
                cmd = f'httpx -u {output_base} -status-code -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 5:
                out = os.path.join(self.output_dir, f"httpx_headers_{domain}.txt")
                cmd = f'httpx -u {output_base} -headers -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 6:
                out = os.path.join(self.output_dir, f"httpx_methods_{domain}.txt")
                cmd = f'httpx -l "{self.wordlist_path}" -methods GET,POST -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 7:
                out = os.path.join(self.output_dir, f"httpx_follow_{domain}.txt")
                cmd = f'httpx -l "{self.wordlist_path}" -follow-redirects -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 8:
                out = os.path.join(self.output_dir, f"httpx_timeout_{domain}.txt")
                cmd = f'httpx -l "{self.wordlist_path}" -timeout 10 -retries 2 -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 9:
                out = os.path.join(self.output_dir, f"httpx_conc_{domain}.txt")
                cmd = f'httpx -l "{self.wordlist_path}" -c 50 -o "{out}"'
                self.replace_current_line(cmd)
                
            elif option_index == 10:
                out = os.path.join(self.output_dir, f"httpx_custom_{domain}.txt")
                cmd = f'httpx -u https://{domain}/path -o "{out}"'
                self.replace_current_line(cmd)


        elif tool_name.lower() == "subfinder":
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            if option_index == 1:
                out = os.path.join(self.output_dir, f"subfinder_passive_{domain}.txt")
                cmd = f"subfinder -d {domain} -o \"{out}\""
                self.replace_current_line(cmd)
            elif option_index == 2:
                out = os.path.join(self.output_dir, f"subfinder_recursive_{domain}.txt")
                cmd = f"subfinder -d {domain} -recursive -o \"{out}\""
                self.replace_current_line(cmd)
            elif option_index == 3:
                out = os.path.join(self.output_dir, f"subfinder_brute_{domain}.txt")
                cmd = f"subfinder -d {domain} -brute -w \"{self.wordlist_path}\" -o \"{out}\""
                self.replace_current_line(cmd)
            elif option_index == 4:
                resolvers = "resolvers.txt"
                out = os.path.join(self.output_dir, f"subfinder_resolvers_{domain}.txt")
                cmd = f"subfinder -d {domain} -o \"{out}\" -r \"{resolvers}\""
                self.replace_current_line(cmd)
            elif option_index == 5:
                out = os.path.join(self.output_dir, f"subfinder_timeout_{domain}.txt")
                cmd = f"subfinder -d {domain} -timeout 10 -o \"{out}\""
                self.replace_current_line(cmd)
            elif option_index == 6:
                out = os.path.join(self.output_dir, f"subfinder_threads_{domain}.txt")
                cmd = f"subfinder -d {domain} -t 50 -o \"{out}\""
                self.replace_current_line(cmd)
            elif option_index == 7:
                out = os.path.join(self.output_dir, f"subfinder_all_{domain}.txt")
                cmd = f"subfinder -d {domain} -all -o \"{out}\""
                self.replace_current_line(cmd)
            elif option_index == 8:
                out = os.path.join(self.output_dir, f"subfinder_cert_{domain}.txt")
                cmd = f"subfinder -d {domain} -o \"{out}\" -crt"
                self.replace_current_line(cmd)
            elif option_index == 9:
                out = os.path.join(self.output_dir, f"subfinder_{domain}.json")
                cmd = f"subfinder -d {domain} -o \"{out}\" -oJ"
                self.replace_current_line(cmd)
            elif option_index == 10:
                out = os.path.join(self.output_dir, f"subfinder_custom_{domain}.txt")
                cmd = f"subfinder -d {domain} -o \"{out}\""
                self.replace_current_line(cmd)
                
        elif tool_name.lower() == "dnsx":
            domain = re.sub(r'^https?://', '', self.domain.strip()).rstrip('/')
            if option_index == 1:
                out = os.path.join(self.output_dir, f"dnsx_basic_{domain}.txt")
                cmd = f'dnsx -d {domain} -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 2:
                out = os.path.join(self.output_dir, f"dnsx_a_aaaa_{domain}.txt")
                cmd = f'dnsx -d {domain} -a -aaaa -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 3:
                out = os.path.join(self.output_dir, f"dnsx_cname_{domain}.txt")
                cmd = f'dnsx -d {domain} -cname -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 4:
                out = os.path.join(self.output_dir, f"dnsx_mx_txt_{domain}.txt")
                cmd = f'dnsx -d {domain} -mx -txt -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 5:
                resolvers = "resolvers.txt"
                out = os.path.join(self.output_dir, f"dnsx_resolvers_{domain}.txt")
                cmd = f'dnsx -d {domain} -r "{resolvers}" -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 6:
                out = os.path.join(self.output_dir, f"dnsx_wildcard_{domain}.txt")
                cmd = f'python3 -c "print(\'generate-check\')" && dnsx -d {domain} -silent -o \"{out}\"'
                self.replace_current_line(cmd)

            elif option_index == 7:
                out = os.path.join(self.output_dir, f"dnsx_brute_{domain}.txt")
                cmd = f'dnsx -d {domain} -w "{self.wordlist_path}" -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 8:
                out = os.path.join(self.output_dir, f"dnsx_probe_{domain}.txt")
                cmd = f'dnsx -d {domain} -a -o "{out}" | httpx -silent -o "{os.path.join(self.output_dir, f"httpx_from_dnsx_{domain}.txt")}"'
                self.replace_current_line(cmd)

            elif option_index == 9:
                out = os.path.join(self.output_dir, f"dnsx_{domain}.json")
                cmd = f'dnsx -d {domain} -o "{out}"'
                self.replace_current_line(cmd)

            elif option_index == 10:
                out = os.path.join(self.output_dir, f"dnsx_custom_{domain}.txt")
                cmd = f'# Custom dnsx: dnsx -d {domain} -o \"{out}\"'
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