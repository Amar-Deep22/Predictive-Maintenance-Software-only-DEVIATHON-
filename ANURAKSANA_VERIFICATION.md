# Anuraksana feature verification — 30 October 2026

Implemented: portal title/header, accessibility label, alert heading, comparison slide and guide renamed to Anuraksana. Existing internal request-header/storage keys are retained for compatibility; the Telegram bot account username is unchanged.

3D inspection: selectable component geometry and keyboard-accessible dropdown for all 12 exported components; related sensor history and guidance; explicit lack of dedicated bearing/gearbox signals; no component diagnosis/lifetime claims.

Telegram workflow: new alerts create linked drafts and include acknowledgement/start buttons. Configured private-chat workers only; start requires Approved status, assigns the first available worker and records In progress. Duplicate callbacks do not duplicate responses. Closed orders remain closed. Response times and worker IDs are exposed in Work orders. Polling skips unsaved edits and writes include conflict detection.

Checks: 34 frontend tests and 8 backend tests passed, including model artifact evaluation, persistence, alert escaping and worker lifecycle/authorization. Database backup: backend/data/portal-before-worker-responses.sqlite3.

Remaining live verification: running backend is still the old process. Restart is required to enable the new listener and response API. Browser use is currently disabled. No live worker acknowledgement has been claimed or simulated on real worker accounts. Old Telegram messages do not acquire new buttons; start a new replay after restarting.
