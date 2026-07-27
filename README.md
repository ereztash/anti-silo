# Anti-Silo

**Local pre-flight source audits for consultants and agencies building client RAG systems.**

Anti-Silo inspects a client source folder before ingestion and produces a
deterministic `GO`, `CONDITIONAL GO`, or `STOP` decision, a Readiness Score,
and a client-ready Audit Pack. It does two genuinely different things, and
reading the score correctly means not conflating them:

1. **Corpus hygiene** — finds problems that make *any* folder worse for RAG,
   regardless of content: failed or partial extraction, duplicate files,
   unsupported formats, empty files. This needs no special conventions and
   works the same on any real folder you point it at.
2. **Provenance-discipline enforcement** — checks whether claims carry a
   source anchor, corroboration, and (optionally) a hash link back to a real,
   independently verifiable source. This is where the top of the score range
   lives, and it rewards a *tagging convention* your team adopts
   (`source_of_truth:`, `raw_source_hash:`, etc.) — an ordinary client folder
   that has never used one will score in a narrow, low band regardless of how
   good its content actually is. **A low score there means "this folder
   hasn't adopted structured provenance tagging," not "this content is
   bad."** Read [Readiness Score Method](#readiness-score-method) before
   presenting a score as a judgment on a client's content.

The Desktop app keeps all processing on the local machine. The optional hosted
Web Beta processes only the files selected by the user in a temporary Vercel
Function and does not retain them in Anti-Silo storage.

## Quick Start

No install, no upload — see the verdict on sample data in one click:
[run the no-upload demo](https://anti-silo.vercel.app/?demo=1).

On your own folder:

- **Desktop:** drag the client source folder onto the app. Preflight runs
  immediately — no project setup required for a first read.
- **Web Beta:** [open the hosted beta](https://anti-silo.vercel.app/), select
  up to 150 files, and scan.
- **CLI:** `python -m anti_silo.cli pulse --vault path/to/vault`

Every path runs the same deterministic engine. The Desktop and Web surfaces
present its verdict as `GO` / `CONDITIONAL GO` / `STOP`; the `pulse` CLI
reports the same underlying decision in engine vocabulary
(`proceed` / `blocked` / `source_backed_pending_corroboration`), because it is
built for scripting rather than for a client conversation.

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

## Architecture

Python, 45 modules, ~5,240 lines, 125 tests. No service to run, no database, no
account.

**Local by construction, not by policy.** The engine contains no HTTP client, no
telemetry upload and no model API call — a `grep` for `requests`/`urllib`/
`socket` across the engine returns nothing. The Desktop GUI binds `127.0.0.1` by
default. That is what makes this deployable inside an environment where the
corpus cannot leave; see [SECURITY.md](SECURITY.md) for the full data boundary.

**No model in the decision path.** Every verdict is computed by explicit rules
over file bytes and metadata. Nothing here calls an LLM, so nothing here can
hallucinate a finding — and the same folder produces the same report on any
machine.

**Determinism is enforced, not asserted.** Every filesystem traversal is sorted,
hashes stream over real bytes, deduplication is order-independent, and no
wall-clock value enters a decision. Two runs on the same corpus produce the same
verdict, the same score and the same ordering. (Report *artifacts* embed a
generation timestamp, so they are not byte-identical; the decisions are.)

**Intake:** `.pdf` `.docx` `.xlsx` `.csv` `.md` `.txt` `.html` `.htm` `.json`.
Anything else is reported explicitly as `unsupported` rather than silently
skipped — a file that was not scanned is a finding, not an absence.

**Bounded by design.** Extraction is capped during accumulation, not after, and
compressed archives are refused at the zip central directory before parsing
begins. A module-length limit is enforced by the test suite rather than by
convention.

## Security Model

The scanned corpus is untrusted input and the Audit Pack is a deliverable that
leaves the machine. Five vectors were found by red-team testing during
development, each reproduced with a working exploit before the fix and re-run
against it: folder escape via symlink/junction, CSV formula injection into the
client pack, decompression bombs in `.xlsx`/`.docx`, rate-limit bypass on the
hosted path, and a source-root path leaking into client exports. All are closed.

One limit is stated rather than hidden: a `raw_source_hash` declared inside a
file is now cross-checked against hashes computed from real bytes, but an
operator who controls both files can still construct a match. Eliminating that
requires an external attestation chain, which is a design decision, not a patch.

Full threat model, per-vector verification, and known limits:
**[SECURITY.md](SECURITY.md)**.

## Programmatic Use

Every CLI command prints its full payload as JSON on stdout, so a scan can be
gated in CI or piped into another tool without screen-scraping.

```bash
# Fail a pipeline when the corpus is not fit to ingest
python -m anti_silo.cli enforce --vault ./client-corpus || exit 1

# Full pre-flight payload for your own tooling
python -m anti_silo.cli pulse --vault ./client-corpus > preflight.json
```

| Exit code | Meaning |
|---:|---|
| `0` | Command completed |
| `1` | Invalid configuration or profile; failed snapshot |
| `2` | `enforce` found blocked items |

**Read this before wiring a gate:** `pulse` exits `0` even when the verdict is
`STOP` — its decision lives in the JSON, not in the exit status. **`enforce` is
the command that returns a non-zero status**, and it is the one to use as a CI
gate. Verified by running both against a corpus with a blocking claim: `pulse`
→ `0`, `enforce` → `2`.

Commands: `pulse` `ingest` `index` `triangulate` `contradiction` `queue`
`enforce` `eligible` `spine` `snapshot` `gui` `brain`. Scan profiles
(`--profile`) tune thresholds per corpus type: `default` `research` `rag` `repo`
`prompts` `cor-sys`.

## Who Pays and Who Uses It

The initial buyer and user is the same person today: an AI consultant, RAG
delivery lead, or small agency that receives client documents before scoping
or implementation.

Anti-Silo is useful when you need to:

- catch corpus-hygiene problems (duplicates, failed extraction, unsupported
  formats) before they enter a RAG pipeline, on any client folder
- see whether a corpus has adopted verifiable provenance tagging, and enforce
  that discipline once it has
- scope cleanup work before committing to a delivery plan
- explain exclusions and remediation requirements to a client
- produce a repeatable handoff artifact for an implementation team
- keep sensitive source material local

**Economic buyer:** the consultant or agency principal who decides to adopt
the tool. **Technical buyer:** today the same person — there is no separate
technical evaluator yet; this splits out once a larger agency or an in-house
AI/compliance team adopts it. **Daily user:** the consultant or delivery lead
running a scan before every new client engagement. **Auditor:** the client's
own compliance or legal reviewer, who receives the exported Audit Pack as the
artifact of record — a report recipient today, not yet a logged-in user.

## Commercial Model

**Sold per audit pack, not per terabyte.** A folder going into a RAG deployment
is a decision event, not a storage volume. Volume pricing would charge most for
the corpora that are cheapest to judge and least for the small, dense,
high-consequence ones where a wrong answer actually costs something.

**What a pack is:** one corpus, one verdict, the full diagnostic and remediation
queue, and an exported Audit Pack you can hand to a client or an auditor. Re-scans
of the same corpus during a remediation cycle are part of the same pack — you are
buying the decision, not the button press.

**What it does not cost you:** no per-seat licensing, no data egress, no vendor
cloud in the path, no BAA/DPA to negotiate for the local deployment, and no
security review of a SaaS surface that does not exist. For many buyers this is
the larger number.

**Where pricing sits.** Two published comparables bracket the work:

| | Price | What you get |
|---|---|---|
| **Aparavi** | ~$8,400/yr per 25TB | Volume-based data prep and classification |
| **Knowledge-governance consultancy** (e.g. Earley) | ~$45,000–55,000 per project | The same assessment, delivered as human hours, once |

Anti-Silo is the repeatable version of the second one at closer to the first's
order of magnitude. **Exact pricing is being set with the first design
partners** — stated plainly rather than published as a rate card we have not
yet validated against a real buyer. If you are evaluating this now, you are
early enough to shape both the price and the roadmap.

**Status, so nothing here reads as more than it is:** zero paying customers,
zero completed pilots. The engineering is verified and the commercial model is
a hypothesis. See [docs/INVESTOR_BRIEF.md](docs/INVESTOR_BRIEF.md) for the full
evidence position, roadmap gates and market analysis.

## Alternatives, and When They Are the Right Answer

An honest map of what else you would consider. Most of this category is real and
mature; the gap Anti-Silo fills is narrower than "data quality for AI."

| Option | Choose it when | Where it stops |
|---|---|---|
| **File analysis / ROT tools** (Komprise, Aparavi, Congruity360, Shinydocs — 200+ vendors in this Gartner category) | You need to classify, tier or retire unstructured data at petabyte scale | They analyze files and metadata. None of them scores whether a given PDF will *parse badly and lose its tables silently*. |
| **Knowledge-governance consulting** | You need organizational change, taxonomy design and stakeholder alignment — not a check | Non-repeatable, non-deterministic, and you cannot run it again next month against the same corpus |
| **Post-generation evaluation** (LLM-as-judge, RAG eval suites) | You already shipped and need to measure answer quality | It measures the output. It cannot tell you a source document was truncated during ingestion two weeks ago |
| **Nothing — ingest and iterate** | The corpus is small, well-known, and a wrong answer is cheap | This is a legitimate choice. If a wrong answer carries no liability, a pre-flight gate is overhead |

**The specific gap:** independent research across vendor claims and engineering
blogs found no competitor scoring **extraction failure** — whether a document
will be parsed badly and lose content without anyone noticing. Peer-reviewed
work (OHRBench, ICCV 2025) establishes that this failure is real and material.
Conflicting-version detection is claimed by one vendor but not demonstrated.

**And the honest counterweight**, because a technical evaluator will find it:
Barnett et al., *Seven Failure Points When Engineering a RAG System* (CAIN 2024)
— the most-cited independent taxonomy of RAG failures — lists none of
duplication, conflicting versions, or extraction failure among its seven, and
argues that RAG validation "is only feasible during operation." That is a direct
argument against a pre-ingestion product. Our position is that it describes
where failures are *observed*, not where they are *introduced*, but the paper is
real and the disagreement is genuine.

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
  both surfaces, sourced from the same engine. The threshold is remembered per
  client profile: pick a recent client and their stricter bar is restored.
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
- **Grounding Permit.** A second, deliberately separate output from the
  Readiness Score: given a requested use (`locate` / `draft` / `advise` /
  `decide` / `act`), an audience (internal / client / external), and a failure
  impact (low / financial / legal / safety), it states what the corpus's
  weakest-link evidence tier actually authorizes — `granted`, `conditional`
  (with a downgraded, safer authority), or `denied` — plus what's allowed,
  what isn't, and what would raise the grant. The Readiness Score is never
  changed by this choice; only the permission is. Anti-Silo audits file-level
  evidence, not organizational governance, so `decide` is never fully granted
  (owner and human-fallback are attested to separately, not verified by the
  tool) and `act` is never granted at all — the standard RAG-security
  distinction between retrieval permission and action permission. Exports as
  `GROUNDING_PERMIT.md` / `.json` in the Desktop Audit Pack; both surfaces ask
  the same three questions before Scan and compute the permit from one engine
  (`anti_silo/grounding_permit.py`).
- **Executive Card.** A 3-line, jargon-free summary — what's allowed, what's
  missing, how long to fix — next to the verdict on both surfaces and at the
  top of both client-facing HTML reports. Says nothing about tiers or
  "grounding"; a client reads it without asking what a term means.
- **Branding (Desktop).** Settings → הגדרות מיתוג sets a logo and business name
  that are embedded in every exported client report, so the report reads as
  the consultant's own work. Persists locally (`%LOCALAPPDATA%\AntiSilo\branding.json`)
  across scans. A separate, per-report free-text "consultant notes" field
  appears at the end of the client report.
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
| `NO DATA` | The folder is empty or every file was excluded — there is no corpus to assess. Not a positive result. |
| `GO — hygiene only` | Extraction and duplication are clean, but every source marker in scope was written inside the scanned folder. Hygiene passed; provenance was never opined on. |

The verdict is deterministic and policy-based. It is not a probabilistic
confidence score.

### Disclaimer of Opinion

Audit practice separates an *adverse* opinion ("the provenance is bad") from a
*disclaimer* ("I cannot form one"). They are not interchangeable, and Anti-Silo
issues both.

Extraction failure is fully decidable from the bytes, so it gets a full opinion.
Contradicting drafts get an opinion on *detection* only — the tool states that
two versions conflict, never which one is current. Provenance gets a **formal
disclaimer** whenever every `trust_origin` in scope is `self_declared`: a corpus
that vouches for itself gives the tool no independent footing, and a score
computed from it would be an opinion the evidence cannot support.

When provenance is disclaimed the grounding permit **cannot be fully granted** —
not because the evidence fell short of the bar, but because nothing here can say
it cleared it. Measured before this rule existed, a fabricated, wholly
self-referential corpus was granted `locate` outright while carrying
`self_declared` on every row. The same corpus now returns `conditional → none`.

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

**A folder that has never adopted `source_of_truth:`/`raw_source_hash:`
tagging cannot score above 40 per file**, because every file in it lands in
`indexed_unverified` — there is no path to `triangulated` (100) or
`source_backed` (75) without an explicit source anchor. Concretely: a small,
well-written, entirely legitimate business folder (a handbook, meeting notes,
a pricing sheet, a proposal) with no tagging convention scores **~40,
`CONDITIONAL GO`, 0% grounding-eligible** — the same band a genuinely messy
folder would land in. That is not this tool failing to notice the folder is
fine; it is this tool measuring something else entirely (whether provenance
is *machine-verifiable*), which a normal client folder was never going to
have. Reserve top-of-scale readings for corpora that have adopted the tagging
convention; for everything else, read the score as "has this adopted
structured provenance" rather than "is this good."

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
- **near-duplicate documents** — reworded drafts of the same document, which
  hashing cannot see (see below)
- **near-duplicates that contradict each other** — the same document in several
  versions quoting different figures
- missing source anchors
- synthesis documents without a source spine
- graph-only or weakly supported claims
- contradiction hard blocks
- changes in ready, review, blocked, and corpus-issue counts between scans
- readiness-score movement between scans

Anti-Silo can also generate strict grounding allowlists and source-spine repair
templates for structured knowledge vaults.

## Near-Duplicates and Contradicting Drafts

Byte-identical duplicates are the *rare* case in a real client folder. People
do not copy files, they save `sow.md`, `sow-v2.md`, `sow-FINAL.md` — three
near-identical documents quoting three different prices. SHA-256 sees three
unrelated files. The retriever sees three strong matches and cannot tell which
one is current, so the model may ground on a superseded draft and state an
obsolete number with full confidence.

Anti-Silo compares documents by overlap of word 3-grams (a bottom-k shingle
sketch) and separates two cases:

| Finding | Severity | Meaning |
|---|---|---|
| `near_duplicate` | cleanup | Overlapping versions that agree. They inflate the index and crowd out other sources in retrieval. |
| `near_duplicate_conflict` | review | Overlapping versions that **disagree on their figures**. The report names the conflicting values. |

The method is deterministic and model-free, like the rest of the engine: the
same bytes produce the same score on any machine, and the score is explainable
to a client as "these documents share ~94% of their phrasing".

**Calibration and limits.** The threshold (`near_duplicate_threshold`, default
`0.72`) was set by measurement, not intuition. Against the realistic
false-positive case — two *different* engagements written on one template —
a true near-duplicate scores `0.96` and the template pair `0.46` on long
documents. On short documents the same pair scores `0.82` versus `0.62`: still
separable, but a narrower margin, because a handful of shingles means a single
edit moves the score a lot. Short documents are therefore the weaker signal
here, which is why a near-duplicate on its own is only `cleanup`, and
disagreeing figures are what raise it to `review`.

## The Grounding Firewall

`eligible_sources.csv` (the `eligible` CLI command) is the allowlist that
actually gates what a RAG pipeline may load: every row carries a `source_hash`
(SHA-256 of the source content) alongside its trust tier, so a downstream
system can verify it is grounding on the exact file Anti-Silo audited, not a
same-named replacement. Nothing is added to that allowlist without passing the
promotion gate first — `enforce` (`promotion_gate.json`) checks each source's
tier against the configured `promotion_policy` and only marks tiers that
clear it `promotion_allowed`; everything else stays `review_before_promotion`
or blocked. The firewall is this pair together: a hash-verified identity, plus
a policy gate that decided it was allowed to have one.

## One Decision, Not Many Gates

Triangulation, contradiction penalties, the evidence-upgrade queue, and the
promotion gate are four separate checks — a consultant does not have time to
read four reports before every client call. `pulse` runs all of them and
compresses the result into a single top-level `decision`
(`blocked` / `conditional` / a passing verdict), so Enforcement is a
one-field answer, not an exercise in cross-referencing outputs by hand.

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

### Who vouches for a source

Every trust tier answers "is there a source anchor". A separate field,
`trust_origin`, answers the harder question of **who said so**:

| `trust_origin` | Meaning |
|---|---|
| `self_declared` | The source marker is written inside the scanned folder. The corpus is vouching for itself. |
| `operator_attested` | A person explicitly picked an independent source through the repair flow. |

This distinction is surfaced rather than folded into the score, and that is a
deliberate limit rather than an omission: **nothing inside a folder can
establish that a source is independent of that folder.** A file asserting
`source_of_truth: true` is an assertion by whoever assembled the folder —
structurally the same kind of statement as the claim it vouches for. A
determined author can therefore reach `source_backed` with a fabricated chain.

Anti-Silo does not pretend to detect that, because it cannot from inside the
corpus. It reports the origin so the reader can weigh it. Whether
`self_declared` is acceptable depends on whose folder it is: for an operator
auditing their own vault it is the intended model, and for an adversarial or
unknown corpus it is close to worthless. That judgment stays with the person,
which is also why `decide` is never fully granted by the Grounding Permit.

By default, blocked-claim detection (`blocked_marker_mode: field`) only
checks recognized frontmatter fields, not free body text — this is
deliberate, to avoid false-positiving on prose that merely *discusses* a
refuted claim. The practical consequence: an explicit, severe warning written
as plain prose ("this was refuted after publication; people were harmed") is
not caught by default. `critical_safety_markers` in the config (empty by
default) is a narrow, additive exception — phrases listed there are always
checked against full body text regardless of mode. It ships empty because
there is no universal list of "dangerous phrases" across arbitrary document
domains that would respect your content the way a domain-specific list you
choose would; populate it for your own content type if you need this net.

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
- returns the verdict, Readiness Score, a per-file classification breakdown (why each file landed in its tier), remediation queue, Risk Register, and a Grounding Permit for the requested use/audience/failure-impact set before scanning
- lets the consultant download a client-ready HTML report, raw JSON, and the Risk Register as CSV
- lets the consultant copy a client-ready summary, copy a personal accomplishment post, and save a
  shareable 1200×630 verdict card (PNG, generated client-side via Canvas, no server round-trip) — a
  small "🎉 you hit GO" prompt surfaces these when the verdict is GO
- signs both the Web and Desktop client-facing HTML reports with a subtle "generated with Anti-Silo"
  footer line
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

## Evidence Repair Queue

Knowing a claim is `source_backed` instead of `triangulated` is a diagnosis, not
a plan. `queue` turns the Trust Tiers above into a concrete, prioritized
evidence-upgrade queue: every claim that isn't yet `triangulated` gets one row with an
`upgrade_path` (`source_anchor_backfill`, `corroboration_backfill`,
`source_and_corroboration_backfill`, `ledger_validation`, `repair_or_retire`,
or `source_spine_backfill`) and a plain-language `required_evidence`
description of what closes the gap, ranked by tier severity.

```powershell
python -m anti_silo.cli queue --vault path/to/vault
```

Output: `evidence_upgrade_queue.json`, `evidence_upgrade_queue.csv`, and
`EVIDENCE_UPGRADE_QUEUE.md` — a ranked list an analyst or knowledge manager can
work top-down, instead of hunting for which of hundreds of claims to fix next.

This is a triage tool, not a repair robot: it never attaches a source,
promotes a tier, or retires a claim on its own — it only computes what a
human still needs to go get. **The pain it targets:** unsupported claims
otherwise have no repair workflow at all, only a static trust-tier label.

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

**Evaluating as a buyer?** Start with [Architecture](#architecture),
[Security Model](#security-model), [Programmatic Use](#programmatic-use) and
[Commercial Model](#commercial-model).

**Evaluating as an investor?** [docs/INVESTOR_BRIEF.md](docs/INVESTOR_BRIEF.md)
carries the evidence position, roadmap gates and market analysis, with every
figure marked measured, public-source or hypothesis. It states plainly that
there are zero customers and a pre-registered test that has not been run.

## License

Proprietary. All rights reserved — see [LICENSE](LICENSE). This repository is
public for transparency and evaluation; it is not open source, and no license
to use, copy, modify, or redistribute the Software is granted except by
separate written agreement.
