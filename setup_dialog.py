import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QGuiApplication

class InitialSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Initial Setup")
        self.setFixedSize(420, 260)
        self.center(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.domain_label = QLabel("Domain:")
        self.domain_input = QLineEdit()
        layout.addWidget(self.domain_label)
        layout.addWidget(self.domain_input)

        self.wordlist_label = QLabel("Path to wordlist (file):")
        wordlist_h = QHBoxLayout()
        self.wordlist_input = QLineEdit()
        self.wordlist_browse = QPushButton("Browse")
        self.wordlist_browse.clicked.connect(self.browse_wordlist)
        wordlist_h.addWidget(self.wordlist_input)
        wordlist_h.addWidget(self.wordlist_browse)
        layout.addWidget(self.wordlist_label)
        layout.addLayout(wordlist_h)

        self.output_dir_label = QLabel("Output directory:")
        output_h = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_browse = QPushButton("Browse")
        self.output_dir_browse.clicked.connect(self.browse_output_dir)
        output_h.addWidget(self.output_dir_input)
        output_h.addWidget(self.output_dir_browse)
        layout.addWidget(self.output_dir_label)
        layout.addLayout(output_h)

        self.output_name_label = QLabel("Output filename (e.g. results.txt):")
        self.output_name_input = QLineEdit()
        layout.addWidget(self.output_name_label)
        layout.addWidget(self.output_name_input)

        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self.on_submit)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_h.addWidget(self.cancel_btn)
        btn_h.addWidget(self.submit_btn)
        layout.addLayout(btn_h)

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