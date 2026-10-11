# cfo.ai plan: RecallOps India (hypothesis-based unit economics)

Built 2026-10-12 in a free cfo.ai workspace by asking Ari (cfo.ai's assistant) for a 12-month model. The workspace is private; sharing has not been enabled, so these files are the evidence a reader can open.

**Everything financial below is a HYPOTHESIS.** The only measured inputs are the model usage and test results from our own runs on synthetic fixtures (see `../metrics/` and the neatlogs traces in `hackathon.md`). The prices, customer counts, review time and costs are placeholders chosen by the builder and not validated with any customer.

## Inputs
| Input | Value | Type |
|---|---|---|
| Tokens per agent run (two alerts, 339 stock rows) | 5,326 prompt + 3,413 completion = 8,739 | MEASURED (synthetic data) |
| Model calls / time per run | 31 calls, about 60 s | MEASURED |
| Uncertain rows sent to human review per run | about 11 | MEASURED (synthetic data) |
| Blended model price | USD 1.00 per million tokens | HYPOTHESIS (placeholder, not the gateway's real price) |
| Subscription | USD 150 per distributor per month | HYPOTHESIS |
| Runs per distributor-month | 4 (main), 1 (second scenario) | HYPOTHESIS |
| Review time / reviewer cost | 3 min per row, USD 8 per hour | HYPOTHESIS |
| Hosting and tooling | USD 60 per month | HYPOTHESIS |
| Starting cash | USD 10,000 | HYPOTHESIS |
| Paying distributors, Nov 2026 to Oct 2027 | 1, 2, 3, 4, 4, 5, 7, 9, 12, 15, 17, 20 (99 distributor-months) | HYPOTHESIS |

Excluded, not zero: founder pay, sales, legal/compliance, taxes.

## Results as reported by Ari (checked by hand, see below)
| | 4 runs (main) | 1 run |
|---|---|---|
| Direct cost per run | about USD 4.41 (model 0.008739 + human review about 4.40) | same |
| Direct cost per distributor-month | USD 17.63 | USD 4.41 |
| Gross margin before hosting | 88.24% | 97.06% |
| 12-month revenue | USD 14,850 | USD 14,850 |
| 12-month included costs | USD 2,465.86 | USD 1,156.47 |
| Closing cash | USD 22,384.14 | USD 23,693.53 |

- Human review is about 99.8% of direct run cost under these hypotheses, so the main economic risk is review workload and willingness to pay, not token prices. Model price from 0.5x to 10x moves gross margin only from 88.26% to 88.03%.
- Price sensitivity at 4 runs: USD 50 gives 64.73% gross margin and USD 12,484 closing cash; USD 400 gives 95.59% and USD 47,134.
- Cash never reaches zero in either case, so burn-based runway is shown as N/A (not infinite runway).

## Hand check (arithmetic only)
99 distributor-months x USD 150 = USD 14,850. 99 x USD 17.63 + 12 x USD 60 = USD 2,465.9. USD 10,000 + 14,850 - 2,466 = USD 22,384. One-run: 99 x 4.41 + 720 = USD 1,156.5, closing USD 23,693.5. These match Ari's figures; the inputs are still unvalidated.

## Files
- `economics-cash-forecast.jpg`, `economics-page-top.jpg`: Ari's Economics & runway page (cash curve for the 4-run case, assumptions text).
