\# World Cup Prediction Bot (WCPB)



A cloud-native, high-fidelity Telegram bot built with Aiogram 3 designed to manage and automate community-based prediction tournaments for the FIFA World Cup. The system features dynamic background database synchronizations, advanced football scoring matrix calculations, and real-time live standing aggregations.



\## 🚀 Key Architectural Features



\* \*\*Asynchronous Execution Model:\*\* Driven by Aiogram 3 FSM (Finite State Machine) architectures ensuring fully non-blocking multi-user engagement loops.

\* \*\*Cloud-Native Persistent Storage:\*\* Fully integrated with an enterprise-tier PostgreSQL cloud database utilizing advanced upsert syntax operations (ON CONFLICT) to maximize transactional integrity.

\* \*\*Automated Cron Ingestion Engines:\*\* Equipped with an autonomous background orchestration scheduler tracking real-time livescores and group data intervals from the external Football Data API channels.

\* \*\*Advanced Mathematical Tie-Breaking Ledger:\*\* Compiles dynamic tournament standings calculated against aggregate user point tallies, filtering micro-wins (exact 10-point margins) over basic alphabet order parameters.



\---



\## 🏗️ Relational Schema Core



The database manages four structural layers inside the PostgreSQL cloud ecosystem:

\* \*\*Users Master Ledger:\*\* Maintains strict indexing on verified Telegram parameters alongside total points.

\* \*\*Matches Matrix:\*\* Monitors team object declarations, live completion states, and timestamps.

\* \*\*Predictions Matrix:\*\* Relates user states directly to upcoming matches with dynamic cascade rules.

\* \*\*Standings Table:\*\* Groups team stats to replicate accurate global groups layout.



\---



\## 📁 Repository Structure



\* src/bot.py : Main Application Gateway \& Bot Orchestrator

\* src/database.py : Relational Cloud Database Engine

\* src/fetch\_matches.py : Third-Party API Sync Engine

\* requirements.txt : Production dependency manifest

\* README.md : Architecture Documentation Overview



\---



\## 🛠️ Production Quick Start



\### Step 1: Environment Variable Configuration

To host and execute the system pipelines, deploy a standard .env configuration mapping the following credentials:

\* TELEGRAM\_BOT\_TOKEN=your\_telegram\_bot\_token\_here

\* FOOTBALL\_API\_KEY=your\_football\_data\_org\_api\_key\_here

\* DATABASE\_URL=postgres://user:password@host:port/dbname



\### Step 2: Local Environment Execution

Install the production dependency layer and spin up the bot pipeline manually by running:

\* pip install -r requirements.txt

\* python -m src.bot



\### Step 3: Cloud Deployment Blueprint (Render \& Cron Integration)

The system is fully optimized for continuous delivery within a Render Web Service framework:

\* \*\*Background Pooling:\*\* Auto-wakes and pools state queries every 15 minutes via custom external ping tools (UptimeRobot / Cron-Job) to bypass standard free-tier idling limits.

\* \*\*Runtime Orchestration:\*\* The main initialization pipeline forks an asynchronous polling daemon alongside the web instance task to execute autonomous API synchronization updates every 900 seconds.



\---

\*Developed as a high-fidelity system design solution handling real-time gamified tracking pipelines on scalable cloud structures.\*

