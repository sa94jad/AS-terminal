"""AS Terminal: a small terminal-like environment for Python and Termux."""

import code
import curses
import os
import shlex
import signal
import subprocess
import sys
import threading
from pathlib import Path


VERSION = "1.1.2"


class ASTerminal:
    """A lightweight command environment. It does not replace the Android shell."""

    def __init__(self):
        self.cwd = Path.cwd()
        self._process = None
        self._process_lock = threading.RLock()
        self._output_lock = threading.Lock()
        self._running = True

    def _print(self, value=""):
        with self._output_lock:
            print(value, flush=True)

    def banner(self):
        self._print("Welcome to AS")
        self._print("You can test and write your code here.")
        self._print("VERSION : " + VERSION)
        self._print("")
        self._print("Enjoy:")
        self._print("")

    def _active_process(self):
        with self._process_lock:
            if self._process is not None and self._process.poll() is None:
                return self._process
            return None

    def _run_process(self, args, shell=False):
        if self._active_process() is not None:
            self._print("A command is already running. Type Stop AS to stop it.")
            return

        try:
            process = subprocess.Popen(
                args,
                shell=shell,
                cwd=str(self.cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
                start_new_session=(os.name == "posix"),
            )
        except FileNotFoundError:
            self._print("Command not found.")
            return
        except Exception as exc:
            self._print("Could not start command: " + str(exc))
            return

        with self._process_lock:
            self._process = process

        self._print("[AS] Command started. Type Stop AS to cancel it.")

        def read_output():
            try:
                if process.stdout is not None:
                    for line in process.stdout:
                        self._print(line.rstrip("\n"))
                return_code = process.wait()
                if return_code == 0:
                    self._print("[AS] Process finished.")
                else:
                    self._print("[AS] Process ended with code " + str(return_code) + ".")
            except Exception as exc:
                self._print("[AS] Output error: " + str(exc))
            finally:
                with self._process_lock:
                    if self._process is process:
                        self._process = None

        threading.Thread(target=read_output, daemon=True).start()

    def _send_process_input(self, line):
        process = self._active_process()
        if process is None or process.stdin is None:
            self._print("The running command is not accepting input.")
            return
        try:
            process.stdin.write(line + "\\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            self._print("The running command has closed its input.")

    def stop_command(self):
        process = self._active_process()
        if process is None:
            self._print("There is no running command.")
            return

        self._print("[AS] Stopping the current command...")
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
        except ProcessLookupError:
            pass
        except Exception:
            try:
                process.terminate()
            except Exception:
                pass

    def python_editor(self):
        self._print("Python environment opened.")
        self._print("Type Exit.python() to return to AS.")
        self._print("Ctrl+C cancels the current input; it does not close AS.")
        console = code.InteractiveConsole()
        while self._running:
            try:
                prompt = "... " if console.buffer else ">>> "
                line = input(prompt)
            except KeyboardInterrupt:
                console.resetbuffer()
                self._print("^C")
                continue
            except EOFError:
                self._print("")
                break

            if not console.buffer and line.strip() == "Exit.python()":
                self._print("Leaving Python environment.")
                break

            try:
                console.push(line)
            except KeyboardInterrupt:
                console.resetbuffer()
                self._print("^C")
            except SystemExit:
                self._print("Python environment is still available. Use Exit.python() to return.")

    def _read_file(self, path):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()\n            return lines if lines else [""]
        except FileNotFoundError:
            return [""]
        except UnicodeDecodeError:
            self._print("This editor supports UTF-8 text files only.")
            return None
        except OSError as exc:
            self._print("Could not open file: " + str(exc))
            return None

    def _curses_editor(self, path, lines):
        def editor(stdscr):
            try:
                curses.curs_set(1)
            except curses.error:
                pass
            stdscr.keypad(True)
            row = 0
            col = 0
            top = 0
            left = 0
            saved = False

            while True:
                height, width = stdscr.getmaxyx()
                text_height = max(1, height - 1)
                if row < top:
                    top = row
                elif row >= top + text_height:
                    top = row - text_height + 1
                if col < left:
                    left = col
                elif col >= left + max(1, width - 1):
                    left = col - max(1, width - 1) + 1

                stdscr.erase()
                for screen_row in range(text_height):
                    line_index = top + screen_row
                    if line_index < len(lines):
                        visible = lines[line_index][left:left + max(1, width - 1)]
                        try:
                            stdscr.addstr(screen_row, 0, visible)
                        except curses.error:
                            pass

                status = " " + str(path) + " | Ctrl+X: Save | Ctrl+C: ignored "
                try:
                    stdscr.addstr(height - 1, 0, status[:max(0, width - 1)], curses.A_REVERSE)
                    stdscr.move(row - top, min(max(0, col - left), max(0, width - 1)))
                except curses.error:
                    pass
                stdscr.refresh()

                try:
                    key = stdscr.get_wch()
                except KeyboardInterrupt:
                    continue

                if isinstance(key, str):
                    if key == "\x18":  # Ctrl+X
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                        saved = True
                        break
                    if key == "\x03":  # Ctrl+C is deliberately ignored
                        continue
                    if key in ("\n", "\r"):
                        tail = lines[row][col:]
                        lines[row] = lines[row][:col]
                        lines.insert(row + 1, tail)
                        row += 1
                        col = 0
                    elif key in ("\x7f", "\b"):
                        if col > 0:
                            lines[row] = lines[row][:col - 1] + lines[row][col:]
                            col -= 1
                        elif row > 0:
                            previous_length = len(lines[row - 1])
                            lines[row - 1] += lines[row]
                            del lines[row]
                            row -= 1
                            col = previous_length
                    elif key.isprintable():
                        lines[row] = lines[row][:col] + key + lines[row][col:]
                        col += 1
                else:
                    if key == curses.KEY_UP and row > 0:
                        row -= 1
                        col = min(col, len(lines[row]))
                    elif key == curses.KEY_DOWN and row < len(lines) - 1:
                        row += 1
                        col = min(col, len(lines[row]))
                    elif key == curses.KEY_LEFT:
                        if col > 0:
                            col -= 1
                        elif row > 0:
                            row -= 1
                            col = len(lines[row])
                    elif key == curses.KEY_RIGHT:
                        if col < len(lines[row]):
                            col += 1
                        elif row < len(lines) - 1:
                            row += 1
                            col = 0
                    elif key == curses.KEY_HOME:
                        col = 0
                    elif key == curses.KEY_END:
                        col = len(lines[row])
                    elif key == curses.KEY_DC:
                        if col < len(lines[row]):
                            lines[row] = lines[row][:col] + lines[row][col + 1:]
                        elif row < len(lines) - 1:
                            lines[row] += lines[row + 1]
                            del lines[row + 1]

            return saved

        return curses.wrapper(editor)

    def open_editor(self, filename):
        if not filename:
            self._print("Usage: Url filename.py")
            return
        path = Path(filename).expanduser()
        if not path.is_absolute():
            path = self.cwd / path
        lines = self._read_file(path)
        if lines is None:
            return
        try:
            saved = self._curses_editor(path, lines)
            if saved:
                self._print("Saved: " + str(path))
        except Exception as exc:
            self._print("Terminal editor could not start: " + str(exc))
            self._print("Use a real terminal (for example, Termux) and try again.")

    def install_package(self):
        try:
            requirement = input("Enter your pip : ").strip()
        except (KeyboardInterrupt, EOFError):
            self._print("\nPackage installation cancelled.")
            return
        if not requirement:
            self._print("No package name was entered.")
            return
        try:
            packages = shlex.split(requirement)
        except ValueError as exc:
            self._print("Invalid package input: " + str(exc))
            return
        if not packages:
            self._print("No package name was entered.")
            return
        self._run_process([sys.executable, "-m", "pip", "install"] + packages)

    def help(self):
        self._print("AS Terminal commands:")
        self._print("  Editor.py       Open the Python environment")
        self._print("  Url file.py     Create or edit a UTF-8 file")
        self._print("  pips download   Install a Python package")
        self._print("  Stop AS         Stop the running command")
        self._print("  pwd             Show the current directory")
        self._print("  cd PATH         Change the current directory")
        self._print("  clear           Clear the screen")
        self._print("  exit            Close AS Terminal")
        self._print("")
        self._print("Inside Python, type Exit.python() to return here.")

    def execute(self, command):
        command = command.strip()
        if not command:
            return

        if command == "Stop AS":
            self.stop_command()
            return

        if self._active_process() is not None:
            self._send_process_input(command)
            return

        if command in ("Editor.py", "editor.py"):
            self.python_editor()
            return

        if command == "pips download":
            self.install_package()
            return

        if command.startswith("Url "):
            self.open_editor(command[4:].strip())
            return
        if command == "Url":
            try:
                filename = input("Enter file name: ").strip()
            except (KeyboardInterrupt, EOFError):
                self._print("")
                return
            self.open_editor(filename)
            return

        if command in ("help", "AS.help()"):
            self.help()
            return
        if command in ("exit", "quit"):
            self._running = False
            return
        if command == "AS.terminal":
            self._print("AS Terminal is already running.")
            return
        if command == "pwd":
            self._print(str(self.cwd))
            return
        if command.startswith("cd"):
            parts = shlex.split(command)
            target = parts[1] if len(parts) > 1 else str(Path.home())
            new_path = Path(target).expanduser()
            if not new_path.is_absolute():
                new_path = self.cwd / new_path
            try:
                self.cwd = new_path.resolve(strict=True)
                if not self.cwd.is_dir():
                    raise NotADirectoryError(str(self.cwd))
            except OSError as exc:
                self._print("cd: " + str(exc))
            return
        if command == "clear":
            print("\033[2J\033[H", end="", flush=True)
            return

        self._run_process(command, shell=True)

    def run(self):
        self.banner()
        while self._running:
            try:
                command = input("$AS: ")
            except KeyboardInterrupt:
                self._print("^C (AS Terminal is still running)")
                continue
            except EOFError:
                self._print("")
                break
            self.execute(command)

        process = self._active_process()
        if process is not None:
            self.stop_command()
        self._print("AS Terminal closed.")


def main():
    ASTerminal().run()


if __name__ == "__main__":
    main()
