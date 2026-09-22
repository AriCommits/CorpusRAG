"""Media file discovery for video processing.

Provides :func:`discover_media_files`, a helper for resolving a user-supplied
path (a single file or a directory) into a sorted list of media files matching
a set of extensions. Its directory-empty error shape is intentionally
compatible with :meth:`tools.video.transcribe.VideoTranscriber.transcribe_folder`
so callers can rely on a consistent message.
"""

from collections.abc import Iterable
from pathlib import Path

__all__ = ["MAX_DISCOVERED_FILES", "discover_media_files"]

# Directory names excluded from recursive traversal.
_EXCLUDED_DIRS = frozenset({"scratch", ".git", "__pycache__"})

# Hard cap so a symlink-to-root tree cannot queue the whole disk.
MAX_DISCOVERED_FILES = 500


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
    max_files: int = MAX_DISCOVERED_FILES,
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
        max_files: Maximum number of matches to return. Exceeding the cap
            raises ``RuntimeError`` rather than silently truncating.

    Returns:
        Sorted list of matching :class:`~pathlib.Path` objects.

    Raises:
        FileNotFoundError: If ``root`` does not exist, is a file with an
            unsupported suffix, or is a directory containing no matches.
        RuntimeError: If more than ``max_files`` matches are found.
    """
    root = Path(root)
    normalized = _normalize_extensions(extensions)
    accepted = set(normalized)
    supported_formats = ", ".join(normalized)

    if root.is_file():
        if root.is_symlink():
            raise FileNotFoundError(
                f"Unsupported file format: {root}\nSupported formats: {supported_formats}"
            )
        if root.suffix.lower() in accepted:
            return [root.resolve()]
        raise FileNotFoundError(
            f"Unsupported file format: {root}\nSupported formats: {supported_formats}"
        )

    if not root.is_dir():
        raise FileNotFoundError(
            f"No supported media files found in {root}\nSupported formats: {supported_formats}"
        )

    root_resolved = root.resolve()

    def _accept(path: Path) -> bool:
        if path.is_symlink() or not path.is_file():
            return False
        if path.suffix.lower() not in accepted:
            return False
        if recursive and _is_excluded(path, root):
            return False
        try:
            path.resolve().relative_to(root_resolved)
        except ValueError:
            return False
        return True

    if recursive:
        raw = (p for p in root.rglob("*") if _accept(p))
    else:
        raw = (p for p in root.iterdir() if _accept(p))

    matches: list[Path] = []
    overflow = False
    for path in raw:
        if len(matches) >= max_files:
            overflow = True
            break
        matches.append(path)

    if overflow:
        raise RuntimeError(
            f"Found more than {max_files} media files under {root}. "
            "Narrow the folder or pass --no-recursive."
        )

    matches = sorted(matches)

    if not matches:
        raise FileNotFoundError(
            f"No supported media files found in {root}\nSupported formats: {supported_formats}"
        )

    return matches
