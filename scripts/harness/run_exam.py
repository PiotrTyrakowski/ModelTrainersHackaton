"""Solve an organiser-format exam.json with a small model behind an OpenAI-compatible server (llama-server).

python run_exam.py --exam exam.json --out answers.json --server http://127.0.0.1:8080/v1 \
    [--retrieval data/raw/retrieval/wiki-ehistoria-v1/index.sqlite --k 4] [--votes 5] [--images] \
    [--essay-bank data/essay-bank/v2/*.jsonl]
Output: {"exam_id", "answers": [{"id", "answer"}]} plus <out>.trace.json (raw samples, contexts, essay choice).
Essays are never generated: they are selected from the prepared bank.
"""
import argparse, base64, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import SYSTEM, kind, user_text, vote_closed, medoid

ap = argparse.ArgumentParser()
ap.add_argument("--exam", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--server", default="http://127.0.0.1:8080/v1")
ap.add_argument("--model", default="local")
ap.add_argument("--retrieval", default=None, help="sqlite index with a chunks table")
ap.add_argument("--k", type=int, default=4)
ap.add_argument("--ctx-chars", type=int, default=1300)
ap.add_argument("--votes", type=int, default=1, help="samples for closed items (majority vote)")
ap.add_argument("--open-samples", type=int, default=1, help=">1: medoid of samples for open items")
ap.add_argument("--temperature", type=float, default=0.7)
ap.add_argument("--max-tokens", type=int, default=400)
ap.add_argument("--images", action="store_true")
ap.add_argument("--essay-bank", nargs="*", default=None)
ap.add_argument("--essay-judge", type=int, default=0, help=">0: the model picks among the top lexical candidates per topic")
ap.add_argument("--essay-k", type=int, default=5, help="lexical candidates per topic shown to the judge")
ap.add_argument("--essay-final", choices=["judge", "lexical"], default="lexical", help="how the topic is chosen among per-topic finalists")
ap.add_argument("--workers", type=int, default=8)
ap.add_argument("--only", default=None, help="comma-separated item ids")
ap.add_argument("--kinds", default=None, help="comma-separated item kinds to answer (closed,open,essay)")
ap.add_argument("--neutral-format", action="store_true",
                help="show closed-item answer syntax without the example values (e.g. '1: P albo F')")
args = ap.parse_args()

exam = json.loads(Path(args.exam).read_text(encoding="utf-8"))
exam_dir = Path(args.exam).resolve().parent
items = [it for it in exam["items"] if (not args.only or it["id"] in args.only.split(","))
         and (not args.kinds or kind(it) in args.kinds.split(","))]

retriever = None
if args.retrieval:
    import sqlite3
    sys.path.insert(0, str(HERE.parent / "checkpoints"))
    from focused_retrieval import FocusedRetriever
    class _C: pass
    c = _C(); c.db = sqlite3.connect(args.retrieval, check_same_thread=False)
    retriever = FocusedRetriever(c)

bank = None
if args.essay_bank:
    from essay_bank import Bank
    bank = Bank(args.essay_bank)


def context_for(it):
    if not retriever:
        return None
    class Q: pass
    # written image descriptions are an extraction aid, not exam content: never let them steer retrieval
    q = Q(); q.prompt = it["question"]; q.source_text = re.sub(r"\[Obraz:[^\]]*\]", "", it.get("source_text", "") or "")
    passages, _ = retriever.search(q, k=args.k)
    if not passages:
        return None
    out = []
    for p in passages:
        title, _, body = p["text"].partition("\n")
        out.append(f"[{title.split(' — ')[0].strip()}] " + " ".join(body.split())[: args.ctx_chars])
    return "\n\n".join(out)


def image_parts(it):
    parts = []
    for im in it.get("images", []):
        p = im["path"] if isinstance(im, dict) else im
        p = Path(p) if Path(p).is_absolute() else exam_dir / p
        if p.exists():
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()}})
    return parts


def chat(msgs, temperature, max_tokens, seed):
    body = {"model": args.model, "messages": msgs, "temperature": temperature, "top_p": 0.95 if temperature > 0 else 1.0,
            "max_tokens": max_tokens, "seed": seed, "repeat_penalty": 1.05,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(args.server.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"]["content"] or "", d["choices"][0].get("finish_reason")
        except Exception as e:  # transient server errors
            err = e; time.sleep(2 + 3 * attempt)
    return "", f"error: {err}"


def strip_think(t):
    return re.sub(r"(?s)<think>.*?</think>", "", t).strip()


def normalise_closed(ans, fmt):
    """Coerce a closed answer to the syntax shown in answer_format (labels and value set)."""
    ans = re.sub(r"[*_`#]", "", ans or "")
    fl = [l.strip() for l in fmt.strip().splitlines() if l.strip()]
    m = [re.match(r"^([0-9A-Za-z]{1,3})\s*:\s*(.+)$", l) for l in fl]
    if fl and all(m):
        labels = [x.group(1) for x in m]
        pf = all(x.group(2) in ("P", "F") for x in m)
        got = {}
        for l in ans.splitlines():
            mm = re.match(r"^\s*([0-9A-Za-z]{1,3})\s*[:.)\-–]\s*(.+?)\s*$", l)
            if mm and mm.group(1) in labels and mm.group(1) not in got:
                v = mm.group(2).strip()
                if pf:
                    v = "P" if re.match(r"(?i)^(p|prawda)", v) else ("F" if re.match(r"(?i)^(f|fałsz)", v) else v[:1].upper())
                else:
                    v = re.split(r"[\s,;.]", v)[0]
                got[mm.group(1)] = v
        if not got and pf:  # e.g. "P F P" on one line
            vals = re.findall(r"\b([PF])\b", ans)
            got = {l: v for l, v in zip(labels, vals)}
        return "\n".join(f"{l}: {got.get(l, '?')}" for l in labels)
    if re.fullmatch(r"[A-F]", fmt.strip()):
        mm = re.search(r"\b([A-F])\b", ans)
        return mm.group(1) if mm else ans.strip()[:1]
    return ans.strip()


def neutral_format(fmt):
    """Closed-item answer syntax without example values: small models often copy '1: P / 2: F' or 'A'
    verbatim as their answer. normalise_closed() still maps the reply back to the official syntax."""
    fl = [l.strip() for l in fmt.strip().splitlines() if l.strip()]
    m = [re.match(r"^([0-9A-Za-z]{1,3})\s*:\s*(.+)$", l) for l in fl]
    if fl and all(m):
        def slot(v):
            v = v.strip()
            return "P albo F" if v in ("P", "F") else "litera" if re.fullmatch(r"[A-Z]", v) else "numer" if v.isdigit() else v
        return ("\n".join(f"{x.group(1)}: {slot(x.group(2))}" for x in m) +
                "\n(Każdą linię uzupełnij własnym rozstrzygnięciem.)")
    if re.fullmatch(r"[A-F]", fmt.strip()):
        return "Jedna wielka litera oznaczająca wybraną odpowiedź."
    return fmt


def essay_label(i):
    return (bank.entries[i].get("title") or bank.entries[i]["topics"][0])[:160]


def vote_rotations(prompt_of, keys, both_ways=False):
    """Ask one multiple-choice question with the options in every cyclic order (optionally also
    reversed) at temperature 0, so the position bias of a small model cancels out."""
    from collections import Counter
    orders = []
    for r in range(len(keys)):
        o = keys[r:] + keys[:r]
        orders.append(o)
        if both_ways:
            orders.append(o[::-1])
    votes = Counter()
    for s, o in enumerate(orders):
        letters = "ABCDEFGH"[:len(o)]
        a, _ = chat([{"role": "user", "content": prompt_of(o, letters)}], 0.0, 8, seed=2000 + s)
        m = re.search(r"\b([A-H])\b", strip_think(a))
        if m and m.group(1) in letters:
            votes[o[letters.index(m.group(1))]] += 1
    return votes


def judge_essay(question):
    """Lexical top-k per topic; the model names the candidate on the same subject (rotation votes).
    The topic is then chosen by a second rotation vote over the per-topic finalists (--essay-final judge)
    or by the finalists' lexical score (--essay-final lexical). The model never writes the essay."""
    finals = []
    for n, text, ranked in bank.candidates(question, k=args.essay_k):
        if not ranked:
            continue
        idx = [i for _, i in ranked]
        sc = {i: s for s, i in ranked}

        def p1(o, L, text=text):
            listing = "\n".join(f"{l}) {essay_label(i)}" for l, i in zip(L, o))
            return (f"Temat wypracowania:\n{text}\n\nPrzygotowane wypracowania:\n{listing}\n\n"
                    "Które wypracowanie dotyczy dokładnie tego samego zagadnienia co temat (ta sama postać, "
                    "wydarzenie lub zjawisko i ten sam okres)? Odpowiedz jedną literą.")
        v = vote_rotations(p1, idx) if len(idx) > 1 else {idx[0]: 1}
        pick = max(idx, key=lambda i: (v.get(i, 0), sc[i]))
        finals.append({"topic": n, "topic_text": text, "entry": bank.entries[pick]["id"], "index": pick,
                       "score": round(sc[pick], 4), "votes": {bank.entries[i]["id"]: c for i, c in v.items()},
                       "top": [(bank.entries[j]["id"], round(x, 3)) for x, j in ranked]})
    best = max(range(len(finals)), key=lambda k: finals[k]["score"])
    final_votes = {}
    if len(finals) > 1 and args.essay_final == "judge":
        def p2(o, L):
            listing = "\n".join(f"{l}) Temat: {finals[k]['topic_text'][:320]}\n   Gotowe wypracowanie: {essay_label(finals[k]['index'])}"
                                for l, k in zip(L, o))
            return ("Do każdego tematu wypracowania dobrano jedno gotowe wypracowanie.\n\n" + listing +
                    "\n\nW której parze gotowe wypracowanie najdokładniej odpowiada swojemu tematowi (ta sama postać, "
                    "wydarzenie lub zjawisko, ten sam okres i to samo zagadnienie)? Odpowiedz jedną literą.")
        v2 = vote_rotations(p2, list(range(len(finals))), both_ways=True)
        final_votes = {finals[k]["topic"]: c for k, c in v2.items()}
        best = max(range(len(finals)), key=lambda k: (v2.get(k, 0), finals[k]["score"]))
    return {**finals[best], "final_votes": final_votes, "finalists": [{k: f[k] for k in ("topic", "entry", "score", "votes", "top")} for f in finals]}


def solve(it):
    t0 = time.time()
    k = kind(it)
    trace = {"id": it["id"], "kind": k}
    if k == "essay":
        if bank is None:
            return it["id"], "", {**trace, "error": "no essay bank"}
        if args.essay_judge:
            sel = judge_essay(it["question"])
            ans = f"Temat {sel['topic']}.\n" + bank.entries[sel["index"]]["essay"].strip()
        else:
            ans, sel = bank.answer(it["question"])
        return it["id"], ans, {**trace, "essay": sel, "seconds": round(time.time() - t0, 2)}
    ctx = context_for(it)
    src = re.sub(r"\[Obraz:[^\]]*\]", "[Ilustracja]", it.get("source_text", "") or "")
    view = {**it, "source_text": src}
    if k == "closed" and args.neutral_format:
        view["answer_format"] = neutral_format(it.get("answer_format", ""))
    text = user_text(view, ctx)
    content = (image_parts(it) + [{"type": "text", "text": text}]) if args.images else text
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    n = args.votes if k == "closed" else args.open_samples
    outs = []
    for s in range(n):
        temp = 0.0 if s == 0 else args.temperature
        a, fin = chat(msgs, temp, args.max_tokens, seed=1000 + s)
        outs.append((strip_think(a), fin))
    samples = [a for a, _ in outs]
    if k == "closed":
        fmt = it.get("answer_format", "")
        norm = [normalise_closed(a, fmt) for a in samples]
        ans = vote_closed(norm) if n > 1 else norm[0]
        ans = normalise_closed(ans, fmt)
    else:
        ans = medoid(samples) if n > 1 else samples[0]
    trace.update({"samples": samples, "finish": [f for _, f in outs], "context": ctx, "seconds": round(time.time() - t0, 2)})
    return it["id"], ans, trace


def solve_safe(it):
    """An item that raises gets an empty answer (allowed by the answer contract) instead of aborting the run."""
    try:
        return solve(it)
    except Exception as e:
        return it["id"], "", {"id": it["id"], "kind": kind(it), "error": f"{type(e).__name__}: {e}"}


t0 = time.time()
with ThreadPoolExecutor(args.workers) as ex:
    res = list(ex.map(solve_safe, items))
answers = [{"id": i, "answer": a} for i, a, _ in res]
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text(json.dumps({"exam_id": exam.get("exam_id"), "answers": answers}, ensure_ascii=False, indent=1), encoding="utf-8")
Path(args.out + ".trace.json").write_text(json.dumps({"args": vars(args), "seconds": round(time.time() - t0, 1), "items": [t for _, _, t in res]}, ensure_ascii=False, indent=1), encoding="utf-8")
print("answered", len(answers), "in", round(time.time() - t0, 1), "s ->", args.out)
