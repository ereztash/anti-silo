# Anti-Silo adversarial review - 2026-07-16

Purpose: try to refute Anti-Silo as both a trust engine and a standalone product, using COR-SYS graph constraints plus code-level probes.

## Bottom line

Anti-Silo survives only as an evidence-hygiene product: it can say whether a file has provenance markers, source hashes, and promotion-gate status under a deterministic local policy.

It does not yet survive as a "truth verifier", "legal/research validator", or "trust this document" product for nontechnical users. The current GUI language and quick-scan flow can overstate confidence, especially because quick scan stages each input document as a source for itself.

## Graph-based refutations

1. The COR-SYS graph explicitly defines itself as a projection for refutation, not a source of truth.
   Provenance: `COR-SYS-Graph/00-MOC/🏠 בית.md`.

2. Hubs, semantic similarity, lexical support, VoC, and telemetry are pointers, not evidence.
   Product implication: Anti-Silo must not sell "graph confidence" as field confidence.

3. Product-fit does not bypass ICP-fit.
   Provenance: `COR-SYS-Graph/80-מוצרים/מוצרים hub.md`.
   Product implication: "everyone with messy files" is too broad. The first wedge needs a paid, specific user with an externally visible consequence.

4. B2B/team/organization direction was already marked as a second business, not a natural extension.
   Provenance: `COR-SYS-Graph/80-מוצרים/ספריית-סימפטומים B2B.md`.
   Product implication: personal/SMB desktop trust-checker and enterprise governance are different ICPs, sales motions, and evidence thresholds.

5. The corroboration ledger repeatedly rejects automatic promotion.
   Provenance: `COR-SYS-Graph/_קורוברציה/פנקס-קורוברציה.md`.
   Product implication: Anti-Silo should default to "needs review" unless evidence is independently anchored, not merely internally coherent.

## Code-level findings

### High - Quick Scan can mark arbitrary local documents as source-backed by themselves

`anti_silo/ingest.py` stages each source file as a Markdown claim with:

- `claim_kind: synthesis`
- `source_hash: <digest>`
- `raw_source_hash: <same digest>`
- `claim: extracted document content...`

Relevant lines: `anti_silo/ingest.py:187`, `anti_silo/ingest.py:189`, `anti_silo/ingest.py:190`, `anti_silo/ingest.py:195`.

Probe:

- Direct `pulse` on a folder with an unsupported draft claim produced `graph_only` and `blocked`.
- The same folder after `ingest` produced `source_backed: 2` and `source_backed_pending_corroboration`.

Attack:

A user can drop a random draft, hallucinated summary, or fake contract into Quick Scan and receive "backed by source" because the original file is treated as its own raw source.

Needed mitigation:

Quick Scan should distinguish "self-origin file was indexed" from "claim is backed by an independent source". Suggested tiers:

- `local_document_indexed`
- `self_backed`
- `source_backed_independent`
- `triangulated`

GUI copy should not say "מגובה במקור" for self-backed intake.

### High - Local GUI has no CSRF/session token

Relevant lines: `anti_silo/gui.py:338`, `anti_silo/gui.py:364`, `anti_silo/gui.py:432`, `anti_silo/gui.py:453`.

The server binds to `127.0.0.1`, which is good, but POST endpoints accept requests without an origin check or one-time session token.

Attack:

A malicious local webpage cannot easily read the response due to browser policy, but it can still trigger scans or discard actions against the localhost server if it can guess the port/path shape.

Needed mitigation:

Generate a per-server token, embed it in the page, require it in `X-Anti-Silo-Token`, and reject POSTs with unexpected `Origin` / `Host`.

### High - The engine checks provenance markers, not semantic truth

Relevant lines:

- Markdown-only claim scan: `anti_silo/scanner.py:126`, `anti_silo/scanner.py:136`.
- Marker-based blocked detection: `anti_silo/scanner.py:69`.
- Marker-based contradiction categories: `anti_silo/contradiction.py`.

Attack:

A contract can be "source-backed" while legally wrong. A research note can cite a real PDF while misrepresenting it. Anti-Silo currently cannot detect that mismatch.

Needed mitigation:

Make the Trust Boundary visible in the GUI and exports: "בודק מקוריות ותיעוד, לא נכונות משפטית/מחקרית/עסקית."

### Medium - Optional extractor failures can become staged claims

Relevant lines: `anti_silo/ingest.py:91`, `anti_silo/ingest.py:100`, `anti_silo/ingest.py:120`.

If optional extraction dependencies are missing, extractors return placeholder text like extraction unavailable. The staged document can still be hashed and counted through the same intake path.

Needed mitigation:

Add `extraction_status` to staged metadata and force `extraction_failed` into a blocked/review tier.

### Medium - Truncation can hide the refuting evidence

Relevant lines:

- CSV limited to 200 rows: `anti_silo/ingest.py:55`.
- XLSX limited to 200 rows per sheet: `anti_silo/ingest.py:106`.
- PDF limited to 20 pages: `anti_silo/ingest.py:125`.
- JSON limited to 20,000 chars: `anti_silo/ingest.py:68`.

Attack:

The decisive contradiction can be on page 21, row 201, or past 20,000 chars.

Needed mitigation:

Expose `truncated: true` as a trust penalty. A truncated source should never be eligible for "ready to use".

### Medium - Hebrew localization is companion output, not full output replacement

Relevant lines: `anti_silo/report_labels.py:70`, `anti_silo/report_labels.py:106`, `anti_silo/report_labels.py:111`, `anti_silo/report_labels.py:121`.

The canonical technical files still exist in English, and the Hebrew CSV keeps `technical_tier`.

Needed mitigation:

Position `--lang he` as "localized companion reports" unless canonical output schemas are fully localized.

### Medium - Drag and drop is not reliable in normal browsers

Relevant lines: `anti_silo/gui.py:370`.

The code already warns when the browser does not expose `file.path`, but product copy should not imply full drag-and-drop until packaged desktop mode exists.

### Low - Quick scan temporary directory creation has unnecessary delete/recreate race

Relevant lines: `anti_silo/quick_scan.py:14`, `anti_silo/quick_scan.py:17`, `anti_silo/quick_scan.py:18`.

`mkdtemp` creates a unique directory, then deletes it and later recreates it through ingest. The risk is low, but keeping the directory and writing into it directly is simpler.

## Product refutation

The strongest product attack is not technical: the user asks, "Can I trust this document?" Anti-Silo currently answers a narrower question: "Does this document have acceptable local provenance markers under a policy?"

Those are different buying promises.

Anti-Silo is commercially defensible if the wedge is:

- "Show me which files are safe to use as inputs for AI/RAG/workflow grounding."
- "Prevent graph-only or synthesis-only notes from being promoted into source truth."
- "Create a local audit trail before a document becomes an approved source."

Anti-Silo is not yet defensible if the wedge is:

- "Tell me whether this legal contract is correct."
- "Tell me whether this research claim is true."
- "Tell me whether this folder is trustworthy."
- "Replace human source review."

## Recommended next gates

Implemented on 2026-07-16:

1. Quick Scan now emits `indexed_unverified` for self-indexed intake. The local
   file hash cannot anchor its own claim.
2. `extraction_failed` and `extraction_truncated` are hard trust penalties.
3. The GUI generates a per-server CSRF token and requires it for every POST.
4. The GUI and exported HTML report display a Trust Boundary statement.

Remaining product gate:

1. Run one paid or externally consequential pilot before treating the prosumer product as validated.
