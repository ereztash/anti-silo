# Anti-Silo

**Local pre-flight source audits for consultants and agencies building client RAG systems.**

Anti-Silo inspects a client source folder before ingestion. It identifies
provenance gaps, extraction failures, unsupported formats, duplicate content,
and sources that should not enter grounding under the configured policy. The
result is a deterministic `GO`, `CONDITIONAL GO`, or `STOP` decision, an
explainable Readiness Score, and a client-ready Audit Pack.

The Desktop app keeps all processing on the local machine. The optional hosted
Web Beta processes only the files selected by the user in a temporary Vercel
Function and does not retain them in Anti-Silo storage.

## Why Anti-Silo

A folder of documents is not automatically a RAG-ready corpus. Common problems
appear before chunking, embeddings, retrieval, or prompt design:

- important files cannot be extracted completely
- duplicate documents create conflicting or overweighted retrieval
- summaries are treated as primary sources
- claims have no traceable source anchor
- unsupported files silently remain outside the index
- the consultant and client have no shared record of what was accepted

Anti-Silo turns that ambiguous intake step into an auditable pre-flight gate.

## Who It Is For

The initial user and buyer is an AI consultant, RAG delivery lead, or small
agency that receives client documents before scoping or implementation.

Anti-Silo is useful when you need to:

- assess whether a client corpus is ready for ingestion
- scope cleanup work before committing to a delivery plan
- explain exclusions and remediation requirements to a client
- produce a repeatable handoff artifact for an implementation team
- keep sensitive source material local

## Consultant Workflow

1. Drag the client source folder onto the app (or pick it) — Preflight runs
   immediately and returns the verdict, corpus diagnostics, and prioritized
   remediation queue. No project setup is required for a first read.
2. Optionally name the client and engagement — these are only needed to title
   the report and to compare scans over time — then re-scan.
3. Repair, exclude, or replace problematic sources, then scan again.
4. Use the scan delta to show what changed.
5. Export `ANTI_SILO_PREFLIGHT_PACK.zip` for the client call, SOW, or ingestion handoff.

Project metadata and summary-only scan history are stored locally. Source file
contents are not copied into project history.

## The Console

The working screen is built around one rule: **the consultant must be able to
answer "can I build on this?" in under three seconds, and defend every point of
the score in front of a skeptical client.**

- **Verdict band, above the fold.** One verdict chip (`GO` / `CONDITIONAL GO` /
  `STOP`, always icon + word, never color alone), the Readiness Score with a
  threshold meter (default `GO ≥ 85`), and a single primary action for the
  current state. Everything else is progressive disclosure.
- **Custom GO threshold.** The GO band defaults to 85 but is configurable
  (`go_threshold` in the config, clamped to 60–100) — set a stricter bar for a
  regulated domain per scan on Desktop. The meter and labels follow the value on
  both surfaces, sourced from the same engine.
- **The score is a ledger, not a gauge.** "How was this computed" folds out
  under the score into plain arithmetic — files per evidence tier × points,
  averaged over the scope, minus the duplicate penalty, capped by STOP
  findings. The numbers come from the same engine components that the exported
  report prints, so the console and the client artifact always agree.
- **Scan delta.** After a re-scan, the band shows the readiness movement against
  the previous scan (score before → after, ready/review/blocked deltas) and a
  ghost marker for the previous score on the meter — the repair loop is
  measured, not narrated.
- **Trust boundary at the moment of misreading.** A single quiet line under the
  verdict ("checks source chain and extraction integrity — not factual
  correctness"), expandable, and repeated verbatim in the client report.
- **Triage tiles and tables.** Three tiles (passed / needs sources / do not
  rely) filter the file table; the remediation queue leads with the
  highest-impact actions; the risk register and effort range are SOW-ready.
  Every remediation and risk item carries a plain-language RAG-impact line —
  *why it matters* (retrieval bias, hallucination risk, data loss) — sourced
  once on the server so the Web and Desktop surfaces always show the same text.
- **What-If projection (Desktop).** Mark problem files as fixed and pick an
  action per file; the projected Readiness Score and verdict update live via a
  deterministic `/api/simulate` (no re-scan), recomputed by the same engine. The
  projection is realistic, not optimistic — "add a source" moves a file to
  *source-backed*, not straight to *ready* — so a projected GO stays honest.
- **Light + dark themes, RTL Hebrew UI, keyboard and screen-reader friendly**
  (visible focus states, `aria-live` scan status), served as a single
  self-contained document from `127.0.0.1` with no CDN and no network calls.

The design rationale, information architecture, and a standalone interactive
prototype of this screen live in [`docs/design/`](docs/design/UI_DESIGN.md).

## Preflight Verdicts

| Verdict | Meaning |
|---|---|
| `GO` | No source-policy or extraction blockers were found under the active policy. |
| `CONDITIONAL GO` | The corpus can proceed after named review, provenance, or cleanup actions. |
| `STOP` | At least one blocking source, provenance, contradiction, or extraction issue must be resolved before ingestion. |

The verdict is deterministic and policy-based. It is not a probabilistic
confidence score.

### Readiness Score Method

The `0-100` score is intentionally explainable:

- `triangulated` files contribute 100 points
- `source_backed` files contribute 75 points
- `indexed_unverified` files contribute 40 points
- synthesis files without a source spine contribute 30 points
- blocked or unsupported files contribute 0 points
- exact duplicates deduct 2 points each, up to 15 points
- any `STOP` finding caps the final score at 49

The weighted total is divided by all files in scope, including unsupported
files. The report exposes the components and methodology used for every score.
This is a corpus-readiness indicator, not a factual-quality score.

## What the Audit Pack Contains

Each completed Preflight can export:

| Artifact | Purpose |
|---|---|
| `ANTI_SILO_REPORT.html` | Client-readable verdict, scope impact, diagnostics, and remediation plan. |
| `PREFLIGHT_SUMMARY.json` | Machine-readable verdict and audit summary. |
| `REMEDIATION_QUEUE.csv` | Prioritized actions for blocked, review, and cleanup items. |
| `RISK_REGISTER.csv` | Formal risk IDs, categories, severity, and recommendations. |
| `SCAN_DELTA.json` | Previous-versus-current readiness and issue metrics. |
| `SOW_READY.md` | Copy-ready scope input with executive summary, material risks, and a planning range. |
| `CLIENT_SOURCE_MANIFEST.json` | Sanitized source inventory without the local source-root path. |
| `eligible_sources.csv` | Sources allowed into grounding under the active policy, when available. |
| `ANTI_SILO_PREFLIGHT_PACK.zip` | Portable bundle containing the client-facing artifacts. |

## What It Detects

- unsupported file formats
- empty files
- failed or partial extraction
- exact duplicate content using SHA-256
- missing source anchors
- synthesis documents without a source spine
- graph-only or weakly supported claims
- contradiction hard blocks
- changes in ready, review, blocked, and corpus-issue counts between scans
- readiness-score movement between scans

Anti-Silo can also generate strict grounding allowlists and source-spine repair
templates for structured knowledge vaults.

## Trust Boundary

Anti-Silo evaluates provenance, extraction completeness, and configured source
policy. It can determine whether a source is eligible for grounding under that
policy.

It does **not** prove:

- that a document is factually or professionally correct
- that a source semantically supports every claim made from it
- that a RAG system is legally compliant or production-ready
- that users adopted the product or received value from it
- that the product has validated market demand

**Grounding eligible is not the same as true, useful, adopted, or commercially
validated.**

## Install and Run

### Hosted Web Beta

The browser version is designed for small consultant pre-flight checks when a
local installation is inconvenient. It supports up to 150 selected files,
1.5 MB per file, and 2.8 MB of source content per scan.

[Open the hosted Web Beta](https://anti-silo.vercel.app/) ·
[Run the no-upload demo](https://anti-silo.vercel.app/?demo=1)

[Deploy Anti-Silo to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fereztash%2Fanti-silo)

The Web Beta:

- accepts `.md`, `.txt`, `.csv`, `.json`, `.html`, `.htm`, `.docx`, `.xlsx`, and `.pdf`
- offers a built-in demo corpus so the workflow can be evaluated without uploading files
- requires explicit cloud-processing consent before any user-selected file is sent
- runs the existing deterministic Preflight engine in a temporary Python Function
- returns the verdict, Readiness Score, a per-file classification breakdown (why each file landed in its tier), remediation queue, and Risk Register
- lets the consultant download a client-ready HTML report, raw JSON, and the Risk Register as CSV
- does not provide scan history, watch mode, source repair, or the complete Audit Pack yet

Run the complete hosted flow locally for development or UI review:

```bash
python scripts/serve_web_beta.py
```

The preview binds only to `127.0.0.1`, opens at `http://127.0.0.1:8766/`,
and serves both the browser assets and the real `/api/scan` implementation.
Open `http://127.0.0.1:8766/?demo=1` to run the no-upload demo immediately.

Vercel Functions limit request and response payloads to 4.5 MB. Anti-Silo uses
a lower 2.8 MB content limit to leave room for JSON and Base64 encoding. Use the
Desktop app for sensitive corpora, larger folders, repeat scans, and full client
exports.

### Windows App

For the packaged desktop build:

1. Open the [latest release](https://github.com/ereztash/anti-silo/releases/latest).
2. Download `Anti-Silo-Setup.exe` from **Assets**.
3. Install and open **Anti-Silo** from the Desktop shortcut or Start menu.

The packaged release may trail the current `main` branch. To run the latest
source version, use the developer setup below.

### Developer Setup

Anti-Silo requires Python 3.11 or newer.

```powershell
git clone https://github.com/ereztash/anti-silo.git
cd anti-silo
python -m pip install -e ".[dev]"
python -m anti_silo.cli gui
```

The local interface opens at [http://127.0.0.1:8765](http://127.0.0.1:8765).
Use a different port when needed:

```powershell
python -m anti_silo.cli gui --port 8777
python -m anti_silo.cli gui --no-browser
python -m anti_silo.cli gui --open-path path/to/client-folder
```

## Privacy and Local Storage

- The Desktop server binds to `127.0.0.1` by default.
- Desktop source documents are not sent to cloud APIs.
- State-changing GUI requests require a per-session local token.
- Client project summaries are stored under `%LOCALAPPDATA%\AntiSilo\projects.json` on Windows.
- Quick Scan uses temporary local staging that can be discarded from the UI.
- Client-facing exports omit the local source-root path.
- The hosted Web Beta sends selected files to a temporary Vercel Function,
  returns the report in the same request, and does not add persistence.

## Supported Intake Formats

The default intake policy includes:

```text
.md  .txt  .csv  .json  .html  .htm  .docx  .xlsx  .pdf
```

Text formats work with the standard installation. Extraction for `.docx`,
`.xlsx`, and `.pdf` uses optional local Python packages when available. A
missing, corrupt, or unreadable file degrades to a per-file `extraction_failed`
result and never aborts the rest of the scan; missing, failed, or truncated
extraction remains visible in the report and can create a hard block. The hosted
report explains the likely cause and a recommended action for each extraction
failure.

Intake does not let a file certify itself as an independent source. Ordinary
documents enter review as `indexed_unverified` until provenance is established.

## CLI

The same deterministic engine is available without the GUI:

```powershell
python -m anti_silo.cli ingest --vault path/to/source-folder --output-vault path/to/staging-vault
python -m anti_silo.cli index --vault path/to/vault
python -m anti_silo.cli triangulate --vault path/to/vault
python -m anti_silo.cli contradiction --vault path/to/vault
python -m anti_silo.cli queue --vault path/to/vault
python -m anti_silo.cli enforce --vault path/to/vault
python -m anti_silo.cli eligible --vault path/to/vault
python -m anti_silo.cli spine --vault path/to/vault
python -m anti_silo.cli pulse --vault path/to/vault
```

Use a custom policy or scan profile:

```powershell
python -m anti_silo.cli pulse --vault path/to/vault --config contracts/default_config.json
python -m anti_silo.cli pulse --vault path/to/vault --profile rag
python -m anti_silo.cli pulse --vault path/to/vault --profile research
python -m anti_silo.cli pulse --vault path/to/vault --lang he
```

## Trust Tiers

| Tier | Meaning |
|---|---|
| `triangulated` | Claim, source anchor, and corroboration are present. |
| `source_backed` | A source anchor exists, but corroboration is still required. |
| `indexed_unverified` | The file was staged locally but has no independent source verification. |
| `corroborated_no_source` | Corroboration exists, but the primary source is missing. |
| `ledger_supported` | An internal ledger references support, but the evidence is weak. |
| `graph_only` | The claim exists only as an internal assertion. |
| `refuted_or_blocked` | The claim is explicitly blocked, refuted, or over-claimed. |

By default, only `triangulated` sources are eligible for production grounding.
Review candidates remain separate from the production allowlist.

## Development

Run the complete test suite:

```powershell
python -m pytest -q
```

Build the Windows executable:

```powershell
python -m pip install -e ".[desktop]"
pyinstaller packaging/anti_silo_gui.spec
```

Additional documentation:

- [Consultant pilot plan](docs/CONSULTANT_PILOT.md)
- [Launch readiness gates](docs/LAUNCH_READINESS.md)
- [Distribution and signing](docs/DISTRIBUTION.md)
- [Desktop packaging](packaging/README.md)
- [UI/UX design spec](docs/design/UI_DESIGN.md) and the
  [interactive design prototype](docs/design/prototype.html) (open locally in a
  browser; runs on realistic sample data with a live scoring engine)

## Current Product Status

Version `0.5.0` is engineering-verified as a local Consultant Decision Pack. It
adds the Readiness Score, Risk Register, bilingual executive summary, cleanup
planning range, expanded Scan Delta, and SOW-ready export. Market demand is
still a field hypothesis. The next promotion gate is repeated use on real
client folders, client-facing use of the Audit Pack, and paid pilot evidence.
The repository also includes a hosted Web Beta for small, temporary pre-flight
checks; it does not replace the local privacy boundary or full Desktop workflow.

This repository contains the portable product layer only. Do not commit private
client folders, CRM exports, credentials, or sensitive source material.
