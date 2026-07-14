#!/usr/bin/env python3
"""
Daily quote injector for README.md.

Design notes (read before touching):
- This script must NEVER raise an uncaught exception. A bad run should degrade
  gracefully (skip the update, log why, exit 0) rather than fail the whole
  Action, because a red workflow run for a cosmetic README quote is not worth
  blocking future scheduled runs or alarming anyone.
- All file writes are atomic (write to a temp file, then os.replace) so a
  crash mid-write can never leave README.md truncated or corrupted.
"""

import random
import datetime
import re
import os
import sys
import logging
import tempfile

# --- Structured logging so failures are diagnosable from the Actions log tab ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("daily_quote")

# Feature toggle: lets you disable the quote-rotation logic in an emergency
# without commenting out code. Set DISABLE_QUOTE_UPDATE=true as a repo/workflow
# env var to make this a safe no-op.
DISABLE_QUOTE_UPDATE = os.environ.get("DISABLE_QUOTE_UPDATE", "false").lower() == "true"

README_PATH = "README.md"
MARKER_START = "<!-- DAILY_QUOTE_START -->"
MARKER_END = "<!-- DAILY_QUOTE_END -->"
BLOCK_PATTERN = re.compile(
    rf"({re.escape(MARKER_START)}).*?({re.escape(MARKER_END)})", re.DOTALL
)

# Curated quote library — kept deliberately small and high-signal rather than
# padded with filler duplicates.
QUOTES = [
    "The only way to go fast is to go well. – Robert C. Martin",
    "Simplicity is the soul of efficiency. – Austin Freeman",
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. – Martin Fowler",
    "First, solve the problem. Then, write the code. – John Johnson",
    "Make it work, make it right, make it fast. – Kent Beck",
    "Code is like humor. When you have to explain it, it's bad. – Cory House",
    "Sometimes it's better to leave something alone, to pause, and that's very true of programming. – Joyce Park",
    "Programming isn't about what you know; it's about what you can figure out. – Chris Pine",
    "Clean code always looks like it was written by someone who cares. – Robert C. Martin",
    "Talk is cheap. Show me the code. – Linus Torvalds",
    "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away. – Antoine de Saint-Exupéry",
    "The computer was born to solve problems that did not exist before. – Bill Gates",
    "Debugging is twice as hard as writing the code in the first place. – Brian Kernighan",
    "If you optimize everything, you will always be unhappy. – Donald Knuth",
    "The best error message is the one that never shows up. – Thomas Fuchs",
    "Measuring programming progress by lines of code is like measuring aircraft building progress by weight. – Bill Gates",
]


def read_file_safely(path: str) -> str | None:
    """Read a file, returning None (not raising) if it doesn't exist or can't be read."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.info("%s not found — will create it.", path)
        return None
    except OSError as e:
        # Fragile point: permissions issues, disk problems, etc. Never crash — log and bail.
        log.error("Could not read %s: %s", path, e)
        return None


def write_file_atomically(path: str, content: str) -> bool:
    """
    Write content to `path` atomically: write to a temp file in the same
    directory, flush + fsync, then os.replace() over the target. This means
    a crash mid-write can never leave a half-written README.md.
    Returns True on success, False on any failure (never raises).
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_readme_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, path)  # atomic on POSIX
            return True
        except Exception:
            # Clean up the temp file if the replace step never happened.
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    except OSError as e:
        log.error("Atomic write to %s failed: %s", path, e)
        return False


def pick_quote(previous_content: str | None) -> str:
    """Pick a random quote, avoiding an immediate repeat of yesterday's quote if possible."""
    if previous_content:
        match = BLOCK_PATTERN.search(previous_content)
        if match:
            previous_block = match.group(0)
            candidates = [q for q in QUOTES if q not in previous_block]
            if candidates:  # only filter if it doesn't empty the pool
                return random.choice(candidates)
    return random.choice(QUOTES)


def main() -> int:
    if DISABLE_QUOTE_UPDATE:
        log.warning("DISABLE_QUOTE_UPDATE is set — skipping update (feature toggle active).")
        return 0

    if not QUOTES:
        # Defensive: should never happen, but a safe default beats a crash.
        log.error("Quote library is empty — nothing to write. Exiting cleanly.")
        return 0

    existing_content = read_file_safely(README_PATH)
    selected = pick_quote(existing_content)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    new_block = f"{MARKER_START}\n**Daily Coding Quote:** *{selected}*\n\n*Updated: {now}*\n{MARKER_END}"

    if existing_content is None:
        final_content = "# Hi there 👋\n\n" + new_block + "\n"
        action = "created"
    elif BLOCK_PATTERN.search(existing_content):
        final_content = BLOCK_PATTERN.sub(new_block, existing_content, count=1)
        action = "updated"
    else:
        final_content = existing_content.rstrip() + "\n\n" + new_block + "\n"
        action = "appended"

    if write_file_atomically(README_PATH, final_content):
        log.info("README %s successfully with quote: %s", action, selected)
        return 0
    else:
        # Graceful degradation: log clearly, but exit 0 so the workflow doesn't
        # red-X over a cosmetic feature. Change to `return 1` if you'd rather
        # the Action visibly fail on write errors.
        log.error("Failed to write README — leaving existing file untouched.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
