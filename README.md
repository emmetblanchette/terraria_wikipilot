# Terraria Wikipilot

Terraria Wikipilot is a desktop overlay prototype for gameplay assistance: hit a global hotkey, ask a Terraria question in natural language, and get concise answers backed by live Terraria Wiki lookups.

## Proposed stack (and why)

- **Python 3.11+**: fast local iteration and good desktop tooling.
- **PySide6 (Qt)**: reliable always-on-top desktop overlay behavior, compact custom UI, keyboard/mouse input.
- **keyboard**: global hotkey registration for quick show/hide.
- **requests + BeautifulSoup**: practical live wiki lookup + parsing pipeline (search, fetch, extract).
- **python-dotenv**: simple config overrides without code edits.

This avoids risky game injection/hooking and delivers a real, usable overlay window.

## Project structure

```text
.
├── app.py
├── .env.example
├── requirements.txt
└── terraria_wikipilot/
    ├── __init__.py
    ├── config.py            # settings + environment mapping
    ├── hotkey_manager.py    # global hotkey registration
    ├── logging_utils.py     # logging setup
    ├── models.py            # data models
    ├── query_service.py     # query → search → fetch orchestration
    ├── summarizer.py        # concise gameplay-oriented formatting
    ├── wiki_client.py       # Terraria Wiki API + scraping
    └── overlay/
        └── window.py        # overlay UI + async query handling
```

## How the overlay works

- Starts as a **small always-on-top window**.
- Anchors to the **bottom-right** of your primary screen.
- Includes a **collapsed mode** (tiny header-only strip) and expanded mode.
- Uses a **global hotkey** (default `Ctrl+Alt+T`) to show/hide instantly.
- Keeps UI responsive during fetches via Qt thread pool workers.
- Has:
  - input field + Enter-to-submit
  - loading indicator
  - scrollable answer area
  - clear button
  - recent queries dropdown
  - copy-link and open-page actions

## Wiki retrieval pipeline

Each question runs a clear flow:

1. **User query**
2. **Wiki search** using `action=query&list=search`
3. **Page fetch** for top match using `action=parse`
4. **Summarization/formatting** into short gameplay-focused output

Behavior notes:
- Includes source page title + URL in results.
- If several pages might match, shows top alternatives.
- On network/parse failures, surfaces explicit error messages instead of guessing facts.

## Setup

1. Create and activate a virtual env (recommended).
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Optional config:

   ```bash
   cp .env.example .env
   ```

   Adjust values like `WIKIPILOT_HOTKEY` or `WIKIPILOT_OPACITY`.

4. Run:

   ```bash
   python app.py
   ```

## Hotkey behavior

- Default hotkey: `Ctrl+Alt+T`
- When pressed:
  - if hidden → shows overlay, brings it to front, re-anchors to bottom-right
  - if visible → hides overlay instantly

## Known limitations / tradeoffs

- Global hotkeys can vary by OS/session permissions (especially Linux Wayland).
- “Stay on top while Terraria is focused” is implemented as a practical always-on-top desktop overlay, not process-specific game hooking.
- Summary extraction is heuristic; pages with unusual wiki markup may produce less clean snippets.
- Section extraction currently targets a few useful headings (`Drops`, `Crafting`, `Tips`, `Notes`, etc.) and may miss others.

## Next improvements

- Make hotkey configurable from UI (not just env).
- Add optional click-through mode when inactive.
- Add fuzzy intent routing for “best/early/hardmode” style queries.
- Add per-section cards with richer structured extraction.
- Add small local cache for faster repeated lookups.
