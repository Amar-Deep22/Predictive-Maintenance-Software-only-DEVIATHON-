# Easy demo guide

## Where ML works
You click Start engine and run model. The backend reads the first 30 cycles from NASA FD001, calculates latest value, mean, variation and slope for each retained sensor, and sends those features to a trained Random Forest with 250 trees. Its output is remaining useful life (RUL), in operating cycles. Feed next readings advances by 1, 10 or 30 cycles and repeats inference. The model is not retrained by a click. Priority rules translate the prediction into a maintenance action.

## Every section
| Section | What you do | What ML does |
|---|---|---|
| Sensor Replay | Choose an engine and press the run buttons | Computes fresh RUL predictions from recorded sensor windows |
| FD001 Maintenance | See the combined dashboard | Displays predictions, ranking, trends, metrics and work orders |
| Machines | Show 4/5 engines; inspect one | Ranks engines by model-derived urgency; reference rows use saved test predictions |
| 3D Digital Twin | Orbit, change camera, cutaway, pause visual motion | Uses predicted priority for casing colour; movement is decorative, not predicted physics |
| Sensor Trends | Choose a sensor and review its history | Sensor curve is raw recorded data; RUL curve is model output |
| Fault Alerts | See why an engine needs attention and inspect evidence | Flags predicted RUL <=30 cycles and explains its priority band |
| Maintenance Reports | Assign, approve and track a draft work order | Stores a snapshot of the prediction; saving/status changes are ordinary database operations |
| Model Evaluation | Read metrics and download CSV | Compares model predictions against known test answers |

## Five-minute demo
1. Sensor Replay: choose engine 34. Click Start engine and run model. At cycle 30 the expected RUL is about 155.4.
2. Choose 10 cycles per click and Feed next readings and predict. At cycle 40 expected RUL is about 149.3. Explain that the input window is now cycles 11-40.
3. Open Sensor Trends and show the changing sensor readings and RUL curve.
4. View result in 3D. Explain the same model result controls status colour. Camera/cutaway are presentation controls.
5. Machines: inspect reference Engine 034. Its saved final observed point is cycle 203 with RUL about 6.9. This is a different point in the same engine history, not a conflicting prediction.
6. Fault Alerts: show urgent review, HPC inspection focus and replacement-not-established explanation.
7. Draft a work order; in Maintenance Reports add an assignee and notes, save, then reload to show persistence.
8. Model Evaluation: MAE 14.36 means average absolute error of 14.36 cycles; RMSE 19.52 penalizes large errors. Precision about 95.5% and recall 84% apply to the 30-cycle alert definition, not overall model accuracy.

## Honest claims
This is recorded-data replay, not live sensors. Risk index is not failure probability. Cycles are not hours/days. HPC is the known FD001 degradation scenario, not learned component diagnosis. The model cannot confirm that an engine or bearing needs replacement. RUL need not decrease monotonically. Engine 1 has only 31 recorded test cycles, so engine 34 is better for a longer demo.

## Before presenting
Keep python run.py running. Open one portal tab to reduce graphics pressure. Verify the 3D canvas renders on your presentation browser; an unavailable WebGL message is a rendering limitation, not a model failure. Local browser automation must be enabled to finish the remaining agent-driven checks.
