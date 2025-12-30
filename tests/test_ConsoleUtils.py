"""
Tests for ConsoleUtils module.
"""

from unittest.mock import patch

from lendingbot.modules import ConsoleUtils


class TestConsoleUtils:
    def test_get_terminal_size_windows(self):
        with (
            patch("platform.system", return_value="Windows"),
            patch(
                "lendingbot.modules.ConsoleUtils._get_terminal_size_windows", return_value=(100, 40)
            ),
        ):
            size = ConsoleUtils.get_terminal_size()
            assert size == (100, 40)

    def test_get_terminal_size_linux(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch(
                "lendingbot.modules.ConsoleUtils._get_terminal_size_linux", return_value=(120, 50)
            ),
        ):
            size = ConsoleUtils.get_terminal_size()
            assert size == (120, 50)

    def test_get_terminal_size_default(self):
        with patch("platform.system", return_value="Unknown"):
            size = ConsoleUtils.get_terminal_size()
            assert size == (80, 25)

    def test_get_terminal_size_tput(self):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.side_effect = [b"100\n", b"40\n"]
            size = ConsoleUtils._get_terminal_size_tput()
            assert size == (100, 40)

            mock_exec.side_effect = Exception("error")
            assert ConsoleUtils._get_terminal_size_tput() is None

    def test_get_terminal_size_linux_env(self):
        with (
            patch.dict("os.environ", {"LINES": "50", "COLUMNS": "120"}),
            patch(
                "lendingbot.modules.ConsoleUtils.struct.unpack", side_effect=Exception("no ioctl")
            ),
        ):
            size = ConsoleUtils._get_terminal_size_linux()
            assert size == (120, 50)
