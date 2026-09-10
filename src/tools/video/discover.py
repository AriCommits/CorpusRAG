"""Media file discovery for video processing.

Provides :func:`discover_media_files`, a helper for resolving a user-supplied
path (a single file or a directory) into a sorted list of media files matching
a set of extensions. Its directory-empty error shape is intentionally
compatible with :meth:`tools.video.transcribe.VideoTranscriber.transcribe_folder`
so callers can rely on a consistent message.
"""

from collections.abc import Iterable
from pathlib import Path

__all__ = ["discover_media_files"]

# Directory names excluded from recursive traversal.
_EXCLUDED_DIRS = frozenset({"scratch", ".git", "__pycache__"})


def _normalize_extensions(extensions: Iterable[str]) -> list[str]:
    """Return a normalized, lower-cased list of extensions.

    Each extension is lower-cased and guaranteed to start with a single dot,
    preserving the caller's ordering (used for the "Supported formats" message).

    Args:
        extensions: Iterable of extensions, with or without a leading dot.

    Returns:
        Normalized list of extensions such as ``[".mp4", ".mkv"]``.
    """
    normalized: list[str] = []
    for ext in extensions:
        ext = ext.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        normalized.append(ext)
    return normalized


def _is_excluded(path: Path, root: Path) -> bool:
    """Return True if any path component between ``root`` and ``path`` is excluded.

    Args:
        path: Candidate file path discovered under ``root``.
        root: The directory that discovery started from.

    Returns:
        True when the file lives inside an excluded directory.
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    # Check every directory component (exclude the file name itself).
    return any(part in _EXCLUDED_DIRS for part in relative.parts[:-1])


def discover_media_files(
    root: Path | str,
    extensions: Iterable[str],
    *,
    recursive: bool = True,
) -> list[Path]:
    """Discover media files under ``root`` matching ``extensions``.

    Behaviour:
        * If ``root`` is an existing file, it is returned (as a single-element
          list) when its suffix matches ``extensions``; otherwise a
          :class:`FileNotFoundError` is raised naming the supported formats.
        * If ``root`` is a directory, it is scanned for matching files. When
          ``recursive`` is True (default) the scan uses ``rglob`` and skips any
          file inside ``scratch``, ``.git`` or ``__pycache__`` directories.
          When ``recursive`` is False only the directory's direct children are
          considered.
        * Matching is case-insensitive; the returned list is stably sorted.
        * An empty result for a directory raises a :class:`FileNotFoundError`
          whose message mirrors
          :meth:`VideoTranscriber.transcribe_folder`.

    Args:
        root: File or directory to inspect.
        extensions: Iterable of accepted extensions (dot optional).
        recursive: Whether to descend into subdirectories.

    Returns:
        Sorted list of matching :class:`~pathlib.Path` objects.

    Raises:
        FileNotFoundError: If ``root`` does not exist, is a file with an
            unsupported suffix, or is a directory containing no matches.
    """
    root = Path(root)
    normalized = _normalize_extensions(extensions)
    accepted = set(normalized)
    supported_formats = ", ".join(normalized)

    if root.is_file():
        if root.suffix.lower() in accepted:
            return [root.resolve()]
        raise FileNotFoundError(
            f"Unsupported file format: {root}\n"
            f"Supported formats: {supported_formats}"
        )

    if not root.is_dir():
        raise FileNotFoundError(
            f"No supported media files found in {root}\n"
            f"Supported formats: {supported_formats}"
        )

    if recursive:
        candidates = (
            p
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in accepted
            and not _is_excluded(p, root)
        )
    else:
        candidates = (
            p
            for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in accepted
        )

    matches = sorted(candidates)

    if not matches:
        raise FileNotFoundError(
            f"No supported media files found in {root}\n"
            f"Supported formats: {supported_formats}"
        )

    return matches
