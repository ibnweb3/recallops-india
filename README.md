# RecallOps India

An agent that takes an official Indian drug-quality alert (CDSCO "Not of Standard Quality" batches), finds those exact batches in a distributor's stock, places verified digital holds, traces which customers received them, drafts notices, and reopens its earlier decisions when a second alert adds batches.

Built solo for neatHack 2026 ("Build an agent that works").

> **Read this first.** The alert batches are real CDSCO data. The distributor, stock, invoices, customers and every deliberate error are **synthetic** (labelled in every file). A CDSCO result is specific to the tested batch: "not on the list" is a scoped finding, never a safety clearance, and a digital hold does not prove physical removal. All business numbers are hypotheses. See [Limits](#limits).

## What it does

```
CDSCO alerts (real) -> matcher (code) -> alias check (small model, only if a name is ambiguous)
                    -> holds in a stock service -> read every hold back -> trace customers -> draft notices (never sent)
```

- **Code does the matching and the arithmetic.** A hold needs the batch number (normalised for case, separators and O/0 only, never edit distance), the product, and at least one corroboration (manufacturer or dates), with no contradiction. Conflicts or thin evidence go to a human.
- **The model has two small jobs:** judge whether two product names are the same drug when code cannot tell, and draft notices. A failed or "unsure" answer never becomes a hold or a clearance, and a model "no" cannot clear a row when batch, manufacturer and dates all agree.
- **Holds are real state changes** in a local SQLite stock service, idempotent per action id. If a hold times out after it was written, the agent reads the row back instead of repeating it.
- **It never sends anything and never releases a hold.**
- **A second alert reopens decisions** (rows judged "not listed" or "review" can become holds; existing holds are left alone).

## Results

Same synthetic fixture, scored against an answer key (`data/fixtures/truth.json`) by reading the stock service state. Round 1 = real JUL-2026 alert; round 2 = JUL + AUG-2026.

| | Correct holds | Missed | Wrong holds |
|---|---|---|---|
| Name-only baseline, round 1 | 56 / 61 | 5 | 87 |
| Name-only baseline, round 2 | 80 / 93 | 13 | 110 |
| Agent, round 1 | 61 / 61 | 0 | 0 |
| Agent, round 2 | 92 / 93 | 0 | 0 (the 93rd row goes to review) |

Also: 12 uncertain rows routed to review each round; round 2 reopened 32 earlier decisions; customers traced 44/44 and 54/54; 13 and 17 invoice lines have no batch number and are reported as unresolved exposure; in the recovery run, 3 holds timed out after writing and were reconciled by read-back with 0 duplicate hold events. One agent run is about 5.3k prompt + 3.4k completion tokens over 31 model calls (about 60 s). Raw numbers: [`evidence/metrics/`](evidence/metrics).

These results come from one fixture written by the same author as the matcher. They show the mechanics work, not that real distributor records will behave the same.

## The three tools

- **neatlogs**: the baseline and the agent run as separate workflows (`recallops-baseline`, `recallops-agent`), with workflow, agent, tool and model spans. Four traced runs; the workspace is private, so screenshots of the traces are in [`evidence/neatlogs/`](evidence/neatlogs) (trace ids are in [`hackathon.md`](hackathon.md)).
- **Entire**: each build step is a checkpoint tied to the session. Command output is in [`evidence/entire/`](evidence/entire).
- **cfo.ai**: a 12-month unit-economics and runway model from the measured token usage. Summary and screenshots in [`evidence/cfo-ai/`](evidence/cfo-ai). Human review, not model tokens, dominates cost under the stated assumptions (about 99.8% of direct cost). Prices, customers and review time are placeholders; no customer has validated them.

[`hackathon.md`](hackathon.md) is the build log: every step, failure, fix and test that really ran.

## Run it

Python 3.13 (neatlogs needs below 3.14).

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
RECALLOPS_TRACE=0 .venv/Scripts/python -m pytest -q          # 40 tests, offline
.venv/Scripts/python -m recallops.fixtures                   # regenerate the synthetic fixtures (deterministic, seed in the file)
.venv/Scripts/python -m recallops.run baseline               # name-only baseline, scored
.venv/Scripts/python -m recallops.run agent --no-llm         # agent without the model: uncertain names go to review
```

Live runs need a `.env` with `LITELLM_API_KEY` (an OpenAI-compatible gateway; `LLM_BASE_URL`, `LLM_MODEL`, `LLM_DRAFT_MODEL` are optional) and `NEATLOGS_API_KEY` for traces. Never commit `.env`.

```bash
.venv/Scripts/python -m recallops.run agent --name my-run
.venv/Scripts/python -m recallops.run agent --name my-recovery --inject-timeout 3 --inject-round 1
```

Output goes to `runs/<name>/` (git-ignored): metrics, per-round reports, traced customers and the drafted notices (`outbox/`).

## Layout

| Path | What |
|---|---|
| `recallops/alerts.py`, `portal.py` | Parse the real March 2025 CDSCO PDF and the JUL/AUG-2026 portal rows |
| `recallops/fixtures.py` | Synthetic distributor built around real alert batches, plus the answer key |
| `recallops/stockservice.py` | SQLite stock service with real state transitions and failure injection |
| `recallops/matcher.py`, `agent.py` | Evidence rules and the agent loop |
| `recallops/baseline.py`, `evaluate.py`, `run.py` | Name-only baseline, scorer, runner |
| `recallops/llm.py`, `tracing.py` | Model client with a call cap; optional neatlogs tracing |
| `data/alerts/` | Real CDSCO alert rows (raw and parsed) |
| `data/fixtures/` | Synthetic CSVs and `truth.json` (the answer key; never given to the agent) |
| `evidence/` | Run metrics, Entire output, cfo.ai summary |

## Limits

- One synthetic fixture, written by the same author as the matcher. Real distributor records will have mess that is not modelled.
- One matcher rule was added after seeing a live run (recorded in `hackathon.md`).
- Only two portal months and one PDF month were parsed; there is no live fetch from the CDSCO portal.
- No customer interviews; the business plan is a hypothesis.
- Recall deadlines and retailer duties per recall class are not hard-coded because they were not confirmed from CDSCO's own text.
- A CDSCO NSQ alert is not the same as a recall direction; a pharmacist-led action policy would be needed before real use.

## Data

Alert rows come from CDSCO's public NSQ alerts (the March 2025 PDF and the online portal, cdscoonline.gov.in). Everything else is generated.

License: not yet chosen by the author.
