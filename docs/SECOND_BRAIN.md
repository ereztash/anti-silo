# Independent Local Second Brain

## Purpose

The Brain is a local knowledge and decision store that uses Anti-Silo's trust
tiers as visible constraints. It is intentionally generic: no external graph,
client system, account, or cloud service is required.

## Data model

`brain.json` stores append-friendly entries:

- `source`: imported from a Quick Scan and keeps its original trust tier.
- `note`: a contextual memory item.
- `decision`: a conclusion that may link to one or more source entries.
- `question` and `task`: open loops that should not be mistaken for evidence.

## Trust rules

1. Importing a scan never upgrades a source's tier.
2. A decision with no linked source is placed in the review queue.
3. A decision linked to any source below `triangulated` is placed in the review queue.
4. The Brain never claims semantic truth, real-world use, user value, or commercial validation.

## Local operation

Run `python -m anti_silo.cli brain`. The service binds to `127.0.0.1` by
default, uses no external API, and stores the Brain outside the scanned vault.

The first empty Brain screen asks one question: what the user is thinking
about. It then opens the matching note, question, or decision composer. A
decision can link to scanned sources, and the trust queue remains visible when
the linked evidence is incomplete.
