"""Shared formatting utilities used across layers."""


def humanize_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size:.1f} PB"


def humanize_duration(seconds: float) -> str:
    """Format a duration as a compact human string.

    Talking-head takes are short, so seconds/minutes dominate; hours are kept
    for completeness. Examples: 0s, 42s, 1m 5s, 1h 1m.
    """
    total = round(seconds or 0.0)
    if total < 60:
        return f"{total}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"
