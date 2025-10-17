import platform
import os
import signal
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

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
                self.process = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.cwd,
                    preexec_fn=os.setsid
                )

            for line in iter(self.process.stdout.readline, ''):
                if line is None:
                    break
                self.output_signal.emit(line.rstrip('\n'))
            if self.process.stdout:
                self.process.stdout.close()
            self.process.wait()
        except Exception as e:
            self.output_signal.emit(f"[Error] {str(e)}")
        finally:
            self.finished_signal.emit()
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
                try:
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    try:
                        self.process.terminate()
                    except Exception:
                        pass
            else:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
                except Exception:
                    try:
                        self.process.terminate()
                    except Exception:
                        pass
        except Exception:
            pass