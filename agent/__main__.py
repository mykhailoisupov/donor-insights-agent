import os
import sys

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from agent.analyst import ask

sys.stdout.reconfigure(encoding="utf-8")
result = ask(" ".join(sys.argv[1:]))
for call in result["calls"]:
    print(">", call)
print()
print(result["answer"])
print()
print(f"verifier: {'passed' if not result['problems'] else 'FAILED'}, retries: {result['retries']}")
for problem in result["problems"]:
    print("  -", problem)
