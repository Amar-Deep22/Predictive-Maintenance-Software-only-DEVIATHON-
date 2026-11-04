# Anuraksana — updated portal design guide

Updated: 29 October 2026. Documents the current source implementation, including automatic replay and simplified machine names. This is not a proposed redesign or a claim of completed visual testing.

## Theme and identity

A light industrial maintenance workspace with a warm off-white background, white rounded cards, charcoal pill buttons, coral emphasis and muted sage/olive supporting colours. The video reference influenced the pale workspace, compact icon rail and staged reveal animations; the result is not an exact reproduction.

Brand: **Anuraksana / ML Operations**. Context: **PREDICTIVE MAINTENANCE · NASA FD001**. Machines use simple display names such as **Machine 01** and **Machine 34**. Reference results and replay sessions are distinguished in selectors. Technical session IDs remain visible for tracing predictions.

## Implementation and theme layers

| File | Responsibility |
|---|---|
| `src/App.tsx` | Sidebar, header, navigation and page headings |
| `src/main.tsx` | Base stylesheet followed by reference-theme import |
| `src/styles.css` | Foundational layout, typography and legacy component rules |
| `src/reference-theme.css` | Active light-theme overrides, responsive layout and entrance motion |
| `src/predictive.css` | Maintenance components and automatic replay animation |
| `src/PredictiveMaintenance.tsx` | Active sections, controls, chart presentation and UI states |
| `src/MotorScene.tsx` | Procedural Three.js machine illustration |
| `src/autoReplay.ts` | Sequential automatic replay behaviour |
| `backend/telegram_alerts.py` | Telegram message formatting |

The older dark colours remain in base styles but are overridden for the current light interface. There is no implemented user-selectable light/dark theme. Some legacy CSS selectors belong to earlier controls that are not rendered by the current app.

## Colour palette

| Role | Colour |
|---|---|
| Workspace | `#f3f3f1` |
| White panel | `#ffffff` |
| Raised surface | `#f8f8f6` |
| Sidebar / header | `#fafaf8` |
| Divider token | `#e5e5e1` |
| Main text | `#262725` |
| Muted token | `#6c706c` |
| Primary button | `#252823` with white text |
| Active navigation | `#242622` with white icon |
| Circular brand icon | `#e76650` with white cube |
| Accent token | `#c34b38` (legacy variable name: `--cyan`) |
| Keyboard focus | `#c64e37` |
| Result card | `#f8faf4` |
| Result value | `#343e29` |
| Sensor chart line | `#df604b` |
| RUL chart line | `#333333` |
| Critical fleet card | Gradient `#f38b6d` to `#dd5e4f` |
| 3D viewport | `#101c28` |

### Priority badge colours

| Priority | Text / background | RUL rule |
|---|---|---|
| Critical | `#ac3f28` / `#fde7df` | 15 cycles or fewer |
| High | `#8e601b` / `#fff0d9` | More than 15, up to 30 |
| Medium | `#766718` / `#f3f0da` | More than 30, up to 60 |
| Low | `#4c7035` / `#eaf1e3` | More than 60 |

Badges include written labels. Missing predictions show Pending rather than an invented number. The urgency index is derived from RUL, not a failure probability.

## Typography

Font stack: `Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`. Inter is a preferred font; the inspected styles do not establish that it is bundled, so system fallbacks may render.

- Brand: 21 px, weight 750.
- Desktop page title: 34 px, weight 650, -1.3 px letter spacing.
- Section heading: 20 px, weight 650; subheading: 16 px.
- Maintenance explanatory text: 12 px, line height 1.8.
- Eyebrow: 9 px uppercase with wide letter spacing.
- Result values: 28 px, weight 600.
- Fleet KPI values: 43 px; critical KPI: 60 px.
- Tables: 12 px; headers: 9 px; supporting labels: 10 px.
- Fleet KPI numbers use tabular figures to reduce layout movement.

## Shell, spacing and surfaces

Desktop sidebar width is 82 px. Navigation is icon-only with accessible names, title tooltips and `aria-current` on the selected page. Icons use Lucide React: shield, CPU, cube, activity, bell, clipboard, gauge and play. The brand uses a cube inside a coral circle.

The 76 px header contains the brand, page breadcrumb, User guide link and FD001 MODEL label. Content is offset by the sidebar, has approximately 30/32 px outer padding and a maximum width of 1700 px.

Panels have white backgrounds, 18–19 px corners, thin neutral borders and subtle shadows. Maintenance panels use 25 px vertical / 28 px horizontal padding on wide screens. Main panel gaps are 22 px. Result cards have 14 px corners and a four-column desktop grid.

## Sections and page content

| Section | Current UI |
|---|---|
| FD001 Maintenance | Combined maintenance overview, controls, selected-machine details and model metrics |
| Machines | Fleet KPI cards, ranked table, top 4/top 5/all selector and selected-machine details |
| 3D Digital Twin | Machine selection, camera controls, cutaway, pause/resume motion, viewport and life-cycle cards |
| Sensor Trends | Sensor selection, sensor-history graph and predicted-life graph |
| Fault Alerts | Prioritised alert cards with explanation, inspection recommendation and actions linking to trends, 3D and work orders |
| Maintenance Reports | Saved orders with assignee, status, notes and Save action |
| Model Evaluation | MAE, RMSE, alert precision/recall cards, baseline, methodology text and CSV download |
| Sensor Replay | Default opening page; manual/automatic controls, activity animation, latest inference cards and trends |

The selected machine is shared across sections. Sections consume the same model results; they do not have independent prediction models.

## Buttons, forms and states

Primary buttons are charcoal pills with white text and approximately 22 px corners. Secondary buttons have pale surfaces and dark text. Hover changes the surface; disabled controls prevent conflicting actions during replay.

Inputs, selects and text areas use pale backgrounds, dark text, light green-grey borders and 9 px corners. Labels sit above inputs. Work-order forms have two desktop columns, with notes spanning both.

Keyboard focus uses a 2 px coral outline with 4 px offset. Errors use `role="alert"`; notices/progress use `role="status"`. Controls provide loading, disabled, pending, empty and error states. Connection errors expose a retry action. Work orders display Draft, Approved, In progress, Completed or Cancelled according to allowed transitions.

## Automatic replay animation

The status panel uses a 34 px circular activity indicator, status text, processed-cycle information and a 5 px activity track. Sage accents include `#64854f` and `#789460`, with translucent pale-green backgrounds.

States are Starting machine replay, Reading sensors and predicting, Finishing current batch, Replay complete, Replay stopped and Replay interrupted. Completion displays a checkmark and filled track; errors display an exclamation indicator.

The ring rotates every 1 second. A segment travels across the track every 1.8 seconds. This is an activity indicator, **not a percentage-complete measurement**. Completion fills the track with a 0.4-second transition.

Automatic replay supplies 30 recorded cycles per batch and waits 2 seconds after each completed result before requesting the next. Requests are sequential. It stops at the recording end or on an error. Stop does not undo an in-flight batch or an alert already submitted. The page must remain open. The animation does not fabricate readings or certify Telegram delivery.

## Other motion

- Shell reveal: approximately 0.65 seconds.
- Heading reveal: 0.7 seconds after a 0.12-second delay.
- Cards and panels: staggered fades, upward movement, slight scaling and blur removal.
- Buttons: 2 px hover lift and 0.97 pressed scale.
- Fleet cards: 4 px hover lift and soft shadow.
- KPI values: ease from zero over about 1 second after a 280 ms delay.
- Chart lines: 1100 ms ease-out animation.

Reduced-motion preferences disable the relevant entrance, replay and chart animations and KPI interpolation. This is not a guarantee that all 3D motion follows that setting; the viewport also exposes a Pause visual motion button.

## Charts

Recharts provides responsive line charts, axes and hover tooltips. The sensor graph is 240 px high, with a coral line, no point dots and a light grid. The RUL graph is 210 px high, with a dark line and no point dots.

Horizontal axes represent observed operating cycles. Sensor graphs identify the selected sensor and unit. RUL uses remaining operating cycles and begins after 30 readings. Trends can rise or fall; the UI must not imply a forced countdown.

## 3D illustration

Three.js, React Three Fiber and Drei render the procedural machine. The viewport is 460 px high with a dark technical background contrasting with the light workspace. View controls include Isometric, Front, Side and Top, plus cutaway and pause/resume visual motion. Loading and WebGL fallback presentation exist.

Casing colour follows model-derived maintenance priority. Grey indicates insufficient history. Shaft rotation is decorative, not measured RPM. The model is an illustrative motor/engine proxy rather than an exact NASA engine CAD model or a connected physical digital twin.

## Responsive layout and print

- Minimum page width: 360 px.
- At 1100 px or below: breadcrumb is hidden, fleet lead card spans the row, fleet KPI cards use three columns and padding reduces.
- At 700 px or below: sidebar is 58 px, header 65 px, heading 27 px; result cards use two columns and forms stack.
- Small-screen fleet cards use two columns, with the final KPI spanning the row.
- Labels and selects expand to full width on narrow screens.
- Tables keep an 850 px minimum content width inside a horizontally scrollable wrapper.
- Print styling hides the sidebar/header and removes the main-shell offset.

## Telegram presentation

Alerts use HTML formatting with escaped dynamic values. The alert title, machine name, priority, predicted remaining life, Random Forest model name, inspection focus and important action labels are bold. Session IDs are monospace. Blank lines separate identification, reasoning, action and context.

Recorded-data context, uncertain replacement advice, the HPC scenario assumption and the distinction between cycles and days remain visible. Previously sent messages keep their original format.

## Content and interpretation rules

- Call the data recorded NASA FD001 simulation readings, not live sensor measurements.
- Separate ML-based remaining life from rule-based priority and urgency scores.
- Keep cycles as the main unit; an hours/days conversion is not implemented.
- Explain HPC as an inspection recommendation from the dataset scenario, not learned multi-component diagnosis.
- Preserve session IDs and work-order history for tracing results.
- Do not imply the 3D illustration provides measured vibration, current or rotation speed.
- Keep error/pending states honest; animation alone does not establish successful inference or delivery.

## Verification scope

Prepared from the current React components and stylesheet source. It does not claim a fresh visual browser inspection, an exact video match, or a completed accessibility audit. Browser automation is currently blocked by the app's browser-use setting. Some older component styles remain in the repository and should not be mistaken for currently visible features.


## UI simplification update — 29 October 2026

This update supersedes the denser layouts described above:

- Display labels: Overview, Run a demo, Work orders and Model results; internal navigation keys remain unchanged.
- Desktop sidebar is now 205 px with visible text labels above 1100 px. Smaller screens retain the compact icon rail.
- Replay has one prominent automatic start action and a stop control. Manual controls and session identifiers are expandable.
- Three result cards show remaining life, priority and processed cycles. Detailed prediction timing and end-of-life explanations are expandable.
- Overview now focuses on fleet/priority information instead of exposing every section at once.
- Sensor charts are shown on Sensor Trends and Run a demo, avoiding duplication on other pages.
- Long alert explanations, inspection instructions and evaluation methodology are behind native details/summary controls.
- Short recorded-data, unit and component-diagnosis context remains visible near relevant results.
- Existing light palette, 3D illustration, replay animation, model, work orders and Telegram logic are retained.


## Navigation consolidation

The duplicate Overview entry has been removed. Machines is the single destination for fleet summaries, priority ranking and selected-machine information. Clicking the Anuraksana logo opens Machines. Run a demo remains the default opening page. This supersedes earlier references to a separate Overview page.


## Decision emphasis update

Remaining life is the dominant result card, with a priority-aware top border and a larger numerical value. Ranked rows emphasise machine names and remaining life. Inspection focus and next actions use a restrained coral callout; dataset assumptions stay alongside the recommendation. Table supporting text has stronger contrast. Highlighting is limited to decision-relevant content.


## Larger content typography

Body copy, form labels and expandable summaries now use 16 px. Table cells and buttons use 15 px; supporting table text uses 13 px. Section headings use 24 px (22 px on small screens), subheadings 20 px, and desktop navigation labels 14 px. This supersedes earlier smaller font sizes. Mobile input text uses 16 px; tables retain horizontal scrolling.


## Detailed aircraft digital twin

The 3D page uses the detailed Blender aircraft engine, exported as a local GLB with 12 component groups and five decorative rotors. Original metallic materials are preserved. The high-pressure compressor receives the selected machine’s ML priority highlight; this is the FD001 inspection assumption, not an independent component diagnosis. Remaining life remains the engine-level prediction. Camera presets, cutaway and pause controls are retained. Reduced-motion preferences stop rotation. Blender timeline alerts and studio labels are excluded.
