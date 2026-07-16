#!/usr/bin/env python3
"""
Daily/weekly profile updater for README.md.
- Quote: rotates DAILY (random, avoids repeating the previous one)
- Currently Learning: rotates WEEKLY (deterministic by ISO week number)
- Project Highlight: rotates WEEKLY (deterministic by ISO week number)
"""

import random
import datetime
import re
import os
import sys
import logging
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("profile_updater")

DISABLE_UPDATE = os.environ.get("DISABLE_QUOTE_UPDATE", "false").lower() == "true"
README_PATH = "README.md"

MARKERS = {
    "quote": ("<!-- DAILY_QUOTE_START -->", "<!-- DAILY_QUOTE_END -->"),
    "learning": ("<!-- LEARNING_START -->", "<!-- LEARNING_END -->"),
    "project": ("<!-- PROJECT_START -->", "<!-- PROJECT_END -->"),
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def block_pattern(start: str, end: str) -> re.Pattern:
    return re.compile(rf"({re.escape(start)}).*?({re.escape(end)})", re.DOTALL)


# ----------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------
def load_lines(filename: str, fallback: list[str]) -> list[str]:
    path = os.path.join(SCRIPT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            if lines:
                log.info(f"Loaded {len(lines)} entries from {filename}")
                return lines
        except OSError as e:
            log.warning(f"Could not read {filename}: {e}. Using fallback.")
    log.warning(f"{filename} not found or empty. Using fallback list.")
    return fallback


FALLBACK_QUOTES = [
    "The only way to go fast is to go well. – Robert C. Martin",
    "Talk is cheap. Show me the code. – Linus Torvalds",
]

FALLBACK_LEARNING = [
    "🧠 Rust for systems programming",
    "🔐 Web3 security & smart contract auditing",
    "☁️ Distributed systems design",
]

FALLBACK_PROJECTS = [
    "🚀 [Project Name](https://github.com/nandasava/REPO) — one-line description here",
]


# ----------------------------------------------------------------
# File helpers
# ----------------------------------------------------------------
def read_file_safely(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.info("%s not found — will create it.", path)
        return None
    except OSError as e:
        log.error("Could not read %s: %s", path, e)
        return None


def write_file_atomically(path: str, content: str) -> bool:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_readme_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, path)
            return True
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    except OSError as e:
        log.error("Atomic write to %s failed: %s", path, e)
        return False


# ----------------------------------------------------------------
# Selection logic
# ----------------------------------------------------------------
def pick_daily(pool: list[str], previous_content: str | None, start: str, end: str) -> str:
    """Random pick, avoiding immediate repeat of the last block's content."""
    if previous_content:
        match = block_pattern(start, end).search(previous_content)
        if match:
            previous_block = match.group(0)
            candidates = [q for q in pool if q not in previous_block]
            if candidates:
                return random.choice(candidates)
    return random.choice(pool)


def pick_weekly(pool: list[str]) -> str:
    """Deterministic pick based on ISO week number — same all week, changes once a week."""
    week_number = datetime.date.today().isocalendar()[1]
    return pool[week_number % len(pool)]


def replace_block(content: str, start: str, end: str, new_inner: str) -> str:
    new_block = f"{start}\n{new_inner}\n{end}"
    pattern = block_pattern(start, end)
    if pattern.search(content):
        return pattern.sub(new_block, content, count=1)
    else:
        return content.rstrip() + "\n\n" + new_block + "\n"


# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
def main() -> int:
    if DISABLE_UPDATE:
        log.warning("DISABLE_QUOTE_UPDATE is set — skipping.")
        return 0

    quotes = load_lines("quotes.txt", FALLBACK_QUOTES)
    learning = load_lines("learning.txt", FALLBACK_LEARNING)
    projects = load_lines("projects.txt", FALLBACK_PROJECTS)

    existing_content = read_file_safely(README_PATH)
    content = existing_content if existing_content is not None else "# Hi there 👋\n\n"

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    # 1. Daily quote
    q_start, q_end = MARKERS["quote"]
    selected_quote = pick_daily(quotes, existing_content, q_start, q_end)
    content = replace_block(
        content, q_start, q_end,
        f"**Daily Coding Quote:** *{selected_quote}*\n\n*Updated: {now}*"
    )

    # 2. Weekly "Currently Learning"
    l_start, l_end = MARKERS["learning"]
    selected_learning = pick_weekly(learning)
    content = replace_block(
        content, l_start, l_end,
        f"**📚 Currently Learning:** {selected_learning}"
    )

    # 3. Weekly Project Highlight
    p_start, p_end = MARKERS["project"]
    selected_project = pick_weekly(projects)
    content = replace_block(
        content, p_start, p_end,
        f"**⭐ Project Highlight:** {selected_project}"
    )

    if write_file_atomically(README_PATH, content):
        log.info("README updated. Quote: %s | Learning: %s | Project: %s",
                  selected_quote, selected_learning, selected_project)
        return 0
    else:
        log.error("Failed to write README — leaving existing file untouched.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
