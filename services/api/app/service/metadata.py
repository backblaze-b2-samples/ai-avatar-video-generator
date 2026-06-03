"""Lightweight file metadata extraction.

Trimmed from the starter's image/EXIF/PDF inspector down to what this app
actually needs: a checksum for every upload, plus the playback duration of a
rendered take. Duration is read straight from the MP4 container header (the
`mvhd` movie-header atom) — no decoding, no ffmpeg, no extra dependency — so it
is cheap enough to run inline on every render and on video uploads.
"""

import hashlib
import logging
import struct
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes, humanize_duration

logger = logging.getLogger(__name__)


def extract_video_duration(file_data: bytes) -> float | None:
    """Return the duration (seconds) of an MP4/MOV from its `mvhd` atom.

    Walks the top-level atom list to find `moov`, then its `mvhd` child, and
    reads the timescale + duration fields. Returns None if the structure isn't
    recognised (e.g. fragmented MP4 with no top-level mvhd). Header-only — never
    reads more than the atom sizes declare.
    """
    try:
        moov = _find_atom(file_data, b"moov", 0, len(file_data))
        if moov is None:
            return None
        moov_start, moov_end = moov
        mvhd = _find_atom(file_data, b"mvhd", moov_start, moov_end)
        if mvhd is None:
            return None
        body = mvhd[0]
        version = file_data[body]
        if version == 1:
            # version(1) + flags(3) + created(8) + modified(8)
            ts_off = body + 4 + 8 + 8
            timescale = struct.unpack(">I", file_data[ts_off:ts_off + 4])[0]
            duration = struct.unpack(">Q", file_data[ts_off + 4:ts_off + 12])[0]
        else:
            ts_off = body + 4 + 4 + 4
            timescale = struct.unpack(">I", file_data[ts_off:ts_off + 4])[0]
            duration = struct.unpack(">I", file_data[ts_off + 4:ts_off + 8])[0]
        if not timescale:
            return None
        return round(duration / timescale, 2) or None
    except Exception:
        logger.warning("Video duration extraction failed", exc_info=True)
        return None


def _find_atom(
    data: bytes, name: bytes, start: int, end: int
) -> tuple[int, int] | None:
    """Find an atom by 4-byte `name` within [start, end).

    Returns (body_start, atom_end) where body_start is just past the 8-byte
    atom header. Atoms are `[size:4][type:4][body...]`.
    """
    pos = start
    while pos + 8 <= end:
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        atom_type = data[pos + 4:pos + 8]
        if size == 1:  # 64-bit extended size
            size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            body = pos + 16
        else:
            body = pos + 8
        if size < 8:
            return None
        if atom_type == name:
            return body, pos + size
        pos += size
    return None


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
) -> FileMetadataDetail:
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    duration_seconds: float | None = None
    if content_type.startswith("video/") or extension in ("mp4", "mov", "m4v"):
        duration_seconds = extract_video_duration(file_data)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=datetime.now(UTC),
        duration_seconds=duration_seconds,
        duration_human=(
            humanize_duration(duration_seconds)
            if duration_seconds is not None
            else None
        ),
    )
