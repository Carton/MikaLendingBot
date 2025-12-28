import os
import platform
import shlex
import struct
import subprocess


def get_terminal_size() -> tuple[int, int]:
    """getTerminalSize()
    - get width and height of console
    - works on linux,os x,windows,cygwin(windows)
    originally retrieved from:
    http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    current_os = platform.system()
    tuple_xy: tuple[int, int] | None = None
    if current_os == "Windows":
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
            # needed for window's python in cygwin's xterm!
    if current_os in ["Linux", "Darwin"] or current_os.startswith("CYGWIN"):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
        tuple_xy = (80, 25)  # default value
    return tuple_xy


def _get_terminal_size_windows() -> tuple[int, int] | None:
    try:
        from ctypes import create_string_buffer, windll

        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (
                _bufx,
                _bufy,
                _curx,
                _cury,
                _wattr,
                left,
                top,
                right,
                bottom,
                _maxx,
                _maxy,
            ) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except Exception:
        pass
    return None


def _get_terminal_size_tput() -> tuple[int, int] | None:
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:
        cols = int(subprocess.check_output(shlex.split("tput cols")))
        rows = int(subprocess.check_output(shlex.split("tput lines")))
        return (cols, rows)
    except Exception:
        pass
    return None


def _get_terminal_size_linux() -> tuple[int, int] | None:
    def ioctl_GWINSZ(fd: int) -> tuple[int, ...] | None:
        try:
            import fcntl
            import termios

            cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))  # type: ignore
            return cr
        except Exception:
            pass
        return None

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)  # type: ignore
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except Exception:
            pass
    if not cr:
        try:
            cr = (int(os.environ["LINES"]), int(os.environ["COLUMNS"]))
        except Exception:
            return None
    return int(cr[1]), int(cr[0])
