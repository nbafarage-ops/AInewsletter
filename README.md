# AI Pulse Weekly

A weekly newsletter that aggregates updates from across the AI field —
model releases, research, and industry news — into one digest, with a
subscribe page and automated content generation.

## How it works

- **`docs/`** — the public landing page with an embedded subscribe form,
  deployable as a static site (e.g. via GitHub Pages).
- **`scripts/generate_issue.py`** — pulls recent posts from the RSS feeds
  listed in `scripts/feeds.yaml`, compiles them into a Markdown digest,
  writes it to `issues/<date>.md`, and creates it as a **draft** email in
  Buttondown for you to review and send.
- **`.github/workflows/newsletter.yml`** — runs the script every Monday
  (and on demand) and commits the generated digest.
- **Buttondown** — hosts your subscriber list, handles unsubscribes, and
  sends the actual emails. This repo only ever creates *drafts*; nothing
  is emailed to subscribers without you clicking Send in the Buttondown
  dashboard.

## Setup

### 1. Create a Buttondown account

Done — account created, username is `AIPulse`. Generate an API key under
Settings → Programming (needed for step 3, optional for now).

### 2. Wire up the subscribe form

Done — `docs/index.html` points at `buttondown.com/AIPulse`.

### 3. Add the API key as a GitHub secret

In this repository's Settings → Secrets and variables → Actions, add a
secret named `BUTTONDOWN_API_KEY` with the API key from step 1. This lets
the scheduled workflow create draft issues automatically. If you skip
this, the workflow will still generate and commit the digest file — it
just won't push a draft to Buttondown.

### 4. Enable GitHub Pages

In Settings → Pages, set the source to the `docs/` folder on your default
branch. Your subscribe page will be live at
`https://<you>.github.io/<repo>/`.

### 5. Adjust your sources (optional)

Edit `scripts/feeds.yaml` to add, remove, or reorder RSS sources. Each
entry becomes a section in the digest. RSS URLs occasionally change —
if a source stops showing up, check whether its feed URL moved.

## Running it locally

```bash
cd scripts
pip install -r requirements.txt
python generate_issue.py --days 7          # writes issues/<date>.md, posts a draft
python generate_issue.py --days 7 --no-draft  # local test, skips Buttondown
```

## Publishing an issue

1. Wait for (or manually trigger, via the Actions tab → "Generate
   Newsletter Issue" → "Run workflow") the weekly run.
2. Review the generated draft in your Buttondown dashboard — trim,
   reorder, or add commentary as you like.
3. Click Send. Buttondown delivers it to every subscriber and handles
   unsubscribe links automatically.

## Notes

- The generator only ever creates **drafts** — sending is always a manual,
  human step in Buttondown.
- `BUTTONDOWN_API_BASE` can be overridden via environment variable if
  Buttondown's API host changes; check their current API docs if draft
  creation starts failing.
