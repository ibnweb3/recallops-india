# hackathon.md: RecallOps India (neatHack 2026)

Rules for this file (from the neatlogs hackathon skill): never delete old entries, record only tests that actually ran, keep planned and completed work separate, never fabricate results, no secrets / .env / private traces / tokens / personal data. Link only sanitized, shareable evidence.

## 1. Project summary
- **Name:** RecallOps India (working name)
- **One line:** An agent that takes an official Indian drug-quality alert (CDSCO "Not of Standard Quality" batches), reconciles it against a distributor's messy stock and invoice records, places verified digital holds, traces where held batches went, and proves what it did.
- **Track:** Build an agent that works (the only track)
- **Problem it solves:** CDSCO publishes a monthly list of drug batches that failed quality tests, and stockists, distributors and retailers are expected to find and withdraw those exact batches. The alert is a PDF table (product, batch, manufacturing and expiry month, manufacturer, failed test); the stock is in someone's billing software. Matching them is slow and error-prone: brand versus generic names, strengths inside names, odd batch formats, month-only dates. A failure is specific to a tested batch, so wrongly holding other batches costs money and missing a listed batch is a safety risk.
- **Public repo:** https://github.com/ibnweb3/recallops-india (private for now; to be made public on Oct 12 after a secrets check)
- **Demo video (3 min max):** <url, filled in on Oct 12>

## 2. Team
- Solo: <name / handle you choose to publish>
- Registered on Luma as team: <team name>
- Web check-in done: [ ] (date/time: )

## 3. Stack (what is ACTUALLY used; update as it changes)
| Part | Choice | Status (planned / in use / dropped) |
|---|---|---|
| Language / runtime | Python 3.13 (neatlogs needs < 3.14) | in use |
| LLM provider / model | hackathon LiteLLM gateway (OpenAI-compatible) through the openai SDK 3.28.0; nova-lite for alias judgements, claude-haiku for drafted notices; key in .env as LITELLM_API_KEY | in use |
| Alert parsing | pdfplumber on the CDSCO monthly NSQ PDFs (March 2025); JSON rows copied from the CDSCO online portal for newer months (JUL and AUG 2026) | in use |
| Inventory environment | synthetic CSV fixtures (data/fixtures) loaded into a local SQLite stock service with real state transitions and idempotent holds | in use |
| neatlogs SDK + project | workflowName: recallops-baseline / recallops-agent; @span WORKFLOW/AGENT/TOOL spans plus neatlogs.wrap on the OpenAI client | in use |
| neatlogs MCP / REST (reading cost and KPIs) | | planned |
| Entire CLI | 0.11.4, `entire enable --agent claude-code` | in use |
| entire-graph plugin | | planned |
| cfo.ai (plan / CSV) | | planned |
| Other | | planned |

## 4. How each required tool is used (this feeds the 25% score and the video)
| Tool | Role in building / running / planning | Evidence link or file | Done |
|---|---|---|---|
| neatlogs | traces for the baseline and the agent under separate workflow names; before/after cost, tokens, errors; cost alerts | exported from 4 runs (SDK counters: 0 export failures); trace links recorded in section 5 (private project, login needed); run metrics in evidence/metrics/ | [x] |
| Entire (checkpoints) | every build session checkpointed; no secrets in transcripts | | [ ] |
| Entire (entire-graph) | | | [ ] |
| cfo.ai | unit economics: price per resolved alert vs model cost per alert | | [ ] |

## 5. Evidence checklist (judges verify these)
- [x] Agent improved: before trace link + after trace link + the numbers compared (links are to a private neatlogs project and need a login; making them viewable by judges is not set up)
  - Before (workflowName / trace ids): recallops-baseline, trace 37fd62f8ca903b8bed6a654354af6234: https://app.neatlogs.com/traces/37fd62f8ca903b8bed6a654354af6234?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f
  - After (workflowName / trace ids): recallops-agent. First run (before the added rule), trace a204710bdbc71cce221e7788af251e11: https://app.neatlogs.com/traces/a204710bdbc71cce221e7788af251e11?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f ; after the added rule, trace 24a0438ea5b27de21487c1095a959374: https://app.neatlogs.com/traces/24a0438ea5b27de21487c1095a959374?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f
  - Metrics (correct holds, wrong holds, missed holds, unresolved, tokens, cost USD, duration): round 1 (JUL alert) baseline 56/61 correct, 5 missed, 87 wrong holds; agent 61/61, 0 missed, 0 wrong. Round 2 (JUL+AUG) baseline 80/93, 13 missed, 110 wrong; agent 92/93, 0 missed, 0 wrong, 1 extra row sent to review. Agent run: 31 model calls, 5326 prompt + 3413 completion tokens (the same totals appear in the neatlogs trace), 60.7 s; baseline 4.4 s, no model calls. Cost USD: not read from neatlogs (the trace view I opened showed tokens and time only) and not computed. 13 invoice lines in round 1 and 17 in round 2 have no batch number and are listed as unresolved exposure. Source: evidence/metrics/*.json. Fixture is synthetic, one seed.
- [x] neatlogs used: trace links (section 5, Before/After/Recovery); workflow names recallops-baseline and recallops-agent, 44 spans per agent trace (workflow, agent, tool and LLM spans)
- [ ] Entire used: `entire checkpoint list` output / one `explain`
- [ ] cfo.ai used: business plan covering pricing, costs, revenue, runway (Page link + screenshots)
- [x] Recovery run: 3 holds timed out after the write succeeded; the agent read each row back, found it HELD and did not repeat the write (0 duplicate hold events). Trace d59857e3b5a80adeebbddb83748f18d0: https://app.neatlogs.com/traces/d59857e3b5a80adeebbddb83748f18d0?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f
- [ ] Built in public: links to posts tagged #neatHack
- [ ] Code written during the hackathon: public repo, commits dated Oct 10 to Oct 12
- [ ] No secrets in the repo or in Entire transcripts (checked on: )

## 6. Plan vs completed (keep both lists honest)
### Planned (not done yet)
- [x] Confirm the alert format across more months (done 2026-10-11, see build log): newer alerts are portal-only; JUL-2026 (239 rows) and AUG-2026 (220 rows) read and parsed. Older months (2019 to 2025) not read.
- [x] Fixture generator (done 2026-10-11): recallops/fixtures.py
- [x] Naive baseline (done 2026-10-11): recallops/baseline.py
- [x] Agent loop (done 2026-10-11): recallops/agent.py, matcher.py
- [x] Downstream trace and drafted supplier/customer notices (done 2026-10-11; drafts only, nothing is sent; 12 customer drafts per round are model-written, the rest use a template)
- [ ] Reconciliation and evidence packet: per-round report.json, trace.json and outbox/ exist (git-ignored under runs/); sanitized copies in evidence/ so far hold metrics and the two recovery-run reports only
- [x] Expansion event (done 2026-10-11): the real AUG-2026 alert as a second round reopens 31-32 earlier decisions
- [x] Failure injection (done 2026-10-11): 3 holds time out after the write; the agent reads the service back and does not repeat them
- [ ] Evaluation: correct / wrong / missed / unresolved per run, several runs each. Done so far: one baseline run (deterministic code), three agent runs on one fixture seed. Not done: other seeds, repeated model runs.
- [ ] cfo.ai plan from the measured numbers
- [ ] Demo video + README + submission post

### Completed (move items here only when they work, with the date)
- 2026-10-10: CDSCO NSQ alert parser (recallops/alerts.py) parses the real March 2025 alert into 70 entries (S.No 1-70), joining entries split across page breaks and handling one DD/MM/YYYY date; 6 tests pass.
- 2026-10-11: Synthetic fixtures (339 stock rows, 177 items, 599 sales lines, 60 customers, answer key), SQLite stock service, naive baseline, matcher + agent loop, scorer; live runs traced to neatlogs; 40 tests pass. Results are in the build log entry for 20:15 IST.
- 2026-10-11: CDSCO online portal parser (recallops/portal.py) parses the real JUL-2026 (239 rows) and AUG-2026 (220 rows) NSQ alerts; the PDF parser is unchanged; 15 tests pass in total (6 PDF, 9 portal).
- 2026-10-10: Entire CLI 0.11.4 installed; Python 3.13 environment with neatlogs 1.4.26; neatlogs local doctor and end-to-end probe passed.

## 7. Build log (newest at the bottom; one entry per session; never delete)
Entry format:

### YYYY-MM-DD HH:MM (IST) | session title
- **What changed:** (files / features)
- **Decisions and why:**
- **Experiments / failures / fixes:**
- **Tests actually run:** (command + result; failures listed, not hidden)
- **Evidence added:** (sanitized links only)
- **Next:**

### 2026-10-10 19:10 (IST) | setup and idea choice
- **What changed:** created the repo, .gitignore, this file. Installed Entire CLI 0.11.4. Set up Python 3.13 and neatlogs.
- **Decisions and why:** chose a recall-reconciliation agent on Indian drug-quality alerts. It runs on a real official source, has a checkable answer set, needs few model calls (the model budget is $20), and shows state, recovery and iteration. Earlier ideas considered and dropped: an accessibility fixer, a bug-report verifier, a lead finder.
- **Experiments / failures / fixes:** none yet. Note: building started about six hours after the 12:30 IST kickoff.
- **Tests actually run:** `neatlogs doctor --probe` passed (8 of 8 checks). A one-off pdfplumber extraction of the March 2025 CDSCO NSQ alert returned a clean table (9 pages, about 76 entries); only that one month has been checked so far.
- **Evidence added:** none yet.
- **Next:** extract more months and confirm the format; fixtures; baseline.

### 2026-10-10 19:15 (IST) | alert parser on the real March 2025 CDSCO PDF
- **What changed:** recallops/alerts.py (PDF to structured entries), tests/test_alerts.py, data/alerts/raw/NSQ-2025-03.pdf (public CDSCO document), data/alerts/parsed/NSQ-2025-03.json, requirements.txt.
- **Decisions and why:** keep the raw cell text next to every parsed field so nothing is lost. Dates stay month-level ("YYYY-MM") because the alerts give month/year only.
- **Experiments / failures / fixes:** the first parse gave 73 rows for 70 real entries: three entries are split across page breaks (a fragment with no S.No and no batch at the top of the next page), and one row writes dates as DD/MM/YYYY. Fixed by joining fragments onto the previous entry and keeping the month from the full date. Scripted requests to cdsco.gov.in returned 403 and guessed file names for other months returned 404, so only the March 2025 file (fetched through the web-fetch tool) is in the repo. Newer months are on an online portal that has not been read yet.
- **Tests actually run:** `python -m pytest -q` -> 6 passed. Expected values were read from the PDF itself.
- **Evidence added:** none yet.
- **Next:** read a newer month from the CDSCO portal; fixture generator; naive baseline.

### 2026-10-11 19:45 (IST) | newer CDSCO alerts from the online portal
- **Correction:** this entry was first stamped 14:15 (IST); that was UTC from the shell's `date`. IST is UTC+5:30, so about 19:45.
- **What changed:** recallops/portal.py (portal rows to the same AlertEntry shape), tests/test_portal.py, data/alerts/raw/portal-JUL-2026.jsonl (239 rows) and portal-AUG-2026.jsonl (220 rows), data/alerts/parsed/portal-*.json. AlertEntry gained two optional fields, reporting_source and report_month; recallops/alerts.py is otherwise unchanged.
- **Decisions and why:** newer alerts are not PDFs. cdscoonline.gov.in/CDSCO/viewPublicNSQDrug renders a DataTable from JSON (one table per reporting month, year/month/source filters) with month names like "Jun-2026". Rather than change the PDF parser, a second small parser maps portal rows onto the same entry shape. JUL-2026 is intended as the first alert and AUG-2026 as the expansion alert; they overlap on some batches, which is real data, not something I added. Rows are stored verbatim (typos, line breaks and "?" placeholders included); cleaning happens in the parser and the original text stays in `raw`.
- **Experiments / failures / fixes:** the sandboxed shell could not resolve cdscoonline.gov.in, so the rows were read in the built-in browser. A browser-to-localhost POST was blocked by the browser pane, so the rows were copied through chat in chunks and written to disk by hand. To catch transcription errors, each file was checked against a 32-bit FNV-1a hash and per-row lengths computed on the page: one dropped character ("Dist Dhar" for "Dist. Dhar") was found that way and fixed; after that JUL (71131 characters, 239 rows) and AUG (67221 characters, 220 rows) match the page exactly. The portal's fields are clean enough to parse, but the data is messy: 2 July rows have batch "Not Mentioned" and no dates, 1 July batch number is split over two lines ("T-2611
36"), 1 August row has expiry before manufacture, 2 August batches carry a trailing comma, and one batch is reported twice with different spacing (BKBP02601 and "BKBP O2601"). The parser flags these in `issues` instead of dropping them.
- **Tests actually run:** `python -m pytest -q` -> 15 passed (6 existing PDF tests, 9 new portal tests). `python -m recallops.portal` on each file: JUL 239 entries, 3 with issues; AUG 220 entries, 3 with issues.
- **Evidence added:** none yet (no traces).
- **Next:** fixture generator (stock, invoices, downstream sales from these real batches, labelled synthetic); naive name-only baseline; agent loop under neatlogs.

### 2026-10-11 20:00 (IST) | synthetic fixtures, stock service, naive baseline
- **What changed:** recallops/fixtures.py (generator), data/fixtures/*.csv and truth.json (answer key), recallops/stockservice.py (SQLite stock service), recallops/evaluate.py (scorer), recallops/baseline.py, tests/test_fixtures.py and tests/test_stock_and_baseline.py.
- **Decisions and why:** every table is labelled synthetic (a `_synthetic` column and SYNTHETIC-FIXTURE.txt). Affected stock rows are built from real JUL/AUG-2026 alert rows; everything else is invented. Deliberate mess: shorthand and typo'd item names, pharmaceutical synonyms (acetaminophen for paracetamol), batch spellings (case, separators, trailing comma, O for 0), month formats, missing dates or manufacturer, the same batch split across two warehouses, sibling batches of an affected product (some one character apart), the same batch number on a different product (collision), same batch with a different manufacturer, ledger gaps, and sales lines with no batch number. truth.json says, for each stock row and each alert round, whether a careful operator should hold, review or leave it. "no_hold" is recorded as a scoped finding, never a clearance. Scoring reads the stock service state, not the run's own claims.
- **Experiments / failures / fixes:** the first baseline run held 198 of 279 rows because every "unrelated" item reused a product name from the alerts, which made the baseline look like a straw man. I rebalanced the generator (66 generics that appear in no alert, with fictional makers, plus 38 name-alike lots) and regenerated; this changed the fixture after seeing a baseline result, which is recorded here. Two of my own tests were wrong (one scored round 1 against the state after round 2; one expected a collision to be cleared when dates matched), fixed in the tests, not in the code.
- **Tests actually run:** `python -m pytest -q` -> 30 passed at the end of this step. Baseline (no model calls, deterministic) on the final fixtures: round 1 (JUL alert): correct holds 56 of 61, missed 5, wrong holds 87, review rows 0 of 11 flagged; round 2 (JUL + AUG): correct 80 of 93, missed 13, wrong holds 110. The baseline holds every sibling batch and every name-alike product, and misses shorthand and synonym names.
- **Evidence added:** evidence/metrics/live-baseline.json (from the traced run, see next entry).
- **Next:** the agent loop traced under its own workflow name.

### 2026-10-11 20:15 (IST) | agent loop, live runs traced to neatlogs
- **What changed:** recallops/matcher.py (evidence rules, no model), recallops/agent.py (reconcile, act, verify by read-back, trace customers, draft notices, reopen on a second alert), recallops/llm.py (gateway client with a call cap), recallops/tracing.py (optional neatlogs), recallops/run.py, scripts/llm_probe.py, tests/test_agent.py, openai==3.28.0 in requirements.txt.
- **Decisions and why:** the code does the matching and arithmetic. The model is asked only (1) whether two product names are the same drug when code cannot tell (nova-lite), and (2) to draft notices (claude-haiku), at most 12 customer drafts per round, the rest from a template. A hold needs batch (case/separator/O-0 normalised, never edit distance) plus product plus at least one corroboration (manufacturer or dates) and no contradiction; conflicts or missing corroboration go to human review. A model failure or "unsure" never becomes a hold or a clearance. Nothing is sent, and the agent never releases a hold. The agent is an explicit loop with model judgement steps, not a free-running tool-calling model: cheaper and easier to verify.
- **Experiments / failures / fixes:** the shell used for my own commands has no network, so live runs (model gateway, neatlogs) were run from the Terminal panel. First live agent run (tag run:live-agent): round 2 missed 1 held row, "Para+Phen+Caff TAB", shorthand for 3 of the alert's 4 ingredients; the model answered "different combination of ingredients" and the row was cleared although batch, manufacturer and dates all agreed. I added the rule that a model "no" escalates to review in that case, then re-ran (tag run:live-agent-v2). `git commit` hung for over 30 minutes because Entire's prepare-commit-msg hook waits at a "Link this commit to session context? [Y/n/a]" prompt that a non-interactive shell cannot answer; I did not answer it on the builder's behalf.
- **Tests actually run:** `python -m pytest -q` -> 40 passed (offline, the model replaced by a stub). Live runs, same fixture and seed, results scored against truth.json straight after each round:
  - baseline (recallops-baseline, no model): round 1 correct 56/61, missed 5, wrong holds 87; round 2 correct 80/93, missed 13, wrong holds 110.
  - agent, first run (run:live-agent): round 1 correct 61/61, missed 0, wrong 0, review 11 of 11 weak or conflicting rows flagged; round 2 correct 92/93, missed 1, wrong 0.
  - agent, after the added rule (run:live-agent-v2): round 1 correct 61/61, missed 0, wrong 0; round 2 correct 92/93, missed 0, wrong 0, review 11 of 11 plus 1 extra (the shorthand row). Customers traced 44/44 (round 1) and 54/54 (round 2) with no extras; 13 and 17 invoice lines have no batch number and are listed as unresolved exposure. Round 2 reopened 32 earlier decisions (rows judged not listed or review in round 1 that the second alert turned into holds). 31 model calls per run, about 5.3k prompt and 3.4k completion tokens in total; wall time about 60 s per run.
  - recovery run (run:live-agent-recovery): 3 holds in round 1 time out after the write succeeded; the agent read each row back, found it HELD, and did not repeat the write: 0 duplicate hold events, 0 verification problems, results identical to v2.
  - neatlogs SDK delivery counters after each traced run: 0 span drops, 0 export failures. I did not check the neatlogs dashboard or API, so I have not confirmed the traces show up there or how cost is computed.
- **Evidence added:** evidence/metrics/*.json and evidence/reports/ (round reports of the recovery run). Trace links: none recorded yet.
- **Next:** copy the trace links for the four traced runs from neatlogs into the evidence checklist; answer the Entire prompt so these changes can be committed and checkpointed; cfo.ai plan from measured token counts; README and demo script; other fixture seeds and repeated runs.

### 2026-10-11 20:55 (IST) | neatlogs trace links recorded
- **What changed:** hackathon.md only (section 3 and 4 tables, section 5 evidence checklist).
- **Decisions and why:** the four live runs map to traces by workflow name and by the duration neatlogs shows, which matches my own run metrics: recallops-baseline 4.4 s (trace 37fd62f8ca903b8bed6a654354af6234); recallops-agent first run 55.5 s (a204710bdbc71cce221e7788af251e11); after the added rule 60.7 s (24a0438ea5b27de21487c1095a959374); recovery run 58.5 s (d59857e3b5a80adeebbddb83748f18d0). The dashboard's list view does not show the run:<name> tag, so duration is what ties each trace to a run. The dashboard also lists one older trace from 10 October (neatlogs.doctor.v2, the setup check), which is not part of these results.
- **Experiments / failures / fixes:** I signed nothing in myself; the builder signed in to neatlogs in the built-in browser and I only read the traces list and trace pages. Token totals on the v2 trace (5326 prompt, 3413 completion) match my own counters. I did not find a dollar cost in the trace view, so no cost figure is recorded.
- **Tests actually run:** none (documentation change).
- **Evidence added:** trace links in section 5. They point to a private neatlogs project and need a login, so a judge cannot open them yet.
- **Next:** make the traces viewable by judges (share link or screenshots) and check for a cost column; cfo.ai plan; README and demo script; other fixture seeds and repeated runs.

## 8. Demo details
- **Length:** 3 min max. Must cover neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning, result for each.
- **Script:** (to be written once the loop works)
- **How to reproduce the demo:**
  1.
  2.
- **Recorded:** [ ]  **Uploaded:** [ ]  **Link checked from a logged-out browser:** [ ]

## 9. Known limitations and next steps
- Stock, invoices and failures are synthetic fixtures built from real alert batches. Results show the mechanics, not proven customer value.
- A CDSCO NSQ result is specific to the tested batch. "Not on the list" is a scoped finding, never a safety clearance. A digital hold does not prove physical removal.
- Recall deadlines and retailer duties per recall class were not confirmed from CDSCO's own text, so they are not hard-coded.
- The fixture generator, the answer key and the matcher were written by the same builder in the same week. The mess types in the fixtures (name shorthand, batch spellings, missing dates, sibling batches, collisions) are the ones the matcher was designed for. Zero wrong and zero missed holds on this fixture shows the mechanics work; it does not show the same on real distributor records, which will contain mess that is not modelled here.
- One rule was added to the matcher after seeing a live run (a model's "no" cannot clear a row when batch, manufacturer and dates all agree). Both the before and after runs are recorded below.
- The ledger check only covers held lots; the five deliberate ledger-gap lots in the fixtures did not land on held lots, so the live runs do not exercise that path.
- Sales lines with no batch number are reported as unresolved exposure; they are not matched to customers and never cleared.
- No customer interviews and no willingness-to-pay evidence; the business plan is a hypothesis.
- Alert PDFs may change layout between months; only one PDF month has been checked. Newer months are portal-only and were copied by hand from the portal's own table data (JUL-2026 and AUG-2026 only); I did not build or test a live fetch from the portal.

## 10. Submission status
- Window: Oct 12, 7:00-11:55 PM IST (planned close; final cutoff is announced on Discord)
- [ ] Repo public, commits verified
- [ ] Evidence folder in repo
- [ ] Video link works
- [ ] Quote post drafted with: team, name, project, public repo, demo link, official neatlogs post kept attached
- [ ] Posted (time):
- Post URL:
- Note: opening the draft alone does not submit. Do not submit without the builder's explicit go-ahead.
