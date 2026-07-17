# Anti-Silo Consultant Pilot

## Objective

Validate one narrow claim: an AI consultant will use an Anti-Silo Preflight
Audit Pack in a real client RAG engagement and pay for the workflow.

Engineering completion is not market validation. A successful pilot must
produce an external decision such as excluding a document, requesting evidence,
changing the cleanup scope, or delaying ingestion.

## Initial Customer

- Independent AI consultant or agency with 1-20 people.
- Builds at least three client RAG or knowledge-assistant projects per year.
- Receives document folders before estimating or implementing the project.
- Works with private material and values local processing.
- Owns both the technical delivery and the client conversation.

Exclude enterprise procurement teams, general consumers, and teams asking only
for post-production RAG evaluation during this pilot.

## Offer

**Founding Consultant Pilot:** run one real client source folder through
Anti-Silo, repair or exclude the highest-priority findings, and deliver the
client Audit Pack with its Readiness Score, Risk Register, and SOW-ready scope
input.

Test a paid price of USD 99-149 for the first engagement. This is a pricing
hypothesis, not a permanent plan. Decide between per-audit and subscription
pricing only after at least five real engagements reveal repeat frequency and
value.

## Message

> Audit a client's RAG source folder before it reaches the index. Anti-Silo runs
> locally, identifies provenance and ingestion risks, creates a remediation
> queue, and exports a client-ready Preflight report and SOW input.

Never promise truth verification, zero hallucinations, legal compliance, or a
complete RAG quality score.

## Fourteen-Day Execution

### Days 1-2: Demo asset

- Record a 60-90 second walkthrough: create project, scan, explain the
  Readiness Score and one formal risk, repair one item, rescan, and export the
  Audit Pack and SOW-ready scope input.
- Use a mixed corpus containing a supported source, an unverified synthesis, an
  unsupported format, an extraction failure, and a duplicate.
- CTA: `Run one real client folder with us`.

### Days 3-7: Qualified outreach

- Contact 30 founders or delivery leads of AI/RAG consultancies.
- Use one question: `Before you quote a RAG project, how do you decide which
  client documents are allowed into the index?`
- Invite only people with a current or recent client corpus.

### Days 8-14: Live audits

- Run at least three real folders locally.
- Capture time to first verdict and time to exported Audit Pack.
- Ask which finding changed the SOW, cleanup plan, exclusion list, or ingestion
  decision.
- Request payment or a paid continuation; interest without a real folder does
  not count.

## Scorecard

| Metric | Pass |
|---|---:|
| Qualified conversations from 30 contacts | 5 or more |
| Consultants providing a real folder | 3 or more |
| Paid pilots | 2 or more |
| Audit Packs used in a client conversation or SOW | 3 of 5 pilots |
| Findings judged actionable | 60% or more |
| Second client project within 45 days | 1 or more |

The product North Star is `client_audit_packs_used`, not scans, files, or local
telemetry events.

## Interview Questions

1. What do you do today when a client gives you a document folder?
2. Which mistake is most expensive: missing material, unsupported files,
   duplicates, unclear provenance, or something else?
3. Who performs cleanup, and how is that work represented in the SOW?
4. Which part of this report would you show the client?
5. What would have to change before you used it on a second engagement?
6. Does the workflow need local desktop folders, or is a SharePoint/S3 connector
   mandatory before the first paid use?

Do not ask only what the participant would hypothetically pay. Ask for a real
folder, a real next action, and a paid pilot.

## Kill Or Pivot Criteria

- Fewer than three qualified participants offer a real folder.
- Fewer than two paid pilots after ten qualified conversations.
- Most findings are informative but do not change any client or ingestion action.
- The report is not shared or referenced in client delivery.
- Most prospects require cloud connectors before they can run a first audit.
- Consultants already obtain the same actionable artifact from their existing
  ingestion or evaluation stack.

If the desktop requirement fails, preserve the deterministic engine and move the
same policy, remediation, and report contract behind a CLI/API integration. Do
not build connectors before this signal repeats in paid pilots.
