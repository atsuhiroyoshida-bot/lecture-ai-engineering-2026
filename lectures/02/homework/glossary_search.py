"""第2回 宿題（発展）: 用語集を検索して答える、いちばん簡単な仕組み。

質問の中に用語集の語か別名が入っていれば、その語の説明文をそのまま返す。
入っていなければ「用語集に見つかりません。」と返す。
学習させたモデルと同じ25問に答えさせ、ノートブックと同じ採点で比べる。

照合のしかたを2通り試す。
- 単純な部分一致：名前が質問のどこかに含まれていれば当たり
- 英字の区切りつき：英字の名前は、前後が英数字でないときだけ当たり（日本語の名前は部分一致のまま）

使い方:
    python3 glossary_search.py <glossary.json> <eval_questions.json> <結果を書き出す json>
"""

import json
import re
import sys
import time

NOT_FOUND = "用語集に見つかりません。"


def build_index(terms):
    """語と別名を、(名前, 語の情報) の組の一覧にする"""
    return [(name, t) for t in terms for name in [t["term"], *t.get("aliases", [])]]


def is_ascii(name):
    return all(ord(c) < 128 for c in name)


def matches(name, question, word_boundary):
    if is_ascii(name):
        if word_boundary:
            # 前後が英数字でないときだけ当たりにする（1文字の別名「r」が「DoRA」の中に当たるのを防ぐ）
            pattern = r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])"
            return re.search(pattern, question, flags=re.IGNORECASE) is not None
        return name.lower() in question.lower()
    return name in question


def search(question, index, word_boundary):
    hits = [(name, t) for name, t in index if matches(name, question, word_boundary)]
    if not hits:
        return NOT_FOUND, None, None
    name, t = max(hits, key=lambda h: len(h[0]))   # 当たった名前のうち、いちばん長いものを選ぶ
    return t["definition"], t["term"], name


def evaluate(questions, refusal, index, word_boundary):
    rows = []
    t0 = time.perf_counter()
    for q in questions:
        answer, found_term, matched_name = search(q["question"], index, word_boundary)
        row = {"id": q["id"], "category": q["category"], "term": q["term"], "question": q["question"],
               "found_term": found_term, "matched_name": matched_name, "raw": answer}
        if q["category"] in ("same", "paraphrase"):
            row["hit"] = [w for w in q["must_include"] if w in answer]
            row["ok"] = len(row["hit"]) == len(q["must_include"])
        else:
            row["ok"] = any(p in answer for p in refusal)   # 用語集に無い語は「見つからない」と返したら ○
        rows.append(row)
    seconds = time.perf_counter() - t0
    summary = {"label": "search_word_boundary" if word_boundary else "search_substring",
               "seconds": round(seconds, 6)}
    for cat in ["same", "paraphrase", "unknown"]:
        sub = [r for r in rows if r["category"] == cat]
        summary[cat] = f"{sum(r['ok'] for r in sub)}/{len(sub)}"
    return summary, rows


def main():
    glossary_path, eval_path, out_path = sys.argv[1:4]
    terms = json.load(open(glossary_path, encoding="utf-8"))["terms"]
    ev = json.load(open(eval_path, encoding="utf-8"))
    index = build_index(terms)
    results = {}
    for word_boundary in (False, True):
        summary, rows = evaluate(ev["questions"], ev["refusal_phrases"], index, word_boundary)
        results[summary["label"]] = {"summary": summary, "rows": rows}
        print(json.dumps(summary, ensure_ascii=False))
        for r in rows:
            if not r["ok"] or (r["category"] == "unknown" and r["found_term"]):
                print(f"  × {r['id']} {r['question']} | 当たった名前: {r['matched_name']}（{r['found_term']}）")
    json.dump(results, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("保存:", out_path)


if __name__ == "__main__":
    main()
