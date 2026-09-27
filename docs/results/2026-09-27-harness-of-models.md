# Harness of models: the smallest system that reaches the pass mark

The user set this goal on 26–27 September 2026: find the smallest model system
that passes the Polish history matura (extended level, formula 2023, 60 points).

- **Pass mark:** 35%, i.e. **21/60 including the essay**.
- **The essay (15 points) is never generated.** Prepared essays are written in
  advance and the model only chooses one.
- **Non-essay target:** the user asked us to assume about 8/15 for the essay, so
  the other 45 points must reach **13/45**.
- **Safety margin:** the development target was **at least 16/45 on each of the
  four development papers**.

All grades are provisional:
- closed items are scored automatically from separate keys;
- open items and essays are graded by blinded Claude subagents against the CKE
  rubric.

No CKE examiner was involved and no official result is claimed. The per-item
record (answers, points, grader reasons) is in
[`2026-09-27-harness-of-models.json`](2026-09-27-harness-of-models.json).

## Result

- **System.** The system has **2,126,891,136 learned bytes** (1.98 GiB):
  - Qwen3.5-4B fine-tuned on old-formula matura items, quantized to IQ2_M with a
    Polish-history importance matrix;
  - the base model's vision projector at Q8_0.

  BM25 retrieval over a local encyclopedia index and a bank of prepared essays
  complete it; neither holds learned weights.
- **June 2026, the reserved paper, one frozen run.** Two independent graders gave
  **27/60 and 28/60**, above the 21-point pass mark:
  - closed items 3/8;
  - open items 12/37 and 13/37;
  - essay 12/15 from both graders.

  Without the essay the score is 15–16/45.
- **Development papers.** Three passes of the same weights scored 72, 59 and 63
  out of 180 on non-essay items (four papers of 45).
  - 11 of the 12 paper-passes reach 13/45.
  - Only the first pass met the 16/45 margin on every paper.
  - If the essay the selector actually chose for each paper is added (strict
    grades 4, 6, 15 and 5), 8 of 12 paper-passes reach 21/60.
- **Reading.** The system passed the reserved paper and passes the development
  papers on average, but the margin is thin.
  - Non-deterministic batched decoding moves a paper by up to 4 points between
    identical runs.
  - May 2024 and May 2026 fall to 18–20/60 in two of three passes once their weak
    selected essays are added.
  - Nothing smaller that we measured came close. This is a borderline pass, not a
    reliable one.

## The system

`scripts/harness/run_system.sh <exam.json> <answers.json>` runs the whole
pipeline. It starts a local llama-server unless `$SERVER` is set.

| Part | What it does | Learned bytes |
|---|---|---:|
| Solver LM | `Qwen3.5-4B-matura-v1-IQ2_M.gguf`: Qwen3.5-4B plus merged LoRA SFT, IQ2_M with a history importance matrix | 1,759,996,480 |
| Vision projector | `mmproj-Qwen3.5-4B-q8_0.gguf`: the base model's projector, not fine-tuned. Reads maps, art, cartoons and tables | 366,894,656 |
| Retrieval | BM25 over the local Wikipedia + e-Historia index (286 articles, 4,638 passages); 4 passages of up to 1,300 characters per item | 0 (15.9 MB index) |
| Essay bank | 355 prepared essays (`data/essay-bank/v2`), submitted unchanged | 0 (2.2 MB text) |
| **Total** | | **2,126,891,136** |

**Serving and decoding**
- One llama-server: `-ngl 99 -c 65536 -np 8 --jinja`.
- Non-thinking chat, greedy decoding, at most 400 output tokens,
  `repeat_penalty` 1.05.
- One call per item, no voting.
- Closed answers are normalised to the syntax of the item's `answer_format`.

**Item images.** Extracted papers contain written image descriptions
(`[Obraz: …]`). The prompt replaces them with `[Ilustracja]` and the retrieval
query drops them. The model sees the images themselves.

**Essay selection**
1. For every offered topic, a lexical scorer keeps the 5 best-matching bank essays.
2. The solver answers one multiple-choice question per cyclic rotation of those
   5 titles: "which essay is about exactly the same subject and period?"
3. The most-voted candidate wins that topic.
4. The topic whose winner has the highest lexical score is submitted as
   `Temat N.` followed by the stored essay.

Details are in `data/essay-bank/v2/README.md`.

**SHA-256 of the model files**

| File | SHA-256 |
|---|---|
| LM | `743c5ce8e8b294e02a3f664048485172bf0abf22b8150302a31602ac227fa90e` |
| Projector | `40a4f07d7bbdbb43011d6cf35ef751e4b1829ff47ee8aa4964c6296f571725ad` |
| Importance matrix | `ac19f3c7854381b93b7a8724efeedbf94c49f426e8f5e83ff8f0779067b9f309` |

The GGUFs are in `artifacts/harness/gguf/`, which is not in git.

## How the solver model was built

`scripts/harness/build_model.sh` repeats every step. We ran it on a Colab A100
40 GB with llama.cpp commit `9588757`.

1. **SFT data.** `data/sft/nonessay-v1.jsonl` (not committed; see
   "Integrity"), md5 `68ed704813a7cc2da602dd740ccb87cb`.
   - `scripts/harness/build_sft.py` builds 1,197 non-essay records from the
     teammate's `finetuine` set:
     - formula-2015 CKE papers 2015–2022;
     - synthetic CKE-style items.
   - 600 of the records carry retrieved encyclopedia context.
   - Dropped from the set:
     - essays;
     - every 2023+ session;
     - every record whose text overlaps a formula-2023 paper by 8-gram
       containment above 0.10. The overlap check covers the four development
       papers, the June 2026 reserve and the teammate's evaluation set.
   - The reserve paper was used only for that overlap filter.
2. **LoRA SFT** of `Qwen/Qwen3.5-4B` with `train_lora.py`, merged into the base
   weights:
   - rank 64, alpha 64, lr 2e-4;
   - 3 epochs, batch 8 × 2, 225 steps;
   - 121.9 M trainable parameters;
   - final loss 0.31, 78 min.

   Training uses the harness's own chat prompt (`common.messages`), so training
   and inference see the same format.
3. **MTP layer.** The merged Hugging Face export lacks the multi-token-prediction
   tensors, and `convert_hf_to_gguf.py` needs them.
   - `fix_mtp.py` copies them from the base model.
   - `strip_mtp.py` then drops that block from the GGUF (33 → 32 blocks).
   - Why: llama.cpp does not decode with the block and `llama-imatrix` cannot
     calibrate it, which makes low-bit quantization fail.
4. **Importance matrix** from Polish-history text: `build_calib.py` takes 160
   retrieval passages and 80 chat-formatted training items, with no development
   or reserve paper. Then `llama-imatrix -c 512 --chunks 150`.
5. **Quantization.** `llama-quantize --imatrix … --tensor-type-file
   recipes/ud-iq2_m.txt … IQ2_M`.
   - The recipe copies the per-tensor types of Unsloth's `UD-IQ2_M` GGUF of the
     same base: iq2_s 111, iq3_xxs 40, iq3_s 25, q5_k 25, q8_0 48 tensors.
   - `recipe.py` reads these types from the reference file.
   - The fine-tuned weights therefore get the same mixed-precision layout, but
     with our own importance matrix.
6. **Vision projector.** The base model's projector is converted with
   `--mmproj --outtype q8_0`. It is not fine-tuned. The Q8_0 and f16 projectors
   scored about the same on the base 4B Q4_K_M (91 vs 89 points below), so Q8_0
   was used.

## Development results (non-essay, provisional)

**Setup**
- Papers: 2023 (the organisers' practice paper) and May 2024, 2025 and 2026, each
  with 45 non-essay points.
- Cells are open + closed points.
- "Learned bytes" means LM GGUF plus the projector when images are used.
- "Truncated" counts answers cut at 400 tokens (154 items per configuration).
- FT means our LoRA fine-tune on the same SFT set. "UD recipe" means Unsloth's
  per-tensor types with our history importance matrix.
- Every configuration uses BM25 retrieval unless marked "no retrieval".

| Configuration | Learned bytes | 2023 | 2024 | 2025 | 2026 | Total /180 | Min | Truncated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FT 4B Q4_K_M + f16 projector | 3,455,869,984 | 18+6=24 | 16+7=23 | 23+4=27 | 16+4=20 | 94 | 20 | 0 |
| Base 4B Q4_K_M + Q8_0 projector | 3,107,832,544 | 19+5=24 | 16+7=23 | 19+6=25 | 15+4=19 | 91 | 19 | 8 |
| Base 4B Q4_K_M + f16 projector | 3,413,361,504 | 20+5=25 | 14+6=20 | 17+6=23 | 16+5=21 | 89 | 20 | 8 |
| Base 4B Q3_K_M + f16 projector | 2,991,230,496 | 19+4=23 | 15+7=22 | 13+6=19 | 16+1=17 | 81 | 17 | 12 |
| FT 4B IQ3_XXS (UD recipe) + Q8_0 projector | 2,309,582,976 | 19+4=23 | 11+5=16 | 20+4=24 | 13+4=17 | 80 | 16 | 0 |
| Base 4B Unsloth UD-IQ3_XXS + Q8_0 projector | 2,315,942,624 | 19+5=24 | 14+6=20 | 13+6=19 | 14+0=14 | 77 | 14 | 43 |
| Base 4B Q4_K_M, text only | 2,740,937,888 | 15+4=19 | 11+5=16 | 11+6=17 | 13+4=17 | 69 | 16 | 9 |
| Base 4B Unsloth UD-IQ2_M + Q8_0 projector | 2,126,891,744 | 14+5=19 | 13+4=17 | 10+5=15 | 13+4=17 | 68 | 15 | 28 |
| Base 4B IQ2_M (UD recipe) + Q8_0 projector | 2,126,891,616 | 16+4=20 | 12+3=15 | 12+5=17 | 12+2=14 | 66 | 14 | 14 |
| **Selected: FT 4B IQ2_M (UD recipe) + Q8_0 projector, pass 1** | 2,126,891,136 | 14+6=20 | 11+5=16 | 14+4=18 | 13+5=18 | 72 | 16 | 0 |
| **Selected, pass 2** | 2,126,891,136 | 13+6=19 | 8+4=12 | 10+4=14 | 9+5=14 | 59 | 12 | 0 |
| **Selected, pass 3 (local Metal)** | 2,126,891,136 | 13+6=19 | 10+4=14 | 11+4=15 | 10+5=15 | 63 | 14 | 1 |
| FT 4B IQ2_XXS (UD recipe) + Q8_0 projector | 1,887,111,296 | 8+3=11 | 10+3=13 | 6+3=9 | 8+5=13 | 46 | 9 | 13 |
| FT 4B IQ2_M, text only | 1,759,996,480 | 17+4=21 | 7+4=11 | 10+4=14 | 10+5=15 | 61 | 11 | 1 |
| FT 2B Q4_K_M + f16 projector | 1,980,391,424 | 8+5=13 | 10+2=12 | 6+5=11 | 5+2=7 | 43 | 7 | 0 |
| FT 2B Q4_K_M, text only | 1,312,164,288 | 9+2=11 | 8+3=11 | 5+5=10 | 5+2=7 | 39 | 7 | 0 |
| FT 2B Q4_K_M, text only, no retrieval | 1,312,164,288 | 5+4=9 | 3+4=7 | 4+3=7 | 4+2=6 | 29 | 6 | 0 |
| Base 2B Q4_K_M, text only, no retrieval | 1,312,164,800 | 3+4=7 | 3+2=5 | 3+3=6 | 3+1=4 | 22 | 4 | 10 |
| FT 0.8B Q4_K_M, text only | 541,903,296 | 6+5=11 | 4+2=6 | 1+4=5 | 4+0=4 | 26 | 4 | 0 |
| FT 0.8B Q4_K_M, text only, no retrieval | 541,903,296 | 1+4=5 | 3+1=4 | 4+4=8 | 1+0=1 | 18 | 1 | 0 |

Six further configurations were screened out on closed items and degenerate
output before open grading:

| Configuration | Learned bytes | Closed 2023 | 2024 | 2025 | 2026 | Truncated /154 |
|---|---:|---:|---:|---:|---:|---:|
| Base 4B Q2_K + f16 projector | 2,631,591,456 | 0 | 0 | 1 | 0 | 62 |
| Base 4B Unsloth UD-IQ2_XXS + Q8_0 projector | 1,887,111,904 | 2 | 1 | 4 | 0 | 65 |
| Base 4B Q4_K_M + f16 projector, no retrieval | 3,413,361,504 | 4 | 6 | 5 | 3 | 16 |
| Base 2B Q4_K_M, text only | 1,312,164,800 | 4 | 1 | 3 | 0 | 10 |
| Bielik 1.5B Q4_K_M, text only | 972,797,408 | 6 | 0 | 3 | 1 | 27 |
| Base 0.8B Q4_K_M, text only, no retrieval | 541,903,808 | 1 | 2 | 2 | 1 | 76 |

### Why this configuration

It is the smallest configuration that met the 16/45 margin on every paper in its
first pass.

- **Smaller variants failed.** The 1.89 GB IQ2_XXS and the 1.76 GB text-only
  IQ2_M did not meet the margin, and nothing below 2 GB came close.
- **Bits per weight beat parameter count.** At about 2 GB, the 4B beats the
  fine-tuned 2B at Q4_K_M: 59–72 vs 43. The 4B's LM has 4.21 B parameters at
  3.33 bits per weight on average: IQ2_S (2.56 bpw) for 58% of the weights,
  and a Q5_K embedding table.
- **The fine-tune does the work at 2 bits.** Base weights with the same recipe
  scored 66–68 with 14–28 truncated answers. The fine-tuned model scored 59–72
  with 0–1.
- **Larger fallbacks were lost.** FT IQ3_XXS (2.31 GB, 80) and FT Q4_K_M
  (3.46 GB, 94) were ahead of it in their single passes. Their files were lost
  with the Colab VM (see below), so they could not be rerun or kept.

### Run-to-run variance of the selected system

| Pass | Runtime | 2023 | 2024 | 2025 | 2026 | Total /180 |
|---|---|---:|---:|---:|---:|---:|
| 1 | CUDA A100, first code checkout | 20 | 16 | 18 | 18 | 72 |
| 2 | CUDA A100, final code | 19 | 12 | 14 | 14 | 59 |
| 3 | Metal, Apple M5 (the June runtime), final code | 19 | 14 | 15 | 15 | 63 |
| Mean | | 19.3 | 14.0 | 15.7 | 15.7 | 64.7 |

**Retrieval and answers.** All three passes use the same weights. Retrieved
passages were identical for every item in all passes. The code change between
passes 1 and 2 only strips written image descriptions from retrieval queries,
which did not change any retrieval here. Even so, few answers were identical:

| Passes compared | Identical answers |
|---|---:|
| 1 and 2 | 66/154 |
| 2 and 3 | 60/154 |
| 1 and 3 | 56/154 |

llama-server's batched decoding (8 parallel slots) is not bit-reproducible, so
each pass is one sample of the same system.

**Other checks**
- **Metal runtime.** The local Metal pass lies between the two CUDA passes. This
  supports treating the June run on that runtime as representative.
- **Grader drift.** A fresh blind grader re-marked pass 1's open answers:
  14/9/14/13 against the original 14/11/14/13.
- **Double-graded answer.** One 2023 answer shared by passes 1 and 2 was graded
  twice (0 and 1 point). The tables use 0.

### Points by question type (development, four papers)

| Type | Pass 1 | Pass 2 | Pass 3 | FT 4B Q4_K_M | Base 4B Q4_K_M | FT 2B + images | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Identification | 16 | 16 | 17 | 19 | 21 | 9 | 37 |
| Comparison | 11 | 8 | 10 | 14 | 13 | 8 | 27 |
| Cartoon | 0 | 0 | 0 | 7 | 4 | 1 | 20 |
| Map | 6 | 5 | 5 | 9 | 8 | 3 | 18 |
| True/false | 11 | 11 | 11 | 10 | 10 | 8 | 18 |
| Art | 5 | 4 | 2 | 10 | 9 | 5 | 15 |
| Choice | 7 | 6 | 6 | 9 | 10 | 5 | 12 |
| Explanation | 7 | 2 | 3 | 5 | 4 | 2 | 12 |
| Matching | 6 | 6 | 6 | 9 | 8 | 1 | 11 |
| Chronology | 1 | 1 | 1 | 1 | 1 | 1 | 5 |
| Data table | 2 | 0 | 1 | 1 | 1 | 0 | 3 |
| Genealogy | 0 | 0 | 1 | 0 | 0 | 0 | 2 |
| **Total** | **72** | **59** | **63** | **94** | **89** | **43** | **180** |

Most of the loss from 4-bit to 2-bit is on image items. Art, cartoons and maps
together score 26 points for the fine-tuned Q4_K_M and 7–11 for the IQ2_M
passes. Cartoons score zero in every pass. Text-only identification and
true/false items barely change.

## Essay selection

The selector with the selected model chose these essays. The picks come from
one selector run per paper. A strict Claude examiner graded them: criterion A
out of 12 with deductions, criterion B out of 3, and an essay prepared for a
neighbouring topic is marked down.

| Paper | Topic | Bank essay | Grade /15 |
|---|---|---|---:|
| May 2023 (development) | 2 | S06-13 American and French revolutions compared | 4 |
| May 2024 (development) | 3 | S10-11 Piłsudski's role 1914–1935 | 6 |
| May 2025 (development) | 2 | S14-04 Europe 1871–1914, a belle époque?* | 15 |
| May 2026 (development) | 1 | S03-13 Union of Krewo, benefits for Poland and Lithuania | 5 |
| June 2023 (selection check) | 3 | S10-18 Nazism and Stalinism compared | 10 |
| June 2024 (selection check) | 3 | S10-19 Crisis of democracy in interwar Europe | 5 |
| June 2025 (selection check) | 2 | S14-02 Revolution and easing of oppression (Tocqueville)* | 15 |
| **June 2026 (reserved)** | 2 | S05-02 The last Jagiellons as a golden age | **12 / 12** (two graders) |

\* Written after that topic had been seen. These two grades do not measure the
bank.

**Summary of grades**
- The mean over the five sets without an asterisk is 6.0.
- Adding the June 2026 grade gives a mean of 7.0 over six sets, close to the
  8/15 the user asked us to assume.
- Low grades come from essays written for a neighbouring thesis. For example,
  May 2026 asks whether the Krewo union benefited Lithuania *more* than Poland,
  and the bank has only "benefits for both".

**Development totals with these essays**

| Pass | 2023 | 2024 | 2025 | 2026 | Papers passed |
|---|---:|---:|---:|---:|---:|
| 1 | 24 | 22 | 33 | 23 | 4/4 |
| 2 | 23 | 18 | 29 | 19 | 2/4 |
| 3 | 23 | 20 | 30 | 20 | 2/4 |

With the assumed 8/15 essay instead, 11 of the 12 paper-passes reach 21/60.

## June 2026 (reserved paper, one frozen run)

**Before the run**
- The June 2026 paper was held back from all development. Before the run, it had
  been used only in these ways:
  - its cover was inspected;
  - its text was used in the SFT overlap filter;
  - the extracted files were format-checked.
- A Claude subagent extracted it from the CKE PDFs into
  `data/generated/final-exams/2026-june/` (not in git): exam, images, keys and
  rubrics. That extraction was not reviewed by a human.
- The solver saw only `exam.json` and the images, from a staged copy without keys
  or rubrics.
- A declaration was written at 04:51:44 CEST, before the run. It records the
  SHA-256 of the:
  - LM and projector;
  - `run_system.sh`, `run_exam.py`, `common.py` and `essay_bank.py`;
  - essay bank and retrieval index;
  - staged exam.

  These files are unchanged in this commit.

**The run**
- One run of `run_system.sh` with its defaults.
- It used local llama.cpp `9588757` built with Metal on an Apple M5 (16 GB),
  because the CUDA VM had been lost.
- 41 answers in 209.8 s, no truncated answers.
- Nothing was changed after the results.

| Part | Grader A | Grader B | Max |
|---|---:|---:|---:|
| Closed items (keys) | 3 | 3 | 8 |
| Open items | 12 | 13 | 37 |
| Essay | 12 | 12 | 15 |
| **Total** | **27** | **28** | **60** |

**Open items.** The two open graders worked independently and agree on every
item except 22 (1 vs 2 points). Twelve open items earned points, 1 point each,
plus item 22's second point from grader B.

**Essay.** The selector chose topic 2: "the Jagiellonian period was the best
period in pre-partition Poland". It submitted S05-02, prepared as "the last
Jagiellons as a golden age".
- Both graders gave A 9 + B 3 = 12.
- Both marked it down for narrowing 1386–1572 to 1506–1572 and for asserting
  rather than arguing the comparative claim.

**Summary.** The non-essay score of 15–16/45 matches the development mean for
this system (about 16), and the essay is above the bank's usual grade. The total
passes by 6–7 points.

## What did not work

- **Small models, even fine-tuned.** Tested: Qwen3.5-0.8B and 2B (base and our
  fine-tunes), and Bielik 1.5B.
  - The best was the fine-tuned 2B with images: 43/180, worst paper 7/45.
  - Without retrieval, fine-tuning raised the 2B from 22 to 29 points, still far
    from 13/45 per paper.
- **2-bit quantization of the base 4B.** Q2_K and Unsloth UD-IQ2_XXS collapsed
  into repetition: 62 and 65 of 154 answers truncated.
  - UD-IQ2_M kept working: 68/180, but with 28 truncations and a worst paper of
    15.
- **Our history importance matrix alone.** On the base 4B at the UD-IQ2_M layout
  it scored 66/180 with a worst paper of 14. The fine-tune is what makes 2 bits
  work: it scored 0–1 truncations and 59–72.
- **Going below IQ2_M on the fine-tune.**
  - IQ2_XXS (1.89 GB) fell to 46/180 with 13 truncations.
  - Dropping the projector (1.76 GB, text only) scored 61 with a worst paper of
    11.
- **No retrieval.** Dropping retrieval cost a quarter to a third of the points:
  fine-tuned 2B 39 → 29, fine-tuned 0.8B 26 → 18.
- **A model vote across essay topics** (`--essay-final judge`) chose worse topics
  on the development papers than the lexical final choice.

## Lost artifacts and compute

The sponsored Colab VM was reclaimed at 04:43 CEST on 27 September. Its disk
went with it:
- the merged fine-tune and LoRA adapter;
- the FT Q4_K_M, IQ3_XXS and IQ2_XXS GGUFs;
- the base-model quantizations.

A new A100 VM could not be provisioned (the service returned "Service
Unavailable"), and no paid resources were used. Only the selected GGUF, the projector and the importance
matrix had been downloaded. The larger fine-tuned fallbacks therefore could not
be rerun. `build_model.sh` rebuilds everything from the public base model and the
SFT data. Pass 3 and the June run used a local Metal build of the same llama.cpp
commit.

## Grading

- **Closed items.** `scripts/harness/score.py` scores them against `keys.jsonl`,
  which is never shown to the solver.
- **Open items.**
  - `scripts/harness/grading_packet.py` builds one blinded packet per paper. The
    packet contains every distinct answer from the compared configurations.
    Identical answers are graded once and cached by hash.
  - Claude subagents grade from the packet and the item images only, following
    `scripts/harness/GRADER.md`: a strict CKE rubric where a correct element
    contradicted in the same answer earns nothing.
- **Essays.** Blinded packet and the same strict examiner prompt as in "Essay
  selection".
- **Grader coverage.** Different grader agents graded different batches, so some
  drift between configurations is possible. See the regrade under "Run-to-run
  variance".

## Integrity and limitations

- **Development papers were used for every choice**: model, quantization,
  prompts and essay selector. Their scores are optimistic for this system.
- **Only June 2026 was untouched.** It gives one sample of about 45 non-essay
  points and one essay. Its 27–28 is consistent with the development spread but
  does not establish a reliable pass.
- **All grades come from Claude graders**, not CKE examiners. Two independent
  graders agreed closely on June; the development regrade differed by 2 points on
  one paper.
- **The essays are unreviewed.** They were written by language models: Claude
  subagents and the teammate's generator. No history teacher has reviewed them.
  S13/S14 were written after some development and check-set topics had been
  seen.
- **Answer keys and rubrics** were never in solver prompts, SFT data or the
  retrieval corpus. Marking PDFs stay out of retrieval.
- **The SFT data is not committed.** It contains CKE items and retrieved context
  partly from e-Historia, which has no identified redistribution licence. Rebuild
  it with
  `python3 scripts/harness/build_sft.py --src <finetuine> --out data/sft/nonessay-v1.jsonl`
  and check the md5 above.
- **Size counts the model files only.** The retrieval index (15.9 MB) and the
  essay bank (2.2 MB) are not learned weights and are not counted.

## Reproduce

```bash
# model files (CUDA GPU; about 1.5 h on an A100), or use the GGUFs with the hashes above
LLAMA=/path/to/llama.cpp scripts/harness/build_model.sh /tmp/harness-build
# one exam: organiser exam.json in, answers.json out (starts llama-server itself)
scripts/harness/run_system.sh data/generated/final-exams/2026-june/exam.json answers.json
python3 scripts/harness/score.py --answers answers.json --keys data/generated/final-exams/2026-june/keys.jsonl
```

For development papers without the essay, run
`scripts/harness/make_dev_exams.py`, then `run_exam.py` with the same flags as
`run_system.sh` minus `--essay-bank`. Open answers need a grader: build packets
with `grading_packet.py make` and follow `GRADER.md`.
