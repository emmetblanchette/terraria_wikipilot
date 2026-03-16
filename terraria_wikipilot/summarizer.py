from __future__ import annotations

from terraria_wikipilot.models import QueryResponse


def format_response(response: QueryResponse) -> str:
    if response.error:
        return f"⚠️ {response.error}"

    if not response.page:
        if response.matches:
            lines = ["No exact page fetched. Top matches:"]
            for idx, match in enumerate(response.matches, start=1):
                lines.append(f"{idx}. {match.title} — {match.snippet}")
            return "\n".join(lines)
        return "No matching Terraria Wiki pages found."

    lines = [f"Summary: {response.page.summary}", ""]
    for section_name, body in response.page.sections.items():
        lines.append(f"{section_name}: {body}")
        lines.append("")

    if response.matches and len(response.matches) > 1:
        lines.append("Other possible matches:")
        for match in response.matches[1:4]:
            lines.append(f"• {match.title}")

    lines.append("")
    lines.append(f"Source: {response.page.title}")
    lines.append(response.page.url)
    return "\n".join(lines).strip()
