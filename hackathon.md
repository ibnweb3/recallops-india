# hackathon.md: RecallOps India (neatHack 2026)

Rules for this file (from the neatlogs hackathon skill): never delete old entries, record only tests that actually ran, keep planned and completed work separate, never fabricate results, no secrets / .env / private traces / tokens / personal data. Link only sanitized, shareable evidence.

## 1. Project summary
- **Name:** RecallOps India (working name)
- **One line:** An agent that takes an official Indian drug-quality alert (CDSCO "Not of Standard Quality" batches), reconciles it against a distributor's messy stock and invoice records, places verified digital holds, traces where held batches went, and proves what it did.
- **Track:** Build an agent that works (the only track)
- **Problem it solves:** CDSCO publishes a monthly list of drug batches that failed quality tests, and stockists, distributors and retailers are expected to find and withdraw those exact batches. The alert is a PDF table (product, batch, manufacturing and expiry month, manufacturer, failed test); the stock is in someone's billing software. Matching them is slow and error-prone: brand versus generic names, strengths inside names, odd batch formats, month-only dates. A failure is specific to a tested batch, so wrongly holding other batches costs money and missing a listed batch is a safety risk.
- **Public repo:** <url, not created yet>
- **Demo video (3 min max):** <url, filled in on Oct 12>

## 2. Team
- Solo: <name / handle you choose to publish>
- Registered on Luma as team: <team name>
- Web check-in done: [ ] (date/time: )

## 3. Stack (what is ACTUALLY used; update as it changes)
| Part | Choice | Status (planned / in use / dropped) |
|---|---|---|
| Language / runtime | Python 3.13 (neatlogs needs < 3.14) | in use |
| LLM provider / model | thin client behind env vars (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL); hackathon LiteLLM key ($20 budget) or own key | planned |
| Alert parsing | pdfplumber on the CDSCO monthly NSQ PDFs | planned |
| Inventory environment | CSV fixtures + local SQLite stock service with real state transitions | planned |
| neatlogs SDK + project | workflowName: recallops-baseline / recallops-agent | planned |
| neatlogs MCP / REST (reading cost and KPIs) | | planned |
| Entire CLI | 0.11.4, `entire enable --agent claude-code` | in use |
| entire-graph plugin | | planned |
| cfo.ai (plan / CSV) | | planned |
| Other | | planned |

## 4. How each required tool is used (this feeds the 25% score and the video)
| Tool | Role in building / running / planning | Evidence link or file | Done |
|---|---|---|---|
| neatlogs | traces for the baseline and the agent under separate workflow names; before/after cost, tokens, errors; cost alerts | | [ ] |
| Entire (checkpoints) | every build session checkpointed; no secrets in transcripts | | [ ] |
| Entire (entire-graph) | | | [ ] |
| cfo.ai | unit economics: price per resolved alert vs model cost per alert | | [ ] |

## 5. Evidence checklist (judges verify these)
- [ ] Agent improved: before trace link + after trace link + the numbers compared
  - Before (workflowName / trace ids):
  - After (workflowName / trace ids):
  - Metrics (correct holds, wrong holds, missed holds, unresolved, tokens, cost USD, duration):
- [ ] neatlogs used: trace links or screenshots
- [ ] Entire used: `entire checkpoint list` output / one `explain`
- [ ] cfo.ai used: business plan covering pricing, costs, revenue, runway (Page link + screenshots)
- [ ] Recovery run: an action failed and the agent did X next (trace link)
- [ ] Built in public: links to posts tagged #neatHack
- [ ] Code written during the hackathon: public repo, commits dated Oct 10 to Oct 12
- [ ] No secrets in the repo or in Entire transcripts (checked on: )

## 6. Plan vs completed (keep both lists honest)
### Planned (not done yet)
- [ ] Confirm the alert format across more months. Only March 2025 is parsed so far. CDSCO now publishes newer alerts through an online portal (cdscoonline.gov.in) with year/month/source filters instead of PDFs; its table has not been read yet
- [ ] Fixture generator: stock, invoices and downstream sales built from real batches in the real alerts (labelled synthetic)
- [ ] Naive baseline: name-only matching ("before")
- [ ] Agent loop: rules, matching, investigation of ambiguous rows, holds, read-back
- [ ] Downstream trace and drafted supplier/customer notices
- [ ] Reconciliation and evidence packet
- [ ] Expansion event (a second alert or state order) that reopens earlier decisions
- [ ] Failure injection: a hold that times out after a successful write; the agent reconciles instead of repeating it
- [ ] Evaluation: correct / wrong / missed / unresolved per run, several runs each
- [ ] cfo.ai plan from the measured numbers
- [ ] Demo video + README + submission post

### Completed (move items here only when they work, with the date)
- 2026-10-10: CDSCO NSQ alert parser (recallops/alerts.py) parses the real March 2025 alert into 70 entries (S.No 1-70), joining entries split across page breaks and handling one DD/MM/YYYY date; 6 tests pass.
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
- No customer interviews and no willingness-to-pay evidence; the business plan is a hypothesis.
- Alert PDFs may change layout between months; only one month has been checked so far.

## 10. Submission status
- Window: Oct 12, 7:00-11:55 PM IST (planned close; final cutoff is announced on Discord)
- [ ] Repo public, commits verified
- [ ] Evidence folder in repo
- [ ] Video link works
- [ ] Quote post drafted with: team, name, project, public repo, demo link, official neatlogs post kept attached
- [ ] Posted (time):
- Post URL:
- Note: opening the draft alone does not submit. Do not submit without the builder's explicit go-ahead.
