"""Small optional Qt helpers for FreeCAD command UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

QtCore: Any = None
QtGui: Any = None
QtWidgets: Any = None

try:
    from PySide import QtCore as _QtCore
    from PySide import QtGui as _QtGui
    from PySide import QtWidgets as _QtWidgets
except Exception:
    pass
else:
    QtCore = _QtCore
    QtGui = _QtGui
    QtWidgets = _QtWidgets


def show_info(title: str, message: str) -> bool:
    if QtWidgets is None:
        return False
    QtWidgets.QMessageBox.information(None, title, message)
    return True


def ask_yes_no(title: str, message: str) -> bool | None:
    if QtWidgets is None:
        return None
    response = QtWidgets.QMessageBox.question(None, title, message)
    return response == QtWidgets.QMessageBox.Yes


def copy_to_clipboard(text: str) -> bool:
    if QtWidgets is None:
        return False
    QtWidgets.QApplication.clipboard().setText(text)
    return True


def open_local_file(path: Path) -> bool:
    if QtCore is None or QtGui is None:
        return False
    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
    return True
