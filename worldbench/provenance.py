"""Run provenance and reproducibility helpers."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

from worldbench.version import WORLD_BENCH_VERSION


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def sha256_json(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def input_file_record(
    role: str, path: str | Path, *, base_dir: str | Path | None = None
) -> dict[str, Any]:
    source = Path(path)
    display_path, redacted = safe_display_path(source, base_dir=base_dir)
    return {
        "role": role,
        "path": display_path,
        "path_redacted": redacted,
        "sha256": sha256_file(source),
        "bytes": source.stat().st_size,
    }


def safe_display_path(
    path: str | Path, *, base_dir: str | Path | None = None
) -> tuple[str, bool]:
    source = Path(path)
    if not source.is_absolute():
        return source.as_posix(), False

    base = Path(base_dir) if base_dir is not None else Path.cwd()
    try:
        return source.relative_to(base.resolve()).as_posix(), False
    except ValueError:
        return source.name, True


def environment_provenance(*, decoder_backend: str | None = None) -> dict[str, Any]:
    return {
        "worldbench_version": WORLD_BENCH_VERSION,
        "git_commit": git_commit(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "platform": platform.platform(),
        "decoder_backend": decoder_backend,
        "opencv_version": optional_module_version("cv2"),
        "imageio_version": optional_module_version("imageio"),
        "imageio_ffmpeg_version": optional_module_version("imageio_ffmpeg"),
        "ffmpeg_version": ffmpeg_version(),
    }


def git_commit(cwd: str | Path | None = None) -> str | None:
    executable = shutil.which("git")
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # nosec B603
            [executable, "rev-parse", "HEAD"],
            cwd=Path(cwd) if cwd is not None else Path.cwd(),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def optional_module_version(name: str) -> str | None:
    try:
        module = __import__(name)
    except Exception:
        return None
    version = getattr(module, "__version__", None)
    return str(version) if version is not None else None


def ffmpeg_version() -> str | None:
    executable = None
    try:
        import imageio_ffmpeg

        executable = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        executable = shutil.which("ffmpeg")
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # nosec B603
            [str(executable), "-version"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    first = next(
        (line.strip() for line in completed.stdout.splitlines() if line.strip()), ""
    )
    return first[:200] if first else None


def codec_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "codec",
        "pixelformat",
        "fps",
        "duration",
        "nframes",
        "size",
        "source_size",
        "plugin",
    }
    safe: dict[str, Any] = {}
    for key in allowed:
        value = metadata.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, tuple)):
            safe[key] = [
                item for item in value if isinstance(item, (str, int, float, bool))
            ]
    return safe
