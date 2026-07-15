# NyayaSetu — Evaluation Study Instrument

Two evaluation tracks: **(A) automated technical metrics** (already measured,
reproducible) and **(B) a human user-acceptance study** (this instrument, ready
to run with real participants).

---

## Track A — Automated technical metrics (measured)

Reproduce with `eval/` scripts; consolidated in `eval/results/SUMMARY.md`.
Covers: language detection, RAG retrieval, governance-text classification,
offline translation, and per-task latency/CPU/memory across profiles.

---

## Track B — Human user-acceptance study

Target cohort (per the paper): **25 citizens + 8 government officials.** This
instrument standardizes recruitment, tasks, and scoring so results are
comparable and defensible.

### B.1 Consent (read to each participant)

> "You are helping evaluate a prototype government-services assistant. Your
> participation is voluntary, you may stop anytime, and no personally
> identifying information is recorded. Your task performance and opinions will
> be used only in aggregate."

Record only: participant ID (anonymous), role (citizen/officer), preferred
language, age band, digital-literacy self-rating (1–5).

### B.2 Citizen tasks (each timed, success recorded)

| # | Task | Success criterion |
|---|------|-------------------|
| C1 | Find a scheme you may be eligible for by asking in your language | Relevant scheme surfaced |
| C2 | Ask the eligibility criteria of that scheme | Correct criteria read back |
| C3 | File a grievance by voice | Grievance saved with correct category |
| C4 | Track the grievance status | Status located unaided |
| C5 | Understand a published notice (narrated) | Participant paraphrases correctly |

### B.3 Officer tasks

| # | Task | Success criterion |
|---|------|-------------------|
| O1 | Triage the grievance inbox | Correct department/priority confirmed |
| O2 | Draft a notice with AI assistance | Usable draft in < 10 min |
| O3 | Resolve + close a grievance with SLA | Lifecycle completed correctly |

### B.4 Post-task questionnaire (5-point Likert; 1=strongly disagree)

1. The system understood what I said/asked.
2. The information was correct and useful.
3. It was easy to use without help.
4. It worked in my language.
5. I would use this for real government services.
6. (Officers) This reduced my manual effort.

### B.5 Metrics computed

- **Task success rate** (% per task, per cohort).
- **Time on task** (median seconds).
- **Assistance events** (times the participant needed help).
- **SUS-style acceptance** (mean of Likert items, per cohort).
- **Qualitative themes** (open feedback, coded).

### B.6 Data template

`eval/study/responses.csv` columns:
`participant_id, role, language, age_band, literacy, task_id, success,
time_s, assists, q1..q6, notes`

An empty template lives at `eval/study/responses_template.csv`. Field
recruitment of citizens/officials is carried out by the research team; the
instrument above makes those sessions structured and the results reproducible.
