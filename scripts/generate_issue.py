#!/usr/bin/env python3
"""
Generate one AI Pulse Weekly issue.

Pulls recent entries from the RSS/Atom feeds listed in feeds.yaml, compiles
them into a Markdown digest, writes it to issues/<date>.md, and (if
BUTTONDOWN_API_KEY is set) creates it as a *draft* email in Buttondown for
human review — it never sends automatically.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import tz

ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = Path(__file__).resolve().parent / "feeds.yaml"
ISSUES_DIR = ROOT / "issues"
BUTTONDOWN_API_BASE = os.environ.get("BUTTONDOWN_API_BASE", "https://api.buttondown.email/v1")
REQUEST_TIMEOUT = 15
SUMMARY_MAX_CHARS = 220


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("feeds", [])


def clean_summary(raw_html):
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_MAX_CHARS:
        text = text[:SUMMARY_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    return None


def fetch_source_items(source, cutoff):
    name, url = source["name"], source["url"]
    items = []
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "AIPulseWeekly/1.0 (+newsletter digest bot)"},
        )
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:  # noqa: BLE001 - one bad feed must not kill the run
        print(f"  ! skipping {name}: {exc}", file=sys.stderr)
        return items

    for entry in parsed.entries:
        published = entry_datetime(entry)
        if published is None or published < cutoff:
            continue
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue
        items.append(
            {
                "source": name,
                "title": re.sub(r"\s+", " ", title).strip(),
                "link": link,
                "published": published,
                "summary": clean_summary(getattr(entry, "summary", "")),
            }
        )
    return items


def dedupe(items):
    seen = set()
    unique = []
    for item in items:
        key = item["link"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def render_markdown(by_source, issue_date, days):
    lines = [
        f"# AI Pulse Weekly — {issue_date.strftime('%B %d, %Y')}",
        "",
        f"_Updates from across the AI field over the last {days} days._",
        "",
    ]
    any_items = any(items for items in by_source.values())
    if not any_items:
        lines.append("_No new items found in this window — check feed sources._")
        return "\n".join(lines) + "\n"

    for source_name, items in by_source.items():
        if not items:
            continue
        lines.append(f"## {source_name}")
        lines.append("")
        for item in items:
            date_str = item["published"].astimezone(tz.UTC).strftime("%b %d")
            line = f"- **[{item['title']}]({item['link']})** ({date_str})"
            if item["summary"]:
                line += f" — {item['summary']}"
            lines.append(line)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def post_draft_to_buttondown(subject, body_markdown):
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print("BUTTONDOWN_API_KEY not set — skipping draft creation (digest file was still written).")
        return False

    try:
        resp = requests.post(
            f"{BUTTONDOWN_API_BASE}/emails",
            headers={"Authorization": f"Token {api_key}"},
            json={"subject": subject, "body": body_markdown, "status": "draft"},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code >= 400:
            print(f"Buttondown API error {resp.status_code}: {resp.text}", file=sys.stderr)
            return False
        print("Created draft issue in Buttondown for review.")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Could not reach Buttondown API: {exc}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="look-back window in days")
    parser.add_argument("--max-per-source", type=int, default=8, help="cap items per source")
    parser.add_argument("--output-dir", default=str(ISSUES_DIR), help="directory for the digest file")
    parser.add_argument("--no-draft", action="store_true", help="skip creating a Buttondown draft")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    issue_date = datetime.now(timezone.utc)

    feeds = load_feeds()
    by_source = {}
    print(f"Fetching {len(feeds)} sources (look-back: {args.days} days)...")
    for source in feeds:
        items = fetch_source_items(source, cutoff)
        items = dedupe(items)
        items.sort(key=lambda i: i["published"], reverse=True)
        by_source[source["name"]] = items[: args.max_per_source]
        print(f"  {source['name']}: {len(by_source[source['name']])} item(s)")

    markdown = render_markdown(by_source, issue_date, args.days)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{issue_date.strftime('%Y-%m-%d')}.md"
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote digest to {out_path}")

    if not args.no_draft:
        subject = f"AI Pulse Weekly — {issue_date.strftime('%B %d, %Y')}"
        post_draft_to_buttondown(subject, markdown)


if __name__ == "__main__":
    main()
