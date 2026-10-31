# AS Terminal

**Version:** 1.2.1

AS Terminal is a lightweight Python command environment for Termux and Android. It adds convenient everyday file and system commands while still using the operating-system shell for commands it does not handle itself. It is not a replacement for Termux, Android, or Linux.

## Requirements

- Python 3.8 or newer
- Termux or another terminal emulator
- No third-party runtime dependencies

## Install from this repository

```bash
python -m pip install git+https://github.com/sa94jad/AS-terminal.git
```

Or install a local clone:

```bash
git clone https://github.com/sa94jad/AS-terminal.git
cd AS-terminal
python -m pip install .
```

Start it:

```bash
as-terminal
```

You can also run it without installing the console command:

```bash
python -m as_terminal
```

## Everyday commands

| Command | What it does |
| --- | --- |
| `ls [-a] [PATH]` | List files; `-a` includes hidden files |
| `pwd` | Show the current directory |
| `cd [PATH]` | Change directory; no path goes to your home directory |
| `cat FILE` | Print a UTF-8 text file |
| `touch FILE` | Create an empty file |
| `mkdir [-p] DIR` | Create a directory |
| `cp SOURCE DEST` | Copy a file |
| `mv SOURCE DEST` | Move or rename a file |
| `rm FILE` | Remove a file after confirmation; directories are not removed |
| `rmdir DIR` | Remove an empty directory |
| `info` | Show Python, platform, and directory information |
| `which COMMAND` | Find a command on PATH |
| `clear` | Clear the terminal |
| `help` | Show all built-in commands |
| `exit` | Close AS Terminal |

Other system commands are passed to your operating-system shell. This keeps AS small and avoids reimplementing the full shell.

## Python and editor

- `python` opens the interactive Python environment.
- Type `exit()` or `quit()` to return to AS.
- `edit filename.py` opens the built-in UTF-8 text editor.
- PHP source files can also be opened with `edit filename.php`; the editor is a plain-text editor (no PHP syntax highlighting or PHP execution).
- In the editor, use the arrow keys to move and **Ctrl+X** to save.

## PHP on Termux

Run these commands at the **AS Terminal** prompt:

```text
pkg php download
Upgrade & php
edit index.php
```

- `pkg php download` asks Termux's package manager to install PHP.
- `Upgrade & php` asks the package manager to install/update only the PHP package; it does not run the system-wide `pkg upgrade` command.
- These are AS Terminal built-ins. They are not commands that replace or modify the normal Termux shell commands.
- PHP installation requires Termux and an available `pkg` command.

## Installing Python packages

At the AS prompt, use the standard pip command:

```text
pip install requests
```

You can install multiple packages in one command:

```text
pip install requests rich
```

AS runs pip through the same Python interpreter used to launch AS Terminal.

## Process behavior

- External commands run asynchronously.
- While a command is running, input is sent to that process.
- Type `stop` to stop the running process.
- Ctrl+C at the AS prompt does not close AS Terminal.

## Development and tests

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

The GitHub Actions test workflow checks Python 3.8, 3.11, and 3.13.

## License

MIT. See [LICENSE](LICENSE).
