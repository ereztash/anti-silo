# Anti-Silo

Anti-Silo is a portable trust engine for local knowledge graphs.

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
| `corroborated_no_source` | claim + corroboration, but source is missing |
| `ledger_supported` | ledger mention exists, but support is weak |
| `graph_only` | graph assertion only |
| `refuted_or_blocked` | blocked, refuted, or over-claimed |

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

## Product Boundary

This repository contains the portable product layer only. It should not contain private client graphs, CRM exports, real ledgers, or sensitive source material.
