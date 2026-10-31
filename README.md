# AS Terminal

**Version:** 1.1.2

AS Terminal is a small Python-based command environment designed for Termux and Android. It provides a familiar prompt and a few custom commands. It runs on top of your existing operating-system shell; it is not a replacement for Termux, Android, or Linux.

## Install

From the GitHub repository:

```bash
python -m pip install git+https://github.com/dnsfb28ejxizk-star/AS-terminal.git
```

Or install a local clone:

```bash
python -m pip install .
```

Then start it:

```bash
AS.terminal
```

You can also run it without installing the console command:

```bash
python -m as_terminal
```

## Welcome screen

```text
Welcome to AS
You can test and write your code here.
VERSION : 1.1.2

Enjoy:

$AS:
```

## Commands

| Command | What it does |
| --- | --- |
| `Editor.py` | Opens the interactive Python environment |
| `Url sajad.py` | Opens the built-in text editor for a file |
| `pips download` | Asks for a package name, then installs it with pip |
| `Stop AS` | Stops the currently running external command or pip installation |
| `cd PATH` | Changes the working directory |
| `pwd` | Prints the working directory |
| `clear` | Clears the screen |
| `help` | Shows commands |
| `exit` | Closes AS Terminal |

Inside the Python environment, type:

```python
Exit.python()
```

to return to the AS prompt.

## Built-in editor

Open or create a file:

```text
Url sajad.py
```

Use the arrow keys to move, type to edit, and **Ctrl+X** to save and return to AS. Ctrl+C is ignored by the editor.

## Installing packages

At the AS prompt:

```text
pips download
Enter your pip : requests
```

The package is installed into the same Python interpreter used to launch AS Terminal. You can also enter a pip requirement or a Git URL, for example:

```text
git+https://github.com/OWNER/REPOSITORY.git
```

## Important behavior and limits

- Ctrl+C at the AS prompt does not close AS Terminal.
- Ctrl+C inside the Python prompt cancels the current input and returns to the Python prompt.
- Ctrl+C in the built-in editor is ignored. Ctrl+X saves the file.
- External commands run asynchronously so that `Stop AS` can be typed while one is running.
- While an external command is running, lines you type are sent to that command as standard input. Type `Stop AS` to stop it instead.
- AS Terminal uses your current Python installation and its pip. It does not bundle Python or install packages into a separate environment.
- The built-in editor is a small text editor, not a full replacement for nano or a graphical IDE.

## License

MIT. See [LICENSE](LICENSE).
