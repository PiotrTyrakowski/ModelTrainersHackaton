"""Deterministic, answer-blind Polish lexical retrieval over the pinned corpus.

No question IDs, answer keys, external model calls or historical answer mappings.
Prefix normalisation is a lightweight inflection heuristic, not a lemmatiser.
"""

from collections import Counter, defaultdict
import math
import re
import unicodedata


VERSION = "focused_bm25_v1"


def normalise(text):
    text = text.lower().replace("ł", "l")
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


def stem(word):
    return word[:5] if len(word) > 5 else word


STOP = {stem(w) for w in normalise("""
aby albo ale ani az bardziej bedzie byla byli bylo byly byc co czy dla do gdy gdzie
ich jego jej jest jako jak jaka jaki jakie ktora ktore ktory ktorych ktorym lecz
lub maja mial miedzy mimo mozna nad nie niego nich niz oba obie obu oraz owe pod
ponad przez przy sie tak taka takie tego tej ten tez to tym tych tylko wiec wobec
wszystkie za zas ze zeby zostal zostala zostaly
podaj wyjasnij rozstrzygnij ocen dokoncz uzasadnij przyporzadkuj uzupelnij wybierz
przedstaw przedstawiono przedstawiony zaprezentowany zaznacz zapisz wymien
odpowiedz odpowiedzi uzasadnienie rozstrzygniecie stwierdzenie prawdziwy prawdziwosc
falszywy zrodlo zrodla zrodle zrodel fragment tekst tekstu informacja informacjami
odwolujac podstawie wiedzy wlasnej zadanie zadania polecenie rozwiazanie
przyklad przyklady cecha cechy nazwa nazwe nazwisko imie slowa slowami wyrazow
jedna jeden jednej dwie dwoch dwa trzy trzech numer numerem litera litere
fotografia fotografii rycina rysunek ilustracja obraz obrazie mapa mapie plan
moneta monecie okolicznosciowa tablica tabela wykres plakat znaczek
stosowana historiografii wspomniany cytowany opracowanie historyczny historia
temat tematy stanowisko argumentacja aspekt minimum powinna liczyc
uwzgledniajac potwierdzajace teze tezy potwierdza charakterystyczna
element graficzny tytul kontekst wymowa sposob postac malarz roku
""").split()}
BROAD = {stem(w) for w in normalise("polska polski europejski europa panstwo panstw kraj krol krola wladca wladzy panowanie polityczny spoleczny gospodarczy wojna wojny wieku").split()}


def words(text):
    for w in re.findall(r"[a-z]+|\d{3,4}", normalise(text)):
        if len(w) < 3 or re.fullmatch(r"[ivxlcdm]+", w) or w.startswith("interpret"):
            continue
        term = stem(w)
        if term not in STOP:
            yield term


def source_for_query(question):
    """Respect explicit singular source references; preserve all exam inputs."""
    text = question.source_text
    parts = list(re.finditer(r"(?im)^\s*źródło\s+(\d+)\.", text))
    references = set(re.findall(r"(?i)źród(?:ło|ła|le)\s+(\d+)", question.prompt))
    blocks = {}
    for i, match in enumerate(parts):
        end = parts[i + 1].start() if i + 1 < len(parts) else len(text)
        blocks[match[1]] = text[match.end():end]
    # An unresolved reference must not silently remove available evidence.
    if references and references <= blocks.keys():
        text = "\n".join(blocks[k] for k in blocks if k in references)
    else:
        references = set()
    clean = []
    for line in text.splitlines():
        # Image paths and bibliographic names must not become historical clues.
        if re.search(r"(?i)^\s*(?:na podstawie:|\[obraz:)|https?://|www\.|\b\w+\.(?:pl|org|com)\b|\bs\.\s*\d", line):
            continue
        clean.append(line)
    return "\n".join(clean), sorted(references)


class FocusedRetriever:
    def __init__(self, corpus):
        self.records = []
        self.df = Counter()
        self.postings = defaultdict(set)
        for cid, text, source, licence in corpus.db.execute(
                "SELECT id,text,source,licence FROM chunks ORDER BY id"):
            counts = Counter(words(text))
            title = text.split("\n", 1)[0].split(" — ", 1)[0]
            title_words = set(words(title))
            i = len(self.records)
            self.records.append(({"id": cid, "text": text, "source": source,
                                  "licence": licence}, counts, title_words))
            self.df.update(counts.keys())
            for term in counts:
                self.postings[term].add(i)
        self.n = len(self.records)
        self.average_length = sum(sum(c.values()) for _, c, _ in self.records) / max(1, self.n)

    def search(self, question, k=3):
        if k < 1:
            raise ValueError("top_k must be positive")
        source, refs = source_for_query(question)
        # Creation of an illustration is not a historical uprising ("powstanie").
        query_prompt = re.sub(r"(?i)roku powstania(?: tego)? (?:rysunku|obrazu|plakatu)", "", question.prompt)
        prompt_terms, source_terms = set(words(query_prompt)), set(words(source))
        terms = prompt_terms | source_terms
        # Use the entire cleaned input; no first-80-token truncation.
        weights = {t: (2 if t in prompt_terms else 1) for t in terms if t in self.df}
        informative = {t for t in weights if not t.isdigit() and t not in BROAD
                       and self.df[t] / max(1, self.n) < .20}
        trace = {"version": VERSION, "source_references": refs,
                 "prompt_terms": sorted(prompt_terms), "source_terms": sorted(source_terms),
                 "informative_terms": sorted(informative), "selected": [],
                 "reason": "no_informative_query_terms"}
        if not informative:
            return [], trace
        candidates = set().union(*(self.postings[t] for t in informative))
        ranked = []
        for i in candidates:
            record, counts, title = self.records[i]
            overlap = informative & counts.keys()
            title_overlap = informative & title
            # A named topic in a title can be enough; otherwise require two clues.
            if len(overlap) < 2 and not title_overlap:
                continue
            length_norm = .25 + .75 * sum(counts.values()) / max(1, self.average_length)
            score = 0
            for t in weights.keys() & counts.keys():
                idf = math.log(1 + (self.n - self.df[t] + .5) / (self.df[t] + .5))
                tf = counts[t]
                score += weights[t] * idf * (tf * 2.2 / (tf + 1.2 * length_norm)
                                             + (2.5 if t in title else 0))
            ranked.append((score, record, sorted(overlap), sorted(title_overlap)))
        ranked.sort(key=lambda row: (-row[0], row[1]["id"]))
        passages, per_article = [], Counter()
        for score, record, matched, title_matched in ranked:
            if score < ranked[0][0] * .45:
                break
            # Avoid three near-duplicate passages from the same article.
            if per_article[record["source"]] >= 2:
                continue
            passages.append(record)
            per_article[record["source"]] += 1
            trace["selected"].append({"id": record["id"], "score": round(score, 6),
                                      "matched_terms": matched, "title_terms": title_matched})
            if len(passages) == k:
                break
        trace["reason"] = "selected" if passages else "no_passage_passed_overlap_gate"
        return passages, trace


def retrieve(question, context):
    from matura_lab.core import BudgetExceeded
    if context.get("corpus") is None:
        raise ValueError("Focused retrieval needs a corpus")
    if context["budget"].remaining() <= 0:
        raise BudgetExceeded("No retrieval time remains")
    corpus = context["corpus"]
    if not hasattr(corpus, "_focused_retriever_v1"):
        corpus._focused_retriever_v1 = FocusedRetriever(corpus)
    result = corpus._focused_retriever_v1.search(question, context.get("top_k", 3))
    if context["budget"].remaining() <= 0:
        raise BudgetExceeded("Retrieval exceeded question budget")
    return result
