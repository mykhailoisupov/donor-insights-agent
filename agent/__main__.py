import os
import sys

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from agent.analyst import ask

sys.stdout.reconfigure(encoding="utf-8")
answer, calls = ask(" ".join(sys.argv[1:]))
for call in calls:
    print(">", call)
print()
print(answer)
