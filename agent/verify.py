import re

MONTH = re.compile(r"\d{4}-\d{2}")
DATE = re.compile(r"\b\d{4}-\d{2}(-\d{2})?\b")
DAY = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
                 r"\s+\d{1,2}(st|nd|rd|th)?\b")
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)
YEAR = re.compile(r"(?<![$\d,.])\b(19|20)\d{2}\b(?![,.]?\d)")
NUMBER = re.compile(r"(\$)?(\d[\d,]*(?:\.\d+)?)\s*(%|[KkMm]\b|thousand\b|million\b)?")
SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6}


def facts(obj, labels=None):
    labels = labels or {}
    if isinstance(obj, dict):
        labels = labels | {k: v for k, v in obj.items() if isinstance(v, str)}
        for key, value in obj.items():
            yield from facts(value, labels | {"month": key} if MONTH.fullmatch(str(key)) else labels)
    elif isinstance(obj, list):
        for value in obj:
            yield from facts(value, labels)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield abs(obj), labels


def numbers(text):
    text = YEAR.sub("", DATE.sub("", DAY.sub("", LIST_MARKER.sub("", text))))
    for _, digits, unit in NUMBER.findall(text):
        digits = digits.rstrip(",")
        decimals = len(digits.split(".")[1]) if "." in digits else 0
        yield float(digits.replace(",", "")), decimals, (unit or "").lower()


def matches(value, decimals, unit, known):
    scale = SCALE.get(unit, 1)
    candidates = [known * 100, known] if unit == "%" else [known]
    return any(abs(round(c / scale, decimals) - value) < 1e-9 for c in candidates)


def same_metric_over_time(before, after):
    for first in before:
        for second in after:
            shared = set(first) & set(second) - {"month"}
            if all(first[k] == second[k] for k in shared) and first.get("month", "") < second.get("month", " "):
                return True
    return False


def check(answer, given, calls):
    data = [(v, labels) for name, _, result in calls if name != "change" for v, labels in facts(result)]
    known = [v for _, _, result in calls for v, _ in facts(result)]
    known += [v for name, args, _ in calls if name != "change" for v, _ in facts(args)]
    known += [v for v, _, _ in numbers(given)]

    problems = []
    for value, decimals, unit in numbers(answer):
        if not any(matches(value, decimals, unit, k) for k in known):
            problems.append(f"{value:g}{unit} in the answer does not appear in any tool result.")

    for name, args, _ in calls:
        if name != "change":
            continue
        before = [labels for v, labels in data if abs(v - abs(args["before"])) < 1e-6]
        after = [labels for v, labels in data if abs(v - abs(args["after"])) < 1e-6]
        if not before or not after:
            problems.append(f"change() was called with {args}, but those values are not from tool results.")
        elif not same_metric_over_time(before, after):
            problems.append(f"change() was called with {args}. It compares one metric between two months, "
                            f"with the earlier month as before. These values are not that.")
    return problems
