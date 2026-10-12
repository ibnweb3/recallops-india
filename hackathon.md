# hackathon.md: RecallOps India (neatHack 2026)

Rules for this file (from the neatlogs hackathon skill): never delete old entries, record only tests that actually ran, keep planned and completed work separate, never fabricate results, no secrets / .env / private traces / tokens / personal data. Link only sanitized, shareable evidence.

## 1. Project summary
- **Name:** RecallOps India (working name)
- **One line:** An agent that takes an official Indian drug-quality alert (CDSCO "Not of Standard Quality" batches), reconciles it against a distributor's messy stock and invoice records, places verified digital holds, traces where held batches went, and proves what it did.
- **Track:** Build an agent that works (the only track)
- **Problem it solves:** CDSCO publishes a monthly list of drug batches that failed quality tests, and stockists, distributors and retailers are expected to find and withdraw those exact batches. The alert is a PDF table (product, batch, manufacturing and expiry month, manufacturer, failed test); the stock is in someone's billing software. Matching them is slow and error-prone: brand versus generic names, strengths inside names, odd batch formats, month-only dates. A failure is specific to a tested batch, so wrongly holding other batches costs money and missing a listed batch is a safety risk.
- **Public repo:** https://github.com/ibnweb3/recallops-india (public since 2026-10-12, after a secrets check)
- **Demo video (3 min max):** https://youtu.be/8an_y3CCGqg (YouTube, public, 1:44)

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
| cfo.ai (plan / CSV) | free workspace; Ari built a hypothesis-based unit-economics and runway model from our measured token usage | in use |
| Other | | planned |

## 4. How each required tool is used (this feeds the 25% score and the video)
| Tool | Role in building / running / planning | Evidence link or file | Done |
|---|---|---|---|
| neatlogs | traces for the baseline and the agent under separate workflow names; before/after cost, tokens, errors; cost alerts | exported from 4 runs (SDK counters: 0 export failures); trace ids recorded in section 5 (private project, login needed, no share links made); screenshots of three traces in evidence/neatlogs/; run metrics in evidence/metrics/ | [x] |
| Entire (checkpoints) | every build session checkpointed; no secrets in transcripts | evidence/entire/ (checkpoint list, explain, token view); 4 permanent checkpoints for 4 build steps; transcripts scanned for our key values on 2026-10-12: none found | [x] |
| Entire (entire-graph) | | | [ ] |
| cfo.ai | unit economics: price per resolved alert vs model cost per alert | plan pages (private, login needed): https://app.cfo.ai/quick-katydid-282d8b64/pages/420adc7b-5fd2-4e0f-a0f9-2e099aeb4929 ; evidence/cfo-ai/ (summary and screenshots) | [x] |

## 5. Evidence checklist (judges verify these)
- [x] Agent improved: before trace link + after trace link + the numbers compared (the trace links are to a private neatlogs project and need a login; by the builder's choice no share links were made, and screenshots of the baseline, agent and recovery traces are in evidence/neatlogs/ instead)
  - Before (workflowName / trace ids): recallops-baseline, trace 37fd62f8ca903b8bed6a654354af6234: https://app.neatlogs.com/traces/37fd62f8ca903b8bed6a654354af6234?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f
  - After (workflowName / trace ids): recallops-agent. First run (before the added rule), trace a204710bdbc71cce221e7788af251e11: https://app.neatlogs.com/traces/a204710bdbc71cce221e7788af251e11?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f ; after the added rule, trace 24a0438ea5b27de21487c1095a959374: https://app.neatlogs.com/traces/24a0438ea5b27de21487c1095a959374?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f
  - Metrics (correct holds, wrong holds, missed holds, unresolved, tokens, cost USD, duration): round 1 (JUL alert) baseline 56/61 correct, 5 missed, 87 wrong holds; agent 61/61, 0 missed, 0 wrong. Round 2 (JUL+AUG) baseline 80/93, 13 missed, 110 wrong; agent 92/93, 0 missed, 0 wrong, 1 extra row sent to review. Agent run: 31 model calls, 5326 prompt + 3413 completion tokens (the same totals appear in the neatlogs trace), 60.7 s; baseline 4.4 s, no model calls. Cost USD: not read from neatlogs (the trace view I opened showed tokens and time only) and not computed. 13 invoice lines in round 1 and 17 in round 2 have no batch number and are listed as unresolved exposure. Source: evidence/metrics/*.json. Fixture is synthetic, one seed.
- [x] neatlogs used: trace links (section 5, Before/After/Recovery; login needed) and screenshots (evidence/neatlogs/); workflow names recallops-baseline and recallops-agent, 44 spans per agent trace (workflow, agent, tool and LLM spans)
- [x] Entire used: `entire checkpoint list`, one `explain` and the `tokens` view are saved in evidence/entire/ (the explain file omits the transcript section). The 5th commit (trace links) and later commits are not yet permanent checkpoints in the list; the entire-graph plugin is not set up.
- [x] cfo.ai used: business plan covering pricing, costs, revenue, runway. Economics page https://app.cfo.ai/quick-katydid-282d8b64/pages/420adc7b-5fd2-4e0f-a0f9-2e099aeb4929 ; demo script page https://app.cfo.ai/quick-katydid-282d8b64/pages/2992f952-525d-4b37-96a6-01b390a0eff1 ; inputs page https://app.cfo.ai/quick-katydid-282d8b64/chat/8b28b2aa-ac9f-482f-aad1-5fe6308fc554?panel=page&pageId=11660b66-8470-4aee-809e-f409e8375fc1. Screenshots and a summary are in evidence/cfo-ai/. The workspace is private and sharing is not enabled. All financial inputs except measured token usage are unvalidated hypotheses, and the plan says so.
- [x] Recovery run: 3 holds timed out after the write succeeded; the agent read each row back, found it HELD and did not repeat the write (0 duplicate hold events). Trace d59857e3b5a80adeebbddb83748f18d0: https://app.neatlogs.com/traces/d59857e3b5a80adeebbddb83748f18d0?orgId=ce7719a1-83b3-44f9-bbb2-e503972e205f&projectId=81cd14fe-6d50-4a94-a711-53b905a7d30f
- [ ] Built in public: links to posts tagged #neatHack
- [x] Code written during the hackathon: public repo, commits dated Oct 10 to Oct 12 (all commits in the history are dated 2026-10-10 to 2026-10-12; the repo was made public on 2026-10-12)
- [x] No secrets in the repo or in Entire transcripts (checked on: 2026-10-12): the two key values in .env (LITELLM_API_KEY, NEATLOGS_API_KEY) are absent from all 20 commits, the 5 Entire checkpoint refs, the working tree and both session transcripts. Not covered: the ElevenLabs key (it is not in this project and was never read by me), anything added after the check, and personal data (the transcripts and checkpoints contain the builder's email address and local file paths). Re-run the check right before the repo is made public.

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
- [x] cfo.ai plan from the measured numbers (done 2026-10-12; token usage measured, prices and customers hypothetical)
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

### 2026-10-12 05:00 (IST) | cfo.ai plan built from the measured numbers
- **What changed:** evidence/cfo-ai/ (README with inputs and results, three screenshots). hackathon.md tables and checklist. No code changed.
- **Decisions and why:** the builder signed up for cfo.ai (free workspace "Quick Katydid"); I only used the signed-in browser session, entered no credentials, and did not turn on sharing. I asked Ari for a 12-month unit-economics and runway model, passing the measured usage per agent run (5,326 prompt + 3,413 completion tokens, 31 calls, about 60 s, about 11 rows to human review) separately from my own placeholder assumptions (model price USD 1 per million tokens, subscription USD 150 per month, 4 runs per distributor-month with a 1-run second scenario, review 3 minutes per row at USD 8 per hour, hosting USD 60 per month, starting cash USD 10,000, 1 to 20 paying distributors over 12 months). Ari asked three clarifying questions (monthly distributor counts and start month, runs per month for the main case, and cost scope); I answered them with further assumptions, written into the prompt as hypotheses. Ari tags every input MEASURED or HYPOTHESIS and states that founder pay, sales, legal/compliance and taxes are EXCLUDED, not zero.
- **Experiments / failures / fixes:** typing the first long prompt froze the browser tab for about a minute but the full text went in. Ari's first reply said "run" meant a two-alert run, which is how the measurements were taken; I kept that wording in the plan.
- **Tests actually run:** none (no code). I checked Ari's arithmetic by hand: 99 distributor-months x USD 150 = USD 14,850 revenue; 99 x USD 17.63 + 12 x USD 60 = USD 2,466 costs; closing cash USD 22,384; the one-run case USD 1,156 costs and USD 23,694 closing cash. They match.
- **Result (hypothesis only):** direct cost per run about USD 4.41, of which model tokens are USD 0.0087 and human review USD 4.40 (99.8%); gross margin 88.2% at 4 runs and 97.1% at 1 run before hosting; cash stays positive in both cases, so runway is N/A. Changing model price from 0.5x to 10x barely moves margin; the review-time assumption and price are what matter. This says nothing about whether any distributor would pay: there is no customer evidence.
- **Evidence added:** evidence/cfo-ai/README.md and screenshots; plan page links in section 5 (private).
- **Next:** make the demo cover all three tools; Entire checkpoint evidence (`entire checkpoint list` and one explain); make trace and cfo.ai pages viewable by judges; record the video; make the repo public after a secrets check.

### 2026-10-12 06:00 (IST) | Entire evidence and a narrated demo video
- **What changed:** evidence/entire/ (checkpoint list, explain header and file list, token view), demo/build_video.py, demo/narration.json, demo/assets/, .gitignore (demo/build/). hackathon.md tables and demo section.
- **Decisions and why:** the video is built, not recorded: seven slides drawn from evidence/metrics, a real neatlogs trace screenshot, the real `entire checkpoint list` output and the cfo.ai screenshot, read by Microsoft's built-in Zira voice. It is 153 s, 1280x720. It states on screen and aloud that the data is synthetic, the financials are hypotheses and the result is one fixture written by the same builder. It covers neatlogs, Entire and cfo.ai (architecture, implementation, runtime, reasoning, result for each, though Entire and cfo.ai slides name only the parts that apply). The mp4 is not committed; the builder uploads it.
- **Experiments / failures / fixes:** first render had text overflowing the architecture boxes, a label overlapping the results columns and the command line overlapping the Entire output; fixed and re-rendered. The first draft said "every commit is a checkpoint" but the trace-links commit is not in the list, so it now says each build step. Checked the mp4 with ffprobe (h264 + aac, 152.9 s) and an audio level scan (mean -20.5 dB).
- **Tests actually run:** none for code. Entire checks: `entire checkpoint list` (5 entries: 4 permanent, 1 temporary), `entire checkpoint explain` and `entire checkpoint tokens` for the agent-loop checkpoint (46.4M tokens counted, 98.6% cache/context replay, 146 API calls). Secret scan: the real key values from .env are absent from both session transcripts and from the repo; the only secret-shaped strings were 'lisk-builders...' URLs from earlier research.
- **Evidence added:** evidence/entire/*.txt. The Entire checkpoints, including full session transcripts, were pushed to GitHub with the code; the transcripts contain the builder's email address and local paths, so review them before the repo is made public.
- **Next:** upload the video and check the link logged out; make the neatlogs and cfo.ai pages viewable; README; web check-in and team name; posts; make the repo public after a final check; submission post.

### 2026-10-12 07:45 (IST) | demo video redone with the builder's ElevenLabs method and a local case console
- **What changed:** demo/site/ (a small local case console: decisions with reasons, review queue, reopened decisions, traced customers and draft notices, the timeout-recovery run, and evidence panels for neatlogs, Entire and cfo.ai), demo/make_site_data.py, demo/kit/ (narration, recorder, mixer, local server, run-tts.ps1, env.example.sh), demo/recallops-india-demo.mp4 (not committed). hackathon.md demo section.
- **Decisions and why:** the earlier cut used a built-in Windows voice because I did not know the builder already had a saved demo method; I had not looked, and per-project memory did not carry it over. The builder asked for the same voice and settings as the Colosseum demo. I found them in the builder's saved note and kit (demo-video-method, demo-video-kit): one uncut ElevenLabs request, model eleven_v4, voice c6SfcYrb2t09NHXiT80T, stability 0.18, similarity 0.75, style 0.65, speaker boost off; browser recorded against the audio clock; loudness normalised to -16 LUFS; no captions. The project has no live site (it is a command-line agent over local fixtures), so the screen recording is of a local console that only shows real artifacts: the decisions are recomputed with the same matcher using the model's recorded alias judgements and checked against the counts the live runs reported (61 hold / 12 review / 266 not listed in round 1; 92 / 12 / 235 in round 2). It is a view of recorded results, not a live run of the agent.
- **Experiments / failures / fixes:** the first dry recording showed all three evidence panels visible at once (a CSS rule overrode the hidden attribute), fixed. The model's draft notices contain stray markdown asterisks and a "[Distributor Name]" placeholder: the asterisks are stripped for display only and the narration now says a person finishes and sends each draft. The ElevenLabs key file already on the machine (from the Congress Desk project) worked; the builder should rotate or delete it as the kit notes.
- **Tests actually run:** no code tests. Video checks: a dry run with silent audio to fix the choreography (no LATE steps), then the real take: silencedetect pauses 0.35 to 0.70 s, ebur128 integrated -16.6 LUFS and peak -1.3 dBFS, h264 + aac 104.3 s, and a 13-frame contact sheet checked against the script. I cannot hear audio, so it was not listened to.
- **Evidence added:** none beyond the video file; it is not committed because the builder uploads it.
- **Next:** the builder listens once and approves or asks for a change of tone; upload the video and check the link logged out; README; make the neatlogs and cfo.ai pages viewable; check-in, team name, posts; make the repo public after a final check.

### 2026-10-12 09:15 (IST) | README, pre-public checks and post drafts
- **What changed:** README.md, submission-drafts.md (drafts only, not posted), demo/kit/env.example.sh and run-tts.ps1 (local paths and the other project's key-file path replaced with placeholders), hackathon.md checklist.
- **Decisions and why:** done while the builder edits the video. I prepared everything that does not publish anything. I did not make the repo public, enable sharing on the neatlogs or cfo.ai pages, post, or answer the Luma check-in; those are outward-facing and the builder had said to ask first. No licence added: that is the author's choice.
- **Experiments / failures / fixes:** `git grep` of the working tree found local paths only in git-ignored files (demo/kit/env.sh, __pycache__) after the placeholder edit. The README states the results with the same caveats as this log (one synthetic fixture, same author, one rule added after a live run).
- **Tests actually run:** `python -m pytest -q` -> 40 passed. Secret scan of all commits, the 5 Entire checkpoint refs, the working tree and both session transcripts for the two .env key values: no hits.
- **Evidence added:** README.md.
- **Next:** builder: listen to and edit the video, upload it to X, link check logged out, team name and Luma check-in, decide on the licence, sharing of the neatlogs and cfo.ai pages, and when to make the repo public; then quote-post during the 7:00 to 11:55 PM IST window.

### 2026-10-12 10:00 (IST) | video tooling and post drafts kept out of the public repo
- **What changed:** .gitignore now ignores demo/ and submission-drafts.md; README layout table and sections 8 and 10 of this file no longer point at them. The files stay on the builder's machine.
- **Decisions and why:** the builder asked that the video script, the recording tooling and anything not needed by other people stay out of the public repo. The commit that had added them (a0d21af) was local only, so I undid it with a soft reset before anything was pushed and recommitted without them; no history containing them was published. Earlier log entries above still name demo/ files (the log is not edited retroactively): they exist locally only.
- **Experiments / failures / fixes:** none.
- **Tests actually run:** none (no code change).
- **Evidence added:** none.
- **Next:** push; builder to listen to and edit the video and upload it to X.

### 2026-10-12 10:45 (IST) | repo made public
- **What changed:** repository visibility (GitHub), and the status lines in this file.
- **Decisions and why:** the builder asked for it. Before the switch I re-ran the secret scan over all 19 commits and 8 refs (5 are Entire checkpoint refs): no .env key value, no secret-shaped string. The repo contains no video tooling, narration script or post drafts (git-ignored on purpose).
- **Experiments / failures / fixes:** none. Checked from a signed-out browser: the repo page shows "Public", the README and the folders. The GitHub description still says "work in progress"; not changed.
- **Tests actually run:** none (no code change). `gh repo edit --visibility public` succeeded.
- **Evidence added:** none.
- **Next:** upload the video to X and check it logged out; team name and Luma check-in; licence choice; share or screenshot the neatlogs and cfo.ai pages; submission quote-post inside the 7:00 to 11:55 PM IST window.

### 2026-10-12 13:30 (IST) | demo video uploaded to YouTube
- **What changed:** hackathon.md only (demo link and checklist). The video itself is on YouTube, public.
- **Decisions and why:** the builder asked for a public YouTube upload of the edited video. The upload tool I had accepts under 10 MB and the edit is 15.7 MB, so the uploaded file is a 1280x720 re-encode of the edit (9.8 MB, same audio, same 104 s). Title and description state that the stock and customers are synthetic, the alert batches are real, the business numbers are hypotheses, and link to the repo. Settings I chose: not made for kids; AI-use question answered Yes because the voice-over is a realistic AI-generated voice; no collaborators, no promotion.
- **Experiments / failures / fixes:** the first "Upload videos" click opened a native file picker that froze the page; Escape recovered it, and the dashboard's upload icon opened the in-page dialog instead. The title and description fields are rich text, so they were typed rather than set.
- **Tests actually run:** none (no code). YouTube's copyright check: no issues found. Watch page loaded signed out.
- **Evidence added:** the public video link.
- **Next:** X upload and the tweet (builder); team name and Luma check-in; quote-post in the 7:00 to 11:55 PM IST window with this link as the demo link.

### 2026-10-12 15:10 (IST) | screenshots for the private tools; submission form opened
- **What changed:** evidence/neatlogs/ (three full-resolution trace screenshots and a README), README.md and this file's evidence wording.
- **Decisions and why:** the builder chose screenshots over share links for the neatlogs and cfo.ai pages. The neatlogs screenshots were taken in the builder's signed-in Chrome; the cfo.ai screenshots were already in evidence/cfo-ai/. No share links were created and no page visibility was changed.
- **Experiments / failures / fixes:** I opened the submission form at neatlogs.com/submission, clicked Continue on step 1 (it only saves a draft) and stopped at step 2, which needs the builder's check-in email and an emailed verification code. I did not enter an email or submit. The builder's quote post (x.com/ibnWeb3/status/2109644447700902337) quotes the official launch post, carries the video and tags @neatlogs, @EntireHQ and @arithecfo, as the form requires.
- **Tests actually run:** none (no code).
- **Evidence added:** evidence/neatlogs/.
- **Next:** builder to confirm the check-in email and whether I may read the verification code from their Gmail; then fill the remaining form fields and submit only after a final review with the builder.

## 8. Demo details
- **Length:** 3 min max. Must cover neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning, result for each.
- **Script:** one flowing narration of 13 scenes (problem, holds, why, review queue, second alert, customers, unresolved invoice lines, drafts, timeout recovery, neatlogs, Entire, cfo.ai, limits). Numbers spoken come from the real run artifacts. The narration and the recording tooling (a local case console, scripts, assets) are kept on the builder's machine under demo/ and are git-ignored on purpose: they are not part of the public repo.
- **How to reproduce the results shown in the demo:**
  1. `.venv\Scripts\python.exe -m recallops.run baseline` and `... agent` (needs network and keys in .env for traces and model calls; `--no-llm` and `RECALLOPS_TRACE=0` run offline). Metrics for the runs shown are in evidence/metrics/.
  2. The video itself is a screen recording of a local console over those recorded results with an ElevenLabs voice-over; its tooling is not published.
- **Recorded:** [x] 2026-10-12, 104 s, 1280x720: a screen recording of a local case console (not a deployed site; there is no live site) against one uncut ElevenLabs take (Voice C), no captions. Audio verified by measurement (pauses 0.35 to 0.7 s, -16.6 LUFS, peak -1.3 dBFS), not yet by a person listening. The builder then edited it (animated word captions, 1600x900).  **Uploaded:** [x] YouTube, public, 2026-10-12: https://youtu.be/8an_y3CCGqg (a 1280x720 copy re-encoded to under 10 MB for the upload tool, same audio; the builder's full-quality edit is kept locally).  **Link checked from a logged-out browser:** [x] the watch page loads with the right title and a 1:44 player in a browser that is not signed in to the channel; playback itself was not watched end to end.

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
- [x] Repo public, commits verified (2026-10-12; viewed signed out in a browser: README, folders and the "Public" badge show. Final secret scan before the switch: no .env key value in 19 commits and 8 refs including 5 Entire checkpoint refs)
- [x] Evidence folder in repo (evidence/: metrics, reports, entire, cfo-ai)
- [x] Video link works (YouTube https://youtu.be/8an_y3CCGqg, public; checked loading signed out; an X upload is separate and not done by me)
- [ ] Quote post drafted with: team, name, project, public repo, demo link, official neatlogs post kept attached (drafts with placeholders are kept locally in submission-drafts.md, which is git-ignored; the team name, demo link and the neatlogs post link are missing; nothing is posted)
- [ ] Posted (time):
- Post URL:
- Note: opening the draft alone does not submit. Do not submit without the builder's explicit go-ahead.
