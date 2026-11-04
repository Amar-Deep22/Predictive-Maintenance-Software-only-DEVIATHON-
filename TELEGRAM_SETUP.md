# Telegram worker setup

1. Open the official verified @BotFather account in Telegram. Send /newbot and follow its prompts to choose a name and bot username. Keep the resulting token private.
2. Share the bot username with all three workers. Each worker opens it and presses Start (or sends /start).
3. In a terminal in this project directory run: C:\Python313\python.exe backend\telegram_setup.py
4. Paste the token only into that local hidden prompt. The helper lists private chats that contacted your bot. Match each worker carefully and enter their three distinct chat IDs. If missing, ask them to send /start again and rerun. Use a dedicated bot without an existing webhook or another getUpdates consumer.
5. Type YES locally to enable alerts. Restart python run.py.
6. Run Sensor Replay. Alerts are evaluated after each submitted reading or replay batch. When the latest RUL is <=30, all three workers receive a demo message. High and Critical are separate bands: each worker receives at most one successful notification per session per band. A new replay is a new session. Failed sends retry on a subsequent qualifying replay request. There is no automatic retry timer or guaranteed delivery.

Messages identify engine/session, cycle, RUL, urgency, HPC inspection focus and action. They explicitly say replacement is not established. No real factory location is known. Only new replay requests trigger sends; existing reference engines do not automatically broadcast.

Temperature-rise and general anomaly alerts are NOT implemented: the active model estimates RUL, and FD001 temperatures cannot be treated as generic motor temperature thresholds. Live motor temperature alerts require actual hardware data and equipment-specific limits.

Secrets are stored in backend/telegram.local.json (gitignored). Never share this file. Set enabled to false to disable sending. Database telegram_delivery records sent/failed per recipient and band. Delivery is best-effort; a crash after Telegram accepts a message but before local recording can cause a duplicate.

Current verification: syntax and offline message test only. Bot creation, registration and delivery must be completed with the user's Telegram account. No credentials have been configured and no Telegram messages have been sent.
