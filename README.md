# Terraria Wikipilot

Terraria Wikipilot is a desktop overlay companion for Terraria that now uses a **local RAG knowledge base** built from Terraria Wiki pages.

## Tech stack

- Python 3.11+
- PySide6 (desktop overlay)
- requests + BeautifulSoup (wiki page download/parsing)
- sentence-transformers (`all-MiniLM-L6-v2`) for semantic retrieval
- keyboard + pynput for global hotkeys

## How it works (RAG flow)

1. Build local dataset from wiki pages (`build_knowledge_base.py`).
2. Save parsed pages to `data/wiki_pages.json`.
3. Save chunked retrieval records to `data/wiki_chunks.json`.
4. Build/load embedding cache from `data/wiki_embeddings.pkl`.
5. Query pipeline:
   - normalize query
   - retrieve top chunks semantically
   - prioritize gameplay sections (Summoning/Crafting/Obtaining/Drops)
   - format concise answer

## Project files

- `build_knowledge_base.py` — downloads and processes wiki pages locally.
- `terraria_wikipilot/rag_index.py` — embedding index + semantic `search(query, k=5)`.
- `terraria_wikipilot/query_pipeline.py` — normalize/retrieve/rank/answer backend.
- `terraria_wikipilot/query_service.py` — overlay-facing service wrapper.
- `main.py` — app entrypoint.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Build local knowledge base

```bash
python build_knowledge_base.py
```

This generates:

- `data/wiki_pages.json`
- `data/wiki_chunks.json`

Embeddings cache is created automatically at first query:

- `data/wiki_embeddings.pkl`

## Run overlay

```bash
python main.py
```

## Example queries

- `how do i summon duke fishron`
- `how to summon eye of cthulhu`
- `best way to get obsidian`

## Notes

- If no local KB exists, the app prompts you to run `python build_knowledge_base.py`.
- macOS hotkeys use `pynput`; if permissions fail, enable:
  - System Settings → Privacy & Security → Accessibility
