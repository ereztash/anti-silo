# Anti-Silo — UI/UX design spec & working prototype

**Prototype:** [`prototype.html`](prototype.html) — one self-contained file (inline CSS/JS, no CDN,
no external fonts, no network calls). Open it directly in any browser; it honors the same
constraint as the shipped GUI (single HTML document served from 127.0.0.1, fully offline).

**The demo loop (2 clicks):** the console opens on scan #1 — **STOP · Readiness 40** (a pricing
contradiction + 9 unreadable files). Press **"Stage all recommended"** in the remediation queue,
then **Re-scan** (`r`). The simulated scan applies the staged fixes and recomputes:
**CONDITIONAL GO · Readiness 78**, with the delta panel showing 40 → 78, hard blocks 10 → 0, and
repaired / replaced / excluded counted separately. The scoring engine in the prototype is real and
deterministic — tier weights, −2/duplicate (cap 15), STOP cap at 49, verdict policy — and every
displayed number (score, impact previews, projections, delta, client report) is computed live by
it. Nothing is hardcoded.

---

## 1 · Design thesis

The single highest-leverage decision: **the score is rendered as an auditable ledger, not a
gauge — and every other number in the product (queue impacts, projections, the delta, the client
report) is computed live by that same ledger.** Confidence in this product doesn't come from
polish; it comes from the consultant being able to answer "why 78 and not 80?" in front of a
skeptical client without breaking eye contact. So "How this number was computed" sits directly
under the hero score and folds out into plain arithmetic (files × tier ÷ scope − duplicates, cap),
each remediation item shows its engine-computed "+8 pts" before you commit, and the client report
prints the identical table. One engine, three surfaces — defensibility as architecture, not as
copywriting.

## 2 · Information architecture

### Console (surface 1)

Projects (first-run empty state) → Setup (alias / engagement / consultant / folder — metadata
only) → Scan (aria-live progress) → **Results**, one screen with a fixed hierarchy:

- **Verdict band** (above the fold, 3 cells):
  1. Verdict chip (icon + word — never color alone) + one-sentence headline + the trust-boundary
     line.
  2. Hero score + meter (fill = verdict status color, ghost tick = previous scan, labeled
     GO ≥ 85 threshold) + the fold-out score ledger.
  3. Delta tile + **the single primary CTA**, state-driven: STOP → "Review the remediation
     queue"; changes staged → "Re-scan — N staged"; clean → "Export Audit Pack". Never a second
     primary button on screen.
- **Remediation queue** — stop-clearers first, then by computed impact. Each item: severity,
  plain-language why, file chips, impact ("+9 pts" / "clears a stop condition"), effort estimate,
  stage/skip actions. "Stage all recommended" for the 2-minute pre-call triage.
- **Files & diagnostics** — four stat tiles (scope, hard blocks, duplicates, unverified — with
  before→after deltas), filter chips, full table: tier, points, finding, SHA-256 (duplicates show
  the matching hash).
- **Risk register** — the client's questions with the consultant's answers pre-written; statuses
  (Open / Mitigated / Closed) computed from file state, so remediation visibly closes risks.
- **Audit pack** — all 9 artifacts; JSON/CSV/MD artifacts generate from live state.

### Client report (surface 2)

A fixed-light, print-first document (in the prototype: "Preview client report"): masthead →
verdict box (score + verdict + one sentence) → bilingual EN/HE executive summary → before/after
KPI row that **separately counts repaired vs replaced vs excluded** → the same score ledger →
risk register → a framed trust-boundary paragraph → "generated locally, no files left the
machine" footer. Same tokens and typography as the console; calmer density.

## 3 · Make-or-break microcopy (as shipped in the prototype)

- **Verdict headlines**
  - STOP: *"STOP — Not ready to ingest. Two stop conditions are active: a pricing contradiction
    and 9 unreadable files (31% of scope). Clearing the queue below projects readiness at 78."*
    (the 78 is computed, so it's a promise the re-scan keeps)
  - CONDITIONAL GO: *"Build on 17 of 18 files. No hard blocks remain. 1 file is still
    unverified — ingest flagged, or anchor first (scoped in the SOW)."*
  - GO: *"All files in scope are eligible to ingest."*
- **Score explanation:** *"Deterministic — the same corpus always produces the same score. No
  model, no judgment: each file earns its evidence tier, averaged across every file in scope;
  exact duplicates cost 2 points each (max −15); any stop finding caps the total at 49."*
- **Trust boundary** (one quiet line under the verdict, expandable, and verbatim in the client
  report): *"Covers provenance & extraction integrity — not factual accuracy."* Expanded: *"GO
  means every file is eligible to ingest: readable in full, traceable, and free of hard
  conflicts. Anti-Silo does not judge whether the content is true — that stays your client's
  accountability."*
- **First-run:** *"Audit the client's folder before you build on it. Select the folder exactly as
  you received it — Anti-Silo reads it in place, on this machine only; nothing is uploaded,
  copied, or modified. About a minute later you have a defensible verdict, a scored cleanup list,
  and a client-ready audit pack."*

## 4 · Accessibility & theming

Full keyboard operation (`1–4` sections, `r` re-scan, `e` export, `t` theme, `?` help, `Esc`
close), visible focus states, `aria-live` announcements for scan progress and verdict changes,
status colors always paired with icon + label (never color alone), light + dark themes (follows
OS, toggleable), `prefers-reduced-motion` respected. Copy is structured for a clean RTL/Hebrew
swap (logical CSS properties, dictionary-style strings); the executive summary is bilingual.

## 5 · Pushback on the scoring spec

Averaging across files-in-scope means **excluding files can raise the score without any repair
happening** — and the inverse bites too: in the demo, resolving the critical pricing contradiction
(excluding a 75-point file) moves the score **−1** while clearing a stop condition. The top
priority action can lower the number; meanwhile an exclusion-heavy "GO 92" is exactly what a
skeptical client's technical advisor will spot, and it would cost the product its whole reason to
exist (defensibility). The prototype keeps the spec'd formula but hedges it in three places:
exclusions are never silent (files-in-scope 29 → 18 is printed on the verdict band, delta, and
report), the delta separates *repaired / replaced / excluded* instead of claiming "fixed," and the
manifest lists every exclusion file-by-file. Recommended for v2: report **two numbers** — corpus
quality (the current average) and **coverage** (share of the original corpus that made it in) — so
an exclusion-heavy "GO" visibly bleeds coverage and can't masquerade as cleanup.

---

*All sample data in the prototype is fictional (Northwind Freight Ltd).*
