# Anti-Silo

Anti-Silo is a portable trust engine for local knowledge graphs.

It scans a folder, classifies truth surfaces, evaluates graph claims, runs a triangulation gate, and produces an evidence-upgrade queue. The goal is to prevent a knowledge system from promoting claims just because they are internally consistent.

## What It Does

- Finds claim files and source/truth-surface files.
- Classifies surfaces such as CRM anchors, outcomes, preregistration notes, ledgers, external material, and governance contracts.
- Assigns every claim a promotion and triangulation status.
- Produces machine-readable JSON/CSV and human-readable Markdown reports.
- Runs fully locally.

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

## Product Boundary

This repository contains the portable product layer only. It should not contain private client graphs, CRM exports, real ledgers, or sensitive source material.
