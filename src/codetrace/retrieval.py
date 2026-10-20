"""Version 1 lexical retrieval. Scores are contributions, not probabilities."""
import math
import re
from collections import Counter

ALGORITHM_VERSION = 1


def tokenize(text):
    words = []
    for value in re.findall(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[\u3400-\u9fff]+", text):
        if "\u3400" <= value[0] <= "\u9fff":
            words.extend([value] if len(value) == 1 else [value[n:n+2] for n in range(len(value)-1)])
        else:
            parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|[0-9_]|$)|[A-Z]?[a-z]+|[0-9]+", value)
            words.extend(dict.fromkeys([value.lower(), *(p.lower() for p in parts)]))
    return words


def chunks(path, text):
    lines, result, skipped = text.splitlines(), [], []
    start = 0
    while start < len(lines):
        if len(lines[start]) + 1 > 8000:
            skipped.append(start + 1)
            start += 1
            continue
        end, size = start, 0
        while end < len(lines) and end-start < 80 and size+len(lines[end])+1 <= 8000:
            size += len(lines[end]) + 1
            end += 1
        snippet = "\n".join(lines[start:end])
        result.append({"path": path, "start": start+1, "end": end, "text": snippet, "terms": Counter(tokenize(snippet))})
        if end == len(lines):
            break
        start = max(start + 1, end - 20)
    return result, sorted(set(skipped))


def rank(files, symbols, query, *, check=lambda: None):
    corpus, skipped = [], {}
    for path, file in sorted(files.items()):
        check()
        items, long_lines = chunks(path, file["text"])
        corpus.extend(items)
        if long_lines:
            skipped[path] = long_lines
    terms = set(tokenize(query))
    if not corpus or not terms:
        return [], skipped
    frequency = Counter(t for c in corpus for t in c["terms"])
    average = sum(sum(c["terms"].values()) for c in corpus) / len(corpus) or 1
    results = []
    for item in corpus:
        check()
        length, bm25 = sum(item["terms"].values()), 0.0
        for term in terms:
            tf = item["terms"][term]
            if tf:
                idf = math.log(1 + (len(corpus) - frequency[term] + .5) / (frequency[term] + .5))
                bm25 += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average))
        symbol_score = 3.0 if any(s["path"] == item["path"] and item["start"] <= s["start"] <= item["end"]
                                  and query.lower() in {s["name"].lower(), s["qualified_name"].lower()} for s in symbols) else 0.0
        path_score = 1.0 if query.lower() in item["path"].lower() else 0.0
        score = bm25 + symbol_score + path_score
        if score > 0:
            results.append({k: v for k, v in item.items() if k != "terms"} | {
                "sha256": files[item["path"]]["sha256"], "score": score,
                "contributions": {"bm25": bm25, "symbol": symbol_score, "path": path_score}})
    unique = {(r["path"], r["start"], r["end"]): r for r in results}
    return sorted(unique.values(), key=lambda r: (-r["score"], r["path"], r["start"], r["end"])), skipped
