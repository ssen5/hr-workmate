# HR Workmate

HR Workmate is an AI-powered HR helpdesk assistant built to help **employees and managers** get quick, accurate answers to HR-related queries — without having to dig through policy PDFs or ping the HR team for routine questions.

It combines:
- **RAG (Retrieval-Augmented Generation)** over your company's HR policy document, so policy questions are answered directly from the actual policy text — not guessed.
- **Native tool-calling** via Groq, so the assistant can look up live data (leave balance, leave requests, payroll) and perform real actions (applying for leave, approving/rejecting leave requests) instead of just talking.
- **A local SQLite database** to simulate real HR records — employees, leave requests, and payroll.
- **Confirmation gates** on any action that writes to the database, so nothing gets applied or approved without an explicit yes/no from the user.

---

## What it can do

- Answer HR policy questions (leave rules, code of conduct, benefits, etc.) by retrieving relevant sections from `policy.pdf`
- Look up an employee's leave balance, leave request history, or payroll/salary details
- Let an employee apply for leave (sick leave auto-approves instantly; casual/earned leave goes to their manager as pending)
- Let a manager approve or reject a pending leave request from someone reporting to them
- Hold a natural, multi-turn conversation — it remembers context within a session (e.g. it won't ask for your employee ID twice)

---

## Tech Stack

| Component | Tool |
|---|---|
| LLM | Groq (`openai/gpt-oss-120b`) via `langchain-groq` |
| Orchestration | LangChain (native tool-calling, `bind_tools`) |
| Policy retrieval | Chroma (vector store) + HuggingFace sentence-transformer embeddings |
| Structured data | SQLite |
| PDF parsing | `PyPDFLoader` |

---

## Project Structure

```
hr-workmate/
├── .env                     # holds GROQ_API_KEY
├── policy.pdf               # source HR policy document
├── ingest.py                # builds the Chroma vector index from policy.pdf
├── vectorstore.py           # shared Chroma load/config helper
├── tools.py                 # all tool definitions (policy lookup, DB queries, leave actions)
├── main.py                  # entry point — chat loop
├── database/
│   ├── init_db.py           # creates tables + seeds sample data (run once)
│   ├── update_db.py         # incremental DB changes (new tables, columns, rows)
│   └── mydb.db              # generated SQLite database
└── chroma_policy_db/        # generated vector index (from ingest.py)
```

---

## Setup & Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add your Groq API key

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

### 3. Set up the database

```bash
cd database
python init_db.py
cd ..
```

This creates `mydb.db` with sample employees, leave requests, and payroll records. Use `database/update_db.py` afterward for any incremental changes (new tables, columns, or rows) without wiping existing data.

### 4. Build the policy knowledge base

```bash
python ingest.py
```

This reads `policy.pdf`, splits it into chunks, embeds them, and stores them in a local Chroma vector index (`chroma_policy_db/`). Only needs to be re-run if `policy.pdf` changes.

### 5. Run the assistant

```bash
python main.py
```

You'll be asked to enter an employee ID at startup (simulating a logged-in session) — then you can start chatting.

---

## Example Interactions

```
Enter Employee ID: 1001

You: what's the notice period mentioned in the policy?
Bot: [answers directly from policy.pdf]

You: what's my leave balance?
Bot: [queries the database and answers in plain language]

You: apply for 2 days sick leave starting tomorrow, reason: fever
Bot: [confirms details, asks yes/no, then auto-approves and updates balance]

You: approve leave request 4
Bot: [checks you're the manager, confirms yes/no, then updates status]
```

---

## Notes

- This is a prototype/learning project — the SQL-generation tool (`query_database`) has basic safeguards against destructive queries but is not hardened for production use.
- Salary and leave figures in the seed data are illustrative placeholders.
- Manager-approval routing for pending leave requests currently requires the manager to know the `request_id` — a "list my pending approvals" view is a natural next step.
