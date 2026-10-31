import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from as_terminal.core import ASTerminal, VERSION


class TerminalCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.terminal = ASTerminal()
        self.terminal.cwd = self.root

    def tearDown(self):
        self.temp.cleanup()

    def run_command(self, command):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.terminal.execute(command)
        return output.getvalue()

    def test_version_is_updated(self):
        self.assertEqual(VERSION, "1.2.0")
        self.assertIn("1.2.0", self.run_command("version"))

    def test_touch_ls_and_cat(self):
        self.run_command("touch notes.txt")
        file_path = self.root / "notes.txt"
        self.assertTrue(file_path.is_file())
        file_path.write_text("hello AS\n", encoding="utf-8")
        self.assertIn("notes.txt", self.run_command("ls"))
        self.assertIn("hello AS", self.run_command("cat notes.txt"))

    def test_hidden_files_only_appear_with_all_flag(self):
        (self.root / ".secret").write_text("x", encoding="utf-8")
        self.assertNotIn(".secret", self.run_command("ls"))
        self.assertIn(".secret", self.run_command("ls -a"))

    def test_mkdir_with_parents(self):
        self.run_command("mkdir -p one/two/three")
        self.assertTrue((self.root / "one/two/three").is_dir())

    def test_cd_and_pwd(self):
        target = self.root / "folder"
        target.mkdir()
        self.run_command("cd folder")
        self.assertEqual(self.terminal.cwd, target.resolve())
        self.assertIn(str(target.resolve()), self.run_command("pwd"))

    def test_cd_rejects_multiple_arguments(self):
        output = self.run_command("cd one two")
        self.assertIn("Usage: cd", output)

    def test_copy_and_move(self):
        source = self.root / "source.txt"
        source.write_text("data", encoding="utf-8")
        self.run_command("cp source.txt copy.txt")
        self.assertEqual((self.root / "copy.txt").read_text(encoding="utf-8"), "data")
        self.run_command("mv copy.txt moved.txt")
        self.assertFalse((self.root / "copy.txt").exists())
        self.assertEqual((self.root / "moved.txt").read_text(encoding="utf-8"), "data")

    def test_rm_requires_confirmation(self):
        target = self.root / "remove.txt"
        target.write_text("x", encoding="utf-8")
        with patch("builtins.input", return_value="yes"):
            self.run_command("rm remove.txt")
        self.assertFalse(target.exists())

    def test_rm_cancelled_by_default(self):
        target = self.root / "keep.txt"
        target.write_text("x", encoding="utf-8")
        with patch("builtins.input", return_value=""):
            output = self.run_command("rm keep.txt")
        self.assertTrue(target.exists())
        self.assertIn("Cancelled", output)

    def test_rm_does_not_remove_directories(self):
        folder = self.root / "folder"
        folder.mkdir()
        output = self.run_command("rm folder")
        self.assertTrue(folder.is_dir())
        self.assertIn("directories are not removed", output)

    def test_rmdir_only_removes_empty_directory(self):
        empty = self.root / "empty"
        empty.mkdir()
        self.run_command("rmdir empty")
        self.assertFalse(empty.exists())
        nonempty = self.root / "nonempty"
        nonempty.mkdir()
        (nonempty / "file").touch()
        output = self.run_command("rmdir nonempty")
        self.assertTrue(nonempty.exists())
        self.assertIn("rmdir:", output)

    def test_legacy_nonstandard_package_command_is_not_documented_or_handled(self):
        output = self.run_command("pips download")
        self.assertNotIn("Package name(s):", output)
        self.assertNotIn("pips download", self.run_command("help"))

    def test_pip_install_uses_current_python(self):
        with patch.object(self.terminal, "_run_process") as run_process:
            self.run_command("pip install requests")
        run_process.assert_called_once_with([__import__("sys").executable, "-m", "pip", "install", "requests"])

    def test_bad_quotes_are_reported_without_running_shell(self):
        output = self.run_command('cat "unfinished')
        self.assertIn("Invalid command syntax", output)

    def test_help_mentions_daily_commands(self):
        output = self.run_command("help")
        for command in ("ls", "cat", "touch", "mkdir", "cp", "mv", "rm", "info", "pip install PACKAGE", "python", "edit FILE", "stop"):
            self.assertIn(command, output)


if __name__ == "__main__":
    unittest.main()
