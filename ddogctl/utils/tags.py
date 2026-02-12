"""Tag processing utilities (inspired by dogshell)."""


def parse_tags(tags_str: str) -> list[str]:
    """Parse comma-separated tags with deduplication and whitespace stripping.

    Inspired by dogshell's metric.py tag processing pattern.

    Args:
        tags_str: Comma-separated tags like "service:web,env:prod, team:platform"

    Returns:
        Deduplicated, sorted list of tags
    """
    if not tags_str:
        return []

    # Split, strip whitespace, deduplicate
    tags = set(t.strip() for t in tags_str.split(",") if t.strip())

    # Sort for consistency
    return sorted(tags)


def format_tags_for_display(tags: list[str], max_tags: int = 3) -> str:
    """Format tags for display with truncation.

    Args:
        tags: List of tags
        max_tags: Maximum tags to show (default 3)

    Returns:
        Formatted string like "service:web, env:prod, +2 more"
    """
    if not tags:
        return ""

    if len(tags) <= max_tags:
        return ", ".join(tags)

    shown = ", ".join(tags[:max_tags])
    remaining = len(tags) - max_tags
    return f"{shown}, +{remaining} more"
