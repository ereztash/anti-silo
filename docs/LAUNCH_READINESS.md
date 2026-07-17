# Anti-Silo Launch Readiness

**Status date:** 2026-07-17

## Launch Claim

Anti-Silo is a consultant pre-flight audit for client RAG source folders. It
checks extraction completeness, duplication, provenance markers, and grounding
eligibility under a deterministic policy. It produces a client-readable
verdict, Readiness Score, Risk Register, remediation queue, and SOW input.

It does not verify factual truth, legal correctness, model quality, or market
demand.

## Gate Status

| Gate | Evidence | Status |
|---|---|---|
| Deterministic engine | Complete Python test suite | Pass |
| Consultant decision pack | HTML report, Risk Register, SOW input, Audit Pack | Pass |
| Local privacy boundary | Desktop binds to loopback and keeps source files local | Pass |
| Hosted first-run path | Browser folder selection, no-upload demo, temporary function | Pass in code |
| Hosted consent | Explicit cloud-processing checkbox required for real scans | Pass |
| Hosted abuse boundary | Size limits, origin check, honeypot, per-instance rate limit | Pass for beta |
| Hosted legal copy | Privacy notice and beta terms served with the app | Pass |
| Hosted production URL | Vercel project and public smoke test | Pending owner authorization |
| Distribution | Windows installer workflow and source install instructions | Pass |
| Paid demand | Paid pilot using a real client folder and client-facing artifact | Unproven |
| Repeat demand | Second client engagement by the same consultant | Unproven |

## Production Smoke Test

Run these checks after every hosted deployment:

1. `GET /` returns the Hebrew Preflight UI.
2. `GET /api/scan` returns `{"status":"ready"}`.
3. The no-upload demo completes and displays a verdict, score, remediation, and risks.
4. A real scan cannot start before cloud-processing consent is checked.
5. A small non-sensitive folder completes and returns a downloadable JSON report.
6. Cross-origin POST requests are rejected.
7. `/privacy.html` and `/terms.html` load on desktop and mobile.
8. Runtime logs contain `web_scan_completed` without paths, names, or document content.

## Pilot Funnel

The hosted beta is an activation surface, not proof of demand. The paid pilot
is the commercial test.

| Stage | Two-week target | Evidence that counts |
|---|---:|---|
| Qualified consultant conversations | 5 | Current or recent RAG client corpus |
| Demo completions | 5 | `web_scan_completed` with `demo=true` |
| Real folder audits | 3 | Non-demo completion plus participant confirmation |
| Action-changing findings | 3 | Exclusion, evidence request, cleanup scope, or delayed ingestion |
| Client-facing use | 3 | Report or SOW referenced in a client conversation |
| Paid pilots | 2 | Payment received, not stated willingness |
| Repeat engagement | 1 within 45 days | Same consultant, second client project |

The North Star is `client_audit_packs_used`. Scan count and file count are
diagnostics, not success metrics.

## Offer Under Test

**Founding Consultant Pilot:** one real client source-folder audit, review of
the highest-priority findings, and delivery of the Audit Pack with SOW-ready
scope input.

Initial price hypothesis: USD 99-149 per engagement. Do not choose subscription
pricing until at least five engagements reveal repeat frequency and delivery
value.

## Launch Sequence

1. Authorize and deploy the GitHub repository to Vercel.
2. Run the production smoke test above and record the public URL.
3. Record a 60-90 second walkthrough using the demo corpus.
4. Contact 30 qualified AI consultants or small RAG agencies.
5. Run three real folders locally to preserve the strongest privacy boundary.
6. Ask which finding changed a client, scope, cleanup, or ingestion decision.
7. Ask for payment or a paid continuation during the pilot.
8. Review the kill or pivot criteria in `CONSULTANT_PILOT.md` after ten qualified conversations.

## Scale Gates

Do not describe the business as validated, let alone a guaranteed unicorn,
until evidence advances through these gates:

1. **Problem evidence:** consultants repeatedly show the same expensive intake failure.
2. **Paid workflow evidence:** at least two paid audits change a real engagement decision.
3. **Repeat evidence:** the same consultant uses Anti-Silo on a second client.
4. **Channel evidence:** one acquisition channel produces qualified pilots predictably.
5. **Economic evidence:** delivery cost, conversion, retention, and support load sustain margin.
6. **Expansion evidence:** integrations or team workflows are requested in paid use, not imagined in planning.

The correct promise is a rigorous launch process with falsifiable gates. No
engineering plan can guarantee a unicorn outcome.
