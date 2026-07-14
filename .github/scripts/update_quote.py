import random
import datetime
import re
import os

# 1. Your personal quote library (add 50+ quotes for variety)
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
    "Ruby is rubbish! PHP is phpantastic! – Nikita Popov (sarcasm)"
]

# 2. Pick a random quote and timestamp
selected = random.choice(QUOTES)
now = datetime.datetime.now().strftime("%B %d, %Y at %H:%M UTC")

# 3. Define the block we will inject into README.md
new_block = f"""<!-- DAILY_QUOTE_START -->
**Daily Coding Quote:** *{selected}*

*Updated: {now}*
<!-- DAILY_QUOTE_END -->"""

readme_path = "README.md"

# 4. If README doesn't exist, create a basic one
if not os.path.exists(readme_path):
    with open(readme_path, "w") as f:
        f.write("# Hi there 👋\n\n" + new_block)
    print("README created with new quote.")
    exit(0)

# 5. Read existing README
with open(readme_path, "r") as f:
    content = f.read()

# 6. Replace the old block between the markers (or append if markers missing)
pattern = r"(<!-- DAILY_QUOTE_START -->).*?(<!-- DAILY_QUOTE_END -->)"
if re.search(pattern, content, re.DOTALL):
    updated_content = re.sub(pattern, new_block, content, flags=re.DOTALL)
else:
    # If markers don't exist, append the block to the end
    updated_content = content + "\n\n" + new_block

# 7. Write it back
with open(readme_path, "w") as f:
    f.write(updated_content)

print(f"✅ README updated with: {selected}")
