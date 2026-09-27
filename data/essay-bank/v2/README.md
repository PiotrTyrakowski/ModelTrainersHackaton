# Essay bank v2 (prepared essays, never generated at exam time)

The exam essay (15 of 60 points) is not written by the solver model. `run_exam.py`
submits one of these prepared essays unchanged, prefixed only with `Temat N.`
The small model's only role is to vote which of the top lexical candidates matches
each offered topic (see "Selection" below).

## Files

| File | Entries | Origin |
|---|---:|---|
| `slice-S01.jsonl` … `slice-S12.jsonl` | 12 × 20 | Written offline by Claude subagents from era/theme briefs (no exam keys, rubrics or model answers) |
| `slice-S13.jsonl`, `slice-S14.jsonl` | 2 × 5 | Written after the selection checks to fill observed gaps (see integrity notes) |
| `friend.jsonl` | 105 | Teammate's synthetic essays (`finetuine/data/synth/essays.jsonl`), converted to this schema |
| `bank.jsonl` | 355 | `python3 scripts/harness/merge_bank.py`: all slices + friend, unique ids, at least 320 words |
| `_existing_friend_topics.txt` | – | Friend topics given to slice authors to avoid duplicates |

Schema (one JSON object per line): `id`, `slice`, `era` (`starozytnosc`,
`sredniowiecze`, `nowozytnosc`, `xix`, `xx-1914-1945`, `po-1945`), `period`
(`start`, `end`, negative = BCE), `title`, `topics` (CKE-style wordings the essay
answers; the first is the main thesis), `stance`, `keywords`, `aspects`, `essay`.
Median length 641 words, minimum 456; the exam minimum is 300.

## Selection (`scripts/harness/essay_bank.py`, `run_exam.py --essay-judge 1`)

1. The essay task text is split into its numbered topics.
2. For every topic, a lexical scorer (IDF-weighted title/topic/body overlap,
   adjacent-word pairs, subject and aspect bonuses, period compatibility) ranks
   the bank and keeps the top 5.
3. The solver model answers one multiple-choice question per cyclic rotation of
   those 5 titles at temperature 0 ("which essay is about exactly the same
   subject and period?"); the most-voted candidate wins, ties by lexical score.
   Rotations cancel the small model's position bias.
4. The topic whose winner has the highest lexical score is submitted
   (`--essay-final lexical`; a second model vote across topics was worse on the
   development papers).

## Integrity notes

- All essays were authored by language models (Claude subagents or the
  teammate's generator) and have not been reviewed by a human history teacher.
- Essay grades in `docs/results/2026-09-27-harness-of-models.md` come from a
  strict Claude grader using the CKE rubric; they are provisional.
- The development papers' essay topics (May 2023–2026) were visible while the
  selector was tuned. Old-formula topics overlap the friend's essays.
- The essay topics of seven further sessions (2019–2022 and June 2023–2025,
  `data/raw/exams/history-more-papers-v1`) were used as a selection check.
  `S13`/`S14` were written afterwards and partly cover themes seen there or in
  the development papers (e.g. slavery in antiquity, 1956 in the Eastern bloc,
  Europe 1871–1914), so those sets are no longer unseen for the current bank.
- The June 2026 paper was reserved for the final check and was not used to
  build or tune the bank. In the single frozen run the selector submitted
  S05-02 for its topic 2 (provisional 12/15 from two strict graders). Graded
  picks on the other sets were 4–10/15, apart from two S14 essays written after
  their topics had been seen.
