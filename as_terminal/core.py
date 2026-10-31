"""AS Terminal: a small terminal-like environment for Python and Termux."""

import code
import os
import shlex
import signal
import subprocess
import shutil
import sys
import threading
from pathlib import Path


VERSION = "1.2.0"


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
            process.stdin.write(line + "\n")
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
        self._print("Type exit() or quit() to return to AS.")
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

            if not console.buffer and line.strip() in ("exit()", "quit()"):
                self._print("Leaving Python environment.")
                break

            try:
                console.push(line)
            except KeyboardInterrupt:
                console.resetbuffer()
                self._print("^C")
            except SystemExit:
                self._print("Leaving Python environment.")
                break

    def _read_file(self, path):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            return lines if lines else [""]
        except FileNotFoundError:
            return [""]
        except UnicodeDecodeError:
            self._print("This editor supports UTF-8 text files only.")
            return None
        except OSError as exc:
            self._print("Could not open file: " + str(exc))
            return None

    def _curses_editor(self, path, lines):
        import curses

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
            self._print("Usage: edit FILE")
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


    def _resolve_path(self, value):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.cwd / path
        return path

    def list_directory(self, arguments):
        show_hidden = "-a" in arguments or "--all" in arguments
        targets = [item for item in arguments if item not in ("-a", "--all")]
        if not targets:
            targets = ["."]
        for index, target in enumerate(targets):
            path = self._resolve_path(target)
            if len(targets) > 1:
                self._print(str(path) + ":")
            try:
                if path.is_file() or path.is_symlink():
                    self._print(path.name)
                    continue
                if not path.is_dir():
                    self._print("ls: no such file or directory: " + str(path))
                    continue
                entries = list(path.iterdir())
                if not show_hidden:
                    entries = [entry for entry in entries if not entry.name.startswith(".")]
                entries.sort(key=lambda entry: (not entry.is_dir(), entry.name.casefold()))
                if not entries:
                    self._print("(empty)")
                else:
                    for entry in entries:
                        suffix = "/" if entry.is_dir() else ""
                        self._print(entry.name + suffix)
            except OSError as exc:
                self._print("ls: " + str(exc))
            if index < len(targets) - 1:
                self._print("")

    def show_files(self, arguments):
        if not arguments:
            self._print("Usage: cat FILE [FILE ...]")
            return
        for filename in arguments:
            path = self._resolve_path(filename)
            try:
                if not path.is_file():
                    self._print("cat: not a file: " + str(path))
                    continue
                self._print(path.read_text(encoding="utf-8"),)
            except UnicodeDecodeError:
                self._print("cat: UTF-8 text files only: " + str(path))
            except OSError as exc:
                self._print("cat: " + str(exc))

    def create_files(self, arguments):
        if not arguments:
            self._print("Usage: touch FILE [FILE ...]")
            return
        for filename in arguments:
            path = self._resolve_path(filename)
            try:
                path.touch(exist_ok=True)
                self._print("Created: " + str(path))
            except OSError as exc:
                self._print("touch: " + str(exc))

    def make_directories(self, arguments):
        parents = False
        paths = []
        for item in arguments:
            if item in ("-p", "--parents"):
                parents = True
            else:
                paths.append(item)
        if not paths:
            self._print("Usage: mkdir [-p] DIRECTORY [DIRECTORY ...]")
            return
        for directory in paths:
            path = self._resolve_path(directory)
            try:
                path.mkdir(parents=parents, exist_ok=parents)
                self._print("Created directory: " + str(path))
            except OSError as exc:
                self._print("mkdir: " + str(exc))

    def copy_or_move(self, arguments, move=False):
        action = "mv" if move else "cp"
        if len(arguments) != 2:
            self._print("Usage: " + action + " SOURCE DESTINATION")
            return
        source = self._resolve_path(arguments[0])
        destination = self._resolve_path(arguments[1])
        try:
            if not source.exists() and not source.is_symlink():
                raise FileNotFoundError(str(source))
            if move:
                shutil.move(str(source), str(destination))
            else:
                if source.is_dir():
                    raise IsADirectoryError("cp currently copies files only")
                shutil.copy2(str(source), str(destination))
            self._print(action + ": done")
        except OSError as exc:
            self._print(action + ": " + str(exc))

    def remove_file(self, arguments):
        if len(arguments) != 1:
            self._print("Usage: rm FILE (directories are not removed)")
            return
        path = self._resolve_path(arguments[0])
        if path.is_dir() and not path.is_symlink():
            self._print("rm: directories are not removed; use rmdir for an empty directory")
            return
        try:
            answer = input("Remove " + str(path) + "? [y/N] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            self._print("Cancelled.")
            return
        if answer not in ("y", "yes"):
            self._print("Cancelled.")
            return
        try:
            path.unlink()
            self._print("Removed: " + str(path))
        except OSError as exc:
            self._print("rm: " + str(exc))

    def remove_directory(self, arguments):
        if len(arguments) != 1:
            self._print("Usage: rmdir EMPTY_DIRECTORY")
            return
        path = self._resolve_path(arguments[0])
        try:
            path.rmdir()
            self._print("Removed directory: " + str(path))
        except OSError as exc:
            self._print("rmdir: " + str(exc))

    def system_info(self):
        self._print("AS Terminal " + VERSION)
        self._print("Python: " + sys.version.split()[0])
        self._print("Platform: " + sys.platform)
        self._print("Working directory: " + str(self.cwd))
        self._print("Home directory: " + str(Path.home()))

    def locate_command(self, arguments):
        if len(arguments) != 1:
            self._print("Usage: which COMMAND")
            return
        result = shutil.which(arguments[0])
        self._print(result if result else "Command not found: " + arguments[0])

    def install_package(self):
        try:
            requirement = input("Package name(s): ").strip()
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
        self._print("AS Terminal " + VERSION + " - lightweight daily commands")
        self._print("")
        self._print("Files and folders:")
        self._print("  ls [-a] [PATH]       List files (-a includes hidden files)")
        self._print("  pwd                  Show the current directory")
        self._print("  cd [PATH]            Change directory (default: home)")
        self._print("  cat FILE             Print a UTF-8 text file")
        self._print("  touch FILE           Create an empty file")
        self._print("  mkdir [-p] DIR       Create a directory")
        self._print("  cp SRC DEST          Copy a file")
        self._print("  mv SRC DEST          Move or rename a file")
        self._print("  rm FILE              Remove a file after confirmation")
        self._print("  rmdir DIR            Remove an empty directory")
        self._print("")
        self._print("Tools:")
        self._print("  info                 Show Python and system information")
        self._print("  which COMMAND        Find an installed command")
        self._print("  python               Open the Python interactive interpreter")
        self._print("  edit FILE            Open the built-in text editor")
        self._print("  pip install PACKAGE  Install Python package(s)")
        self._print("  stop                 Stop the running command")
        self._print("  clear                Clear the screen")
        self._print("  help                 Show this help")
        self._print("  exit                 Close AS Terminal")
        self._print("")
        self._print("Other system commands are passed to your operating-system shell.")
        self._print("Inside Python, type exit() or quit() to return here.")

    def execute(self, command):
        command = command.strip()
        if not command:
            return

        if command == "stop":
            self.stop_command()
            return

        if self._active_process() is not None:
            self._send_process_input(command)
            return

        try:
            parts = shlex.split(command)
        except ValueError as exc:
            self._print("Invalid command syntax: " + str(exc))
            return
        if not parts:
            return

        name = parts[0]
        arguments = parts[1:]

        if name == "python":
            self.python_editor()
            return
        if name == "pip" and arguments and arguments[0] == "install":
            if len(arguments) == 1:
                self.install_package()
            else:
                self._run_process([sys.executable, "-m", "pip", "install"] + arguments[1:])
            return
        if name == "edit":
            filename = " ".join(arguments)
            if not filename:
                self._print("Usage: edit FILE")
                return
            self.open_editor(filename)
            return
        if name in ("help", "AS.help()"):
            self.help()
            return
        if name in ("exit", "quit"):
            self._running = False
            return
        if name == "AS.terminal":
            self._print("AS Terminal is already running.")
            return
        if name == "version":
            self._print("AS Terminal " + VERSION)
            return
        if name == "info":
            self.system_info()
            return
        if name == "which":
            self.locate_command(arguments)
            return
        if name == "pwd":
            if arguments:
                self._print("Usage: pwd")
            else:
                self._print(str(self.cwd))
            return
        if name == "cd":
            if len(arguments) > 1:
                self._print("Usage: cd [PATH]")
                return
            target = arguments[0] if arguments else str(Path.home())
            new_path = self._resolve_path(target)
            try:
                resolved = new_path.resolve(strict=True)
                if not resolved.is_dir():
                    raise NotADirectoryError(str(resolved))
                self.cwd = resolved
            except OSError as exc:
                self._print("cd: " + str(exc))
            return
        if name == "ls":
            self.list_directory(arguments)
            return
        if name == "cat":
            self.show_files(arguments)
            return
        if name == "touch":
            self.create_files(arguments)
            return
        if name == "mkdir":
            self.make_directories(arguments)
            return
        if name == "cp":
            self.copy_or_move(arguments, move=False)
            return
        if name == "mv":
            self.copy_or_move(arguments, move=True)
            return
        if name == "rm":
            self.remove_file(arguments)
            return
        if name == "rmdir":
            self.remove_directory(arguments)
            return
        if name == "clear":
            if arguments:
                self._print("Usage: clear")
            else:
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
