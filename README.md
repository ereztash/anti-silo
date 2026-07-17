# Anti-Silo

**Local pre-flight source audits for consultants and agencies building client RAG systems.**

Anti-Silo inspects a client source folder before ingestion. It identifies
provenance gaps, extraction failures, unsupported formats, duplicate content,
and sources that should not enter grounding under the configured policy. The
result is a deterministic `GO`, `CONDITIONAL GO`, or `STOP` decision plus a
client-ready Audit Pack.

All processing stays on the local machine. No source documents are uploaded.

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

1. Create a local project with a client alias, engagement name, and consultant name.
2. Select the client source folder.
3. Run Preflight and review the verdict, corpus diagnostics, and prioritized remediation queue.
4. Repair, exclude, or replace problematic sources, then scan again.
5. Use the scan delta to show what changed.
6. Export `ANTI_SILO_PREFLIGHT_PACK.zip` for the client call, SOW, or ingestion handoff.

Project metadata and summary-only scan history are stored locally. Source file
contents are not copied into project history.

## Preflight Verdicts

| Verdict | Meaning |
|---|---|
| `GO` | No source-policy or extraction blockers were found under the active policy. |
| `CONDITIONAL GO` | The corpus can proceed after named review, provenance, or cleanup actions. |
| `STOP` | At least one blocking source, provenance, contradiction, or extraction issue must be resolved before ingestion. |

The verdict is deterministic and policy-based. It is not a probabilistic
confidence score.

## What the Audit Pack Contains

Each completed Preflight can export:

| Artifact | Purpose |
|---|---|
| `ANTI_SILO_REPORT.html` | Client-readable verdict, scope impact, diagnostics, and remediation plan. |
| `PREFLIGHT_SUMMARY.json` | Machine-readable verdict and audit summary. |
| `REMEDIATION_QUEUE.csv` | Prioritized actions for blocked, review, and cleanup items. |
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

- The server binds to `127.0.0.1` by default.
- Source documents are not sent to cloud APIs.
- State-changing GUI requests require a per-session local token.
- Client project summaries are stored under `%LOCALAPPDATA%\AntiSilo\projects.json` on Windows.
- Quick Scan uses temporary local staging that can be discarded from the UI.
- Client-facing exports omit the local source-root path.

## Supported Intake Formats

The default intake policy includes:

```text
.md  .txt  .csv  .json  .html  .htm  .docx  .xlsx  .pdf
```

Text formats work with the standard installation. Extraction for `.docx`,
`.xlsx`, and `.pdf` uses optional local Python packages when available. Missing,
failed, or truncated extraction remains visible in the report and can create a
hard block.

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
- [Distribution and signing](docs/DISTRIBUTION.md)
- [Desktop packaging](packaging/README.md)

## Current Product Status

Version `0.4.0` is engineering-verified as a local Consultant Preflight
workflow. Market demand is still a field hypothesis. The next promotion gate is
repeated use on real client folders, client-facing use of the Audit Pack, and
paid pilot evidence.

This repository contains the portable product layer only. Do not commit private
client folders, CRM exports, credentials, or sensitive source material.
