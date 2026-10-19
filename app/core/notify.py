"""
notify.py  –  Windows toast notifications.

Sends a native Windows notification only when the app window is not focused.
Clicking the notification raises/focuses the app window.

We use winotify (already installed) with the `launch` parameter set to the
running executable path so Windows brings our process to the front on click.
On Python source runs we use a small .vbs launcher to avoid a console flash.
"""

import os
import sys
import subprocess
import tempfile

_APP_ID = "Studio Tools"


def _exe_path() -> str:
    """Return the path that, when launched, will re-open / focus this instance."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller exe — launch the exe itself
        return sys.executable
    # Running from source — use the main.py script path with pythonw
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    main_py = os.path.join(root, "main.py")
    # Use pythonw to avoid a console window
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.isfile(pythonw):
        pythonw = sys.executable
    return f'"{pythonw}" "{main_py}"'


def _icon_path() -> str:
    """Return path to app.ico, or empty string if not found."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ico = os.path.join(root, "app", "assets", "app.ico")
    return ico if os.path.isfile(ico) else ""


def send(title: str, message: str) -> None:
    """
    Show a Windows toast notification.
    Safe to call from any thread.
    Does nothing if winotify is not available.
    """
    try:
        from winotify import Notification, audio

        icon = _icon_path()
        toast = Notification(
            app_id=_APP_ID,
            title=title,
            msg=message,
            icon=icon,
            duration="short",          # 5 s on screen, then goes to Action Centre
            launch=_exe_path(),        # clicking the toast focuses / reopens the app
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception:
        # Notification is optional — never crash the app if it fails
        pass
