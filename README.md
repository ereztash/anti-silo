# Anti-Silo

Anti-Silo is a portable trust engine for local knowledge graphs.

It scans a folder, classifies truth surfaces, evaluates graph claims, runs a triangulation gate, and produces an evidence-upgrade queue. The goal is to prevent a knowledge system from promoting claims just because they are internally consistent.

## What It Does

- Finds claim files and source/truth-surface files.
- Classifies surfaces such as CRM anchors, outcomes, preregistration notes, ledgers, external material, and governance contracts.
- Assigns every claim a promotion and triangulation status.
- Produces machine-readable JSON/CSV and human-readable Markdown reports.
- Runs fully locally.

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

5. **Audit Snapshot**  
   A Git-managed vault can commit each trust snapshot, creating a chronological audit trail of what was trusted, blocked, or repaired over time.

6. **Operational Use**  
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

## Quick Start

```powershell
python -m anti_silo.cli pulse --vault examples/mini_vault
```

Reports are written to:

```text
examples/mini_vault/anti_silo_out/
```

## CLI

```powershell
python -m anti_silo.cli index --vault examples/mini_vault
python -m anti_silo.cli triangulate --vault examples/mini_vault
python -m anti_silo.cli queue --vault examples/mini_vault
python -m anti_silo.cli enforce --vault examples/mini_vault
python -m anti_silo.cli pulse --vault examples/mini_vault
```

You can pass a custom config:

```powershell
python -m anti_silo.cli pulse --vault path/to/vault --config contracts/default_config.json
```

## Trust Tiers

| Tier | Meaning |
|---|---|
| `triangulated` | claim + source anchor + corroboration |
| `source_backed` | claim + source anchor, still needs corroboration |
| `corroborated_no_source` | claim + corroboration, but source is missing |
| `ledger_supported` | ledger mention exists, but support is weak |
| `graph_only` | graph assertion only |
| `refuted_or_blocked` | blocked, refuted, or over-claimed |

## Hard Enforcement

`enforce` writes `promotion_gate.json`, `promotion_gate.csv`, and `PROMOTION_GATE.md`.
If any claim is blocked by the promotion policy, the command exits with code `2`.

## Content-Addressable Source Linking

Truth surfaces include a SHA-256 `content_hash`. A claim can declare:

```text
source_hash: <sha256>
```

When present, triangulation links the claim to that exact source hash before falling back to filename matching.

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

## Immutable Audit Snapshots

For Git-managed vaults, write a local audit commit:

```powershell
python -m anti_silo.cli snapshot --vault path/to/vault --message "Trust snapshot 2026-07-15"
```

Use `--sign` to request `git commit -S`.

## Product Boundary

This repository contains the portable product layer only. It should not contain private client graphs, CRM exports, real ledgers, or sensitive source material.
