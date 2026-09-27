"""Pick a prepared essay for one of the offered essay topics (no essay generation by the model).

Bank entries (JSONL): {"id","title","topics":[...],"keywords":[...],"period":{"start","end"},"essay",...}
Selection is lexical: stemmed-term overlap between each offered topic's thesis and each entry's
title/topics/keywords (IDF-weighted), plus a bonus when the topic's dates fall inside the entry period.
"""
import json, math, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checkpoints"))
from focused_retrieval import words  # Polish prefix-stem normaliser used by the retrieval baseline

BOILER = set(words("Zajmij stanowisko wobec powyższej tezy i je uzasadnij uwzględniając w swojej argumentacji aspekty aspekt "
                   "polityczny gospodarczy społeczny kulturowy militarny ustrojowy społeczno-gospodarczy polityczno-ustrojowy "
                   "dyplomatyczny religijny wydarzenia trzech wybranych oceń rozstrzygnij porównaj twoja wypowiedź "
                   # evaluative / generic thesis vocabulary: says nothing about the historical subject
                   "przede wszystkim najbardziej najważniejszy najwybitniejszym najwybitniejszy wybitny udaną udany próbą próba "
                   "więcej mniej szkody szkód pożytku korzyści korzystna korzystny niekorzystny sukcesy sukces "
                   "okazała okazał okazały była był były było jest są zawdzięczała zawdzięczał dzięki przyczyną przyczyna "
                   "przyczyniły przyczynił stopniu największym niesłusznie słusznie określane określany nazywany uważany "
                   "przełomem przełom przełomowy apogeum nieunikniona nieunikniony decydujący decydującą kluczowy kluczową "
                   "znaczenie znaczenia upadku upadek rozwój rozwoju wpływ wpływu wpłynęła wpłynął podobne podobny różnice "
                   "dominowały dominował tendencje czasy czasów okres okresie lata latach wieku wiek wieki roku rok "
                   "państwa państwo polska polski polskiego polsce europy europejskich europejskie społeczeństwom społeczeństw "
                   "tradycji tradycja spośród wszystkich właśnie konfliktów"))
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
         "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21}


def topics_of(question):
    """Split an essay task into its numbered topics: [(n, text)]."""
    parts = re.split(r"(?m)^\s*(\d)\.\s+", question)
    out = []
    for i in range(1, len(parts) - 1, 2):
        out.append((int(parts[i]), " ".join(parts[i + 1].split())))
    return out


PREDICATE = re.compile(r"\b(był|była|było|byli|były|jest|są|okazała|okazał|okazały|okazało|przyniosła|przyniósł|przyniosły|"
                       r"osiągnęła|osiągnął|zawdzięczała|zawdzięczał|dominowały|dominował|miały|miał|miała|miało|stanowiła|"
                       r"stanowił|stanowiły|przyczyniły|przyczynił|przyczyniła|doprowadziła|doprowadził|doprowadziły|"
                       r"zakończyła|zakończył|wpłynęła|wpłynął|wpłynęły|odegrała|odegrał|odegrały|umożliwiła|umożliwił|"
                       r"zapewniała|zapewniał|objął|objęła|wynikał|wynikała|wynikały)\b", re.I)
ASPECT = re.compile(r"aspekt\w*:?\s+((?:[\w-]+(?:,\s*|\s+i\s+|\s+oraz\s+)?){1,4})")


def split_topic(topic):
    """(thesis sentence, its grammatical subject) of a CKE essay topic."""
    thesis = re.split(r"\.\s+(?=Zajmij|Oceń|Rozstrzygnij|Porównaj|Uzasadnij|Scharakteryzuj|Przedstaw|Wyjaśnij|W swojej)", topic)[0]
    m = PREDICATE.search(thesis)
    return thesis, (thesis[:m.start()] if m else thesis)


def years_of(text):
    ys = [int(y) for y in re.findall(r"\b(1[0-9]{3}|20[0-2][0-9]|[5-9][0-9]{2})\b", text)]
    for dec, c in re.findall(r"\b(\d0)\.\s+([IVX]{1,5})\s+w", text):  # "lata 50. XX wieku"
        if c in ROMAN:
            ys.append((ROMAN[c] - 1) * 100 + int(dec))
    for a, b in re.findall(r"\b([IVX]{1,5})\s*[–-]\s*([IVX]{1,5})\s+w", text):
        if a in ROMAN and b in ROMAN:
            ys += [(ROMAN[a] - 1) * 100 + 1, ROMAN[b] * 100]
    for c in re.findall(r"\b([IVX]{1,5})(?=\s*(?:w\.|wieku|wiek))", text):
        if c in ROMAN:
            ys += [(ROMAN[c] - 1) * 100 + 1, ROMAN[c] * 100]
    if re.search(r"p\.\s*n\.\s*e\.", text):
        ys = [-y for y in ys]
    return ys


class Bank:
    def __init__(self, paths):
        self.entries = []
        for p in paths:
            for l in open(p, encoding="utf-8"):
                if l.strip():
                    self.entries.append(json.loads(l))
        self.docs, self.titles = [], []
        df = Counter()
        for e in self.entries:
            head = " ".join([e.get("title", "")] + e.get("topics", []) + e.get("keywords", []))
            c = Counter(t for t in words(head) if t not in BOILER)
            body = Counter(t for t in words(e.get("essay", "")) if t not in BOILER)
            self.docs.append((c, body))
            self.titles.append(Counter(t for t in words(e.get("title", "")) if t not in BOILER))
            df.update(set(c) | set(body))
        self.df, self.n = df, len(self.entries)
        self.heads = [" ".join(words(" ".join([e.get("title", "")] + e.get("topics", []) + e.get("keywords", []) + [e.get("essay", "")[:1500]])))
                      for e in self.entries]
        for e in self.entries:  # entries without a period: infer it from years in the essay (10th-90th percentile)
            if not e.get("period"):
                ys = sorted(y for y in years_of(" ".join(e.get("topics", [])) + " " + e.get("essay", "")) if y > 0)
                if ys:
                    e["period"] = {"start": ys[len(ys) // 10], "end": ys[(9 * len(ys)) // 10]}

    def idf(self, t):
        return math.log(1 + (self.n - self.df[t] + .5) / (self.df[t] + .5))

    def weighted_terms(self, topic):
        """Stemmed thesis terms with weights: the grammatical subject (words before the first
        predicate verb) and proper nouns count double; the instruction part is ignored."""
        thesis, subject = split_topic(topic)
        caps = {w for tok in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-ZŁŚŻŹĆŃÓĘĄ][\w-]+", thesis) for w in words(tok)}
        sub = set(words(subject))
        wt = {}
        for t in words(thesis):
            if t in BOILER:
                continue
            wt[t] = max(wt.get(t, 0), 2.0 if (t in sub or t in caps) else 1.0)
        return wt, [t for t in words(thesis) if t not in BOILER]

    def score(self, topic, i):
        head, body = self.docs[i]
        title = self.titles[i]
        wt, seq = self.weighted_terms(topic)
        if not wt:
            return 0.0
        num = den = 0.0
        for t, w in wt.items():
            m = 1.0 if title[t] else (0.9 if head[t] else 0.7 * min(body[t], 4) / 4)
            num += w * self.idf(t) * m
            den += w * self.idf(t)
        s = num / den
        # multi-word subjects ("rewolucja przemysłowa", "unia w Krewie") matched as adjacent stems in the entry text
        hs = self.heads[i]
        pairs = [(a, b) for a, b in zip(seq, seq[1:])]
        if pairs:
            s += 0.3 * sum(1 for a, b in pairs if f"{a} {b}" in hs) / len(pairs)
        # the thesis subject named in the entry title ("Władysław Jagiełło" -> "Panowanie Władysława Jagiełły")
        subj = [t for t, w in wt.items() if w > 1]
        if subj:
            s += 0.3 * sum(1 for t in subj if title[t]) / len(subj)
        # required elements (aspects) named in the task also named in the entry's own topics/aspects
        asp = set(words(" ".join(ASPECT.findall(topic.lower()))))
        if asp:
            mine = set(words(" ".join(self.entries[i].get("aspects", []) + self.entries[i].get("topics", [])).lower()))
            s += 0.15 * len(asp & mine) / len(asp)
        ys = years_of(topic)
        per = self.entries[i].get("period") or {}
        if ys and per.get("start") is not None and per.get("end") is not None:
            lo, hi = min(ys), max(ys)
            s *= 1.15 if (lo <= per["end"] + 5 and hi >= per["start"] - 5) else 0.6
        return s

    def candidates(self, question, k=4, exclude=()):
        """Per offered topic: (n, text, [(score, entry index), ...] best first)."""
        out = []
        for n, text in topics_of(question):
            ranked = sorted(((self.score(text, i), i) for i in range(self.n) if self.entries[i].get("id") not in exclude), reverse=True)
            out.append((n, text, ranked[:k]))
        return out

    def pick(self, question, exclude=()):
        best = None
        for n, text in topics_of(question):
            ranked = sorted(((self.score(text, i), i) for i in range(self.n) if self.entries[i].get("id") not in exclude), reverse=True)
            if not ranked:
                continue
            s, i = ranked[0]
            margin = s - (ranked[1][0] if len(ranked) > 1 else 0)
            cand = {"topic": n, "topic_text": text, "entry": self.entries[i]["id"], "score": round(s, 4), "margin": round(margin, 4),
                    "top3": [(self.entries[j]["id"], round(x, 3)) for x, j in ranked[:3]]}
            if best is None or (s, margin) > (best["score"], best["margin"]):
                best = cand
        return best

    def answer(self, question, exclude=()):
        sel = self.pick(question, exclude)
        e = next(x for x in self.entries if x["id"] == sel["entry"])
        return f"Temat {sel['topic']}.\n" + e["essay"].strip(), sel
