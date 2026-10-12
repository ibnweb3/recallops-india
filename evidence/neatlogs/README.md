# neatlogs screenshots

Screenshots of three traces from the project's neatlogs workspace (taken 2026-10-12). The workspace is private and no share links were created; these images are the public evidence. Run numbers are in [`../metrics/`](../metrics).

| File | Workflow | Run | What it shows |
|---|---|---|---|
| `baseline-trace.jpg` | `recallops-baseline` | name-only baseline, 4.4 s | One workflow span; the output panel shows round 1: 56 correct holds, 5 missed, 87 wrong holds |
| `agent-trace.jpg` | `recallops-agent` | agent run after the added safety rule, 61 s | 44 steps: workflow, `process_alert` agent, `reconcile`, `act_place_holds`, `verify_by_readback`, `trace_downstream`, `draft_notices` tools, and the model calls (`nova-lite` for name checks, `claude-haiku` for drafts) |
| `recovery-trace.jpg` | `recallops-agent` | recovery run, 58 s (3 holds timed out after writing) | Same span structure; the three timed-out holds were read back, not repeated (0 duplicate hold events, see `../reports/`) |

Cost in dollars is not shown here: the trace views I opened showed tokens and time only.
