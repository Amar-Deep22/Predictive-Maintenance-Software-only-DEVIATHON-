# Demo verification — 30 October 2026 (India time)

- Comparison slide: public/assets/model-comparison.pptx; linked on Model results.
- Baseline is the constant training-target median, not a mean predictor. MAE 35.92 vs Random Forest 14.36 cycles (~60% lower).
- Global note identifies simulated NASA FD001 data, operating cycles, and scenario-based HPC recommendation.
- Live API replay: FD001:replay:034:023460fe; finished cycle 203, RUL 6.9446, Critical. All three Telegram sends accepted.
- Edge automatic replay: FD001:replay:034:a4e7ecbb; Replay complete shown, cycle 203, RUL 6.9, Critical. All three Critical deliveries recorded as sent.
- Browser-created work order WO-17C81467 saved with Demo QA team and inspection notes. Assignment and notes survived page reload and were independently verified in SQLite.
- Sensor histories and RUL plots present; evaluation metrics and slide download visible. Model GLB renders in Edge.
- Removed unused mesh compression decoder initialization that generated a CSP/WebAssembly console error; exported GLB is uncompressed.
- Telegram sent means API acceptance, not worker read receipts.
- Two demonstration sessions/orders intentionally retained. No physical maintenance performed. Server-process restart was not part of this check.

## Rotation verification
Two successive browser starts selected Machine 34 then Machine 81; Machine 76 was shown next.
- Machine 34: completed cycle 203, predicted RUL 6.9446, Critical; three Critical Telegram sends recorded as sent.
- Machine 81: completed cycle 213, predicted RUL 8.3343, Critical; three High and three Critical Telegram sends recorded as sent.
Both completion results were independently checked through the live API and SQLite delivery records. Telegram acceptance does not confirm that workers read the messages. Browser access became disabled again during the final verification; completion was confirmed using the API and database.
