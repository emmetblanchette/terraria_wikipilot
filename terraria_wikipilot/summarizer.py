from __future__ import annotations

"""Response formatting helpers."""

import re

from terraria_wikipilot.models import QueryResponse


def _to_bullets(text: str, max_items: int = 5) -> list[str]:
    """Turn paragraph-like text into short bullet points when possible."""
    chunks = re.split(r"(?<=[.!?])\s+|;", text)
    bullets = [chunk.strip(" -•\t\n") for chunk in chunks if len(chunk.strip()) > 10]
    return bullets[:max_items]


def format_response(response: QueryResponse) -> str:
    """Render clean gameplay-focused output for the overlay."""
    if response.error:
        return f"⚠️ {response.error}"

    if not response.page:
        if response.matches:
            lines = ["No exact page fetched. Top matches:"]
            for idx, match in enumerate(response.matches[:5], start=1):
                lines.append(f"{idx}. {match.title}")
            return "\n".join(lines)
        return "No matching Terraria Wiki pages found."

    section_name = next(iter(response.page.sections.keys()), "Summary")
    section_body = next(iter(response.page.sections.values()), response.page.summary)
    bullets = _to_bullets(section_body)

    lines = [response.page.title, "", f"{section_name}:" if section_name else "Summary:"]
    if len(bullets) > 1:
        for bullet in bullets:
            lines.append(f"• {bullet}")
    else:
        lines.append(response.page.summary)

    lines += ["", "Source:", response.page.url]
    return "\n".join(lines).strip()
