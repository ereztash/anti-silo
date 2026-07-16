# Anti-Silo

Anti-Silo is a portable trust engine for local knowledge graphs.

## Start Here: Windows App

Most people should **not** run Anti-Silo from the repository or install Python.

1. Open the [latest Windows download](https://github.com/ereztash/anti-silo/releases/latest).
2. Download `Anti-Silo-Windows.zip` from **Assets**.
3. Extract the ZIP anywhere convenient.
4. Double-click `Anti-Silo.exe`.

The app opens in the browser automatically and starts with a choice to scan the
Desktop, choose another folder, or open the Brain. Nothing is uploaded.

If Windows shows a protection prompt for an unsigned new app, choose **More
info** and then **Run anyway** only after verifying that the download came from
the official `ereztash/anti-silo` release page.

It scans a folder, classifies truth surfaces, evaluates graph claims, runs a triangulation gate, and produces an evidence-upgrade queue. The goal is to prevent a knowledge system from promoting claims just because they are internally consistent.

## Trust Boundary

Anti-Silo is a trust and provenance layer, not a usage-validation layer.

It can say:

- this source is eligible for AI/RAG grounding under the configured policy
- this claim requires review
- this claim must be blocked
- this file needs source or corroboration repair

It does not say:

- the source was used by real users
- the claim created user value
- the claim has product-market fit
- the claim is semantically true in the world
- the business outcome was validated

In short: **grounding eligible is not the same as used, useful, adopted, or commercially validated.**

## What It Does

- Finds claim files and source/truth-surface files.
- Classifies surfaces such as CRM anchors, outcomes, preregistration notes, ledgers, external material, and governance contracts.
- Assigns every claim a promotion and triangulation status.
- Applies a deterministic contradiction-penalty layer when evidence layers conflict.
- Produces machine-readable JSON/CSV and human-readable Markdown reports.
- Produces a strict `eligible_sources` allowlist for AI/RAG grounding.
- Produces source-spine repair templates for synthesis claims.
- Stages ordinary source folders into an Anti-Silo review vault with stable raw-source hashes.
- Runs fully locally.

## What It Does Not Do

- Does not measure product usage or adoption.
- Does not infer user value or commercial validation.
- Does not use NLP, embeddings, or semantic similarity as the core trust decision.
- Does not promote claims because they are internally coherent.
- Does not turn review candidates into production grounding sources.

## Customer Journey

Anti-Silo is designed for teams that already have valuable knowledge spread across local files, docs, notes, CRM exports, research folders, or RAG source folders, but do not yet have a reliable way to decide which material is allowed to count as evidence.

1. **Inventory**  
   The team points Anti-Silo at a local vault or repository. Anti-Silo scans files and identifies claims, truth surfaces, source anchors, ledgers, outcomes, and governance contracts.

2. **Trust Mapping**  
   The system builds a local truth-surface index and assigns each claim a trust tier such as `triangulated`, `source_backed`, or `graph_only`.

3. **Enforcement**  
   Unsupported claims are blocked by the promotion gate. The system exits with a non-zero code when blocked claims exist, so it can be wired into local scripts, CI, release checks, RAG ingestion, or audit workflows.

4. **Repair**  
   Anti-Silo generates an evidence-upgrade queue that tells the team what kind of evidence is missing: source anchor, corroboration, ledger validation, or repair/retirement.

5. **Grounding Allowlist**  
   AI/RAG systems consume `eligible_sources.json`, not the whole folder. By default, only `triangulated` sources are allowed into grounding.
   Grounding eligibility means the source passed the configured provenance policy; it does not mean the source has real-world usage or user-value validation.

6. **Source-Spine Repair**  
   For research synthesis or integrated-model documents, Anti-Silo writes `SOURCE_SPINE_TODO.md` with the exact metadata block needed to connect the synthesis back to source hashes.

7. **Audit Snapshot**  
   A Git-managed vault can commit each trust snapshot, creating a chronological audit trail of what was trusted, blocked, or repaired over time.

8. **Operational Use**  
   The outputs can be used by humans, scripts, or AI/RAG systems to decide which sources are eligible for grounding and which claims must remain out of production.

## Who Pays and Who Uses It

Anti-Silo separates the economic buyer from the daily user.

| Role | Who It Usually Is | What They Need |
|---|---|---|
| Economic buyer | CTO, CISO, Head of AI, Compliance lead, Knowledge Ops lead | Reduce risk from unsupported AI outputs, audit failures, and uncontrolled knowledge sprawl |
| Technical buyer | AI platform engineer, data/ML lead, enterprise architect | Local deterministic gates before RAG ingestion, release, or source promotion |
| Daily user | Knowledge manager, research ops, analyst, documentation owner | See what is trusted, what is blocked, and what evidence is missing |
| Auditor / reviewer | Internal audit, compliance, legal, external reviewer | Trace every trust decision to files, rules, hashes, and generated reports |
| Champion | AI governance owner or team lead hurt by unreliable knowledge systems | Prove that AI grounding can be controlled without sending private data to the cloud |

The buyer pays for control, auditability, and risk reduction. The user works with the reports, queues, and enforcement results.

## Market Fit

- **Audit teams** use Anti-Silo as a deterministic evidence chain for local folders.
- **RAG and AI teams** use it as a grounding gate before sources enter retrieval or model context.
- **Regulated organizations** use it to keep trust decisions local, traceable, and reviewable without external API calls.

## Developer Quick Start

```powershell
python -m anti_silo.cli pulse --vault examples/mini_vault
```

Reports are written to:

```text
examples/mini_vault/anti_silo_out/
```

## Local GUI

For non-technical users, start the local web interface:

```powershell
python -m anti_silo.cli gui
```

Anti-Silo opens a browser at `http://127.0.0.1:8765/`. The default flow is
**Quick Scan**: the user chooses a local folder, Anti-Silo creates a temporary
staging vault under the system temp folder, runs `ingest` + `pulse`, and shows a
plain-language trust report. The user never needs to know what a vault, ingest,
or staging folder is.

| UI Label | Engine Meaning |
|---|---|
| מוכן לשימוש | `triangulated` |
| מגובה, דורש אימות נוסף | `source_backed` |
| נסרק, טרם אומת | `indexed_unverified` |
| סיכום שצריך השלמת מקורות | synthesis without a source spine |
| חסר אסמכתא | `graph_only`, `ledger_supported`, or `corroborated_no_source` |
| סתירה או חסם אמון | refuted/blocked or contradiction hard block |

The GUI includes:

- a first-run welcome screen with Desktop scan, system folder picker, and Brain entry points
- a three-answer simple summary: usable, needs more evidence, or not recommended for reliance
- folder path scan
- best-effort drag/drop folder target
- temporary Quick Scan staging with a "discard temporary results" action
- Hebrew summary cards and a plain-language file table
- simple/professional view toggle
- one-click rescan after the user adds or edits files
- "שמור דוח HTML" export via `ANTI_SILO_REPORT.html`
- source allowlist and source TODO downloads
- a small repair wizard that filters files needing source repair
- opt-in local Watch Mode for folders the user chooses to monitor
- localized companion outputs such as `pulse.he.json`, `PULSE_HE.md`, and `triangulation_gate.he.csv`

Browser security usually hides the full local path during drag/drop. In that
case, paste the folder path into the input. The same UI is ready for desktop
packaging, where drag/drop can expose the path reliably.

The GUI is still fully local and deterministic. It binds to `127.0.0.1` by
default, does not call cloud APIs, requires a per-session local request token
for state-changing actions, and uses the same report files as the CLI.

### GUI Trust Boundary

Anti-Silo checks provenance, source linkage, and whether the inspected text was
complete. It does not determine semantic or professional truth. A local file
that was merely staged for inspection is reported as `indexed_unverified`; it
cannot be used as its own independent source.

## Local Second Brain

Anti-Silo can also run as an independent local second brain:

```powershell
python -m anti_silo.cli brain
```

The Brain opens on the same local-only interface and stores its data in a
separate local `brain.json` file. It does not import, depend on, or expose any
specific knowledge graph or client system.

Use the Brain to keep notes, questions, tasks, decisions, and sources from a
Quick Scan. A source retains the exact trust tier it had during scanning;
adding it to the Brain cannot promote it. Decisions can be linked to their
supporting sources. The review queue flags decisions with no linked source and
decisions that depend on a source below `triangulated`.

This makes the Brain a memory and decision surface, while Anti-Silo remains the
provenance gate. It is deliberately not a semantic-truth engine, user-value
measurement system, or product-validation system.

Optional GUI flags:

```powershell
python -m anti_silo.cli gui --port 8777
python -m anti_silo.cli gui --no-browser
python -m anti_silo.cli gui --open-path path/to/folder
```

Watch Mode is opt-in. After a scan, select the local monitoring action and
Anti-Silo records the folder in a local watch list. A small local polling
service notices file additions or edits, runs a fresh trust check, and stores a
recent event summary. It makes no network calls and never watches a folder
until the user explicitly selects it.

## Source Intake

Use `ingest` when your source material is a regular folder of documents rather
than an Anti-Silo-formatted vault:

```powershell
python -m anti_silo.cli ingest --vault path/to/source-folder --output-vault path/to/staging-vault
python -m anti_silo.cli pulse --vault path/to/staging-vault
```

`ingest` stages supported files as Markdown review units and records:

- intake hash and original relative file path
- `intake_kind: self_indexed`
- extraction status: `complete`, `truncated`, or `failed`
- original extension
- a `SOURCE_MANIFEST.json` audit manifest

Supported intake extensions are `.md`, `.txt`, `.csv`, `.json`, `.html`,
`.htm`, `.docx`, `.xlsx`, and `.pdf`. Heavy extractors are optional: `.docx`,
`.xlsx`, and `.pdf` are extracted when the matching local Python package is
available, and otherwise the staged file records that extraction was
unavailable.

Intake mode does not certify semantic truth and does not create a source claim
from a file's own hash. It produces `indexed_unverified` review items. Failed
or truncated extraction is a hard trust block until the original material is
reviewed completely or extracted again.

## CLI

```powershell
python -m anti_silo.cli gui
python -m anti_silo.cli brain
python -m anti_silo.cli ingest --vault path/to/source-folder --output-vault path/to/staging-vault
python -m anti_silo.cli index --vault examples/mini_vault
python -m anti_silo.cli triangulate --vault examples/mini_vault
python -m anti_silo.cli contradiction --vault examples/mini_vault
python -m anti_silo.cli queue --vault examples/mini_vault
python -m anti_silo.cli enforce --vault examples/mini_vault
python -m anti_silo.cli eligible --vault examples/mini_vault
python -m anti_silo.cli spine --vault examples/mini_vault
python -m anti_silo.cli pulse --vault examples/mini_vault
```

You can pass a custom config:

```powershell
python -m anti_silo.cli pulse --vault path/to/vault --config contracts/default_config.json
```

Localized companion reports:

```powershell
python -m anti_silo.cli pulse --vault path/to/vault --lang he
```

This keeps the canonical technical reports intact and adds Hebrew-friendly
outputs next to them.

You can also choose a scan profile:

```powershell
python -m anti_silo.cli pulse --vault path/to/vault --profile research
python -m anti_silo.cli pulse --vault path/to/vault --profile rag
python -m anti_silo.cli pulse --vault path/to/vault --profile repo
python -m anti_silo.cli pulse --vault path/to/vault --profile prompts
python -m anti_silo.cli pulse --vault path/to/vault --profile cor-sys
```

Profiles are deterministic config overlays. They reduce noise by adding include/exclude directory rules; they do not change the trust logic.
Profile include rules match both child folders and the vault root name, so a profile still works when you run Anti-Silo directly on a folder such as `agents/` or `סוכנים/`.

The `cor-sys` profile keeps full grounding strict (`triangulated` only) but marks `source_backed` claims as `review` and exports them as internal grounding candidates.

## Trust Tiers

| Tier | Meaning |
|---|---|
| `triangulated` | claim + source anchor + corroboration |
| `source_backed` | claim + source anchor, still needs corroboration |
| `indexed_unverified` | locally staged file; no independent source verification |
| `corroborated_no_source` | claim + corroboration, but source is missing |
| `ledger_supported` | ledger mention exists, but support is weak |
| `graph_only` | graph assertion only |
| `refuted_or_blocked` | blocked, refuted, or over-claimed |

`pulse` decisions are intentionally coarse:

| Decision | Meaning |
|---|---|
| `proceed` | no promotion blocks under the active policy |
| `source_backed_pending_corroboration` | every blocked claim has a raw source hash, but still needs corroboration |
| `blocked` | at least one claim is graph-only, refuted/blocked, or has contradiction debt |

## Hard Enforcement

`enforce` writes `promotion_gate.json`, `promotion_gate.csv`, and `PROMOTION_GATE.md`.
If any claim is blocked by the promotion policy, the command exits with code `2`.

The promotion gate also respects contradiction hard blocks. A claim can be
blocked even when its tier would otherwise be reviewable if the configured
contradiction policy finds a hard conflict, such as decision/outcome evidence
without raw source backing.

## Contradiction Penalty

Anti-Silo does not blindly reward evidence accumulation. It also checks whether
evidence layers contradict the trust boundary.

Run:

```powershell
python -m anti_silo.cli contradiction --vault path/to/vault
```

This writes:

- `contradiction_penalty.json`
- `contradiction_penalty.csv`
- `CONTRADICTION_PENALTY.md`

Examples of deterministic penalty rules:

- `graph_only_no_lineage`: a claim exists only as a graph assertion.
- `lineage_without_raw_source`: `lineage_sources` exists, but no reviewed raw `source_hash` was accepted.
- `corroborated_without_raw_source`: corroboration exists without raw source backing.
- `outcome_without_raw_source`: outcome/value/conversion evidence appears without raw source backing.
- `decision_without_raw_source`: decision/action evidence appears without raw source backing.
- `refuted_or_blocked`: blocked/refuted claims override positive evidence layers.

Blocked/refuted detection is field-aware by default. Anti-Silo treats values in
fields such as `status`, `tier`, `decision`, `maturity`, `promotion`, or `gate`
as explicit trust signals. It does not treat arbitrary substrings such as
`cites_refuted` as a refutation by themselves. Set `blocked_marker_mode` to
`substring` in a custom config if you need the older broad matching behavior.

The penalty score is deterministic debt, not probabilistic confidence. Each
penalty row lists the violated rule and repair action. `pulse` includes a
contradiction summary, and `enforce` blocks claims with contradiction hard
blocks.

## Content-Addressable Source Linking

Truth surfaces include a SHA-256 `content_hash`. A claim can declare:

```text
source_hash: <sha256>
```

By default, `raw_source_only` is enabled. In that mode, `source_backed` and `triangulated` require an explicit `source_hash` that points to a raw source surface. A hash that points to an internal vault node, ledger, contract, generated report, or derived synthesis is treated as missing evidence.

This prevents greenlighting claims that are only backed by graph structure or by reports derived from the graph itself.

For text files, Anti-Silo also records a `normalized_content_hash` with line
endings normalized to LF. This lets source links survive Git checkouts across
Windows/macOS/Linux without changing the raw byte-level `content_hash`.

## Research Library Index

Anti-Silo can index raw research libraries made of PDF and HTML files. These files are treated as local source surfaces by extension and path metadata, not by semantic content analysis.

For each indexed PDF/HTML file, Anti-Silo records:

- relative file path
- surface type: `research_library_source`
- SHA-256 `content_hash`
- whether the file can anchor a claim

This lets a later claim or synthesis document point to a paper by `source_hash` without relying on filenames.

## Synthesis Is Not Source

Anti-Silo distinguishes source files from synthesis files. Research summaries, integrated models, meta-analyses, and strategic synthesis documents can contain valuable reasoning, but they are not automatically eligible as grounding sources.

When a synthesis document lacks a source spine, Anti-Silo reports:

```text
synthesis_without_source_spine
```

Repair by adding one of:

- `source_hash`
- `source_spine`
- bibliography
- references
- paper list
- SLR artifact

Generate repair scaffolding:

```powershell
python -m anti_silo.cli spine --vault path/to/vault
```

This writes:

- `source_spine_todo.json`
- `source_spine_todo.csv`
- `SOURCE_SPINE_TODO.md`

## AI / RAG Grounding Allowlist

Generate the exact local sources allowed into grounding:

```powershell
python -m anti_silo.cli eligible --vault path/to/vault
```

This writes:

- `eligible_sources.json`
- `eligible_sources.csv`
- `ELIGIBLE_SOURCES.md`

By default, only `triangulated` claims grant a source eligibility. A blocked or `graph_only` claim never grants grounding access.

Some profiles also write:

- `internal_grounding_candidates.json`
- `internal_grounding_candidates.csv`
- `INTERNAL_GROUNDING_CANDIDATES.md`

These are not production grounding sources. They are deterministic review candidates, usually from `source_backed` claims.

## Immutable Audit Snapshots

For Git-managed vaults, write a local audit commit:

```powershell
python -m anti_silo.cli snapshot --vault path/to/vault --message "Trust snapshot 2026-07-15"
```

Use `--sign` to request `git commit -S`.

## Desktop Packaging

Anti-Silo can be packaged as a Windows desktop executable with PyInstaller:

```powershell
python -m pip install -e ".[desktop]"
pyinstaller packaging/anti_silo_gui.spec
```

The output is written to:

```text
dist/Anti-Silo.exe
```

The executable opens the same local GUI and keeps the same trust boundary:
local processing, deterministic reports, and no cloud calls. Packaging notes
live in `packaging/README.md`.

## Product Boundary

This repository contains the portable product layer only. It should not contain private client graphs, CRM exports, real ledgers, or sensitive source material.
