# Security

Anti-Silo reads folders that, by definition, contain a client's unfiltered
source material. The threat model follows from that: the scanned corpus is
**untrusted input**, and the report is a **deliverable that leaves the machine**.

## Data boundary

| Surface | Where files are processed | Network |
|---|---|---|
| **Desktop app** | Entirely on the local machine | The engine makes no network calls. The GUI binds `127.0.0.1` by default. |
| **CLI** | Entirely on the local machine | None. |
| **Web Beta** (optional) | A temporary Vercel Function, on files the user selects | Files are not retained in Anti-Silo storage. |

The Desktop and CLI paths contain no HTTP client, no telemetry upload, and no
model API call. Telemetry is written locally and filters path, filename, title
and body before storage.

## What is verified, and how

Each item below was reproduced with a working proof of concept before the fix
and re-run against the fix. None is a code review opinion.

| Vector | Status | Verification |
|---|---|---|
| **Folder escape via symlink / NTFS junction** | Fixed | A junction inside a scanned folder pointing outside it caused an external secrets file to be ingested and to appear in the client report. `is_within_root()` now resolves every path and rejects anything landing outside the scan root, at all four traversal sites. Re-running the same PoC yields 6 files, not 7. |
| **CSV formula injection into the client pack** | Fixed | A file named `=1+1+cmd(A1).md` reached `RISK_REGISTER.csv` raw. Scanned filenames are attacker-controlled and ship inside the deliverable. All ten CSV writers now route through one neutralizing escape; the Web Beta's client-side export does the same. |
| **Decompression bomb via `.xlsx` / `.docx`** | Fixed | A 9.6 MB file expanded to ~650M characters in 97 seconds. Output caps alone were not a fix — ~19s sits inside `load_workbook()` before any cap applies. Archives are now refused by inspecting the zip central directory *before* parsing: 0.4s. |
| **Rate-limit bypass** | Fixed | 25 spoofed `X-Forwarded-For` values produced 25 separate buckets; the code also read the *first* comma-separated value rather than the last. Identity now comes from platform-set headers with a socket peer fallback. |
| **Source-root path leaking into client exports** | Fixed | `SOURCE_MANIFEST.json` embedded an absolute local path and was offered for download. Written artifacts now carry the folder name only; the in-memory payload keeps real paths so the pipeline still works. |
| **Self-asserted `raw_source_hash`** | Mitigated, not eliminated | A hash declared in a file's own frontmatter was accepted without ever being computed, so two files with matching arbitrary strings reached the top trust tier. It is now cross-checked against hashes actually computed from real bytes; an unmatched claim is capped below `triangulated` and reported as `unverified_raw_source_hash`. **An operator who controls both files can still construct a match.** Eliminating this needs an external attestation chain, which is a design decision and not a patch. |

## Known limits

- **Provenance cannot be verified from inside the corpus.** When every source
  marker in scope was written inside the scanned folder, Anti-Silo issues a
  formal disclaimer of opinion and will not grant a full permit. It does not
  claim to detect a determined forger.
- **`critical_safety_markers` ships empty by design.** A generic dangerous-phrase
  list produces false blocks on legitimate documents that merely discuss harm
  (medical, legal, incident reports), and a control that cries wolf gets turned
  off. The list is the operator's to define for their own content domain.
- **Semantic correctness is out of scope.** Anti-Silo audits source chains and
  extraction integrity. It does not judge whether the text is factually or
  professionally correct, and it never claims to.

## Reporting a vulnerability

Open a GitHub issue for anything non-sensitive. For anything that would expose
a user's client data, contact the maintainer directly rather than filing
publicly.
