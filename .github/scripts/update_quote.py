#!/usr/bin/env python3
"""
Daily quote injector for README.md.
Loads quotes from a local quotes.txt file (recommended) or falls back to a small list.
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
log = logging.getLogger("daily_quote")

DISABLE_QUOTE_UPDATE = os.environ.get("DISABLE_QUOTE_UPDATE", "false").lower() == "true"
README_PATH = "README.md"
MARKER_START = "<!-- DAILY_QUOTE_START -->"
MARKER_END = "<!-- DAILY_QUOTE_END -->"
BLOCK_PATTERN = re.compile(
    rf"({re.escape(MARKER_START)}).*?({re.escape(MARKER_END)})", re.DOTALL
)

# ----------------------------------------------------------------
# 1. THE SMART LOADER: Reads quotes from an external .txt file
#    (Place a "quotes.txt" file next to this script with 1 quote per line)
# ----------------------------------------------------------------
def load_quote_pool() -> list[str]:
    """Load quotes from quotes.txt. If missing, use a small fallback list."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    quotes_file = os.path.join(script_dir, "quotes.txt")
    
    if os.path.exists(quotes_file):
        try:
            with open(quotes_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            if lines:
                log.info(f"Loaded {len(lines)} quotes from {quotes_file}")
                return lines
        except OSError as e:
            log.warning(f"Could not read quotes.txt: {e}. Using fallback.")
    
    # Fallback (small curated list) — ensures the script never breaks
    log.warning("quotes.txt not found or empty. Using fallback list (17 quotes).")
    return [
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
        "Ruby is rubbish! PHP is phpantastic! – Nikita Popov (sarcasm)"
    ]

# ----------------------------------------------------------------
# 2. HELPER FUNCTIONS (Your existing logic, untouched)
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

def pick_quote(pool: list[str], previous_content: str | None) -> str:
    if previous_content:
        match = BLOCK_PATTERN.search(previous_content)
        if match:
            previous_block = match.group(0)
            candidates = [q for q in pool if q not in previous_block]
            if candidates:
                return random.choice(candidates)
    return random.choice(pool)

# ----------------------------------------------------------------
# 3. MAIN EXECUTION
# ----------------------------------------------------------------
def main() -> int:
    if DISABLE_QUOTE_UPDATE:
        log.warning("DISABLE_QUOTE_UPDATE is set — skipping.")
        return 0

    quote_pool = load_quote_pool()
    if not quote_pool:
        log.error("Quote pool is empty — exiting.")
        return 0

    existing_content = read_file_safely(README_PATH)
    selected = pick_quote(quote_pool, existing_content)
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
        log.error("Failed to write README — leaving existing file untouched.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
