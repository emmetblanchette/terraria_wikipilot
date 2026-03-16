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


## Beginner test guide (with Terraria running)

If you are new to coding, follow these exact steps.

### 1) One-time install

1. Install **Python 3.11+** from https://www.python.org/downloads/
   - During install on Windows, check **“Add Python to PATH”**.
2. Download this project folder to your PC (or clone it).
3. Open a terminal in the project folder:
   - **Windows**: File Explorer → open the folder → click address bar → type `cmd` → Enter.
   - **macOS/Linux**: open Terminal and `cd` into the folder.
4. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

5. Activate it:

   - Windows (cmd):

     ```bash
     .venv\Scripts\activate
     ```

   - macOS/Linux:

     ```bash
     source .venv/bin/activate
     ```

6. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### 2) Start the overlay

1. In the same terminal (with virtual env active), run:

   ```bash
   python app.py
   ```

2. You should see a small **Terraria Wikipilot** window in the bottom-right corner.

### 3) Launch Terraria and test

1. Start Terraria normally (Steam or standalone).
2. While Terraria is focused, press **Ctrl+Alt+T** to toggle the overlay.
3. Ask a question in the box, for example:
   - `How do I summon the Eye of Cthulhu?`
   - `What drops from Queen Bee?`
4. Press **Enter** (or click **Ask**).
5. Confirm you get:
   - a short summary first
   - source page title
   - wiki URL

### 4) Quick behavior checklist

- Toggle show/hide instantly with hotkey.
- Use **–** to collapse and **+** to expand.
- **Clear** empties input/output.
- **Copy Link** copies the source URL.
- **Open Page** opens the full wiki page in your browser.

### 5) If something does not work

- **Hotkey does nothing**:
  - Change to borderless/windowed Terraria and retry.
  - On Linux Wayland, global hotkeys may be restricted; try X11.
  - Change hotkey in `.env` (example: `WIKIPILOT_HOTKEY=ctrl+shift+f1`) and restart app.
- **Overlay not visible over game**:
  - Alt+Tab to overlay once, then back to Terraria.
  - Try running Terraria in borderless window mode.
- **No answers / errors**:
  - Check your internet connection.
  - Terraria Wiki access may be blocked by a proxy/firewall.

### 6) Stop the app

- Close the overlay window, or press `Ctrl+C` in the terminal.

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
