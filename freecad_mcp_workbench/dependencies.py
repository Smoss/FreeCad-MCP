"""Dependency checks and Workbench-local dependency path support."""

from __future__ import annotations

import importlib.util
import os
import site
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DependencyStatus:
    available: bool
    python_executable: str
    python_version: str
    dependency_dir: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "python_executable": self.python_executable,
            "python_version": self.python_version,
            "dependency_dir": self.dependency_dir,
            "message": self.message,
        }


def dependency_dir() -> Path:
    override = os.environ.get("FREECAD_MCP_DEPENDENCY_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".freecad_mcp_workbench" / "python"


def add_dependency_path(path: Path | None = None) -> Path:
    target = path or dependency_dir()
    if target.exists():
        site.addsitedir(str(target))
        if str(target) not in sys.path:
            sys.path.insert(0, str(target))
    return target


def check_mcp_dependency() -> DependencyStatus:
    target = add_dependency_path()
    spec = importlib.util.find_spec("mcp")
    available = spec is not None
    return DependencyStatus(
        available=available,
        python_executable=sys.executable,
        python_version=sys.version.split()[0],
        dependency_dir=str(target),
        message="MCP SDK is importable" if available else "MCP SDK is missing; install package 'mcp' into the dependency directory",
    )


def install_mcp_dependency() -> DependencyStatus:
    target = dependency_dir()
    target.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "install", "--target", str(target), "mcp"]
    try:
        subprocess.check_call(cmd)
    except Exception as exc:
        return DependencyStatus(
            available=False,
            python_executable=sys.executable,
            python_version=sys.version.split()[0],
            dependency_dir=str(target),
            message=f"Automatic install failed: {exc}",
        )
    return check_mcp_dependency()

