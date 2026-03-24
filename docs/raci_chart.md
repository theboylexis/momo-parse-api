# RACI Chart — MomoParse Project

**R** = Responsible (does the work)
**A** = Accountable (owns the outcome)
**C** = Consulted (provides input before)
**I** = Informed (notified after)

## Stakeholders

| ID | Role | Person/Entity |
|----|------|---------------|
| AM | Developer / Project Lead | Alex Marfo |
| FE | Fintech Engineer / Mentor | Alumni startup founder |
| CL | CS Lecturer / Academic Advisor | CS department lecturer |
| TU | Test Users | Friends providing real SMS data |
| TE | Telco Engineers | MTN/Telecel contacts (via LinkedIn) |

## Development Phase

| Task | AM | FE | CL | TU | TE |
|------|----|----|----|----|-----|
| SMS parser (MTN + Telecel) | R/A | I | I | — | C |
| ML categorization model | R/A | C | C | — | — |
| Financial scoring indexes | R/A | C | C | — | — |
| REST API design | R/A | C | I | — | — |
| Demo UI | R/A | I | I | I | — |
| Database layer (PostgreSQL) | R/A | I | — | — | — |
| Deployment (Railway) | R/A | — | — | — | — |
| Test suite | R/A | — | I | — | — |

## Research Phase

| Task | AM | FE | CL | TU | TE |
|------|----|----|----|----|-----|
| Competitor analysis | R/A | C | I | — | — |
| Telco infrastructure research | R/A | C | I | — | C |
| Financial methodology (indexes) | R/A | C | C | — | — |
| SMS template format research | R/A | I | — | — | C |
| Bank of Ghana regulatory review | R/A | C | I | — | — |
| Credit scoring literature review | R/A | — | C | — | — |
| Market sizing | R/A | C | I | — | — |

## Validation Phase

| Task | AM | FE | CL | TU | TE |
|------|----|----|----|----|-----|
| Real SMS testing | R/A | I | I | R | — |
| ML model benchmarking | R/A | — | C | — | — |
| Parser accuracy validation | R/A | — | — | C | C |
| API load testing | R/A | — | — | — | — |
| Demo walkthrough | R/A | C | C | I | — |

## Presentation / Deliverables

| Task | AM | FE | CL | TU | TE |
|------|----|----|----|----|-----|
| Project report writing | R/A | C | A | — | — |
| Beamer presentation | R/A | C | I | — | — |
| Live demo preparation | R/A | C | C | — | — |
| Final defense / presentation | R/A | I | A | — | — |

## Key Decisions Log

| Decision | Made By | Consulted | Date |
|----------|---------|-----------|------|
| Focus on infrastructure over end-user app | AM | FE | 2026-03-24 |
| Remove AirtelTigo support (focus on MTN + Telecel) | AM | — | 2026-03-17 |
| Use RandomForest for categorization | AM | — | 2026-02 |
| Formalize financial indexes (5 cited metrics) | AM | FE | 2026-03-24 |
| PostgreSQL + in-memory fallback architecture | AM | — | 2026-03-17 |
| Research telco internal scoring systems | AM | FE | 2026-03-24 |
| LinkedIn outreach to telco engineers | AM | FE | 2026-03-24 |
