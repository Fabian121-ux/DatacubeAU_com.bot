# Current release decision — 2026-11-07 21:24 WAT (20:24 UTC)

**<NOT TEST READY>**

This fresh overlay supersedes the 17:20 WAT snapshot below. Historical checkboxes are not current proof.

## Verified baseline

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. Main still has migrations 001–033 only.
- Latest overall Tests run [42340254616](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42340254616) succeeded on PR #60 exact head `155430d29414e9d918062ce74d05cbee72edfa6a`: 974 passed, 1 warning, 76.50%. It applied 001–033 + 038–040 only; it did not apply 034–037 or run the sequence preflight, ORM schema audit, or post-test leakage audit.
- Current migration allocation: #48=034, #50=035, #49=036–037, #60=038–040. Unique branch numbering is not integrated 001–040 proof.
- Ten PRs remain open; none has an APPROVED review. Active unresolved inline threads: #60=9, #62=4, #50=4, #49=1, #59=1. #48/#61 have no unresolved threads; #55/#57/#63 have only outdated unresolved threads.
- The branch endpoint reports `protected: false` / `protection.enabled: false`, with required-status-check enforcement `off`; `main` is **not branch-protected**. Configure and verify required independent human review and CI through repository administration before any merge.

## Blocking P0 gates

- [ ] Fix #60's final time-of-check gap: consent is revalidated with `clock_timestamp()` before the later pending-STOP query; consent can expire while that query waits. The same contact-policy ID is rechecked before later source/approval/consent/STOP waits and can expire before transport.
- [ ] After all blocking locks, establish one final dispatch-reservation boundary that revalidates exact authority type and policy/approval ID, current Contact mapping, consent status/provenance/expiry, terminal/pending opt-out, and exact queue recipient/content/media binding using the database clock. Keep locks through one transport attempt; add deterministic two-session expiry/STOP regressions with zero mock-WAHA calls.
- [ ] OWNER must explicitly accept or revise the STOP linearization contract: a STOP committed after the final reservation but before network entry may lose one already-reserved attempt; subsequent attempts must be blocked.
- [ ] OWNER must confirm terminal opt-out is Contact-wide across mapped aliases and cannot be overridden by routine re-consent.
- [ ] OWNER must confirm whether OWNER-attested consent plus opaque `evidence_ref` is sufficient external-contact consent evidence, distinct from contact-specific automation permission and exact one-use send authority.
- [ ] Integrate #48's exact view-once source lock/success-only return marker/PrivateMediaArtifact observation hooks with #60's consent, STOP, quiet-hours, approval, ScheduledAction, and uncertain-send fences in one authoritative worker path.

## Integrated migration and deployment gates

- [ ] Integrate #48 (034), #50 (035), #49 (036–037), and #60 (038–040) in that order.
- [ ] Apply 001–040 from an empty disposable PostgreSQL 16 database; upgrade a representative installed 033 database through 040; verify existing data, constraints, triggers, contiguous ledger/checksums, second-run no-op, and cleanup/leakage.
- [ ] Run migration-sequence preflight, ORM schema audit, and post-test DB-leakage audit on that same integrated candidate. Existing green branch runs validate disjoint subsets only.
- [ ] Compose #60's restricted API runtime DB role and service-specific API/WAHA environment allowlists with #62's pre-DDL database-target, local-seed, migration-sequence, schema-audit, and leakage gates. #62's current Compose still passes broad `.env.production` to API/WAHA/migrate and does not provision `DATABASE_URL_RUNTIME`.
- [ ] Retain #55's schema-qualified public-table leakage audit and #57's local-seed protection. #62 is 36 commits ahead of #61 and already contains #61's sequence guard; do not merge duplicate implementations.

## Identity, governance, and product gates

- [ ] #50: choose an auditable legacy-provenance policy. Migration 035's `updated_at = created_at` heuristic cannot reliably identify all pre-033 defaults; ambiguous rows must remain `legacy_unknown`/NULL or receive explicit OWNER attestation.
- [ ] #49 remains content-only and unintegrated; resolve permanent set-key retirement review before any live producer/selection/dashboard wiring. A message variant never grants send authority.
- [ ] Obtain independent human review and resolve blocking threads. Never self-approve or merge.
- [ ] Verify effective main branch protection and required checks through a repository-admin view.
- [ ] Complete dashboard CRUD/disable, command governance, and observability management before controlled testing.
- [ ] Approve the staged OWNER self-DM → commands → media/view-once → one explicitly approved external-contact plan only after every preceding gate passes.

## Engineering actions in this verification

- Re-fetched main SHA/recent commits, all ten open PR heads, inline review threads/review submissions, exact-head Actions runs, main workflow YAML, migration trees, deployment runner/Compose, and current P0/identity source paths.
- Refreshed only the existing PR #59 roadmap and release-checklist verification overlays. No application code, migrations, tests, production database, deployment, or WAHA behavior changed. The docs-only commit uses `[skip ci]`; no Actions run is claimed.
- This run has GitHub source access but no local repository checkout, Docker, or `psql` execution. No local tests/migrations were run.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---
# Current release decision — 2026-11-07 13:26 WAT (12:26 UTC)

<NOT TEST READY>

This fresh overlay supersedes older checklist snapshots. Historical checkboxes below are not current proof.

## Verified baseline

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (latest main commit 2026-09-08). Exact-SHA Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08; no newer main run was returned.
- Latest overall Tests run [42340254616](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42340254616) succeeded on #60 exact head `155430d29414e9d918062ce74d05cbee72edfa6a`: 974 passed, 1 warning, 76.50%. Its PostgreSQL step applied 001–033 + 038–040 only; it did not run the sequence preflight, ORM schema audit, or DB-leakage audit.
- Main has migrations 001–033. Current branch allocation is #48=034, #50=035, #49=036–037, #60=038–040. Unique branch allocation is not integrated migration proof.
- All ten open PRs have zero APPROVED review submissions. Current active unresolved inline threads: #60=9, #62=4, #50=4, #49=1, #59=1; #63/#57/#55 have only outdated unresolved threads, while #61 and #48 have no unresolved threads. Review state is not a merge-readiness score.
- Main branch protection is unverified: branch-protection read returned 403 and rulesets returned empty.

## Blocking P0 gates

- [ ] Fix the #60 final time-of-check gap: consent can expire during the later pending-STOP query; the original contact-policy authority can expire after its earlier recheck. One final dispatch-reservation boundary must revalidate the exact authority/policy ID, current contact mapping, consent/expiry via PostgreSQL `clock_timestamp()`, pending/terminal opt-out, and exact queue/recipient/payload binding after all blocking locks.
- [ ] Keep mapping, consent, policy/approval, and queue locks through the single transport attempt. Add deterministic two-session tests that expire consent/policy while the final reservation waits and assert zero mock-WAHA calls. Uncertain WAHA outcomes stay quarantined and must never be retried blindly.
- [ ] OWNER must accept or revise the STOP linearization contract: a STOP committed after the final reservation but before network entry may lose that one already-reserved attempt; subsequent sends must be blocked.
- [ ] OWNER must confirm terminal opt-out is Contact-wide across mapped aliases and cannot be overridden by routine re-consent.
- [ ] OWNER must confirm whether OWNER-attested consent plus `evidence_ref` is sufficient evidence of external-contact consent, separately from automation permission and exact per-send authority.
- [ ] Compose #48's exact view-once source lock, success-only return marker, and PrivateMediaArtifact metadata hooks with #60's consent/STOP/quiet-hours/approval/ScheduledAction/uncertain-send fences in one authoritative worker path.

## Integrated migration and deployment gates

- [ ] Integrate migrations in order: #48 (034), #50 (035), #49 (036–037), #60 (038–040). The historical duplicate-034 collision is resolved in branch filenames, but no candidate has proved the combined chain.
- [ ] Apply 001–040 from an empty disposable PostgreSQL 16 database; upgrade a representative installed 033 database through 040; verify second-run no-op and checksums.
- [ ] Run the contiguous-sequence preflight, ORM schema audit, and zero-leakage audit on that same integrated candidate.
- [ ] Compose #60's restricted runtime API DB role and API/WAHA environment allowlists with #62's pre-DDL DB-target, local-seed, and migration-sequence guards. API must not receive migration-owner credentials; WAHA must receive only transport settings.
- [ ] Retain #55's schema-qualified leakage audit and #57's local-seed protection. #62 is a strict descendant of #61 and already contains its migration-sequence guard; if #61 is independently approved/merged first, rebase/retest #62 instead of cherry-picking duplicate guard changes.
- [ ] Keep private-media byte retention OFF until separate TTL/quota/integrity/delete/audit controls are independently approved and validated.

## Identity, governance, and product gates

- [ ] #50: current introduction/identity fallback code checks Identity Registry lifecycle, but migration 035 still uses `updated_at = created_at` to infer historical defaults. Choose an auditable legacy-provenance policy: ambiguous pre-033 rows remain `legacy_unknown`/NULL or require explicit OWNER attestation.
- [ ] Obtain independent human review and resolve blocking threads; no open PR currently has an APPROVED review. Do not self-approve or merge.
- [ ] Verify effective main branch protection and required checks through a repository-admin view.
- [ ] #49 remains content-only and unintegrated; resolve its permanent set-key retirement review before any producer/selection/dashboard wiring.
- [ ] Complete dashboard CRUD/disable, command governance, and observability management before controlled testing.
- [ ] Write and approve the staged OWNER self-DM → commands → media/view-once → one explicitly approved external-contact plan only after all preceding gates pass.

## Engineering actions in this verification

- Re-read main SHA/recent commits, all ten open PR heads, all review submissions and inline threads, recent Actions runs, main workflow YAML, migration trees, deployment runner/Compose, and the current #60/#48/#50 source paths. Compared #61/#62 ancestry and recorded the integration note on PR #61.
- Updated only the existing PR #59 verification overlays in the roadmap and release checklist. No application code, migrations, tests, production database, deployment, or WAHA behavior changed.
- No local repository checkout, `psql`, or Docker executable was available. No local tests/migrations were run and no Actions run was triggered by this docs-only update.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**
---

# Current release verification overlay — 2026-11-07 09:23 WAT (08:23 UTC)

**Release decision: NOT TEST READY.** This is a fresh source/CI/review snapshot, not release certification. Historical checkboxes below are not current proof.

## Verified baseline

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (2026-09-08 11:09:59 UTC); no newer main commit was returned. Exact-SHA Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08.
- Main contains migrations 001–033. Its workflow still lacks migration-sequence preflight, ORM schema audit, and post-test DB-leakage audit. Main Compose still mounts broad `.env.production` into API/WAHA; restricted runtime DB-role isolation is only on PR #60.
- Latest visible Tests run [42340254616](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42340254616) succeeded on PR #60 exact head `155430d29414e9d918062ce74d05cbee72edfa6a`: 974 passed, 1 warning, 76.50%. Its DB step applied 001–033 + 038–040 only, not 034–037; it did not run the sequence preflight, schema audit, or DB-leakage audit.
- Branch protection is **unverified**: fresh branch-protection read returned 403; rulesets returned empty.

## Open PRs and fresh inline review state

Counts are unresolved / total; active unresolved excludes outdated threads. No open PR has an APPROVED review; PR #61 has no review submission.

| PR | Exact head | Unresolved / total | Active unresolved |
|---|---|---:|---:|
| #63 | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 | 0 |
| #62 | `6bf7619656543829641b806b4b5488cdf8ace56e` | 9 / 9 | 4 |
| #61 | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 | 0 |
| #60 | `155430d29414e9d918062ce74d05cbee72edfa6a` | 22 / 24 | 9 |
| #59 | `89fa894deaaac8db23c29cebb911bf4567070490` (before this docs refresh) | 4 / 4 | 1 |
| #57 | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 | 0 |
| #55 | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 | 0 |
| #50 | `2dc4225465c41a0aa47b2a762b7d37bf8e34764a` | 5 / 13 | 4 |
| #49 | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 | 1 |
| #48 | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 | 0 |

All PRs remain open. Green CI and COMMENTED review submissions are not independent approval or merge authorization.

## Blocking product and P0 decisions

1. **STOP boundary:** #60 now checks pending STOP immediately before the single WAHA call and proves STOP committed during approval reservation blocks. A STOP committed after the final receipt read but before network entry may still lose one already-reserved attempt. Fabian must accept that one-attempt linearization point or request a stronger reservation/transport protocol.
2. **Terminal opt-out scope:** #60 currently makes opt-out Contact-wide across current mapped aliases and permanently blocks routine re-consent/OWNER override. Fabian must confirm this is intended.
3. **Consent evidence:** `.contact consent grant` stores OWNER-attested provenance and an opaque evidence reference. Fabian must decide whether that attestation is sufficient evidence of external contact consent, distinct from automation permission and per-send authorization.
4. **Legacy identity provenance:** #50 migration 035 still infers system defaults from `updated_at = created_at`. Historical pre-033 scored reads could have advanced timestamps. Choose unknown/NULL for ambiguous legacy rows or explicit OWNER-attested/immutable seed evidence; no more timestamp heuristics.

## Integration and test gates

- Migration allocation is unique by branch: 034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60). Main remains at 033; the integrated chain has not been proven.
- #60 contains the restricted runtime DB role and service-specific API/WAHA environment allowlists, but lacks #62's pre-DDL target/seed/sequence preflights. #62 has those preflights, schema audit, and leakage gate, but its Compose still injects broad `.env.production` into API/WAHA and lacks #60's restricted runtime role. #61, #55, and #57 are already represented in #62; do not merge duplicate implementations separately.
- #48's PrivateMediaArtifact observation/`.vvopen`/delete wiring is not in #60; #60's worker fences are not in #48. Compose both in one worker path.
- Required proof on one disposable PostgreSQL candidate: fresh 001–040; installed 033→040 upgrade with representative rows; second-run checksum/no-op; sequence preflight; ORM schema audit; zero DB leakage; restricted runtime-role privilege/membership checks; exact-head full suite/coverage; P0 adversarial matrix; mock-WAHA regressions.
- No integrated candidate currently satisfies these gates together. Private-media byte retention remains OFF; no real WAHA test is authorized.

**Highest-value next step:** resolve the OWNER policy decisions, then compose #48/#50/#49/#60 with #55/#57/#61/#62 into one reviewed integration candidate and run the complete disposable-PostgreSQL fresh/upgrade/no-op/security proof. Keep all PRs open pending independent review.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

# Current release verification overlay — 2026-11-07 06:20 WAT

This snapshot supersedes the 2026-11-07 03:24 WAT overlay below. **Release decision: NOT TEST READY.** Historical checkboxes are not current proof.

## Verified baseline

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; exact-SHA Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. Main has migrations 001–033.
- Main `.github/workflows/tests.yml` applies SQL files lexically and enforces 57% coverage, but does not run the contiguous migration preflight, ORM schema audit, or post-test DB-leakage audit. Main Compose still mounts broad `.env.production` into API and WAHA. Branch-protection status is unverified (GitHub API 403; rulesets endpoint empty).
- Exact-head #60 Tests run [42340254616](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42340254616) succeeded on `155430d29414e9d918062ce74d05cbee72edfa6a`: **974 passed, 1 warning, 76.50% coverage**. The disposable DB applied **001–033 + 038–040 only**; it did not prove 034–037, fresh/upgrade 001–040, second-run checksum/no-op, contiguous preflight, combined schema audit, or zero leakage.
- Feature migration allocation is unique across current branches: **034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60)**. Main remains at 033; the old duplicate-034 collision is resolved in branch filenames only.
- Current inline review state: #48 0/15; #49 1/80; #50 5/13 (4 active); #55 1/1 (outdated); #57 1/1 (outdated); #59 4/4 (1 active); #60 22/24 (9 active); #61 0/0; #62 9/9 (4 active); #63 1/1 (outdated). No APPROVED review submission exists; #61 has no review submission.

## Release blockers

- [ ] **P0 STOP linearization:** #60's final pending-STOP read is at `background_workers.py:403`, immediately before the single transport branch at line 449. A STOP committed after that read but before network entry may lose that one already-reserved attempt. Fabian must accept this one-attempt boundary or request a stronger reservation/transport protocol.
- [ ] **P0 consent policy decisions:** confirm terminal opt-out is Contact-wide across mapped aliases with no routine re-consent/override; confirm whether OWNER-attested `.contact consent grant` evidence is sufficient to represent external contact consent, distinct from OWNER automation permission and exact send authority.
- [ ] **P0 worker composition:** #60 now has the view-once source lock and success-only returned marker, but lacks #48's `PrivateMediaArtifactService` observation / `.vvopen` / delete wiring. #48 has that metadata wiring but lacks #60's contact-consent/STOP and final external-contact authority revalidation fences. Integrate both in one worker and run the combined PostgreSQL/mock-WAHA adversarial matrix.
- [ ] **P0 approval/consent:** exact one-use OWNER approval is reserved before the one transport attempt; consent expiry is rechecked after the approval reservation with PostgreSQL `clock_timestamp()`; uncertain outcomes remain quarantined and cannot be requeued/replayed. Independent review remains open.
- [ ] **Integrated migrations:** prove fresh 001–040, installed 033→040 upgrade with representative existing rows, second-run checksum/no-op, and contiguous-sequence validation on one disposable PostgreSQL candidate.
- [ ] **Integrated deployment security:** combine #60's restricted runtime role and API/WAHA environment allowlists with #62's pre-DDL target/seed/sequence guards and schema audit, preserving #55's public-schema-qualified leakage audit and #57's local-seed safety. #62's exact current Compose still mounts `.env.production` into API and WAHA and lacks #60's runtime-role provisioning; #60's runner lacks #62's preflights.
- [ ] **Identity provenance:** #50 migration 035 still uses `updated_at = created_at`; pre-033 scored reads could already have advanced timestamps on genuine defaults. Preserve ambiguous legacy provenance as NULL/unknown or require explicit OWNER attestation / immutable seed evidence; Fabian must choose.
- [ ] **Independent review:** #60 has 22/24 threads unresolved; #62 9/9; #50 5/13; #59 4/4; #49 1/80. #48 has 0/15 unresolved but only COMMENTED reviews; #61 has no review submission. No PR has an APPROVED review.
- [ ] **Dashboard and architecture:** complete required Identity/FAQ/Knowledge/Command Center/Scheduled Action/Private Media management and observability; route Internet through the single Tool Dispatcher/Authority before claiming architecture completion.
- [ ] **Controlled testing:** write/approve the staged OWNER self-DM → commands → media/view-once → one explicitly approved external contact plan only after the preceding gates pass.

## Explicitly not release proof

- #60's exact-head green run applied only 001–033 + 038–040; it does not prove the integrated migration chain, schema audit, or DB-leakage gate.
- #62's exact-head green run applied only 001–033 and does not provision #60's runtime DB role.
- #48, #49, and #50 green runs each applied only their own branch migration subset.
- #59 is documentation-only; this refresh uses `[skip ci]`, so no exact-head test run is expected or claimed.

**REAL WAHA ACTIONS: NONE.** No production DB mutation, WAHA reconnection, real WhatsApp send, unrestricted broadcast, private-media retention activation, merge, self-approval, or destructive cleanup occurred.

# Current release verification overlay — 2026-11-06 21:20 WAT

This snapshot supersedes older release/CI/migration/deployment observations below. Historical checkboxes are not current proof. **Release decision: NOT TEST READY.**

## Verified baseline

- Main remains 5aadd725ed9da08a5eb84eb42b64f0f45f231c79; main contains migrations 001–033. Latest recorded main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08.
- Main workflow applies SQL migrations lexically and runs pytest with a 57% coverage floor. It does not include the contiguous migration preflight, ORM schema audit, or post-test DB-leakage audit.
- Active feature migration allocation is now unique across branches: 034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60). The old duplicate-034 collision is resolved in branch allocation only; no integrated candidate has applied 001–040.

## Release blockers

- [ ] **P0 STOP boundary:** #60 reads pending STOP intent at worker line 280, then performs more database fences before WAHA around line 393. A STOP committed after the read but before the call can miss that attempt. Fabian must explicitly accept the read/reservation as the linearization boundary for one already-reserved attempt, or require a redesigned reservation/transport protocol. Do not describe it as cancellation through actual transport entry.
- [ ] **P0 consent expiry:** #60 revalidates consent at lines 293–298 before later delivery-window and authority/policy checks. The service's utcnow() read can become stale while those later checks wait. Move the expiry check after all later waits or include expires_at > clock_timestamp() in the atomic dispatch reservation; add a PostgreSQL/mock-WAHA regression proving expiry during a later wait yields zero sends.
- [ ] **Consent policy decision:** confirm terminal opt-out is Contact-wide across mapped aliases with no routine override, and whether OWNER-attested .contact consent grant is enough evidence of external consent or a separate external-consent authority is required.
- [ ] **Integrated migrations:** prove fresh 001–040, installed 033→040 upgrade with representative rows, second-run checksum/no-op, and migration-sequence validation in one disposable PostgreSQL candidate.
- [ ] **Integrated deployment security:** combine #60's restricted runtime DB role/service-specific Compose allowlists with #62's target validation, local-seed policy, contiguous-migration preflight, and public-schema audit. API must receive only the restricted runtime URL; WAHA only transport settings; owner DB credentials only migration service.
- [ ] **Test DB integrity:** preserve #55's schema-qualified post-test leakage audit and #57's local fixture seed safety; verify both against the integrated candidate.
- [ ] **Independent review:** #60 has 21/23 total threads (21 unresolved; one quiet-hours-clock thread was withdrawn/resolved after the shared advisory-lock order was verified); #62 9/9; #50 5/13; #59 4/4; #49 1/80; #63, #57, and #55 each 1/1. #48 has 0/15 unresolved threads but only COMMENTED reviews; #61 has no review submission. Branch-local green tests do not substitute for independent approval.
- [ ] **Identity provenance:** #50's migration 035 still uses updated_at = created_at; older scored reads could advance updated_at on system defaults before migration 033. Preserve ambiguous historical rows as unknown/NULL unless immutable evidence or explicit OWNER attestation is approved.
- [ ] **View-once integration:** preserve #48's exact source-message/chat/command lock and success-only return audit when its worker changes are combined with #60. Private-media retention remains OFF.

## Exact-head test evidence (branch-local only)

- #60 head a28cd8fae8180fa395865fbb0b75f5aa07f1dd31: [42242248132](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42242248132) success, 965 passed / 76.54%; migrations 001–033 + 038–040 only, without integrated 034–037/preflight/schema/leakage proof.
- #62 head 6bf7619656543829641b806b4b5488cdf8ace56e: [42210751706](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42210751706) success, 866 passed / 76.01%; migrations 001–033 only.
- #50 head 2dc4225465c41a0aa47b2a762b7d37bf8e34764a: [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success, 855 passed / 76.53%; migrations 001–033 + 035 only.
- #49 head bcd0033e024b177561b8afd41589afe1897ba4de: [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success, 896 passed / 76.67%; migrations 001–033 + 036–037 only.
- #48 head 3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca: [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success; branch-local 001–033 + 034 only.
- These results do not prove a combined fresh/upgrade migration chain, schema audit, DB leakage, or deployment-role boundary. PR #59 is docs-only; this snapshot is committed with [skip ci], so no exact-head test run is expected or claimed.

## Controlled test gate

Do not begin real WhatsApp testing until all blockers above are cleared, the exact integrated head passes the full suite/coverage and P0 adversarial matrix, and an independent reviewer authorizes the release. Then follow the staged OWNER self-DM → commands → media/view-once → one explicitly approved external contact plan. No autonomous real-world send is permitted.

No production database mutation, WAHA reconnection, real WhatsApp send, unrestricted broadcast, private-media retention activation, self-approval, or merge occurred. **REAL WAHA ACTIONS: NONE.**
---

# Current verification overlay — 2026-11-06 13:30 WAT

This snapshot supersedes repository, PR, review, CI, migration, and deployment status below. The historical per-domain product tables still reflect the 2026-09-08 audit and are not current code evidence. This is not release certification.

## Main, workflow, and access

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08 11:09:59 UTC. The latest push-to-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on that exact SHA on 2026-09-08.
- Main contains migrations **001–033**. Main `.github/workflows/tests.yml` applies SQL files lexically, runs pytest with a 57% coverage floor, and does not include the contiguous-migration preflight, ORM schema audit, or post-test database-leakage audit now present on open PR branches.
- The repository rulesets endpoint returned an empty list. The branch-protection endpoint returned 403 `Resource not accessible by integration`; branch-protection state therefore could not be independently confirmed in this verification.
- Latest overall Tests run: [42217772870](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42217772870) succeeded on PR #60 exact head `fa3f47345a2ead27cd56ea4ea70f077f97a3eb73`: **964 passed, 1 warning, 76.57% coverage**. Its disposable PostgreSQL migration step applied 001–033 + 038–040. It did not apply 034–037, run the contiguous-migration preflight, run the ORM schema audit, or run the post-test DB-leakage audit.

## All ten open PRs

Thread counts are unresolved / total; outdated threads remain included. All review submissions currently show COMMENTED; **no open PR has an APPROVED review**.

| PR | Exact head | Latest known exact-head Tests | Unresolved / total threads |
|---|---|---|---:|
| #63 observability audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 / 76.08% | 1 / 1 |
| #62 migration/seed integration | `6bf7619656543829641b806b4b5488cdf8ace56e` | [42210751706](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42210751706) success; 866 / 76.01% | 9 / 9 |
| #61 contiguous migration gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success; 809 / 76.01% | 0 / 0 |
| #60 contact-consent P0 | `fa3f47345a2ead27cd56ea4ea70f077f97a3eb73` | [42217772870](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42217772870) success; 964 / 76.57% (001–033 + 038–040 only) | 20 / 21 |
| #59 verification docs | `6b70e90fbb20fb663ec6abe6b29e8525b240bca3` (before this refresh) | docs-only `[skip ci]`; predecessor `6ab12d4` passed run [42211591484](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42211591484); no run on this head | 4 / 4 |
| #57 local seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success; 811 / 76.01% | 1 / 1 |
| #55 DB leakage audit | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success | 1 / 1 |
| #50 Identity Registry lifecycle | `2dc4225465c41a0aa47b2a762b7d37bf8e34764a` | [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success; 855 / 76.53% | 5 / 13 |
| #49 outbound message library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 / 76.67% | 1 / 80 |
| #48 private-media observation wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |

Every green result above is branch-local. It is not independent approval or proof of the integrated migration/deployment chain.

Review-thread requery — 2026-11-06 12:45 WAT: GitHub now reports PR #48 with 0 unresolved of 15 threads and PR #49 with 1 unresolved of 80. All PR #48 threads are resolved, but its review submissions remain COMMENTED, not APPROVED; PR #49's remaining P2 retired-set-key thread is unresolved. This changes review-thread counts only; it does not authorize merge or change the integrated migration/deployment gates.

Engineering delta — 2026-11-06 13:28 WAT:

- PR #60 advanced from `afbafbf` to exact head [`fa3f473`](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/fa3f47345a2ead27cd56ea4ea70f077f97a3eb73) to fix the media approval digest mismatch. One canonical `content_hash_for_fields()` now feeds the live queue digest, OWNER approval validation, and OWNER draft editing, including `media_mime` and `media_filename`; text-only/locator-only digests remain byte-compatible. Added MIME/filename mutation and media-edit regressions. A source-grounded PR comment is recorded at [#6684810544](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6684810544).
- Exact-head Tests run [42217772870](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42217772870) succeeded: **964 passed, 1 warning, 76.57% coverage**. Migrations 001–033 + 038–040 applied; this did not test 034–037, the contiguous preflight, schema audit, or DB-leakage audit.
- PR #60 remains 20 unresolved / 21 total review threads; no open PR has an APPROVED review. The media digest finding is source-addressed on the current head but remains for independent review. No WAHA action occurred.


## Work completed in this verification

- PR #62 was advanced from `44d7dba65f239a9cfb7bf7a8a5fd98104a84a0f0` to `6bf7619656543829641b806b4b5488cdf8ace56e`.
- Commits [b7ad7a2](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/b7ad7a2d4a8083fe0c0b74ad2581553dd2aed781) and [6bf7619](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/6bf7619656543829641b806b4b5488cdf8ace56e) route all 22 direct `psql` call sites in `scripts/validate_zina_seed_policy.sh` through one `psql_sanitized` helper. It clears `PGHOSTADDR`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGOPTIONS`, `PGSERVICE`, and `PGSERVICEFILE`, and pins `search_path` to `public`.
- Added a fake-`psql` regression that injects all eight variables and verifies the first destructive-call attempt and EXIT-cleanup call both receive the sanitized environment. A static assertion ensures the helper is the only raw `psql` call site.
- Exact-head run [42210751706](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42210751706) passed **866 tests, 1 warning, 76.01% coverage**; migration-sequence preflight, 001–033 application, ORM schema audit, and zero-leakage audit passed. The corresponding #62 review thread has an evidence reply but remains unresolved for independent review.

## Migration and deployment integration blockers

1. Feature migration allocation is now unique: **034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60)**. Main remains at 033. The historical duplicate 034 filenames are resolved across branch trees, but no integrated candidate has proved fresh 001–040, installed 033→040 upgrade with representative existing rows, second-run checksum/no-op, combined schema audit, zero DB leakage, and restricted runtime-role privileges.
2. Deployment hardening is split. #62 has target/seed/sequence preflights, the public-schema audit, and the now-hardened disposable seed-policy harness, but its Compose still injects `.env.production` into postgres/API/WAHA/migrate. #60 has the restricted non-owner API role and service-specific environment allowlists, but lacks #62's pre-DDL target/seed/sequence preflights. Neither merge order is safe by itself. Preserve #55's leakage audit, #57's local-seed safety, and #61's migration-sequence gate in one reviewed candidate.
3. No branch has yet demonstrated the combined 001–040 fresh install, installed 033→040 upgrade, second-run no-op/checksum, schema audit, zero leakage, and runtime-role boundary in the same disposable PostgreSQL candidate.

## P0, identity, and later-product gates

- #60's latest exact-head run passed 961 tests / 76.56% on migrations 001–033 + 038–040 only. The branch now reserves exact one-use OWNER approval before WAHA and rechecks the original authority/policy identity after final consent, STOP, safety, and delivery-window fences. Its ScheduledAction worker fence uses the same queue→action row-lock order as OWNER mutations.
- **OWNER decision required:** accept that STOP committed before the final dispatch reservation blocks delivery, while STOP after reservation cannot recall the one request already entering transport and applies to subsequent sends; otherwise redesign the reservation/transport protocol. Also confirm whether terminal opt-out is Contact-wide across mapped aliases with no routine override, and whether OWNER `.contact consent grant` evidence is sufficient proof of external contact consent or must remain separate from automation permission.
- #60 still requires cumulative #48 view-once source-lock / success-only return-audit integration. No real WAHA send or production reconnection is authorized.
- **New exact-head P1 review finding — 2026-11-06:** PR #60's external media approval path has a digest-version mismatch: `prepare_external_reply()` stamps the v2 `content_hash_for_message()` (including `media_mime`/`media_filename`), while `OwnerOutboundApprovalService._authority_mismatch()` and `edit()` recompute v1 `authority_content_hash()` without those fields. Typed media approvals/edits therefore fail closed before delivery. An actionable source-grounded review comment was added to [PR #60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6684161164). Required regression: approve/edit media with MIME+filename and prove post-approval MIME/filename mutation is denied before mock WAHA. No test or WAHA action was performed for this finding.
- #50's introduction is now limited to assistant/OWNER identity and suppresses disabled/tombstoned identity claims. Migration 035's `updated_at = created_at` legacy provenance heuristic remains unsafe for pre-033 rows whose timestamps may have been advanced by older read paths; preserve ambiguous provenance as unknown unless an explicit OWNER-attested strategy is approved.
- #49 remains an outbound-message-library foundation only; it is not integrated into the live producer, selection, or dashboard. #48 remains metadata observation/return wiring only. Private-media byte retention remains OFF.

## Next safe step and release decision

Continue the independent P0 review, then compose #48/#50/#49/#60 feature migrations and #60/#62/#55/#57/#61 deployment controls into one reviewed candidate. Run the fresh 001–040 chain, installed 033→040 upgrade, checksum/no-op, schema audit, DB-leakage audit, and runtime-role tests on disposable PostgreSQL. Obtain the explicit OWNER decisions and independent human review before any merge or controlled test. **Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**


---

## Verification delta — 2026-11-06 (after PR #62 exact-head run)

- **PR #62 exact head:** `44d7dba65f239a9cfb7bf7a8a5fd98104a84a0f0`. [Tests run 42185122997](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42185122997) passed: **865 passed, 1 warning, 76.01% coverage**. Contiguous migration preflight, branch migrations 001–033, ORM schema audit, full pytest suite and post-test DB-leakage audit all succeeded. The leakage audit found no rows in audited ORM models or existing raw cleanup tables.
- The #62 change [44d7dba](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/44d7dba65f239a9cfb7bf7a8a5fd98104a84a0f0) fixes the shadow-schema false negative by counting `public.<dialect-quoted-table>` and adds a PostgreSQL regression where an earlier `search_path` schema contains a same-named table. The related review thread has an evidence reply but remains unresolved for independent review.
- #62's run applies only 001–033; it does not prove the integrated 001–040 chain or 033→040 upgrade, and the branch still lacks #60's restricted runtime role/service-specific credentials. Keep #62 draft/open.
- **PR #50 introduction source:** `introduction_reply()` now emits only the assistant/OWNER relationship and suppresses it when either default identity is disabled/tombstoned. It no longer makes project/Datacube AU claims. This earlier concern is source-addressed on #50 head `2dc4225465c41a0aa47b2a762b7d37bf8e34764a`, pending independent review. Migration 035 still uses `updated_at = created_at` for legacy provenance and remains unsafe for pre-033 rows whose timestamps were advanced by earlier reads; ambiguous rows must remain unknown unless Fabian approves an evidence/attestation strategy.
- #60 remains exact-head green at 961 passed / 76.56% on `afbafbf`, but only 001–033 + 038–040 were applied. The OWNER STOP-after-reservation contract and contact-consent semantics remain product decisions.
- The docs PR head at the start of this delta was `831917e2797dbe68533f8242feac88de391e4a43`; this is a docs-only `[skip ci]` refresh. No test/migration result is inferred from this documentation write.

---

## Verification delta — 2026-11-06 (after the prior snapshot)

- **PR #62 advanced:** exact head is now `44d7dba65f239a9cfb7bf7a8a5fd98104a84a0f0`. The raw-table leakage audit now counts only `public.<quoted_table>`, not whichever same-named table wins `search_path`; a shadow-schema PostgreSQL regression was ported from #55. Tests run [42185122997](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42185122997) was still in progress at this snapshot. Its migration-sequence preflight, migration application, and ORM schema audit had passed; pytest and the final leakage gate had not yet completed. Do not claim a pass until the exact run completes.
- **PR #50 introduction source has advanced:** `introduction_reply()` now returns only the assistant/OWNER relationship and suppresses it when either `zina` or `fabian` is disabled/tombstoned. It no longer names projects or Datacube AU, so the earlier project-claim gap is source-addressed on head `2dc4225465c41a0aa47b2a762b7d37bf8e34764a`, pending independent review. The separate migration-035 `updated_at = created_at` legacy provenance heuristic remains unsafe for pre-033 rows whose timestamps were advanced by old reads; preserve ambiguous legacy rows as unknown unless Fabian approves a stronger provenance/attestation strategy.
- The current docs PR head at the start of this delta was `b3ea732ea971dada9b479ce32960816e82388b7b`; this verification update is the next docs-only `[skip ci]` commit. No test or migration result is inferred from this documentation write.

---

## Current release verification — 2026-11-06

**Release decision: NOT TEST READY.** This overlay supersedes the older repository/CI snapshot below; historical product checkboxes and per-domain tables remain historical until a fresh full codebase audit.

### Main and latest CI

- Main SHA: `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main push Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. Main still contains migrations 001–033.
- Exact #60 head [afbafbf](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/afbafbfaa4789fd5f209ad63ff4a2cc71ea5ddc2) passed [42184294902](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42184294902): **961 passed, 1 warning, 76.56% coverage**. The run applied 001–033 + 038–040 only; it is not integrated 001–040 or installed 033→040 proof.
- Main Tests workflow still lacks the migration-sequence preflight, ORM schema audit and post-test DB-leakage audit. Those gates exist only on open PR branches.

### Release blockers

- [ ] **Integrated migration chain:** branch allocation is now unique (034 #48, 035 #50, 036–037 #49, 038–040 #60), but no single candidate has run fresh PostgreSQL 001–040, installed 033→040 upgrade, second-run no-op/checksums, and combined schema audit.
- [ ] **Integrated deployment boundary:** combine #60's restricted runtime API role and service-specific Compose allowlists with #62's DB-target validation, local-seed allowlist and pre-DDL contiguous-migration guard. API receives only the restricted runtime URL; WAHA receives only transport settings; owner URLs remain migration-only. Preserve #55's schema-qualified raw-table leakage audit and #57's local-seed safety.
- [ ] **P0 OWNER STOP decision:** accept that STOP before final dispatch reservation blocks, while STOP after reservation cannot recall the already-entering single attempt and blocks subsequent sends; otherwise redesign the reservation/transport protocol. No amount of repeated pre-send reads can cancel a network request already in flight.
- [ ] **Consent semantics:** decide whether terminal opt-out is Contact-wide across all mapped aliases and cannot be routinely overridden; decide whether the OWNER `.contact consent grant` attestation/evidence reference represents external consent or must be a separate authority.
- [ ] **Independent review:** all ten open PRs have review submissions in COMMENTED state only; no APPROVED review was found. #60 has 20/21 unresolved inline threads (9 active, 11 outdated); #62 has 8/8 (5 active); #50 has 5/13 (4 active); #49 has 1/80; #48 has 0/15. Green branch-local CI does not clear unresolved architecture/review blockers.
- [ ] **Identity Registry decisions:** keep generic introduction limited to assistant/OWNER identity or gate every project fact it names. Do not use `updated_at = created_at` to infer old default provenance; preserve ambiguous legacy rows as unknown unless an explicit owner-attested provenance strategy is approved.
- [ ] **Outbound Message Library:** #49 remains foundation only; do not wire live producer selection, contact automation or dashboard until P0 and integrated migrations are complete.
- [ ] **Private media:** #48 observation/metadata wiring does not activate private-byte retention. Retention remains OFF until owner authorization, TTL/quota/integrity/delete/audit controls are separately validated.

### Current PR #60 exact-head work

The latest #60 source/test branch preserves the exact contact-policy authority type and policy ID through the worker, rechecks it after final consent/STOP/safety/window waits, rejects expired/replaced policy authority before transport, reserves exact one-use OWNER approval before WAHA, and quarantines uncertain outcomes. The three latest commits updated stale policy-ID and five-field helper test fixtures; the exact-head suite passed 961 tests at 76.56%. Nine active review threads remain, including the OWNER STOP linearization decision and cross-PR deployment integration. PR #60 remains draft/open.

### Controlled test sequence (not authorized yet)

Only after all integrated P0, migration, deployment, schema/leakage and independent-review gates pass:
1. OWNER self-DM text.
2. OWNER self-DM commands.
3. OWNER self-DM media and view-once.
4. One explicitly approved external contact, with exact one-use authority and consent checks.

No autonomous live WhatsApp exercise. Private-media retention stays OFF. **NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh exact-state verification — 2026-11-06 04:20 WAT (03:20 UTC)

This overlay supersedes the historical 2026-09-08 checkbox snapshot below. It is a source/PR/CI review, not a release certification. Product-phase checkboxes and domain-status tables remain historical until a fresh full codebase audit is completed.

### Current release decision

**NOT TEST READY**

- Main is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest push-to-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08. No newer main push run is visible.
- Current latest overall Tests run: [42096178533](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42096178533), success on PR #60 exact head `f24c8318aa79e0c7519b91a52d0461a2bfed9730`: 958 passed, 1 warning, 76.55% coverage. It applies 001–033 + 038–040 only; it is not the integrated feature-migration chain.
- Main has migrations 001–033. Branch allocations are unique (034 #48, 035 #50, 036–037 #49, 038–040 #60), but no candidate has proved a fresh 001–040 chain or installed 033→040 upgrade/no-op.
- Main Tests workflow has a 57% coverage floor but no contiguous-migration preflight, schema audit, or post-test DB-leakage audit. Main deployment still uses broad `.env.production` mounts and has no proven migration-owner/runtime-role separation.
- All ten open PRs have been inspected. There is no APPROVED review on any open PR. #48 has 0 unresolved inline threads; #60 has 20/21 unresolved (11 active, 9 outdated); #62 has 8/8 unresolved (5 active, 3 outdated). See the roadmap overlay for the exact-head table.

### Blocking engineering gates

- [ ] **P0 contact-policy authority expiry:** #60 must preserve the original contact-policy authority and exact policy ID through the worker. After every final wait/lock, the worker must revalidate that same policy against the database clock and current category/identity; missing, disabled, expired, or no-longer-allowing policy means zero WAHA calls.
- [ ] **P1 policy lock order:** #60 must acquire the exact-chat advisory lock before its first policy-row `FOR UPDATE`; OWNER policy mutations already use advisory-lock → policy-row order. Add two-session tests for both lock winners.
- [ ] **OWNER STOP semantics:** explicitly accept that a STOP committed before the final dispatch reservation blocks, while one arriving after the reservation cannot cancel the already-entering single network attempt and applies to subsequent sends. If that is not acceptable, redesign the dispatch-reservation protocol before real testing.
- [ ] **One integrated deployment candidate:** combine #60's restricted API runtime role and service-specific Compose allowlists with #62's database-target/seed/migration-sequence preflights and libpq/search-path fence. Port #55's schema-qualified raw-table leakage counter and shadow-schema regression into the same candidate.
- [ ] **Migration proof:** fresh 001–040; installed 033→040 upgrade with representative rows; second-run checksum/no-op; schema audit; DB-leakage audit; runtime-role ownership/privilege proof — all on the same exact candidate.
- [ ] **Independent review:** no self-approval, thread resolution, or merge. All PRs remain open; no submitted review is APPROVED.
- [ ] **Identity Registry decisions:** accept unknown provenance for pre-033 rows unless immutable evidence/OWNER attestation exists; do not infer provenance from timestamps. Confirm the shared introduction stays limited to assistant/OWNER identity rather than repeating project claims.
- [ ] **View-once integration:** preserve #48's exact source/chat/command binding, source-row lock, delete fence, success-only return audit, and no-retry quarantine when integrating #60. Private-media retention stays OFF.

### Staged controlled test plan

Do not begin live testing yet. Once all gates above are independently satisfied, stage only in this order:

1. OWNER self-DM text.
2. OWNER commands.
3. Media and view-once behavior.
4. One explicitly approved external contact, with consent and policy checks verified at the final worker fence.

No real WhatsApp sends, production WAHA reconnection, production DB mutation, private-media retention activation, or destructive cleanup occurred in this run.

**REAL WAHA ACTIONS: NONE.**

## Fresh exact-state verification — 2026-11-05 21:17 UTC

This snapshot supersedes the earlier 19:48 UTC overlay below. It is a GitHub source/review/Actions inspection plus documentation update only. It does **not** certify release readiness.

### Main, workflow and migrations

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main commit is still the 2026-09-08 merge of PR #47. The branch endpoint reports `protected=false`.
- Main contains migrations **001–033 only**. The historical 034 collision is now resolved by branch allocation, but none of the feature migrations has landed on main.
- Main `.github/workflows/tests.yml` still applies every available migration in lexical order and runs pytest with a 57% coverage floor. It does not itself enforce contiguous migration numbering, run the ORM schema audit, or run the post-test DB-leakage audit.
- Main `deploy/scripts/run-migrations.sh` still reapplies every seed SQL file on each invocation, including local fixture seeds. The opt-in local-seed correction is still in open PR #57.

### All ten open PRs — live exact heads, review threads and exact-head Tests associations

Unresolved / total counts are from a fresh GitHub review-thread query. A green branch-local run is not proof of the integrated migration chain or independent approval.

| PR | Exact head | Unresolved / total | Exact-head Tests |
|---|---|---:|---|
| #48 PrivateMediaArtifact observation | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success; migrations 001–034 |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; migrations 001–033 + 036–037 |
| #50 Identity Registry follow-up | `2dc4225465c41a0aa47b2a762b7d37bf8e34764a` | 5 / 13 | [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success; **855 passed, 1 warning, 76.53%**; migrations 001–033 + 035 |
| #55 DB-leakage CI gate | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success; main migrations 001–033 plus schema/leakage audit |
| #57 deployment seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success; main migrations 001–033 |
| #59 verification docs | `369d73358899e18a16ed72959e321205c61d81df` before this documentation commit | 4 / 4 | No run associated with this docs-only head; commits use `[skip ci]` |
| #60 contact-consent P0 | `f24c8318aa79e0c7519b91a52d0461a2bfed9730` | 19 / 20 | [42096178533](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42096178533) success; **958 passed, 1 warning, 76.55%**; migrations 001–033 + 038–040 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success; main migrations 001–033 |
| #62 deployment preflight integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 8 / 8 | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; main migrations 001–033 plus schema/leakage audit |
| #63 router/conversation audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; main migrations 001–033 |

The latest visible Tests run is #60 run **42096178533** on exact head `f24c831`. Its log confirms migrations 001–033 then 038–040, followed by pytest: **958 passed**, coverage **76.55%**. It did not run 034–037, the integrated 001–040 chain, installed 033→040 upgrade/re-run checksum validation, schema audit, or DB-leakage audit.

### Current P0 / deployment blockers

1. **P0 — contact-policy authority expiry on #60.** The worker's first authorization can grant `contact_policy` authority, but the final delivery-window helper filters expired/disabled policies out and treats a missing row as “no quiet-hours restriction.” If the original policy expires while later fences wait, the worker can reach WAHA without proving that same policy still authorizes the category. Preserve the original authority type and policy ID; re-lock and revalidate that exact policy's contact/chat, enabled state, category rules and expiry using `clock_timestamp()` after all final waits. Missing, disabled, expired, or no-longer-permitted policy must deny before transport.
2. **P1 — policy lock-order inversion on #60.** Worker `authorize()` locks the policy row before the later delivery-window helper obtains the exact-chat advisory lock. OWNER policy upsert/disable takes advisory lock → policy row. This creates a row → advisory versus advisory → row deadlock cycle. Acquire the shared exact-chat lock before the first policy-row lock and test both two-session lock winners.
3. **OWNER decision — STOP linearization.** A STOP committed before the final durable dispatch reservation blocks. A STOP arriving after that reservation cannot reliably cancel the already-entering single network attempt; it must veto later sends. Fabian must accept or reject this one-in-flight-attempt contract. More pre-send reads do not eliminate the network boundary.
4. **Deployment integration — #60 and #62 cannot be merged independently.** #60 carries the restricted runtime DB role and service-specific Compose environment allowlists but lacks #62's database-target, local-seed and contiguous-migration preflights. #62 carries those preflights but still injects broad `.env.production` into API/WAHA/migrate and its raw-table leakage counter is not schema-qualified after its public-schema existence check. Port #55's `public."<table>"` counter and shadow-schema regression into the integrated candidate.
5. **Integrated migration proof remains absent.** The allocated sequence is unique across branches: #48=034, #50=035, #49=036–037, #60=038–040. Main is still 001–033. One candidate must include all predecessors and prove fresh 001–040, installed 033→040 upgrade with representative rows, second-run checksum/no-op, migration preflight, schema audit, zero DB leakage, and runtime-role privilege boundaries on disposable PostgreSQL.

#50's current 5 unresolved threads still require independent review: shared introduction scope, legacy default provenance (do not infer pre-033 origin from `updated_at = created_at`), and current registry fallback/project-scope behavior. Its green 855-test run validates only 001–033 + 035, not integrated migrations.

### Release state

- Keep #60 draft/open; its green exact-head run does not clear the P0 authority-expiry issue, P1 lock-order cycle, STOP product decision, or 19 unresolved review threads.
- Keep the deployment candidates open until #60/#62/#55/#57/#61 are reconciled into one environment-safe, migration-safe candidate and independently reviewed.
- **NOT TEST READY.** No integrated 001–040 proof, no clean installed-database upgrade proof, no complete dashboard CRUD/observability gate, and no staged controlled-test evidence.
- No production DB operation, production WAHA reconnection, real WhatsApp send, private-media retention activation, self-approval, or merge occurred. **REAL WAHA ACTIONS: NONE.**

---

## Follow-up verification correction — 2026-11-05 19:48 UTC

A further exact-source check found one additional deployment-gate defect on current PR #62 head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`:

- `scripts/audit_zina_test_db_leakage.py` schema-qualifies the raw-table existence probe to `public`, but its subsequent `COUNT(*)` is still unqualified. With `search_path=shadow,public`, a same-named shadow table can be counted while leaked rows in `public` are missed.
- PR #55's branch already contains the correct form — count `public."<quoted table>"` — and `test_raw_table_audit_counts_public_rows_when_search_path_has_shadow_table`.
- #62's green run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) predates that regression and does not validate this path. The finding remains an unresolved #62 review thread; a fresh source-grounded reply was added there. Port #55's schema-qualified counter and shadow-schema regression into the integrated deployment candidate before relying on its leakage gate.

This is a review/documentation correction only. No new test, migration, schema/leakage audit, deployment, or production DB operation was performed.

---

## Latest release verification delta — 2026-11-05 19:44 UTC

This supersedes prior status overlays for current state. It does not mark Zina TEST READY.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, latest commit 2026-09-08 11:09:59 UTC; branch protection currently reports `false`. Main migrations are 001–033. Exact-main Tests [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08.
- Current PR #60 head `f24c8318aa79e0c7519b91a52d0461a2bfed9730`; exact-head Tests [42096178533](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42096178533) succeeded: **958 passed, 1 warning, 76.55% coverage**. Its disposable migration set is 001–033 + 038–040 only.
- #60 now consumes the exact one-use OWNER approval before transport with a database-clock expiry predicate, persists uncertain-delivery evidence, and refuses OWNER replay of uncertain rows. Final contact consent is refreshed after safety/STOP locks, and ScheduledAction is row-locked through the attempt.
- **P0 still open:** contact-policy authority can survive expiry while later worker fences wait. The final delivery-window helper treats an absent active policy as “no quiet-hours restriction” even when that policy was the original send authority. Preserve the authority source/policy ID and revalidate that same row, category, enabled state and expiry with `clock_timestamp()` after all waits; missing/disabled/expired must deny before WAHA.
- **P1 still open:** worker policy-row → advisory-lock ordering conflicts with OWNER policy mutation advisory-lock → policy-row ordering and can deadlock. Acquire the exact-chat mapping lock before the first worker policy row lock; test both two-session lock winners.
- STOP linearization remains a human policy decision: a STOP committed before the durable dispatch reservation blocks; one arriving after reservation may not cancel the already-entering single request.
- Migration allocation is unique across branches (#48=034, #50=035, #49=036–037, #60=038–040), but no integrated 001–040 candidate exists. #60 and #62 remain an incompatible deployment pair: #60 has restricted runtime DB credentials/service allowlists but lacks #62's full preflight set; #62 has preflights but still exposes broad `.env.production` to API/WAHA/migrate. Integrate with #61's continuity gate before any merge/deploy decision.
- Current open PR review-thread counts (unresolved / total): #48 0/15, #49 1/80, #50 5/13, #55 1/1, #57 1/1, #59 4/4, #60 20/20 (11 active), #61 0/0, #62 8/8, #63 1/1. No independent APPROVED review is recorded.
- **NOT TEST READY.** Remaining gates: final contact-policy expiry/lock-order/STOP contract; one integrated 001–040 fresh and installed-upgrade run; schema audit and zero DB leakage; restricted runtime-role and Compose-environment proof; independent review; dashboard CRUD/observability and staged controlled-test evidence. No production DB change, production WAHA reconnection, real WhatsApp send, or private-media retention activation. **REAL WAHA ACTIONS: NONE.**

---

## Latest release verification delta — 2026-11-05 18:33 UTC

This update supersedes older status overlays below for the current PR #50 head and test evidence. It does not mark the product TEST READY.

- Main is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08 11:09:59 UTC, migrations 001–033 only. Latest exact-main Tests: [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), success on 2026-09-08. Main's Tests workflow has a 57% coverage floor but no migration-sequence preflight, ORM schema audit, or DB-leakage audit.
- PR #50 exact head: `2dc4225465c41a0aa47b2a762b7d37bf8e34764a`. Exact-head Tests [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529): **855 passed, 1 warning, 76.53% coverage**. Disposable PostgreSQL applied 001–033 + 035 only; no integrated 001–040, installed upgrade, checksum/no-op, schema-audit, or leakage proof is claimed.
- #50 now returns owner-neutral descriptions for active project facts when Fabian's identity is disabled/tombstoned, while explicit OWNER identity/ownership requests remain fail-closed. Added disabled/tombstoned regressions across Datacube, ZinaX, Moxiz, and aggregate project queries. Five review threads remain unresolved; migration-035 timestamp provenance still needs a human decision.
- Open migration allocation: #48=034, #50=035, #49=036–037, #60=038–040. The duplicate 034 numbering has been reconciled across branches, but no branch proves the integrated 001–040 chain.
- PR #60 exact head `4b36f8af3389a9270aefde4654f1e7b0a9270b3c`; Tests [42019032673](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42019032673) succeeded: **956 passed, 1 warning, 76.57% coverage**. Its uncertain-delivery replay guard is present. Approval expiry at the final transport boundary and contact-policy expiry after fence waits remain P0 blockers; STOP linearization requires OWNER policy acceptance.
- Deployment integration is not safe: #60 has restricted API runtime DB credentials/service allowlists but lacks #62's target/seed/libpq/sequence preflights; #62 has those preflights and schema/leakage checks but still mounts broad `.env.production` into API/WAHA/migrate and does not use the restricted runtime role. Require one integrated candidate and fresh 001–040, installed 033→040 upgrade, second-run checksum/no-op, schema audit, zero DB leakage, runtime-role privilege checks, and rendered Compose environment isolation before deployment approval.
- **NOT TEST READY.** No production DB changes, production WAHA reconnection, real WhatsApp sends, or private-media retention activation. Controlled testing remains blocked pending P0, migration/deployment, independent-review, dashboard/observability, and mock-WAHA gates.

---

## Fresh exact-state verification — 2026-11-05 10:21 WAT

This overlay supersedes older verification tables below wherever heads, run IDs, or review counts differ. It is based on fresh GitHub refs, all ten open PR metadata records and review threads, exact-head workflow associations, recursive migration trees, current main workflow YAML, and deployment source. This is a source/review plus documentation update; it does not certify release readiness.

### Main, workflow, deployment and migration baseline

- origin/main is still 5aadd725ed9da08a5eb84eb42b64f0f45f231c79; the latest main commit is dated 2026-09-08 11:09:59 UTC. The live branch endpoint reports protected=false.
- Main contains SQL migrations 001–033 only. Its latest exact-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08.
- Main .github/workflows/tests.yml triggers for pull requests and pushes to main/master, provisions PostgreSQL 16, applies bot_core/migrations/*.sql lexically, then runs pytest with a 57% coverage floor. Main's workflow does not yet run the migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit.
- Main docker-compose.yml still injects the complete .env.production into postgres, api, waha and migrate. The restricted API runtime-role/service-environment work exists only on #60; the migration-target/seed preflight work exists only on #62. They are not integrated.

### All open PRs — exact heads, review threads and latest exact-head Tests association

“Active unresolved” excludes outdated threads; “outdated unresolved” are historical comments that GitHub still reports unresolved but which are no longer on the current diff.

| PR | Exact current head | Unresolved / total | Active unresolved | Latest exact-head Tests |
|---|---|---:|---:|---|
| #48 PrivateMediaArtifact | 3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca | 0 / 15 | 0 | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success |
| #49 Outbound Message Library | bcd0033e024b177561b8afd41589afe1897ba4de | 1 / 80 | 1 | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success |
| #50 Identity Registry follow-up | e543a704729cc69a859ea61e4e1afb0196d23fdb | 5 / 13 | 4 | [41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413) success — 841 passed, 76.50% |
| #55 DB-leakage CI gate | b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c | 1 / 1 | 0 | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success |
| #57 deployment seed safety | d831ce4e3dd7e56f38d8563dc63abc44f8c37bba | 1 / 1 | 0 | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success |
| #59 verification docs (pre-refresh input) | 80dd9f5a59aa22dc64dee391a33d94dd7ef92b32 | 4 / 4 | 1 | No run on this input head; [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) is for parent bf6e4975d304744147d0306123176004f4d605ce |
| #60 contact-consent P0 | 9a1865cad05114770fe4c8ffeae3b12eed8b34ca | 19 / 19 | 10 | [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) success — 955 passed, 76.53% |
| #61 migration-sequence gate | 8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f | 0 / 0 | 0 | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success — 809 passed, 76.01% |
| #62 deployment preflight integration | a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc | 7 / 7 | 4 | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success — 864 passed, 76.01% |
| #63 router/conversation audit | 13fad868affe01d6069f4288481f8cd8dd341c62 | 1 / 1 | 0 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success — 803 passed, 76.08% |



The pre-refresh input above is the #59 branch head immediately before this 10:21 verification update. The final checklist commit in this update advances #59 again; that resulting docs-only head has no associated Tests run because both commits use [skip ci].

The latest overall Tests run is [41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413), successful on #50's exact current head. #59 has no run on its current head. No review submission on the open PRs is an independent APPROVED review.

### Migration allocation and deployment integration

Recursive trees confirm the feature migrations are uniquely allocated across separate branches:

- Main: 001–033.
- #48: 034 private_media_artifact_source_identity.
- #50: 035 identity_registry_default_backfill.
- #49: 036 outbound_message_library and 037 outbound_message_set_key_registry.
- #60: 038 contact_messaging_consent, 039 contact_messaging_consent_sender_identity, 040 contact_messaging_consent_sender_contact_ids.

The historical duplicate 034 allocation is therefore renumbered, but no current branch contains the integrated 001–040 chain. #50's exact-head run applied 001–033 + 035 only; #60's applied 001–033 + 038–040 only. Their green runs are branch-local and cannot prove the combined sequence or an installed 033→040 upgrade.

#61 adds a migration-name/continuity validator before SQL application in CI and the deployment runner. Its current branch contains only 001–033, so its green result proves the guard on main's chain, not the integrated feature chain. #62 adds database-target, local-seed and libpq preflights before DDL, plus schema/leakage validation. However, #62's Compose still passes broad .env.production to API/WAHA/migrate. #60 has explicit service environment allowlists and a restricted runtime DB role, but its runner lacks #62's target/seed/sequence preflights. Do not merge #60 or #62 independently or choose an arbitrary order.

Required single-candidate proof remains: fresh 001–040; installed 033→040 upgrade; second-run no-op/checksum stability; ORM schema audit; zero DB leakage; runtime-role privilege and sequence tests; rendered Compose service-environment isolation; and preservation of all preflight checks before the first DDL.

### Current P0 and architectural blockers

- Approval expiry and uncertain replay (#60): the worker's exact approval check occurs before later consent, safety-reservation, mapping and STOP-boundary waits. The approval is consumed only after a successful WAHA response. If it expires during those waits, the worker can still send and only then fail consumption. If WAHA outcome is ambiguous, the queue becomes deferred while the approval remains approved; OWNER requeue() accepts approved rows in deferred/failed state, so the same one-use authority can replay a possibly delivered message. Required: reserve/consume the exact approval after all final fences and before the single transport attempt, keep it consumed on uncertainty, and reject requeue when durable delivery evidence is uncertain. Preserve a single queue→approval lock order.
- Contact-policy expiry (#60): authorize() can authorize from a policy before later worker locks. The final delivery-window query filters expired policies out and treats “no active row” as merely no quiet-hours restriction. Preserve the authority source/policy ID and revalidate enabled/expiry/category using a fresh database clock at the final boundary; a policy-authorized row must be denied if that policy is now missing, disabled or expired.
- STOP linearization (#60): the final pending-opt-out-intent read is the dispatch reservation point. A STOP committed before it blocks; a STOP committed after it may be too late to cancel the one already-reserved network attempt. This needs explicit OWNER acceptance. If STOP must veto until actual network entry, the reservation protocol/state machine must be redesigned; another pre-send read cannot guarantee that semantics.
- ScheduledAction cancellation: the current #60 head now locks the exact queued ScheduledAction after the outbound-queue lock and holds it through the single attempt/outcome commit. The exact-head run 41846567978 is green and includes the two-session cancellation regression. This closes that specific worker/OWNER cancellation race, not the separate approval/policy expiry blockers.
- Identity Registry (#50): four active unresolved review threads remain: production introduction paths (reply_planner, /start, reply rules) can bypass the unavailable-identity guard; project-only facts can still reassert Fabian when the OWNER registry entry is disabled/tombstoned; registry-read exceptions must remain fail-closed at both identity and introduction boundaries; and migration 035's updated_at = created_at backfill cannot identify untouched defaults whose timestamps were already advanced by pre-033 reads. The provenance choice is to leave ambiguous legacy rows unknown or require explicit OWNER attestation—do not infer historical provenance from mutable timestamps.
- View-once (#48): exact-head source review confirms the worker locks and validates the exact source message/chat/command binding before WAHA, rejects deleted/mutated sources, and updates returned_to_owner_at only after a successful WAHA response. Its remaining blockers are migration integration and independent review; private-media retention stays OFF.
- Outbound Message Library (#49): this is still a foundation only. No live producer selection, contact targeting, or dashboard integration should proceed before P0 safety and migration reconciliation.

### Readiness and next safe step

NOT TEST READY. No integrated 001–040 fresh/upgrade/no-op run, no complete schema/leakage/runtime-role proof on one candidate, no completed independent review, and unresolved P0 authority/STOP decisions remain. The next safe engineering step is one reviewed integration candidate that preserves #61/#62 preflights and #60's restricted runtime role/environment allowlists while applying migrations 034→040 in order, then runs the complete disposable-PostgreSQL adversarial, migration, schema and leakage matrix. Do not use production DB or live WAHA for this work.

Human decisions required: (1) whether a STOP after the durable dispatch reservation is too late for the one in-flight attempt; (2) whether legacy identity provenance remains unknown or needs an explicit OWNER-attested backfill; (3) whether the shared introduction is limited to assistant/OWNER relationship or must retain project claims with every referenced registry key gated.

This verification update does not claim application-code edits, tests, migrations, schema/leakage audits, PR approval/merge, production DB access, production WAHA reconnection, or any real WhatsApp send. REAL WAHA ACTIONS: NONE.

---

## Source correction — PR #48 view-once return fence (2026-11-05)

The earlier overlay below that says PR #48 still updates `returned_to_owner_at` at queue creation and lacks a final source-deletion fence is stale against exact PR #48 head `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`.

- `background_workers.py` calls `_lock_owner_view_once_source()` before the WAHA call. It requires exact `source_message_id`, `source_chat_id`, and `command_message_id`, locks the source metadata row, and refuses missing/deleted sources or a chat mismatch.
- `_mark_owner_view_once_returned()` is called only in the successful WAHA-response branch; it is not set when the queue row is created or when the transport outcome is uncertain.
- Exact-head regressions include `test_mutating_view_once_source_binding_after_queueing_never_reaches_waha`, `test_delete_after_enqueue_blocks_view_once_return_before_waha`, and `test_uncertain_send_is_not_blindly_retried`.
- Therefore #48's source-binding/deletion/success-timestamp worker fence is present on its branch. Its remaining release blocker is integration of migration 034 into the ordered 001–040 candidate and independent review—not the stale worker-fence claim. Retention remains OFF.

This correction is source/test review only; it does not claim a new test run, merge, or live WhatsApp action.

---

## Fresh review follow-up — 2026-11-05 (after exact-head source review)

This follow-up supersedes the earlier #50 thread count in the verification overlay below. It records a new source-grounded review finding; it does not imply approval, merge readiness, or a new application-code change.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only and `protected=false`. Latest exact-main Tests remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08.
- PR #50 remains at exact head `e543a704729cc69a859ea61e4e1afb0196d23fdb`. Exact-head Tests [41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413) succeeded: **841 passed, 1 warning, 76.50% coverage**. Its disposable DB applied 001–033 + 035 only; no integrated 001–040, installed 033→040 upgrade, second-run checksum/no-op, schema audit, or leakage audit is established.
- A new **P1** review comment is open on [PR #50, `identity_registry_service.py:480`](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50#discussion_r4478109139): with `fabian` disabled/tombstoned, project-only queries can still return owner-attributed Datacube/ZinaX/Moxiz facts because target detection and project-answer fallbacks do not consistently model the OWNER dependency. The requested regression matrix covers project-only queries with the OWNER unavailable. PR #50 now has **5 unresolved / 13 total** review threads. The timestamp-based legacy provenance backfill remains a separate unresolved architectural decision.
- PR #60 remains at exact head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`; exact-head Tests [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) succeeded (**955 passed, 1 warning, 76.53%**), but applied 001–033 + 038–040 only. That run had no contiguous-sequence preflight, schema audit, or DB-leakage audit. The one-use approval/manual-requeue uncertainty path and expired contact-policy authority race remain P0 blockers; STOP linearization still needs OWNER acceptance.
- Migration numbers are unique only across separate branches: #48=034, #50=035, #49=036–037, #60=038–040. No open branch contains the integrated 001–040 chain. #60 and #62 deployment controls remain complementary but incompatible as-is; neither should merge independently.
- This follow-up contains no application-code edit, test, migration, schema/leakage audit, production DB operation, or WAHA action. **NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering delta — 2026-11-05 (post-#50 exact-head verification)

This snapshot supersedes the 2026-11-05 05:20 WAT overlay below. It rechecks main, all ten open PR heads and review threads, the current migration allocation, workflow configuration, and the latest #50 exact-head test run.

### Main, CI and Identity Registry change

- Main remains 5aadd725ed9da08a5eb84eb42b64f0f45f231c79 (last commit 2026-09-08 11:09:59Z); protected=false. Main's latest exact-head Tests run is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. Main contains migrations 001–033 only.
- PR #50 now points to e543a704729cc69a859ea61e4e1afb0196d23fdb. Exact-head [Tests run 41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413) succeeded: **841 passed, 1 warning, 76.50% coverage** (57% gate). The run applied migrations 001–033 and 035 only; it does not prove the integrated 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, schema audit, or DB-leakage audit.
- The #50 identity fallback now preserves Zina's answer when Fabian's registry entry is disabled/tombstoned without repeating Fabian's name: name questions return “I am Zina, an AI assistant”; purpose questions return a Zina-attributed purpose without the OWNER name. If Zina itself is unavailable, the non-assertive fallback remains. Both IdentityRegistryService's special-answer path and BotConfigService's outer fallback follow the same rule. Eight PostgreSQL-session regressions cover four phrases × deleted/disabled OWNER.
- Two intermediate exact-head CI attempts were red (runs [41980298371](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41980298371) and [41980825703](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41980825703)); the first overblocked Zina's independent identity, and the second exposed a wording mismatch between the registry and outer fallback. Both were corrected before the successful exact-head run above.
- PR #50 still has **4 unresolved / 12 total** review threads. Migration 035's updated_at = created_at historical-provenance inference remains an explicit human decision; the existing tests cannot reconstruct pre-033 read history that already advanced timestamps. Do not treat branch-local green CI as independent review or merge approval.

### All open PR heads and review state

| PR | Current head | Review threads unresolved / total | Latest relevant exact-head Tests evidence |
|---|---|---:|---|
| #48 PrivateMediaArtifact | 3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca | 0 / 15 | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success |
| #49 Outbound Message Library | bcd0033e024b177561b8afd41589afe1897ba4de | 1 / 80 | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success |
| #50 Identity Registry | e543a704729cc69a859ea61e4e1afb0196d23fdb | 4 / 12 | [41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413) success |
| #55 DB leakage gate | b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c | 1 / 1 | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success |
| #57 deployment seed safety | d831ce4e3dd7e56f38d8563dc63abc44f8c37bba | 1 / 1 | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success |
| #59 verification docs | d2d274db6171bdfb3d50cf400d5104728d46309d before this docs refresh | 3 / 3 | [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) is for parent SHA bf6e4975d304744147d0306123176004f4d605ce, not the current docs head |
| #60 contact-consent P0 | 9a1865cad05114770fe4c8ffeae3b12eed8b34ca | 19 / 19 | [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) success |
| #61 migration sequence gate | 8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f | 0 / 0 | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success |
| #62 deployment preflight integration | a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc | 7 / 7 | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success |
| #63 router/conversation audit | 13fad868affe01d6069f4288481f8cd8dd341c62 | 1 / 1 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success |

These are branch-local results. A green result on a branch with an incomplete migration subset is not integrated migration evidence.

### Migration allocation and deployment boundary

- Current feature migration numbers are unique across the open branches: #48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040. The historical 034 collision has been reconciled by renumbering #49 to 036–037. Main still has only 001–033; **no open branch contains the complete 001–040 chain**.
- Main .github/workflows/tests.yml uses ubuntu-latest and disposable PostgreSQL 16, then applies for migration in bot_core/migrations/*.sql without a contiguous-sequence preflight before running pytest with a 57% coverage floor. Thus a branch-local run can pass while skipping missing predecessor migrations. PR #61 adds the sequence gate; #62 carries the migration/target/seed preflights.
- #60 has the restricted non-owner API runtime role and service-specific environment allowlists, but lacks #62's DB-target/seed/libpq/contiguous-sequence preflights. #62 has those preflights plus schema/leakage checks, but still passes broad .env.production to API/WAHA/migrate and does not provision/use #60's restricted runtime role. **Neither branch is safe to merge independently or in an arbitrary order.** One integrated candidate must preserve preflight-before-DDL, owner URLs only in migrate, runtime URL only in API, explicit WAHA-only environment, and post-migration runtime-role provisioning.
- Required integration proof: fresh 001–040; installed 033→040 upgrade; second-run no-op/checksum; ORM schema audit; zero DB leakage; runtime-role privilege tests; rendered Compose service-environment isolation.

### P0 outbound and media blockers

- PR #60 still has unresolved P0s. On exact head 9a1865c, the worker consumes the one-use approval only in the WAHA-success branch. An ambiguous WAHA error marks the queue row deferred/uncertain while leaving approval approved; OWNER requeue() currently accepts an approved approval when the queue is deferred or failed, so the same approval can manually replay a possibly delivered request. Reserve/consume the exact approval before the single attempt after all final fences, keep it consumed on uncertainty, and reject requeue when durable delivery evidence is uncertain. Preserve one queue→approval lock order across worker and OWNER mutations.
- A contact-policy-authorized row can retain an earlier authorization while the policy expires during later fence waits; the final delivery-window query drops expired rows and currently treats no active row as “no quiet-hours restriction.” Preserve the original policy ID/source and deny if it is now missing/disabled/expired at the final database-clock check.
- STOP linearization remains a product/OWNER decision: a STOP committed before the durable dispatch reservation must block; a STOP arriving after reservation cannot promise cancellation of an already-entering network request and must govern subsequent sends. Do not invent this policy.
- PR #48's worker-side view-once return fence is present on exact head `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`: the final worker locks the exact source metadata row, validates source message/chat/command IDs, rejects deleted sources before WAHA, and updates `returned_to_owner_at` only after a successful WAHA response. Regressions cover mutation-after-queue, delete-after-queue, and uncertain no-retry. Remaining blockers are ordered migration integration and independent review; retention remains OFF.
- PR #49 remains only the Outbound Message Library foundation; no live producer/selection/dashboard integration until P0 safety and migration reconciliation are complete.

### Readiness and controls

- Current stage: **NOT TEST READY**. Exact-head unit coverage, P0 adversarial matrix, full 001–040 fresh/upgrade/no-op migration proof, schema/leakage audit, cross-branch integration, independent review, mobile CRUD/observability, and mock-WAHA staged tests are not all satisfied.
- No PR was merged, no review thread was resolved, no production DB was accessed or mutated, no production WAHA was reconnected, and no real WhatsApp send was attempted.

## Fresh engineering delta — 2026-11-05 05:20 WAT (04:20 UTC)

This supersedes the 04:17 WAT snapshot below. It rechecks the live main ref, all ten open PR heads/review threads, exact-head Tests associations, current migration inventories, and the #60/#62 deployment candidates.

### Main and exact-head CI

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; `protected=false`. Main's latest exact-head Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. Main still has migrations 001–033.
- PR #50 now points to `9b4e8728f7d7682c9c2e6489a5e6499be12a2628`. Exact-head [Tests run 41967086649](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41967086649) succeeded on 2026-11-05: **833 passed, 1 warning, 76.52% coverage**. Its disposable PostgreSQL workflow applied 001–033 and 035 only. It does not prove integrated 001–040, installed 033→040 upgrade, second-run checksum/no-op, schema audit, or DB leakage.
- #50's current code removes project claims from the shared introduction, requires both `projects` and `fabian` for the aggregate-project fallback, and requires both `zina` and `fabian` for the generic identity fallback. Five regression cases were added. Review remains **4 unresolved / 12 total**; the historical provenance/backfill decision in migration 035 is still unresolved for independent human review.
- Other exact open PR heads remain: #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`; #49 `bcd0033e024b177561b8afd41589afe1897ba4de`; #55 `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c`; #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba`; #60 `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`; #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`; #62 `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`; #63 `13fad868affe01d6069f4288481f8cd8dd341c62`. This documentation branch's pre-refresh head is `45e801bea410ab419f464c128c3c5803d196d47c`; this commit will advance #59 and has no exact-head CI result.
- Exact-head Tests remain successful for #48 [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566), #49 [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545), #55 [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314), #57 [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406), #60 [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978), #61 [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938), #62 [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073), and #63 [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429). #59's previous run [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) is for parent SHA `bf6e4975d304744147d0306123176004f4d605ce`, not its current pre-refresh head.

### Migration and deployment gates

- Feature migrations are allocated without duplicate numbers across branches: #48=034, #50=035, #49=036–037, #60=038–040. No branch contains the full 001–040 chain.
- #60 has explicit API runtime-role and service-environment allowlists, but lacks #62's DB-target/seed/libpq/contiguous-sequence preflights. #62 has those preflights plus schema/leakage gates, but still mounts broad `.env.production` into postgres/api/waha/migrate and does not use #60's restricted runtime role. Do not merge either branch independently or assume they compose.
- Required integration proof remains: fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum, ORM schema audit, zero DB leakage, runtime-role privilege checks, and rendered Compose service-environment isolation.

### P0 and release status

- #60's current exact head has passing branch-local CI, including the recent ScheduledAction worker reservation lock and two-session mock-WAHA regression. It still has unresolved P0 approval reservation/uncertain-requeue and policy-expiry findings. STOP semantics remain an explicit OWNER linearization decision: a STOP committed before final dispatch reservation blocks; one committed after reservation may be too late to cancel the already-entering single network attempt.
- **NOT TEST READY.** No integrated migration/deployment candidate or independent review completion exists. Private-media retention remains OFF. No production database or real WAHA action was performed.

This is a documentation-only verification overlay. It does not claim tests, migrations, schema/leakage audits, approval, merge, or release readiness for this commit.

---

## Fresh engineering verification — 2026-11-05 04:17 WAT (03:17 UTC)

This supersedes the 2026-11-05 03:18 WAT overlay below. I re-fetched main, all ten open PRs, their current heads and review threads, exact-head Actions run metadata, main workflow YAML, migration directories, and the #60/#62 deployment candidates. This is a source/CI review plus documentation refresh only: no application code, tests, SQL migrations, schema audit, leakage audit, production database, or WAHA operation was run in this pass.

### Main and CI — current source, not historical checklist status

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (2026-09-08 11:09:59 UTC); the live branch endpoint reports `protected=false`. No later main commit was found.
- Main contains migrations **001–033 only**. The current `.github/workflows/tests.yml` triggers on PRs and pushes to main/master, applies `bot_core/migrations/*.sql` in lexical order, then runs pytest with a 57% coverage floor. It has no migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit. The separate Strix workflow is manual for its operational scan; no Strix scan was run here.
- Latest exact-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on the exact main SHA above at 2026-09-08 11:10:02 UTC. There is no newer main-branch run.
- Main `docker-compose.yml` still mounts the complete `.env.production` into postgres, api, waha, and migrate. Main `deploy/scripts/run-migrations.sh` has no DB-target/seed/sequence preflight and applies every seed file after migrations.

### Current open PRs — exact heads and live review state

The #59 head below is the snapshot input **before this documentation-only refresh**; this refresh advances that branch and is marked `[skip ci]`.

| PR | Exact head at snapshot | Unresolved / total review threads |
|---|---|---:|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 |
| [#50 Identity Registry follow-up](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | **4 / 12** (corrects the prior 12 / 12 snapshot) |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 (outdated thread) |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 (outdated thread) |
| [#59 verification docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `56106d03dee399bf3990b31af10e38169dc34e56` | 3 / 3 |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9a1865cad05114770fe4c8ffeae3b12eed8b34ca` | 19 / 19 |
| [#61 migration-sequence integrity gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 |
| [#62 deployment seed/migration preflight](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 7 / 7 |
| [#63 conversation observability audit fix](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 (outdated thread) |

### Exact-head CI evidence and scope limits

- #48: [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) succeeded on its exact head; branch contributes migration 034.
- #49: [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded on its exact head; branch contributes migrations 036–037. It remains foundation-only, not live producer/selection/dashboard integration.
- #50: [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) succeeded on its exact head: 828 passed, 76.52% coverage; its migration step applied 001–033 plus 035, not the integrated chain.
- #55: [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) succeeded on its exact head.
- #57: [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) succeeded on its exact head; migration scope was 001–033.
- #59: current docs head `56106d0` is a documentation-only `[skip ci]` update and has no exact-head CI result. The latest cited predecessor run [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) passed 797 tests / 76.01% on `bf6e4975d304744147d0306123176004f4d605ce`, applying 001–033 only; it is not evidence for this docs head.
- #60: [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) succeeded on exact head `9a1865c`: 955 passed, 1 warning, 76.53% coverage. The job contains only the migration-apply step (no sequence preflight/schema/leakage steps); the branch directory contains 001–033 plus 038–040, so it does not prove 001–040 or installed 033→040 upgrade.
- #61: [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded on its exact head; its sequence preflight and 001–033 baseline do not include feature migrations 034–040.
- #62: [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) succeeded on exact head `a8d032d`: 864 passed, 1 warning, 76.01%; migration-sequence preflight, 001–033, ORM schema audit, and post-test leakage audit passed. It does not include feature migrations 034–040.
- #63: [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded on its exact head; its run validates the 001–033 baseline only.

### Migration and deployment integration — still blocking

- Feature migration allocation is ordered and non-colliding **across separate branches**: #48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040. No candidate branch contains all 034–040. #61's contiguous-sequence preflight will reject #60 by itself because 034–037 are absent.
- Required integrated candidate: migrations 001–040 in order; fresh install; installed 033→040 upgrade; second run proving checksum/no-op stability; ORM schema audit; zero DB leakage; runtime-role privilege proof; and rendered Compose service-environment isolation on disposable PostgreSQL. No current run proves this matrix.
- #60 has explicit service environment allowlists and a restricted `zina_runtime` DB role, but its runner lacks #62's DB-target validation, local-seed opt-in, libpq target sanitization, and contiguous-migration preflight; it also applies seed files unconditionally.
- #62 has target validation, seed opt-in, libpq sanitization, migration-sequence preflight, schema audit, and leakage audit, but its Compose file still passes broad `.env.production` to postgres/api/waha/migrate and it does not provision/use #60's restricted runtime role. Merging either branch after the other as-is can regress the other branch's security controls. Consolidate both into one reviewed candidate; do not merge them independently in either order.

### P0 and architectural blockers

1. **One-use approval reservation / uncertain replay (#60):** worker consumption still occurs after a successful WAHA call. An ambiguous send can leave the approval `approved`; OWNER `requeue()` still permits an approved row whose queue status is `deferred` or `failed`, so the uncertain-delivery quarantine has a manual replay path. Reserve the exact approval before the single attempt, after all final fences, using a database-clock conditional transition bound to approval ID, queue ID, inbound ID, exact recipient, and exact payload digest; keep it consumed on uncertain outcomes. First unify worker and OWNER lock order as queue → approval; do not introduce an approval-row lock while OWNER code still locks approval → queue.
2. **Policy expiry (#60):** preserve the original authority source/policy ID and revalidate that same enabled, unexpired policy after all blocking consent/STOP/safety/window locks using PostgreSQL `clock_timestamp()`. If the policy that granted authority is missing, disabled, or expired, deny; do not reinterpret it as absence of a quiet-hours restriction.
3. **STOP linearization (#60 — human decision):** the final pending-STOP read/dispatch reservation is the practical boundary. A STOP committed before reservation blocks; a STOP arriving after reservation may be too late to cancel the already-entering single network attempt. Fabian must explicitly accept or change that contract; keep the send path fail closed until decided. Preserve the inverse-order two-session test and uncertain-send/no-retry tests.
4. **ScheduledAction cancellation race (#60):** the current exact head adds the worker's `FOR UPDATE` lock after the queue lock and a two-session mock-WAHA regression; run 41846567978 passed. This closes that specific code path on the branch, but all #60 review threads remain unresolved and independent review is still required.
5. **Identity Registry (#50):** registry-read exceptions now fail closed, but 4 current unresolved threads remain. Decisions/findings include whether introduction text should omit project/Datacube claims and defer to registry-owned project entries, keeping legacy provenance unknown rather than inferring it from `updated_at = created_at`, and fixing a fallback that can still assert Fabian when the `fabian` registry entry is unavailable.

### Release decision

**NOT TEST READY.** The main branch has no current proof for contact-specific consent, the exact approval/policy expiry fences remain open, STOP semantics require OWNER acceptance, and the 001–040 integrated fresh/upgrade/no-op/schema/leakage/runtime-role matrix is unproven. PR #49 remains foundation-only; PrivateMediaArtifact byte retention remains OFF. No controlled real-WhatsApp stage is authorized by this verification.

**Work performed in this pass:** source/PR/CI/deployment review and this documentation snapshot only. No application code, tests, migrations, schema/leakage audit, production DB, or WAHA action was run. **REAL WAHA ACTIONS: NONE.**

**Highest-value next engineering step:** produce one dedicated integration candidate that reconciles #48/#50/#49/#60 migrations 034–040 and combines #60 runtime-role/service allowlists with #62's target/seed/libpq/sequence preflights, while fixing the two remaining P0 authority races and recording Fabian's STOP decision before any release claim.


---

## Fresh engineering verification — 2026-11-05 03:18 WAT (2026-11-05 02:18 UTC)

This supersedes the 2026-11-05 00:23 WAT snapshot below. I re-fetched main, all ten open PRs and their review threads, exact-head Actions associations, workflow YAML, migration directories on the feature branches, main deployment files, and the current #60/#62 deployment candidates. This is a verification/documentation update only: no application code, test, migration, production database, or WAHA action was changed or run in this pass.

### Main and current workflow

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (2026-09-08 11:09:59 UTC); no later main commit was found. The live branch endpoint still reports `protected=false`. Never push implementation to main; independent review and explicit human authorization remain mandatory.
- Main still has migrations **001–033** only. Its `.github/workflows/tests.yml` applies the lexical migration glob and runs pytest with the 57% coverage floor; it does not yet contain #61's migration-sequence preflight or #55's DB-leakage gate, nor #62's schema-audit step.
- Latest exact-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. No newer main-branch run was found.
- Main `docker-compose.yml` still mounts the entire `.env.production` into **postgres, api, waha, and migrate**. The current #60 branch has explicit service environment allowlists and a restricted runtime DB role; #62 still has the broad env-file configuration. Those two deployment candidates must be reconciled, not merged in either order independently.

### Roadmap freshness correction against current main

- The original roadmap body below was last audited on 2026-09-08 at `0034587`. Its Phase 1 table still says delete, search, provenance, and direct matching tests are missing. Those statements are now stale: PR #47 is merged in current main `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; main contains migration 033, Identity Registry source/entity_type/deleted_at fields, tombstone delete, get-by-key, search, admin GET/DELETE routes, and 14 direct service regression tests. The current #50 work is a follow-up for hardcoded-fallback/tombstone consistency and truthful legacy provenance, not the original missing-CRUD slice.
- The original release checklist's 2026-09-08 `[x]` mechanical-gate snapshot is also historical, not current release proof. #60 has reopened P0 consent/approval/policy-expiry races, and the #60/#62 deployment-role/secret-boundary integration remains unproven. The NOT TEST READY decision below is based on current branch code and exact-head evidence, not the old checked boxes.

### Exact-head CI evidence and its limits

- **#60 current head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`** — [Tests 41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) succeeded: **955 passed, 1 warning, 76.53% coverage**. The job log confirms migrations **001–033 + 038–040** only. It did not apply 034–037, run the schema audit, or run the DB-leakage audit. Its workflow is still the older workflow variant without the migration preflight. The #60 source now includes the exact ScheduledAction worker-row lock and its two-session mock-transport regression; that closes that specific race only.
- **#62 current head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`** — [Tests 41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) succeeded: **864 passed, 1 warning, 76.01% coverage**. Its job confirms migration-sequence preflight, migrations **001–033**, ORM schema audit passed, and DB-leakage audit passed. It does not contain migrations 034–040 and its Compose file still injects `.env.production` into postgres/api/waha/migrate.
- **#50 current head `0a2b38c0ce72b3c4a8fdd49490be504facb34bac`** — [Tests 41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) succeeded: **828 passed, 1 warning, 76.52% coverage**. Its job applies **001–033 + 035** only; this is not the integrated migration chain.
- **#61 current head `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`** — [Tests 40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded: **809 passed, 1 warning, 76.01% coverage**. The sequence preflight passes and its database job applies **001–033** only.
- **#57 current head `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba`** — [Tests 40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) succeeded: **811 passed, 76.01% coverage**; migrations 001–033 only.
- **#63 current head `13fad868affe01d6069f4288481f8cd8dd341c62`** — [Tests 41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded: **803 passed, 76.08% coverage**; migrations 001–033 only.
- **#55 current head `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c`** — [Tests 41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) succeeded; this PR carries the disposable-database leakage gate.
- **#48 current head `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`** — [Tests 40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) succeeded; its branch adds migration 034.
- **#49 current head `bcd0033e024b177561b8afd41589afe1897ba4de`** — [Tests 39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded; its branch adds migrations 036–037. The library remains foundation-only, not live producer/selection/dashboard integration.
- **#59 before this documentation refresh** was `d7af008542005f41a63a974e53d3572c5aa04c6c`; no Tests run is associated with that exact docs head. Parent run [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) passed 797 tests at 76.01% on `bf6e4975d304744147d0306123176004f4d605ce`, applying 001–033 only. This documentation update is marked `[skip ci]`; it has no test result of its own.

### Current open PRs — exact heads and live review-thread counts

| PR | Exact head | Unresolved / total threads | Current disposition |
|---|---|---:|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 | No open inline blocker; still needs integrated migration proof and independent approval |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 | Foundation only; no live producer/selection/dashboard integration |
| [#50 Identity Registry lifecycle fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 12 / 12 | Current identity fallback and provenance decisions remain open |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 (outdated) | No active current-diff thread; independent review still required |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 | Current review thread remains open |
| [#59 verification docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `d7af008542005f41a63a974e53d3572c5aa04c6c` before this update | 3 / 3 | Documentation-only refresh; this commit does not resolve review threads |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9a1865cad05114770fe4c8ffeae3b12eed8b34ca` | 19 / 19 | Exact-head CI green, but P0 authority and deployment integration remain blocked |
| [#61 migration-sequence integrity gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 | Useful preflight; exact branch CI is not integrated release proof |
| [#62 deployment seed/migration preflight](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 7 / 7 | Cross-PR runtime-role and service-secret boundary remains unresolved |
| [#63 conversation observability audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 (outdated) | No active current-diff thread; independent review still required |

### Migration and deployment integration — blocking

- The feature branches allocate migration numbers in order: **#48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040**. These numbers are unique/contiguous across the separate branch trees, but no one feature branch contains the full chain. #60's green run proves only 001–033 + 038–040; #50's run proves only 001–033 + 035. The #61 preflight is designed to reject a gap and will correctly reject #60 in isolation.
- Required integrated candidate: include all migrations 034–040 in the stated order; run fresh 001–040; run installed 033→040 upgrade; run the migration runner a second time and prove checksum/no-op stability; run ORM schema audit and zero-leakage audit; then prove runtime-role privileges and rendered service-environment isolation on disposable PostgreSQL. No current run proves this complete matrix.
- #60's deployment candidate provides explicit postgres/API/WAHA/migrate environment allowlists, passes only the restricted runtime URL to API, keeps migration-owner credentials in migrate, and provisions/verifies `zina_runtime`. Its current runner still lacks #62's database-target preflight, local-seed opt-in guard, libpq target sanitization, and migration-sequence preflight; it applies every seed file unconditionally.
- #62's runner adds target validation, local-seed opt-in, libpq environment sanitization, migration-sequence preflight, schema audit, and its workflow includes the leakage audit. But its current Compose file still mounts `.env.production` into postgres/API/WAHA/migrate and it does not invoke #60's restricted-runtime-role provisioner. Merging either branch after the other as-is would regress the other branch's security controls. Consolidate them into one reviewed candidate; do not merge in either order independently.

### P0 and architectural blockers still open

1. **Exact OWNER approval reservation and lock order (#60).** Approval is currently consumed after a successful WAHA call; on an ambiguous send it can remain `approved`, and OWNER `requeue()` can permit a second attempt for a deferred/uncertain row. Before moving consumption to the final pre-send boundary, unify worker and OWNER approval-mutation lock order as queue → approval; the current OWNER approval path can acquire approval before queue, creating a deadlock cycle if the worker holds queue first. Reserve the exact approval with a conditional database-clock update bound to approval ID, queue ID, inbound ID, exact recipient and payload digest; retain consumption on uncertain transport outcomes.
2. **Contact-policy expiry (#60).** Preserve the authority source/policy ID selected at initial authorization and revalidate that same policy after all final consent/STOP/safety/window locks using PostgreSQL `clock_timestamp()`. An expired/missing/disabled policy that granted authority must deny; it must not become “no quiet-hours restriction.”
3. **STOP/opt-out semantics (#60).** Decide whether terminal opt-out applies contact-wide across all current WhatsApp identifiers or only to one exact chat ID, and define its linearization against a worker already entering the final transport boundary. The conservative send posture remains fail closed until the rule and two-session regressions are accepted.
4. **Identity Registry (#50).** Registry-read exceptions now fail closed and have exact-head tests, but 12 current-diff threads remain. Open decisions include whether generic introduction text should omit project claims or gate every named registry fact, whether unknown legacy provenance remains NULL pending OWNER attestation (do not infer it from `updated_at = created_at`), and the current sibling fallback checks that can still mention Fabian when the `fabian` key is unavailable.
5. **Deployment role/secret boundary (#60/#62).** The API must not receive migration-owner credentials; WAHA and PostgreSQL must not receive unrelated API/admin/provider secrets. Runtime role provisioning and target/seed/migration preflight must coexist in one candidate with a documented credential provisioning/rotation procedure.

### Highest-value next safe engineering step

Do not start outbound-library integration or downstream roadmap phases while the P0 authority fence and migration/deployment integration remain unresolved. The next code candidate should be a reviewed #60/#62 integration branch that first resolves the common queue→approval lock contract and final policy revalidation, then combines the deployment runner/Compose controls without losing either side's protections. Keep every transport test on a mock WAHA client and every database test on disposable PostgreSQL.

**Release state: NOT TEST READY.** No exact integrated 001–040 fresh/upgrade/no-op/schema/leakage/runtime-role proof exists; P0 final authority/STOP decisions and blocking review threads remain. Controlled real-WhatsApp stages have not started. **REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering verification — 2026-11-05 00:23 WAT (2026-11-04 23:23 UTC)

This supersedes the 22:15 WAT snapshot below. It records fresh GitHub state and one additional deployment-isolation review finding. It is not a code fix, approval, merge, or release authorization.

### Main, workflow, and current repository state

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC); the fresh branch and commit queries found no later main commit. Main still contains migrations **001–033** only.
- Main's `.github/workflows/tests.yml` still applies the lexical `bot_core/migrations/*.sql` glob and runs pytest with a 57% coverage floor. The migration-sequence preflight from #61 and schema/DB-leakage audit from #55 are not on main.
- The live `main` branch object reports `protected=false`. Do not push or merge implementation to main; independent human review and explicit authorization remain mandatory.
- The latest overall Tests run is [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978), successful on exact PR #60 head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`: **955 passed, 1 warning, 76.53% coverage**. Its disposable PostgreSQL step applied 001–033 and 038–040 only. It did not apply 034–037, validate integrated 001–040, prove installed 033→040 upgrade/second-run checksum no-op, or run the integrated schema/leakage audits.
- The latest docs PR #59 head is `a3eeb67fbe6f11bca7959d3e2fd8b5b0046d57d5`; no Tests run is associated with that exact head. Parent run [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) passed 797 tests at 76.01% on its parent SHA and applied 001–033 only.

### Open PR inventory — exact heads and current unresolved inline-thread counts

| PR | Exact head | Unresolved threads | Latest exact-head Tests evidence |
|---|---|---:|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 total | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 total | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 4 / 12 total (4 current-diff, 3 outdated) | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 total (outdated) | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 total (outdated) | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success |
| [#59 verification docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `a3eeb67fbe6f11bca7959d3e2fd8b5b0046d57d5` | 3 / 3 total | No exact-head run; docs commits use `[skip ci]` |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9a1865cad05114770fe4c8ffeae3b12eed8b34ca` | 19 / 19 total (10 current-diff, 9 outdated) | Exact-head [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) success |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 7 / 7 total (4 current-diff, 3 outdated) | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 total (outdated) | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success |

### P0 — exact approval can be replayed after an ambiguous send

- Rechecked source on #60's exact head. The worker calls `consume_approval()` only in the WAHA-success branch. An ambiguous `WahaClientError` instead marks the queue row deferred/uncertain while leaving its approval `approved`.
- `OwnerOutboundApprovalService.requeue()` accepts an approved approval when its queue row is deferred/failed. OWNER requeue can therefore make a message eligible for a second WAHA attempt even though the first attempt may already have been accepted.
- Source-grounded finding: [PR #60 review discussion](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4472932656).
- Required: establish one deadlock-free queue→approval lock order for worker and OWNER mutations; reserve/consume the exact approval after every final fence and before transport using exact queue ID, inbound ID, recipient, payload digest, and database-side `expires_at > clock_timestamp()`; keep it consumed on success, ambiguous failure, and interrupted-send recovery; make requeue reject durable uncertain-delivery evidence. Add a PostgreSQL/mock-WAHA regression proving ambiguous send → consumed approval → denied requeue → zero second transport calls.
- The #60 ScheduledAction worker-side `FOR UPDATE` improvement is present on the exact head and its two-session regression passed in 41846567978. It does not close approval replay/expiry or policy-expiry.
- Contact-policy authority still needs revalidation by original policy ID after all blocking locks using `clock_timestamp()`; an expired/missing/disabled authority policy must deny, not become an allowed absence of a quiet-hours restriction. Exact approval reservation must likewise happen at the final boundary.
- OWNER decision still required on STOP linearization: a STOP committed before durable dispatch reservation blocks; after reservation it blocks later sends but cannot reliably retract the one network attempt already reserved/entering transport.
- Integrate #48's exact view-once source lock and success-only return audit with the same final worker. Private-media byte retention remains OFF.

### Deployment / migration integration

- Branch-local migration allocation is sequential: **034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60)**. The historical 034 collision is resolved by allocation only; main still ends at 033 and no integrated 001–040 candidate has passed fresh/upgrade/no-op/checksum/schema/leakage validation.
- #60's Compose candidate uses service-specific allowlists: Postgres receives bootstrap DB variables, API receives the restricted runtime DB URL, WAHA receives transport-only settings, and migrate receives owner/runtime-role bootstrap settings.
- #62's migration runner/workflow carries local-seed, target/libpq, migration-sequence, schema-audit, and DB-leakage checks, but its exact-head Compose still mounts the entire `.env.production` into Postgres, API, WAHA, and migrate. Thus neither deployment candidate subsumes the other.
- New source-grounded P1 review comment filed on #62: the Postgres service itself still receives all of `.env.production`, although it needs only `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`. The finding requests a three-variable allowlist plus a rendered-Compose regression proving no `DATABASE_URL*`, runtime-role, WAHA, admin, or provider secrets enter the database container: [PR #62 comment](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62#issuecomment-6645003499).
- Consolidate #60 and #62 before either merge: preserve all #62 preflights before any DDL/psql call, provision the restricted runtime role after migrations, and keep owner credentials only in migrate, runtime credentials only in API, WAHA settings only in WAHA, and bootstrap variables only in Postgres. Prove fresh 001–040, installed 033→040 upgrade with representative rows, second-run checksum/no-op, schema audit, zero leakage, and runtime-role privilege/ownership/membership tests on disposable PostgreSQL.

### Identity Registry and Message Library

- #50 still has three unresolved threads. The shared introduction currently asserts project/Datacube AU facts while its lifecycle guard checks only assistant/owner identity; recommended scope is an identity-only introduction, with project facts answered through Identity Registry. Legacy rows whose provenance cannot be proven should remain `legacy_unknown`; `updated_at = created_at` cannot recover rows touched by pre-upgrade reads. The human decision is whether unknown legacy provenance is acceptable or OWNER attestation is required.
- #49 has one unresolved thread about permanent set-key retirement after hard deletion. It remains a content-library foundation only: no live producer/selection/dashboard integration until P0 and migration reconciliation pass, and it never grants send authority.

### Verification limits and release decision

- This execution environment has `pytest` and GitHub access but no local `psql` or Docker executable. No local pytest, PostgreSQL migration, schema audit, or DB-leakage run was performed.
- No Actions run was triggered by this documentation update. Existing run links above are fetched GitHub evidence, not tests executed by this run.
- **NOT TEST READY.** No controlled-test stage is authorized. No production DB mutation, WAHA reconnection, real WhatsApp send, private-media retention activation, destructive cleanup, approval, or merge occurred. **REAL WAHA ACTIONS: NONE.**

---

## Fresh P0 release-gate delta — 2026-11-04 22:15 WAT

This supersedes the 18:24 UTC verification snapshot below. It records a newly confirmed exact-approval replay path on PR #60; no source fix or release authorization is implied.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only. Main's Tests workflow still applies the lexical migration glob and has a 57% coverage floor.
- PR #60 exact head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca` passed Tests run [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978): 955 passed, 1 warning, 76.53%. That run applied 001–033 plus 038–040 only; it does not prove integrated 001–040, installed 033→040 upgrade/re-run checksum no-op, schema audit, or DB-leakage audit.
- New P0: after an ambiguous WAHA error, the worker leaves the approval `approved` while the queue becomes `deferred`; OWNER `requeue()` accepts that state and can replay a message that WAHA may already have accepted. See [PR #60 review finding](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4472932656).
- Required before controlled testing: unify queue→approval lock ordering; consume the exact approval atomically after all final fences and before transport using exact queue/inbound/recipient/content binding and `clock_timestamp()`; keep it consumed on uncertain/interrupted outcomes; reject requeue for uncertain evidence; prove ambiguous-send → consumed approval → denied requeue → zero second mock-WAHA calls.
- Also unresolved: original contact-policy expiry must fail closed after final lock waits; exact approval expiry/revocation must be revalidated at the final reservation; OWNER must accept/revise the STOP-after-reservation in-flight-attempt contract; #48 view-once source locking/success-only return audit must be integrated with the same worker.
- Branch-local migration allocation is sequential (#48=034, #50=035, #49=036–037, #60=038–040), but no single candidate has proved fresh 001–040 plus installed 033→040 upgrade, second-run checksum/no-op, schema audit, and zero leakage.
- #60 runtime-role/service-environment changes and #62 target/seed/libpq/sequence preflights are not cumulative. Build and independently review one deployment candidate.
- Review inventory rechecked: #48 0 unresolved; #49 1; #50 3; #55 1 outdated; #57 1 outdated; #59 3; #60 19 (10 active/9 outdated); #61 0; #62 7 (4 active/3 outdated); #63 1 outdated. No open PR has an APPROVED review submission.

**NOT TEST READY.** No controlled WhatsApp stage is authorized. This documentation-only update did not run tests/migrations or mutate a database. Private-media retention stays OFF. **REAL WAHA ACTIONS: NONE.**

---

## Governance correction — 2026-11-04

Fresh follow-up to the 18:24 UTC overlay: the live `GET /branches/main` response reports `protected=false`, and the repository rulesets listing is empty. The separate classic branch-protection endpoint returns 403 through the current connection, but the branch object itself reports main as **not protected**. Treat this as an actual governance risk: do not merge or push implementation to main; require independent human review and explicit authorization regardless of the repository setting.

---
## Fresh engineering verification overlay — 2026-11-04 18:24 UTC

This supersedes the 16:21 UTC snapshot below. It is source-state evidence, not merge or release authorization.

### Main, CI, workflow, and governance

- `main` is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC). The exact-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08; treat it as historical, not current release evidence.
- Main contains SQL migrations **001–033 only**. Its `.github/workflows/tests.yml` still lexically applies `bot_core/migrations/*.sql` and runs pytest with a 57% coverage floor; PR #61's contiguous-sequence preflight and PR #55's post-test schema/DB-leakage audit are not on main.
- Main `docker-compose.yml` still mounts `.env.production` wholesale into API, WAHA, and migration services. PR #60 has a restricted runtime DB role and service-specific environment allowlists; PR #62 has target/seed/libpq/sequence preflights but still has broad env-file injection. These are separate branches and must be reconciled in one cumulative deployment candidate.
- Rulesets returned empty and the branch-protection endpoint returned 403 in the prior verification; current protection state remains **unverified**. Do not infer it from the old baseline.
- All ten open PRs were re-fetched. Review submissions remain `COMMENTED` (or absent); **no open PR has an APPROVED review submission**. Green CI and author comments are not independent approval.

### Open PRs — exact current heads and review-thread state

Counts are unresolved inline threads, shown as active / outdated (total historical threads).

| PR | Exact head | Unresolved | Latest exact-head Tests evidence |
|---|---|---:|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 0 (15) | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 0 (80) | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 3 / 0 (11) | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 0 / 1 (1) | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 0 / 1 (1) | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success |
| [#59 verification docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `8b14340c98c658f7175fbe58135c645cf4ebbaef` before this docs-only update | 1 / 2 (3) | No run for this exact head; parent [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) succeeded |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9a1865cad05114770fe4c8ffeae3b12eed8b34ca` | 10 / 9 (19) | Exact-head [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) success |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 (0) | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 4 / 3 (7) | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 0 / 1 (1) | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success |

- PR #60 exact-head run [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) completed 2026-11-04 14:23 UTC: **955 passed, 1 warning, 76.53% coverage**. Its disposable DB applied 001–033 and 038–040 only. It did not apply 034–037, prove integrated 001–040, exercise installed 033→040 upgrade/second-run checksum no-op, or run the integrated ORM schema and DB-leakage audits.
- PR #59's latest exact-head commit is documentation-only and has no associated run. Parent run [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) passed 797 tests at 76.01%, applying 001–033 only. This overlay is also documentation-only and marked `[skip ci]`; it does not claim tests.

### P0 outbound/ingress findings — release gate remains blocked

- **Verified improvement on #60:** commit [9a1865c](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/9a1865cad05114770fe4c8ffeae3b12eed8b34ca) adds `FOR UPDATE` + `populate_existing=True` to the exact ScheduledAction binding read after the outbound-queue lock. The action lock is held through the single transport attempt and durable outcome commit; OWNER mutations retain queue → action ordering. The exact-head two-session PostgreSQL/mock-WAHA regression passed in run 41846567978.
- **Newly re-confirmed P0 — contact-policy expiry can become permission.** On exact #60 head `9a1865c`, `authorize()` selects a policy using a timestamp captured before the policy-row lock wait. Later, after consent/safety/STOP fences, `check_contact_delivery_window()` filters expired policies out and treats no row as an allowed absence of a quiet-hours restriction. If the original authority was that contact policy, expiry can therefore be reinterpreted as permission. The exact-head source finding was filed at [review comment](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4470922938) at 17:26 UTC. Preserve the original authority type and policy ID; revalidate enabled/disabled/expiry/category with PostgreSQL `clock_timestamp()` after all blocking locks; if the policy supplied authority and is now missing, disabled, or expired, deny. Add a two-session expiry-during-final-fence regression with zero mock-WAHA calls.
- **P0 — exact one-use OWNER approval is not reserved at the final boundary.** Current consumption follows WAHA success. An approval may expire or be revoked while later consent/safety/STOP/window locks wait. Reserve/revalidate the exact approval after those fences, binding queue ID, inbound ID, recipient, payload digest, and DB-side expiry. First establish a deadlock-free global order: the worker holds queue → approval, while OWNER approval mutations currently lock approval → queue. Do not merely add `FOR UPDATE` to the worker approval read.
- **P1 — post-acceptance approval lock cycle:** the worker keeps the queue lock through WAHA and then updates the approval, while OWNER approval mutation takes approval before queue. A concurrent edit/reject can deadlock after WAHA accepts, leaving a stale `sending` row and losing the durable sent/approval reconciliation. The source-grounded finding is [here](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6635969882). Require one lock order and a two-session mock-WAHA regression that blocks at post-acceptance reconciliation.
- **OWNER decision — STOP linearization:** a STOP receipt committed before the final dispatch-reservation boundary must block. A STOP committed after reservation blocks later sends but cannot reliably retract the one network attempt already reserved/entering transport. This is an explicit in-flight-attempt contract, not a race removable by another read. Fabian must accept this boundary or require a redesigned reservation/state machine before controlled testing.
- Consent expiry and the ScheduledAction row-lock improvements have exact-head regression evidence in run 41846567978. This does not clear the policy-expiry or approval-reservation findings, nor the STOP decision.
- Integrate PR #48's exact view-once source lock and success-only return audit into the same final worker before considering the cumulative P0 path complete. PR #48 remains metadata-only; private-media byte retention stays OFF.

### Migration, deployment, and product integration

- Branch-local migration allocation is now sequential: **034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60)**. The historical 034 collision is resolved by allocation, but main still ends at 033 and no integrated candidate has proven the full chain.
- Required disposable PostgreSQL proof: fresh 001–040; installed 033→040 upgrade with representative existing rows; second-run checksum/no-op; combined ORM schema audit; zero DB leakage; and runtime-role privilege/ownership/membership verification. No production DB mutation is authorized.
- #60's runtime-role and per-service environment boundary is not yet combined with #62's pre-DDL database-target, local-seed, libpq, and sequence preflights. #62's current Compose still injects broad `.env.production` into API/WAHA/migrate. Build one cumulative deployment candidate; do not merge either branch independently and assume composition.
- #50 still has three active unresolved threads. Recommended architecture: keep the generic introduction identity-only rather than claiming project/Datacube AU facts unless every such fact is registry-governed; treat uncertain pre-upgrade defaults as `legacy_unknown` unless immutable evidence or explicit OWNER attestation proves provenance. Do not infer historical provenance from `updated_at = created_at`.
- #49 remains a content-library foundation only: no live producer/selection/dashboard integration until P0 and migration reconciliation pass. The library defines what may be said, never whether a send is authorized.

### Release decision

**NOT TEST READY.** No controlled-test stage is authorized. Do not connect/reconnect production WAHA, send real WhatsApp messages, mutate production DB, activate private-media retention, or perform destructive cleanup. The future controlled sequence remains OWNER self-DM text → commands → media/view-once → one explicitly approved external contact, only after every release gate and explicit authorization pass.

**REAL WAHA ACTIONS: NONE.**

---
## Fresh release-gate verification overlay — 2026-11-04 16:21 UTC

This supersedes the 14:23 UTC snapshot below. It is evidence only, not release authorization.

### Mechanical evidence

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last main commit is 2026-09-08. Main workflow remains lexical migrations + pytest at 57%; migration-sequence preflight (#61) and DB-leakage audit (#55) are not on main.
- Latest Tests run [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) passed on exact #60 head `9a1865c`: **955 passed, 1 warning, 76.53% coverage**. It applied 001–033 and 038–040 only; no 034–037, integrated 001–040, installed 033→040/no-op/checksum proof, schema audit, or DB-leakage audit.
- Latest prior green run [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298) passed on #59 head `bf6e497`: 797 passed, 76.01%; migrations 001–033 only.
- All ten open PRs were re-fetched. Unresolved inline threads (active / outdated): #48 0 (0/0; 15 total), #49 1 (1/0; 80 total), #50 3 (3/0; 11 total), #55 1 (0/1), #57 1 (0/1), #59 3 (1/2), #60 19 (10/9), #61 0, #62 7 (4/3), #63 1 (0/1). No PR has an APPROVED review submission.
- GitHub rulesets returned an empty list; the branch-protection endpoint returned 403. Do not claim current main branch protection either way.

### P0 delta and remaining blockers

- #60 commit [9a1865c](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/9a1865cad05114770fe4c8ffeae3b12eed8b34ca) adds worker-side exact ScheduledAction `FOR UPDATE` + `populate_existing=True` after the queue lock and a two-session PostgreSQL/mock-WAHA regression. Exact-head run 41846567978 passed it.
- Still blocking: contact-policy expiry revalidation at the final fence; exact one-use OWNER approval reservation after all blocking checks with a deadlock-free queue/approval lock order; explicit OWNER acceptance of the STOP post-reservation in-flight attempt contract; and cumulative #48 exact-source view-once locking/success-only return audit in the single worker.
- No real WAHA send, production reconnect, or production DB operation was performed.

- Additional P1 found on exact #60 head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`: the worker holds the queue row through WAHA and then updates the approval row in `consume_approval()`, while OWNER approval mutations take the approval advisory/row lock before locking the queue. An overlapping OWNER edit/reject can deadlock after WAHA accepts the send, leaving only a stale `sending` row for later uncertainty quarantine. The five-minute quarantine prevents automatic replay but does not preserve the sent/approval audit outcome. See [source-grounded review comment](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6635969882). A single queue/approval lock order and a two-session post-acceptance race regression are required; no code/test was changed/run for this finding.
### Migration/deployment gate — NOT PASSED

- Branch-local allocation is sequential: #48=034, #50=035, #49=036–037, #60=038–040. The former 034 collision is resolved in allocation, but main still has 001–033 and no integrated candidate has proved fresh 001–040 plus installed 033→040 upgrade/no-op/checksum.
- #60's restricted runtime role/service environment allowlists are not combined with #62's pre-DDL target, seed, libpq, and sequence preflights. #62 still mounts broad `.env.production` into API/WAHA/migrate. One candidate must preserve every preflight before DDL, pass owner credentials only to migrate, restricted runtime URL only to API, and explicit WAHA settings only to WAHA.
- #55's schema/leakage evidence and #62's schema/leakage evidence cover only 001–033, not the combined feature chain.

### Identity/content decisions

- #50: keep the generic introduction identity-only (recommended) or gate every project/Datacube AU fact it names; preserve uncertain pre-upgrade defaults as `legacy_unknown` unless immutable evidence or explicit OWNER attestation proves provenance. Do not use `updated_at = created_at` as historical proof.
- #49 is only the content-library foundation; no live selection/producer/dashboard integration until P0 and migration gates pass.
- #48 remains metadata-only. Private-media retention remains OFF.

**NOT TEST READY.** No controlled test stage is authorized. The integrated migration, deployment, P0 authority, independent-review, and mobile CRUD/observability gates remain open.

**REAL WAHA ACTIONS: NONE.**

---

## Fresh release-gate verification overlay — 2026-11-04 14:19 WAT

This supersedes the 10:31 WAT overlay below. It is evidence only, not release authorization.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08). The main workflow still applies migrations 001–033 and runs pytest at the 57% floor; sequence preflight (#61) and DB-leakage audit (#55) are not on main.
- Latest visible Tests run is [41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463), green on PR #60 parent `3496ff1` (952 passed, 76.51%). It applies 001–033 + 038–040 only. Current #60 head `77f229c` has no exact-head run; no local tests/migrations were run for it.
- Open PR heads/review threads were re-fetched: #48 `3acacbfe` (15 unresolved), #49 `bcd0033e` (80), #50 `0a2b38c0` (11), #55 `b5cb5ff` (1), #57 `d831ce4` (1), #59 `5749189c` (3 before this docs update), #60 `77f229c` (19 after the new inline review), #61 `8a1c1dbf` (0), #62 `a8d032de` (7), #63 `13fad868` (1). No independent APPROVED review is present.
- Migration allocation is sequential but unintegrated: #48=034, #50=035, #49=036–037, #60=038–040. No fresh 001–040 / installed 033→040 / second-run no-op / combined schema and leakage proof exists.
- Deployment integration is blocked: #60's runtime-role/service env boundary is not combined with #62's pre-DDL database-target, seed, libpq and sequence preflights; #62 still exposes broad `.env.production` to API/WAHA/migrate.
- New exact-head #60 P0 review: policy expiry can be converted to permission because the final quiet-hours query treats an expired/missing policy as an allowed absence, even when that policy supplied authority. Revalidate the same policy authority and expiry with PostgreSQL `clock_timestamp()` after all locks; deny if expired. Inline review is filed on [PR #60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60).
- Other #60 P0 blockers remain: exact approval one-use reservation and deadlock-free queue→approval lock order; worker-side ScheduledAction `FOR UPDATE` after queue lock; explicit OWNER STOP linearization decision; cumulative #48 view-once source lock + success-only return audit. Consent expiry, missing source ID, contact-wide STOP history and runtime role have parent-head test evidence, not current-head proof.
- #50 still needs the identity-only introduction decision and a conservative legacy provenance rule; do not infer pre-upgrade provenance from `updated_at = created_at`.
- Branch protection could not be rechecked through the current GitHub connection (403). No main write was attempted.

**NOT TEST READY.** No controlled stage is authorized. Retention stays OFF. No production DB mutation, WAHA reconnection, real WhatsApp send, or destructive cleanup occurred.

**REAL WAHA ACTIONS: NONE.**

---

## Fresh release-gate verification overlay — 2026-11-04 10:31 WAT

This overlay supersedes the 2026-11-04 06:23 WAT snapshot below. It is not release authorization.

### Mechanical evidence

- Main: `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last commit 2026-09-08. Exact-main Tests [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08 only. Treat as historical.
- Main workflow still runs lexical migration glob + pytest at 57%; PR #61's contiguous migration preflight and PR #55's schema/leakage gates are not on main.
- Latest prior green P0 run: #60 parent `3496ff19b72609553ba51daebfdf0f0472298908`, run [41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463): 952 passed, 1 warning, 76.51%. It applied 001–033 and 038–040 only; it did not include 034–037 or run schema/leakage audits.
- New #60 head [77f229c](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/77f229c1a67e6049ea54e2a0803255c915ad3a15) adds row-locked OWNER ScheduledAction mutations and two two-session PostgreSQL regressions. The commit uses `[skip ci]`; there is no exact-head run, and no test/migration/audit result is claimed for it.
- No open PR has an APPROVED review. All ten open PRs remain unmerged; #60 and #62 remain draft.

### Integrated migration/deployment gate — NOT PASSED

- Main has migrations 001–033. Feature branches allocate #48=034, #50=035, #49=036–037, #60=038–040.
- No integrated candidate has passed fresh 001–040, installed 033→040 upgrade with existing rows, second-run checksum/no-op, combined ORM schema audit, zero-leakage audit, and runtime-role privilege/ownership verification.
- #60's restricted runtime role and service env allowlists are not combined with #62's database-target/seed/libpq/sequence preflights. #62 still mounts broad `.env.production` into API/WAHA/migrate. Neither merge order is safe.

### P0 final-dispatch gate — NOT PASSED

- #60 still needs atomic one-use OWNER approval reservation/revalidation after all blocking locks, with exact queue/recipient/content binding and expiry evaluated at the final fence. Preserve one lock order; uncertain transport outcome must not permit replay.
- OWNER decision is required for STOP after the durable dispatch-reservation boundary: pre-reservation STOP blocks; post-reservation STOP blocks later sends but cannot guarantee cancellation of the already-reserved attempt.
- #60's ScheduledAction race fix is committed: OWNER mutations now lock/refresh the action row before status validation, while the worker retains queue→action ordering. Exact-head tests are still pending.
- Integrate #48's exact-source view-once worker lock and success-only return audit into the same worker. Retention remains OFF.
- Contact consent, opt-out, quiet hours, frequency, expiry, media-bound authorization, and worker fence must remain cumulative; no real WAHA calls in engineering.

### Product/review gate — NOT PASSED

- #48 metadata-only; #49 library foundation only; #50 identity/provenance review decisions unresolved; #55/#61/#62 CI/deployment hardening not merged; #63 observability not merged.
- Mobile CRUD/observability, fully integrated single-domain authorities, and controlled-test sign-off remain incomplete.
- Independent review remains required; passing branch CI or this checklist overlay is not approval.

### Release decision

**NOT TEST READY.** Stage A is not authorized. Do not connect/reconnect production WAHA, send real messages, mutate production DB, activate private-media retention, or perform destructive cleanup. Controlled sequence remains owner self-DM text → commands → media/view-once → one explicitly approved external contact, but execution requires a later explicit authorization after all gates pass.

**REAL WAHA ACTIONS: NONE.**

---

## Fresh exact-head verification overlay — 2026-11-04

This source-state overlay supersedes the 2026-11-03 22:24 WAT snapshot below. It is not a release approval. Main has not moved since 2026-09-08; the feature branches are still separate PRs.

### Main, workflow, and governance

- `main` is `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (2026-09-08 11:09:59 UTC); the branch API currently reports `protected=false`.
- Main's `.github/workflows/tests.yml` still applies the lexical migration glob and runs pytest at the 57% coverage floor. It does not yet include PR #61's contiguous-migration preflight or PR #55's post-test DB-leakage audit.
- No open PR has an `APPROVED` review submission. All recorded review submissions are `COMMENTED`; comments and passing CI are not independent approval.

### Current open PR inventory — exact heads

| PR | Exact head | Active unresolved / outdated unresolved threads | Current significance |
|---|---|---:|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 0 (15 resolved) | Metadata observation/return wiring; no private-byte retention. |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 0 | Foundation only; no live producer/selector/dashboard integration. Active finding: retired set keys must not be reused after hard deletion. |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 3 / 0 | Introduction/tombstone consistency, fail-closed registry errors, and trustworthy legacy provenance remain open. |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 0 / 1 | Exact-head Tests [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314): 816 passed, 76.01%; schema and DB-leakage audits passed on 001–033. |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 0 / 1 | One outdated review thread; no merge. |
| [#59 roadmap/checklist refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | self-referential docs head (see live PR) | 1 / 2 | Documentation-only verification overlay; its own commit hash is intentionally omitted because each refresh advances this PR's head. |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `3496ff19b72609553ba51daebfdf0f0472298908` | 9 / 9 | Exact-head [Tests run 41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463) succeeded: 952 passed, 1 warning, 76.51%; alias-wide rate/backlog and media-aware duplicate fences now have exact-head CI evidence. The run applied 001–033 and 038–040 only; no schema/leakage audit. |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 | Exact-head run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded on 001–033 only; it does not validate combined feature migrations. |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 4 / 3 | Exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073): 864 passed, 76.01%, schema audit and DB-leakage audit passed on 001–033. Four active review threads remain, including the real #60 deployment integration conflict. |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 0 / 1 | Observability-only change; one outdated thread. |

### Migration allocation and deployment reconciliation

Current branch allocation is sequential, not yet integrated:

1. #48 — 034 `private_media_artifact_source_identity`
2. #50 — 035 `identity_registry_default_backfill`
3. #49 — 036 `outbound_message_library`, 037 `outbound_message_set_key_registry`
4. #60 — 038–040 contact consent and sender identity/contact evidence

The former 034 collision has been reallocated, but each feature branch still targets main independently. PR #61's guard will reject dependent branches that omit predecessors. No candidate has run fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum, combined schema audit, and zero-leakage validation.

Deployment changes remain non-cumulative: #60 has explicit Compose environment allowlists and a restricted API runtime DB role, but lacks #62's database-target, seed-policy, libpq, and contiguous-sequence preflights. #62 has those preflights, but its Compose still mounts broad `.env.production` into API/WAHA/migrate and does not provision #60's restricted runtime role. A single candidate must preserve all preflight checks before DDL, grant owner credentials only to migrate, pass only the restricted runtime URL to API, and pass only explicit WAHA variables to WAHA.

### P0 safety delta and remaining blockers

- On #60, the worker now calls a shared contact delivery-window guard after final consent revalidation and the pending-STOP boundary, immediately before transport. It applies to exact one-use approvals and exact ScheduledAction bindings. The guard and OWNER policy upsert/disable share the exact-chat transaction advisory lock; active policy rows are locked with `FOR UPDATE`, closing the first-INSERT/missing-row race.
- The first exact-head run for the quiet-hours change exposed the policy upsert timestamp typing error. Commit f69fae4 adds explicit `timestamptz` casts. Exact-head [Tests run 41739953061](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41739953061) succeeded: **948 passed, 1 warning, 76.50% coverage**. Its disposable DB applied 001–033 and 038–040 only; 034–037 were absent. This run did not perform schema or DB-leakage audits, so neither is claimed.
- Commit 8141d0e adds Contact-wide alias rate/backlog aggregation and media duplicate identity using the authority payload digest across aliases; commit 3496ff1 preserves normalized text-only duplicate semantics and updates worker safety fakes for the new `contact_id` argument. Exact-head [Tests run 41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463) succeeded: **952 passed, 1 warning, 76.51% coverage**. The run applied 001–033 and 038–040 only and did not run schema or DB-leakage audits. Parent run [41740867833](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41740867833) failed at the first worker test with a fake-signature `TypeError`; that test-double issue was corrected in 3496ff1.
- Source/test addressed on #60 (exact-head run 41741201463): missing stable transport-message-ID messages fail closed before routing/OWNER commands; consent-event UPDATE/DELETE/TRUNCATE are blocked; the API runtime role is distinct from migration owner, restricted to required privileges, and verified against both directions of role membership/SET ROLE. These remain branch-local and review threads are not cleared; #62 deployment preflight/Compose integration and combined 001–040 upgrade proof are still required.
- Still open on #60: final approval/policy expiry revalidation after all blocking locks, and explicit OWNER acceptance of the STOP reservation/linearization point.
- **Dispatch-reservation implementation constraint — 2026-11-04 02:21 WAT:** exact-head review of #60 confirms the worker locks the `outbound_queue` row before its final authority check, while `OwnerOutboundApprovalService` takes the per-approval advisory lock before locking the approval and queue rows. Do not add an approval `FOR UPDATE` to the current worker order: queue→approval can deadlock with OWNER approval→queue. The final exact-approval fence needs a one-use atomic reservation (conditional `UPDATE ... RETURNING`, matching approval ID, queue ID, inbound ID, exact recipient, exact content digest, approved status, and `expires_at > clock_timestamp()`) **after** all contact-consent, safety, STOP, and delivery-window waits. First establish one lock order across worker and OWNER mutation paths; reserve/consume before transport, and on any uncertain WAHA outcome keep the approval consumed and queue quarantined—never replay automatically. Contact-policy authority also needs a final locked revalidation that evaluates expiry with a fresh database clock after all waits; ScheduledAction authority needs the same exact locked action/queue/target/payload recheck.
- **ScheduledAction cancellation race — 2026-11-04 04:17 WAT:** on #60 exact head `3496ff19b72609553ba51daebfdf0f0472298908`, `_is_exact_scheduled_action_binding()` performs an unlocked status read and `ScheduledActionService.cancel()`, `pause()`, and `reschedule()` load with `session.get()` rather than a shared row lock. An OWNER cancellation can therefore commit after the worker observes `queued`/enabled but before WAHA, while the worker still sends. Added an exact-head inline review on the final worker recheck ([review comment](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4463201277)): establish one queue/action lock order, serialize the worker's final action check and OWNER mutations, and prove both orderings with two-session PostgreSQL/mock-WAHA tests. No source fix or test is claimed; #60 now has 9 active / 9 outdated unresolved threads and remains draft.
- **View-once cumulative worker fence:** #48's exact-source lock and success-only `returned_to_owner_at` transition are absent from #60's current worker. The integrated worker must lock the exact non-deleted `source_chat_id + source_message_id` before transport, stamp returned only after confirmed WAHA success, and preserve uncertain-send quarantine/no-retry. Keep one worker/dispatcher; do not merge either worker branch independently.
- **OWNER decision still required for STOP:** decide whether a STOP committed after a durable dispatch reservation but before/while the WAHA request enters is too late to cancel that one reserved attempt. A pre-reservation STOP must block; a post-reservation STOP must still block every later attempt. If Fabian requires even a post-reservation STOP to cancel the in-flight attempt, repeated reads cannot guarantee that contract and the queue/transport reservation protocol must be redesigned. Require a two-session regression for both event orderings.
- PR #50 still needs the human decision whether generic introductions may assert project/Datacube AU facts after registry tombstones, and a trustworthy legacy-default provenance rule. The `updated_at = created_at` heuristic cannot reconstruct rows already touched by pre-upgrade reads. Registry read failures must not fall back to stale identity assertions.
- PR #49 remains only a library foundation; do not integrate it into a producer before P0 and migration reconciliation. PR #48 remains metadata-only; private-media retention stays OFF.

### Release readiness

**NOT TEST READY. Stage A is not authorized.** No integrated migration candidate, exact-head full suite, combined schema/leakage/runtime-role proof, unresolved-review clearance, or controlled WhatsApp test exists. The controlled test plan is not yet approved for execution. No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, or destructive cleanup occurred. **REAL WAHA ACTIONS: NONE.**

---

## Exact-head CI follow-up — 2026-11-03 22:24 WAT

- PR #60 exact head `fb9693014579283566358f30d80fcc2cc5581795` passed Tests run [41721001922](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41721001922): **942 passed, 1 warning, 76.44% coverage**. The disposable database applied 001–033 and 038–040 only; 034–037 were absent, and this workflow did not run schema/leakage audits.
- The new exact OWNER approval quiet-hours regressions passed. ScheduledAction quiet-hours, alias-wide limits, final authority expiry, media duplicate identity, and STOP linearization remain open P0 gates.
- PR #55 exact-head run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) passed 816 tests / 76.01%; its branch applied 001–033 and passed schema + DB-leakage audits. The shadow-schema raw-table counting fix is present; its review thread is outdated but still unresolved.
- Migration allocation remains branch-local (#48=034, #50=035, #49=036–037, #60=038–040). No integrated fresh 001–040 or installed 033→040/no-op/checksum/schema/leakage/runtime-role proof exists.
- #60/#62 deployment controls remain non-cumulative; #62 still injects broad `.env.production` into Postgres/API/WAHA/migrate. No open PR has an APPROVED review.
- **NOT TEST READY. Stage A not authorized.** Private-media retention OFF. **REAL WAHA ACTIONS: NONE.**

---
## Fresh release-gate delta — 2026-11-03 22:17 WAT

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; exact-main Tests [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) is historical (2026-09-08). Main reports `protected=false`.
- Latest overall Tests run [41721001922](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41721001922) is **in progress** on #60 head `fb9693014579283566358f30d80fcc2cc5581795`; no result is claimed.
- #55 exact-head run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) passed **816 tests / 1 warning / 76.01% coverage**; migrations 001–033, ORM schema audit, and DB-leakage audit passed. This is not integrated 001–040 proof.
- #60 now checks active exact-chat quiet hours before exact one-use OWNER approval. The new regression run is pending; ScheduledAction quiet-hours, alias-wide limits, final authority expiry, media duplicate identity, and STOP linearization remain open.
- Branch-local migration allocation is #48=034, #50=035, #49=036–037, #60=038–040. No integrated fresh 001–040 / installed 033→040 / checksum-no-op / schema / leakage / runtime-role proof exists.
- #60/#62 deployment controls are not cumulative; #62 still injects broad `.env.production` into Postgres/API/WAHA/migrate. Keep both draft/open.
- Review state: no open PR has an APPROVED review; #60 has 10 active / 7 outdated unresolved threads, #62 4 / 3, #50 3 active, #49 1 active.
- **NOT TEST READY. Stage A not authorized.** Private-media retention OFF. **REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering delta — 2026-11-03 21:34 WAT

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest exact-main Tests run [34219252390 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) from 2026-09-08; branch currently reports `protected=false`.
- **Latest overall CI:** PR #55 head `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c`, run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314), succeeded: **816 passed, 1 warning, 76.01% coverage**; migrations 001–033, ORM schema audit, and post-test DB-leakage audit passed. No integrated 001–040 or installed-upgrade proof is implied.
- **PR #55:** raw leakage-table counts are now schema-qualified to `public`; a shadow-schema PostgreSQL regression was added in commit [b5cb5ff](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c). Its one review thread remains unresolved pending independent review and exact-head CI.
- **PR #60 P0:** head `56ddd10ca7f315937c3f597fd2175fafe610f5ed`; exact-head Tests run [41695211554 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41695211554), 939 passed / 76.42%, but only migrations 001–033 + 038–040. Seventeen unresolved review threads remain, including quiet-hours bypasses, approval/policy expiry at final dispatch, alias-wide rate/duplicate limits, media-aware duplicate identity, STOP linearization, and missing cumulative #48 view-once source locking. The consolidated review plan is [comment 6614706465](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6614706465).
- **Migration allocation:** #48=034, #50=035, #49=036–037, #60=038–040. No integrated fresh 001–040 or installed 033→040 upgrade proof exists.
- **Deployment:** #60 runtime-role/service allowlists and #62 target/seed/sequence preflights are not cumulative; #62 still exposes broad `.env.production` to API/WAHA/migrate. Neither merge order is safe.
- **Release:** NOT TEST READY; Stage A not authorized; private-media byte retention remains OFF. **REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering delta — 2026-11-03

This current release gate supersedes the older dated snapshots below. See the roadmap's 2026-11-03 engineering delta for exact open-PR heads and review counts.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest exact-main Tests run [34219252390 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) from 2026-09-08; branch currently reports `protected=false`.
- **Latest exact-head CI:** PR #60 head `56ddd10ca7f315937c3f597fd2175fafe610f5ed`, run [41695211554 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41695211554): **939 passed, 1 warning, 76.42% coverage**. Its workflow applies migrations 001–033 and 038–040 only, not 034–037.
- **P0 improvement:** contact consent expiry is now checked after mapping/Contact/consent locks and again after the final safety/STOP boundary immediately before the transport attempt. Both new PostgreSQL/mock-WAHA regressions passed. A separate asyncpg test-cleanup bug exposed by the first run was fixed; latest exact-head CI is green.
- **Still blocking:** #60 has 17 unresolved threads and remains draft. Quiet-hours bypasses, approval/policy expiry, alias-wide budgets, complete media duplicate identity, and STOP linearization remain open. #60's worker still lacks #48's view-once source lock/success-only return audit.
- **Migration allocation:** #48=034, #50=035, #49=036–037, #60=038–040. The old duplicate 034 is reconciled only across branch-local allocations; no integrated fresh 001–040 or installed 033→040 upgrade proof exists.
- **Deployment:** #60 runtime-role/service allowlists and #62 database-target/seed/sequence preflights are not cumulative. #62 still exposes broad `.env.production` to all services. #55 has one unresolved shadow-schema counting issue; #57 and #61 safeguards remain branch-local.
- **Evidence gaps:** no combined fresh/upgrade/checksum/no-op/schema/leakage/runtime-role proof; no independent approval of blocking reviews; no controlled WAHA test.
- **Human decisions:** STOP after final reservation but before WAHA-entry semantics; whether terminal opt-out is irreversible or has a separately defined OWNER re-consent path; introduction project-claim scope; legacy unknown-provenance policy.
- **Readiness:** **NOT TEST READY. Stage A is not authorized.** Private-media byte retention stays OFF. **REAL WAHA ACTIONS: NONE.**

---

## Current release gate — 2026-11-03 17:18 WAT

This is the current source-verified release status and supersedes the older dated snapshots and historical checkboxes below. See the roadmap's 17:18 WAT overlay for exact PR heads and review-thread inventory.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033; latest exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. Main reports `protected=false`.
- **Latest overall CI:** [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) was cancelled on older PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`. The current #60 head `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` has no exact-head run because its diagnostic-only workflow commit uses `[skip ci]`.
- **Migration allocation:** #48=034, #50=035, #49=036–037, #60=038–040. The old duplicate 034 is reconciled across branch names, but no integrated 001–040 fresh install or 033→040 upgrade has passed.
- **P0:** PR #60 still has 17 unresolved review threads, including quiet-hours bypasses for approval and ScheduledAction, alias-local rate/duplicate limits, incomplete media duplicate identity, expiry-after-lock races, and the STOP/WAHA-entry contract. Its worker also lacks #48's exact view-once source lock and success-only return audit.
- **Deployment:** #60's runtime-role/service allowlists and #62's pre-DDL target/seed/sequence guards are not cumulative. #62 still passes the broad `.env.production` file to all services; #60 lacks #62's preflights. Do not merge either independently.
- **Evidence gaps:** no exact-head Tests run for current #60; no combined fresh/upgrade/checksum/no-op/schema/leakage/runtime-role proof; no current integrated-candidate P0 matrix; no independent approval of the blocking reviews.
- **Human decisions:** accept or revise the STOP reservation boundary; confirm whether terminal opt-out is Contact-wide and irreversible; choose whether generic introductions may mention project claims; define how unverifiable legacy identity provenance is represented.
- **Readiness:** **NOT TEST READY. Stage A is not authorized.** Private-media retention stays OFF. No real WhatsApp send, production DB mutation, or production WAHA reconnection during unattended engineering.

---

## Fresh engineering delta — 2026-11-03 11:21 WAT

This snapshot supersedes the 08:24 WAT verification overlay. I re-fetched `main`, all ten open PRs and review threads, exact-head Tests associations, the main and PR #60 Tests workflow YAML, the four feature migration trees, and the #60/#62 Compose configurations.

### Main and CI

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC); no newer main commit was returned.
- Latest Tests run on exact `main`: [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), success on 2026-09-08. This is historical main evidence, not validation of the open feature branches.
- Latest overall Tests run: [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589), **cancelled** on PR #60's parent head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`. The run marked `test_runtime_role_cannot_mutate_or_disable_consent_history` failed at 86%, then the job was cancelled after an async-fixture faulthandler; no assertion traceback, final suite count, or coverage summary was captured. Current #60 head `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` only changes the test command to `-x --tb=long` / 30-second faulthandler and intentionally uses `[skip ci]`; it has no exact-head run.
- Main `.github/workflows/tests.yml` still applies the lexical migration glob and runs pytest at the 57% coverage floor. It does not include PR #61's sequence preflight, PR #55's schema/leakage audit, or the #62 deployment-target/seed checks. Main's migration runner still has no sequence preflight and runs all seed SQL files.

### All open PRs — exact heads, exact-head Tests, review threads

Counts are unresolved inline threads / total inline threads. A successful branch-local run is not a merge approval or integrated migration proof.

| PR | Exact head | Exact-head Tests | Unresolved / total threads |
|---|---|---|---:|
| #48 PrivateMediaArtifact wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 15 |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | 1 / 80 |
| #50 Identity Registry lifecycle/backfill | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) — 828 passed, 76.52% | 3 / 11 |
| #55 DB-leakage CI gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | 0 / 0 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 1 / 1 |
| #59 roadmap/checklist refresh | Current documentation branch; head advances with this snapshot | No exact-head run; documentation commits use `[skip ci]` | 3 / 3 |
| #60 contact-consent P0 | `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` | No exact-head run; latest prior run 41400297589 cancelled | 17 / 17 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 / 0 |
| #62 deployment/seed preflight integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) — 864 passed, 76.01% | 7 / 7 |
| #63 conversation observability | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) — 803 passed, 76.08% | 1 / 1 |

No open PR has an APPROVED review submission. In particular, #48 has zero unresolved inline threads but still has a cross-PR worker-integration blocker; its green branch run does not make it safe to merge independently.

### Migration and deployment reconciliation

Exact branch trees confirm the previous numbering collision is now resolved **only by branch-local allocation**:

- Main: 001–033.
- #48: 034 `private_media_artifact_source_identity`.
- #50: 035 `identity_registry_default_backfill`.
- #49: 036–037 Outbound Message Library.
- #60: 038–040 contact-consent / sender-identity / sender-contact evidence.

No single candidate has proven a fresh 001–040 chain, an installed 033→040 upgrade preserving existing data, second-run checksum/no-op behavior, ORM schema audit, and zero DB leakage together.

The #60/#62 deployment branches are not cumulative:
- #62 still mounts all of `.env.production` into Postgres, API, WAHA, and migrate. Postgres only needs `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`; API/WAHA do not need migration-owner credentials or unrelated provider/admin secrets.
- #60 has explicit service environment allowlists and a restricted non-owner API DB URL, but its runner does not include #62's database-target, local-seed, and migration-sequence preflights.
- Both branches modify the deployment runner, Compose file, workflow, and README. Neither merge order is safe. Preserve all pre-DDL guards and all service credential boundaries in one independently reviewed candidate; do not merge #60 or #62 separately.

### P0 and architecture blockers

1. **#60 is not dispatch-safe yet.** Current unresolved P0 findings include approval and ScheduledAction paths bypassing the shared quiet-hours guard; alias-local backlog/rate/duplicate budgets; approval, policy, and consent expiry not all revalidated after every final lock; media duplicate checks that omit locator/kind/MIME/filename; and the STOP receipt vs WAHA-entry linearization gap.
2. **OWNER view-once and contact-consent worker changes are not cumulative.** #48 locks the exact source row and marks return only after confirmed WAHA success. #60 contains the consent/STOP fence but lacks that source lock and success-only return audit. Integrate both into one worker and retain uncertain-send quarantine/no automatic retry.
3. **Runtime-role proof is incomplete.** The latest #60 run failed/cancelled without the original assertion traceback. Run the isolated runtime-role integration test only against the disposable CI PostgreSQL service after capacity is confirmed; do not infer a fix from permission-denial log lines.
4. **#62's environment leak remains a deployment blocker.** The Postgres/API/WAHA/migrate containers receive the whole production env file. Keep the existing source-grounded review finding open until service-specific allowlists and rendered-Compose regressions are present.
5. **#50 needs explicit architecture review.** Registry-read failures now return a non-assertive fallback, but three inline threads remain unresolved. Decide whether the generic introduction should mention only Zina/Fabian or also project claims. Do not infer historical `system_default` provenance from `updated_at = created_at`; unverifiable legacy rows should remain unknown unless immutable evidence or explicit OWNER attestation exists.
6. **#49 is foundation-only.** It has no live producer selection or dashboard integration. Do not connect it to external sending until P0 and integrated migration gates are satisfied.

### Release readiness and next step

- **NOT TEST READY. Stage A must not begin.**
- Private-media byte retention remains OFF.
- No integrated 001–040 fresh/upgrade/no-op/schema/leakage proof exists; no current exact-head Tests run exists for #59 or #60.
- Human decisions still required: whether a STOP committed after the final dispatch reservation but before the WAHA request must veto; whether terminal opt-out is reversible and what evidence is required for OWNER consent grants; whether the introduction copy includes project claims; and whether unknown legacy provenance is acceptable or requires OWNER attestation.
- Highest-value next engineering step: after the STOP contract is accepted, create one cumulative, independently reviewed worker/deployment candidate preserving #48 + #60 P0 fences and #55/#57/#61/#62 deployment gates, then prove the reconciled 001–040 fresh/upgrade/no-op/schema/leakage/runtime-role matrix on disposable PostgreSQL.

This update is documentation-only on PR #59. No application source or migration was changed; no Actions workflow, local test, migration, schema audit, or DB-leakage audit was run. No production DB mutation, WAHA reconnection, real WhatsApp send, private-media retention activation, approval, merge, or review-thread resolution occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

# Zina Release Checklist

## Fresh engineering delta — 2026-11-03 08:24 WAT

PR #60 now points to diagnostic-only workflow commit [`1f1c85a3a56924d098085a54f9cd90a5d26a2be2`](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/1f1c85a3a56924d098085a54f9cd90a5d26a2be2). The test command uses `-x --tb=long` and a 30-second faulthandler timeout so the first failing test's traceback is emitted before later async fixture setup. The commit uses `[skip ci]`; no new run or test is claimed. The latest run remains [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589), cancelled on parent head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` after the runtime-role test was marked FAILED at 86%; the log has no assertion traceback or final coverage summary. This diagnostic change is untested and does not clear the P0 consent, worker-integration, or deployment gates.

Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`. Migration allocation remains main 001–033, #48 034, #50 035, #49 036–037, #60 038–040. No combined fresh/upgrade 001–040, checksum/no-op, schema-audit, DB-leakage, and runtime-role proof exists. **NOT TEST READY; REAL WAHA ACTIONS: NONE.**

---

# Zina Release Checklist

## Fresh live verification delta — 2026-11-03 07:20 WAT

This delta supersedes only the cross-branch integration detail below; the 06:23 snapshot remains the source for the full PR inventory. Rechecked exact current PR heads, exact-head Tests associations, open review threads, main workflow YAML, deployment Compose files, migration tree, and the latest cancelled PR #60 job log. The PR #59 pre-update head was `106963b3165e2b6b61f72bc5c889f494d5bc91c5`. This is a documentation-only commit marked `[skip ci]`; no new Actions run, test, migration, schema audit, or DB-leakage audit is claimed.

- **Main remains** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033. The main Tests workflow still applies the lexical migration glob and runs pytest at the 57% floor; it does not run the migration-sequence preflight or DB-leakage audit.
- **Fresh branch comparison proves #60/#62 overlap:** from main, #60 is 104 commits ahead / 0 behind with 36 changed files; #62 is 38 ahead / 0 behind with 13 changed files. Both modify exactly `.github/workflows/tests.yml`, `README.md`, `deploy/scripts/run-migrations.sh`, and `docker-compose.yml`. They are separate main-based candidates, not cumulative branches.
- **The current #62 Compose source** still uses `env_file: .env.production` for Postgres, API, WAHA, and migrate. This exposes unrelated database, admin, WAHA, and provider settings to containers that do not need them. The Postgres container needs only `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`. The existing top-level review comment requests that allowlist plus a rendered-Compose regression; the finding remains unresolved.
- **The current #60 Compose source** has explicit service-specific allowlists and sends the API only `DATABASE_URL_RUNTIME`, while migrate receives owner credentials and provisions the restricted runtime role. But #60's runner does not include #62's target/seed/sequence preflights; #62 does not provision the restricted runtime role. Either merge order can regress one side of the boundary.
- **Exact-head CI:** #62 head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` has successful run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) (**864 passed, 1 warning, 76.01%**); its migration-sequence preflight, migrations 001–033, ORM schema audit, and post-test DB-leakage audit passed. It does not validate 034–040 or an installed 033→040 upgrade. #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` has cancelled run [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589): `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%, followed by a 120-second faulthandler during the next async-generator fixture setup. The job log contains no assertion/teardown traceback, final pytest summary, or coverage result; root cause remains unknown.
- **Migration allocation remains branch-local:** #48=034, #50=035, #49=036–037, #60=038–040. No candidate proves fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, schema audit, and zero leakage together.
- The branch-protection endpoint returned 403 for this integration connection; current protection status is unverified. Do not rely on required branch protection as a safety gate.

**Next engineering step:** construct one dedicated cumulative candidate preserving #62's pre-DDL target/seed/sequence guards and #55 leakage audit, #57 seed policy, #60's restricted runtime-role provisioning and service allowlists, plus the ordered 034–040 feature migrations. Then prove fresh/upgrade/no-op/schema/leakage/runtime-role behavior on disposable PostgreSQL before independent review. Do not merge either deployment PR independently.

**Human decision still required:** accept or strengthen the STOP linearization contract (whether a STOP committed after the final pending-intent read but before WAHA POST is too late). PR #50's introduction-copy and legacy-provenance decisions also remain open. **NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---


## Fresh live engineering verification — 2026-11-03 06:23 WAT

This snapshot supersedes the 2026-11-03 05:24 WAT snapshot below. A new top-level review comment on PR #62 identifies a further deployment secret-boundary gap: the PostgreSQL service still receives the entire `.env.production` file. This is not an inline review thread, so PR #62 remains at 7 unresolved threads (4 current-diff, 3 outdated). Live GitHub refs, all ten open PRs, review threads, workflow YAML, deployment configuration, migration inventory, and the latest cancelled Actions job log were rechecked. PR #59's pre-update head was `f9d0e5ac0356bd515cbbd96e1d1ced8fd92b56bf`. This is a documentation-only refresh on that PR branch and uses `[skip ci]`; no exact-head Tests run is expected for this documentation commit.

### Main and deployment state

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC); the repository's recent `pushed_at` reflects branch activity, not a new main commit.
- The latest Tests run associated with this exact main SHA remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. It is historical main evidence, not validation of the current feature branches.
- Main contains migrations 001–033. `.github/workflows/tests.yml` applies the lexical migration glob and runs pytest with a 57% coverage floor; it does not run the migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit. Main's `deploy/scripts/run-migrations.sh` has checksum handling and a schema audit but no contiguous-sequence preflight.
- Main's `docker-compose.yml` still injects `.env.production` into postgres, API, WAHA, and migrate. The branch-protection endpoint returned 403 in this run and the repository rulesets endpoint returned an empty list; legacy protection could not be independently confirmed, so do not rely on required branch protection as a safety gate.
- Main's `docs/ZINA_IMPLEMENTATION_ROADMAP.md` and `docs/ZINA_RELEASE_CHECKLIST.md` remain stale relative to the feature branches; this verification is on PR #59, not main.

### All open PRs — exact heads, Tests evidence, review threads

Counts are unresolved active current-diff threads / unresolved outdated threads. Exact-head CI results below are branch-local evidence only.

| PR | Exact head | Latest exact-head Tests | Active / outdated unresolved | Total unresolved / threads |
|---|---|---|---:|---:|
| #63 observability audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) — 803 passed, 76.08% | 0 / 1 | 1 / 1 |
| #62 deployment/seed preflights | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) — 846 passed, 76.01% | 4 / 3 | 7 / 7 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 / 0 | 0 / 0 |
| #60 contact-consent P0 | `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` | [41400297589 cancelled](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) | 12 / 5 | 17 / 17 |
| #59 roadmap/checklist | pre-update head `f9d0e5ac0356bd515cbbd96e1d1ced8fd92b56bf` | No exact-head run; documentation commits use `[skip ci]` | 1 / 2 | 3 / 3 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 0 / 1 | 1 / 1 |
| #55 DB-leakage gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) — 815 passed, 76.01% | 0 / 0 | 0 / 0 |
| #50 Identity Registry | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) — 828 passed, 76.52% | 3 / 0 | 3 / 11 |
| #49 Outbound Message Library | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) — 896 passed, 76.67% | 1 / 0 | 1 / 80 |
| #48 PrivateMediaArtifact wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 0 | 0 / 15 |

The latest overall Tests run remains #60 run 41400297589 and is **cancelled**, not green. I fetched its job log in this pass: migrations and Compose helper tests completed; `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%; a 120-second faulthandler then fired while pytest entered the next async-generator fixture, and the job was cancelled at its 20-minute limit. PostgreSQL logs show the expected privilege-denial probes (both SET ROLE directions, setval, consent UPDATE/DELETE/TRUNCATE, trigger alteration, schema CREATE, and SET ROLE postgres), but no assertion/teardown traceback, final test count, or coverage result. The failure's root cause remains unknown; do not infer success or guess a fix.

### Migration and deployment integration

The historical 034 collision is resolved **at branch allocation only**:

- Main: 001–033.
- #48: 034 `private_media_artifact_source_identity`.
- #50: 035 `identity_registry_default_backfill`.
- #49: 036–037 Outbound Message Library.
- #60: 038–040 contact-consent / sender-identity / sender-contact evidence.

No one candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, ORM schema audit, and zero DB leakage together. #60 applies 001–033 plus 038–040; #62's successful run applies 001–033 only. The numbering is contiguous across branch allocations, not yet integrated or release-proven.

#60 and #62 remain unsafe to merge independently or in either order. #60 has service-specific environment allowlists and a restricted non-owner API DB role, but lacks #62's pre-DDL database-target, local-seed, and migration-sequence preflights. #62 has those preflights plus schema/leakage gates, but still exposes the broad `.env.production` file to Postgres/API/WAHA/migrate and does not provision the restricted runtime role. The Postgres container only needs `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`; a new top-level review comment ([#62](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62#issuecomment-6596220710)) requests removal of its `env_file` and a rendered-Compose allowlist regression. Build one cumulative candidate preserving all preflights before the first DDL and the Postgres/API/WAHA/migrate credential boundaries. Integrate #61's sequence gate, #55's leakage audit, and #57's seed policy into that same candidate.

### Current P0 and architecture blockers

1. **Contact consent is not on main.** #60 remains draft/open and its exact-head workflow is cancelled. The main branch therefore does not yet enforce this new explicit contact-consent domain at the final worker fence.
2. **Quiet hours are not authority-independent in #60.** Exact one-use OWNER approval returns before the contact-policy quiet-hours check; exact ScheduledAction binding also bypasses it. One shared final external-contact delivery-window guard must cover both paths and reject malformed timezone/window configuration.
3. **Per-contact limits are alias-local.** Backlog, rate, and duplicate checks use exact `chat_id`; aggregate by stable Contact identity across current mapped aliases while holding the mapping/Contact lock.
4. **Approval/policy expiry can pass during lock acquisition.** Revalidate exact approval and policy expiry after all final locks and immediately before transport; retain uncertain-send quarantine and no automatic replay.
5. **Contact consent can expire while the worker waits for final locks.** `ContactMessagingConsentService` captures `instant` before the exact-chat mapping, Contact, and consent-row locks; the worker can then wait again at the safety-reservation/STOP boundary after consent was read. Revalidate consent against a fresh clock after all final locks and immediately before the single transport attempt, alongside approval/policy expiry. Add deterministic PostgreSQL/mock-WAHA regressions for both the mapping/consent-lock wait and the later worker-lock wait; both must produce zero WAHA calls.
6. **Media duplicate suppression is not payload-complete.** The current duplicate comparison omits locator, media kind, MIME, and filename. Use the canonical media-aware authority digest, scoped to stable recipient/contact identity.
7. **STOP reservation is a product/security contract.** The current implementation treats the final pending-STOP read as the dispatch reservation point. A STOP committed after that read but before the WAHA POST cannot recall the reserved attempt. Keep the two-session boundary regression and obtain OWNER acceptance, or strengthen the shared lock protocol.
8. **Worker integration is not cumulative.** #48 locks the exact OWNER view-once source before dispatch and stamps `returned_to_owner_at` only after a successful WAHA response. #60's worker lacks that source lock/post-success audit. Integrate both into one reviewed worker path; never bypass the single queue/fence or retry an uncertain send.
9. **Runtime-role test is unresolved.** The symmetric role-membership revocation/verification is present on #60's latest head, but run 41400297589 did not pass the runtime-role integration test and captured no assertion traceback. Isolate that exact test on the disposable PostgreSQL target and diagnose fixture setup/cleanup before treating consent-history immutability as proven.
10. **#50 Identity Registry still needs human architecture review.** Registry-read failures now suppress identity assertions and introduction checks honor deleted/disabled `zina`/ `fabian`. The introduction copy still mentions projects and Datacube AU; decide whether to remove those claims or gate the corresponding registry facts. Do not infer legacy provenance from `updated_at = created_at`; leave unverifiable legacy rows unknown unless immutable evidence or explicit OWNER attestation exists.
11. **#49 remains foundation-only.** No live producer selection or dashboard integration is established; do not wire it into external sends before P0 and integrated migration gates pass.
12. **#63 observability audit is a bounded independent candidate.** The exact-head run passed; it fixes audit ordering and adds a validated `internet_used` signal. One outdated unresolved review thread remains, so independent review is still required.

### Readiness and human decisions

- Controlled WhatsApp testing is **NOT READY; Stage A must not begin**. `docs/ZINA_CONTROLLED_TEST_PLAN.md` is absent from main (404).
- Private-media byte retention remains OFF.
- No integrated migration, schema-audit, DB-leakage, or exact-candidate full-suite proof exists.
- Human decisions still required: accept/revise the STOP reservation boundary; decide whether terminal opt-out can ever be reversed and what evidence is required for OWNER consent grants; decide Identity Registry introduction scope and treatment of legacy provenance.
- Highest-value next engineering step: close #60's quiet-hours, alias-budget, approval/policy/consent-expiry, and media-digest P0 findings; isolate the runtime-role test; then build one cumulative #48/#60 worker and #60/#62/#61/#55/#57 deployment candidate for exact integrated migration and safety validation.

This pass performed GitHub source/review/log inspection, decoded the latest CI job log, posted a comment-only diagnostic on PR #60, and refreshed this documentation snapshot. No application source or migration was changed; no local pytest, migration, schema audit, or leakage audit was run; no Actions workflow was triggered. No production DB mutation, WAHA reconnection, real WhatsApp send, private-media retention activation, approval, merge, or review-thread resolution occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh live engineering verification — 2026-11-02 20:20 WAT

This snapshot supersedes the 15:25 UTC review-state overlay below. It was captured from live GitHub refs before the two documentation-only commits described after this snapshot. The snapshot base for PR #59 was head `55e621e2422b051aeb47f913f37f7e26f85fd7f0`; the new commits on this same branch intentionally use `[skip ci]`, so the resulting docs head has no exact-head Tests run.

### Main and workflow state

- `main` is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; the latest main commit is dated 2026-09-08 11:09:59 UTC. No newer main commit was returned.
- The latest Tests run associated with this exact main SHA is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. It is historical evidence, not current feature-chain verification.
- Main's `.github/workflows/tests.yml` applies the lexical `bot_core/migrations/*.sql` glob and runs pytest with a 57% coverage floor. It does **not** run the migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit. The current `deploy/scripts/run-migrations.sh` has checksum skip/mismatch handling and a schema audit, but no contiguous-sequence preflight.
- Main's `docker-compose.yml` still mounts the broad `.env.production` into API, WAHA, and migrate. PR #60 introduces service-specific environment allowlists and a restricted runtime DB login, but lacks PR #62's pre-DDL target/seed/sequence guards. PR #62 has those guards plus schema/leakage checks, but still has the broad environment exposure and no restricted runtime-role boundary. Neither branch is safe to merge independently or in either order; one cumulative deployment candidate is required.
- `docs/ZINA_IMPLEMENTATION_ROADMAP.md` and `docs/ZINA_RELEASE_CHECKLIST.md` on main still identify 2026-09-08 / main `0034587a90bb8d5a79bda41e85091cfea33b969d` as their last-verified baseline. That baseline predates current main `5aadd72` and all current open feature PRs.

### All open PRs — exact heads, exact-head Tests, review threads

Review counts below distinguish unresolved current-diff threads from unresolved outdated threads. No open PR has an APPROVED review submission; submissions are COMMENTED or absent.

| PR | Exact head | Exact-head Tests | Active unresolved | Outdated unresolved | Total unresolved / threads |
|---|---|---|---:|---:|---:|
| #63 observability audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) | 0 | 1 | 1 / 1 |
| #62 deployment/seed/migration integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) | 4 | 3 | 7 / 7 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 | 0 | 0 / 0 |
| #60 contact-consent P0 | `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` | [41400297589 cancelled](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) | 11 | 5 | 16 / 16 |
| #59 roadmap/checklist | snapshot base `55e621e2422b051aeb47f913f37f7e26f85fd7f0` | no run (docs commits use `[skip ci]`) | 1 | 2 | 3 / 3 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 0 | 1 | 1 / 1 |
| #55 DB-leakage gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | 0 | 0 | 0 / 0 |
| #50 Identity Registry | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) | 3 | 0 | 3 / 11 |
| #49 Outbound Message Library | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | 1 | 0 | 1 / 80 |
| #48 PrivateMediaArtifact wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 | 0 | 0 / 15 |

The latest overall Tests run is #60 run 41400297589 and is **cancelled**, not green. Its migration step and Compose helper tests passed, but `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%; a 120-second faulthandler fired while pytest entered the next async-generator fixture, and the job was cancelled at its 20-minute limit. The captured log contains the expected PostgreSQL privilege-denial probes but no assertion/teardown traceback, final test count, or coverage result. Do not infer that the test passed or guess its root cause.

### Migration inventory and integration gate

The earlier 034 filename collision has been renumbered on the feature branches, but only branch-local allocation is proven:

- Main: migrations 001–033.
- PR #48: 034 `private_media_artifact_source_identity`.
- PR #50: 035 `identity_registry_default_backfill`.
- PR #49: 036–037 Outbound Message Library.
- PR #60: 038–040 contact consent / sender identity / sender contact IDs.
- PR #62's successful exact-head run applies 001–033 only.

No candidate has demonstrated one contiguous 001–040 chain from empty PostgreSQL, an installed 033→040 upgrade, second-run no-op/checksum stability, ORM schema audit, and zero DB leakage on the **same integrated candidate**. The former #48/#49 034 collision is therefore resolved at branch allocation, not at release validation.

### Highest-risk integration and policy blockers

1. **Worker paths are not cumulative.** #48 locks the exact OWNER view-once source before WAHA and marks it returned only after confirmed success. #60 adds external-contact consent/current mapping/STOP and final safety checks, but its worker lacks #48's view-once source lock and post-success return audit. Both change `background_workers.py` and `outbound_authorization_service.py`; produce one reviewed candidate preserving both paths. Uncertain WAHA delivery must remain quarantined and never be blindly retried.
2. **#60 quiet-hours bypasses remain P0.** Exact one-use OWNER approval returns before the contact-policy quiet-hours check; exact ScheduledAction binding also returns allowed without that check. A single authority-independent external-contact delivery-window guard must apply to both paths and reject malformed timezone/window configuration.
3. **Contact limits are alias-local.** Backlog/rate/duplicate checks use exact `chat_id`, so aliases for one Contact can receive separate budgets. Aggregate by stable Contact identity across current mapped aliases while holding the exact-chat/Contact mapping lock.
4. **Time-bounded authority can expire while final locks are acquired.** Revalidate approval/policy expiry at the final dispatch boundary after all relevant locks and before transport.
5. **Media duplicate suppression is not payload-complete.** The current duplicate key uses message text/caption, not the canonical media-aware digest (locator, kind, caption, MIME, filename). Identical blank-caption media can evade duplicate detection, while different attachments with the same caption can be conflated.
6. **STOP reservation semantics need explicit OWNER acceptance or a stronger lock protocol.** Current contract treats the final pending-STOP read as the reservation boundary: STOP committed before it vetoes; STOP committed after transport entry cannot reliably recall the attempt, which must remain uncertain/quarantined and never replay. Add the two-session regression and obtain OWNER acceptance before calling this policy complete.
7. **Deployment integration is non-cumulative.** Consolidate #60 runtime-role/service isolation with #62 target preflight, seed safety, migration sequence validation, schema audit, and leakage gate. Keep database-owner credentials out of API/WAHA and prove the runtime login cannot mutate consent history or assume privileged roles.
8. **#50 Identity Registry still needs independent architecture review.** Its exact-head suite is green only for 001–033 plus 035. Keep legacy provenance unknown unless immutable evidence or explicit OWNER attestation exists; do not infer origin from `updated_at = created_at`. Keep introduction copy to identity keys actually governed by the registry (recommended: assistant/owner only; project facts remain registry answers). Registry-read failure must suppress identity claims rather than fall back to hardcoded `bot_config` assertions.
9. **#49 remains foundation-only.** Its green run applies 001–033 and 036–037, not the integrated chain; no live producer/selection/dashboard integration is established by this PR.

### Readiness

- **Controlled WhatsApp testing: NOT READY; Stage A must not begin.** The controlled test plan file `docs/ZINA_CONTROLLED_TEST_PLAN.md` is not present on main (GitHub returned 404).
- Private-media byte retention remains OFF.
- No integrated migration, DB-leakage, or exact-head full-suite proof exists for the combined worker/deployment candidate.
- No merge, approval, production DB operation, WAHA reconnection, or real WhatsApp action is implied by this snapshot.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---


## Fresh review-thread reconciliation — 2026-11-02 15:25 UTC

This snapshot distinguishes unresolved threads from outdated threads. A thread is counted as **active current-diff** only when it is unresolved and not outdated.

| PR | Active current-diff unresolved | Outdated | Unresolved | Total |
|---|---:|---:|---:|---:|
| #63 conversation observability | 0 | 1 | 1 | 1 |
| #62 migration/deployment preflights | 4 | 3 | 7 | 7 |
| #61 migration-sequence gate | 0 | 0 | 0 | 0 |
| #60 contact-consent P0 | 11 | 5 | 16 | 16 |
| #59 release documentation | 1 | 2 | 3 | 3 |
| #57 local-seed safety | 0 | 1 | 1 | 1 |
| #55 DB-leakage gate | 0 | 0 | 0 | 0 |
| #50 Identity Registry | 3 | 3 | 3 | 11 |
| #49 Outbound Message Library | 1 | 50 | 1 | 80 |
| #48 PrivateMediaArtifact | 0 | 9 | 0 | 15 |

- Fresh review-submission queries for all ten open PRs returned **no APPROVED review state**; submissions are COMMENTED or absent. Zero active threads, or a thread marked outdated, is not independent approval.
- The earlier table in this overlay that listed #60 as 14/14 is superseded: the current thread query now reports 16 unresolved / 16 total, of which 11 are on the current diff and 5 are outdated. #59 has 1 active current-diff thread; its other 2 unresolved threads are outdated. #57 and #63 each have one unresolved but outdated thread.
- The highest-risk active review work remains #60 (P0 consent/worker fence) and #62 (deployment preflight/runtime-role integration). #50 still has three active architectural/provenance decisions. #49 remains foundation-only with one active review thread. #48's 15 threads are all resolved, with 9 marked outdated; that does not replace integration testing with #60.

No source code or migration was changed in this review pass. No test, migration, schema audit, or leakage audit was run; no Actions workflow was triggered. No production DB mutation, WAHA reconnection, or real WhatsApp action occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

## Exact Actions log triage — 2026-11-02 14:43 UTC

This is a source/log verification update, not a test pass.

- Re-read the decoded job log for [Tests run 41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589), job `125130478315`, on PR #60 exact head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`.
- PostgreSQL recorded the expected denials for both `pg_auth_members` membership directions (`SET ROLE zina_runtime` from the secondary login and `SET ROLE <parent>` from the runtime login), `setval()`, consent-event UPDATE/DELETE/TRUNCATE, trigger-disable, CREATE in `public`, and `SET ROLE postgres`.
- Pytest still marks `test_runtime_role_cannot_mutate_or_disable_consent_history` **FAILED** immediately after the final denied `SET ROLE postgres` probe. The 120-second faulthandler then fires while pytest is setting up the next async-generator fixture; the captured stack shows the event loop waiting in the fixture wrapper, not an assertion traceback. The run was cancelled at the 20-minute job limit. These logs demonstrate the privilege-denial probes ran, but they do **not** establish why the test failed or that cleanup completed.
- Next diagnostic is an isolated invocation of that one test against the explicitly disposable PostgreSQL service, with uncensored pytest failure/teardown output and bounded connection/cleanup timeouts. Do not infer a source root cause from the PostgreSQL denial messages alone.
- No local test or migration was run in this pass; no Actions run was triggered. The current run remains cancelled, with no final suite count or coverage result. No source change, production DB operation, WAHA reconnection, or real WhatsApp send occurred.

**Release state remains NOT TEST READY. REAL WAHA ACTIONS: NONE.**

## Fresh release verification — 2026-11-02 (current engineering pass)

**Status: NOT TEST READY.** This overlay supersedes the 11:23 WAT snapshot below. It is based on fresh live branch refs, exact-head Actions associations, review threads, workflow YAML, migration allocation, and source review. Historical checked boxes later in this file describe the September baseline, not an integrated release candidate.

### Verified state

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only. Exact-main Tests run `34219252390` succeeded on 2026-09-08; no newer run is associated with this SHA. Main's workflow has a 57% coverage floor but lacks the migration-sequence preflight, ORM schema audit, and post-test DB-leakage gate.
- Latest overall Tests run [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` is **cancelled**. Migration application and Compose helper tests passed; the runtime-role integration test was marked FAILED at 86%, then the 120-second faulthandler timed out during async fixture setup and the job reached its 20-minute cancellation. No assertion traceback, final suite count, or coverage result exists.
- Migration allocation is contiguous by branch only: #48=034, #50=035, #49=036–037, #60=038–040. No single candidate has passed fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum, schema audit, and zero-leakage proof.
- #60 and #62 cannot be merged independently or in either order: #60 provides runtime-role/service credential separation but lacks #62's pre-DDL target/seed/sequence guards; #62 provides those guards plus schema/leakage checks but lacks the restricted API role and still exposes the broad production env file to API/WAHA/migrate. One integrated candidate is required.
- Current branch protection is unverified: the classic protection endpoint returned 403 and the rulesets endpoint returned an empty list.

### P0 release blockers

1. OWNER approval and ScheduledAction authority paths bypass the contact policy's quiet-hours check. The final external-contact fence must enforce quiet hours regardless of authority source and reject malformed timezone/window settings.
2. Contact backlog/rate/duplicate controls are scoped to exact `chat_id`, not stable Contact identity across aliases.
3. STOP receipt commit can race after the worker's final pending-intent read but before the WAHA request. The reservation/linearization contract needs an explicit two-session regression and OWNER acceptance, or a stronger shared lock protocol.
4. Approval/policy expiry can pass while the worker waits for consent, safety-reservation, or mapping locks. Recheck/reserve time-bounded authority after all locks immediately before transport.
5. Media duplicate suppression compares caption/text rather than the exact media-aware payload digest (locator, kind, caption, MIME, filename); blank-caption duplicate media can bypass suppression.
6. The current PR #60 runtime-role integration test is not green or complete; obtain its assertion traceback and fix the async fixture/test-isolation timeout before relying on audit-history protection.

### Other integration and review gates

- PR #50: registry-read failures now fail closed, but generic introduction copy scope and truthful provenance for pre-033 rows remain unresolved. Ambiguous historical rows should remain `legacy_unknown` unless immutable evidence proves origin.
- PR #49: outbound-message library remains foundation only; no live producer selection or dashboard. No external-send integration before P0 and migration gates pass.
- PR #48: private-media observation/return wiring only; retention remains OFF.
- No PR currently has an APPROVED review state. Unresolved threads remain on #60 (16), #62 (7), #59 (3), #50 (3), #49 (1), #63 (1), and #57 (1). #48/#61/#55 have zero unresolved threads, which is not independent approval.

### Current-pass evidence

- Added two source-anchored P0 comments to [PR #60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60): [time-bounded approval/policy expiry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4442435895) and [media-aware duplicate identity](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4442484093). These are review findings, not approvals.
- This pass made no application-code or migration change and ran no local tests, migrations, schema audit, or leakage audit. It triggered no Actions workflow and performed no production DB, WAHA, or real WhatsApp operation. Private-media retention remains OFF.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh release verification — 2026-11-02 11:23 WAT

**Status: NOT TEST READY.** This snapshot supersedes the 09:27 WAT overlay below. The historical checked boxes later in this file were verified against a September 2026 code state; they are not current integrated-release evidence.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only. Latest exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. The checked-in workflow has a 57% coverage floor but no integrated migration-sequence/schema/leakage gates.
- Latest overall Tests run [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` is **cancelled**, not green. Migration application and Compose helper tests passed; the runtime-role integration test failed at 86%, then the 120-second faulthandler fired during async fixture setup. No traceback, final suite count, or coverage is available.
- Open PR #60 now has 14 unresolved / 14 total review threads, including three fresh source-anchored findings: quiet-hours bypass for exact approval, quiet-hours bypass for ScheduledAction, and alias-local per-contact backlog/rate/duplicate limits. STOP reservation linearization still needs explicit OWNER acceptance.
- Branch-level migrations are allocated contiguously (#48=034, #50=035, #49=036–037, #60=038–040), but no single candidate has passed fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum, combined schema audit, and zero-leakage proof.
- #48/#60 must be combined without losing either OWNER view-once source locking/post-success return audit or external-contact consent/STOP/final safety. #60/#62 must also be combined: preserve #62's pre-DDL target/seed/sequence preflights and schema/leakage gates while retaining #60's runtime-role boundary and API/WAHA/migrate environment separation.
- #50 still needs human/independent decisions on introduction-copy scope and truthful legacy provenance. #49 remains an outbound-library foundation only. Private-media retention stays OFF.
- Branch-protection verification is inconclusive: the GitHub branch-protection endpoint returned 403 to the connected integration. Do not claim current protection status.

### Required before controlled testing

1. Fabian accepts or revises the STOP reservation/in-flight boundary and the consent-evidence/re-consent policy.
2. Close quiet-hours and cross-alias limits with PostgreSQL-backed regressions; preserve one shared final authorization/worker fence.
3. Diagnose and pass the isolated runtime-role integration test, then pass full exact-head pytest/coverage.
4. Build one reviewed integration candidate preserving #48/#60 worker behavior and #60/#62 deployment isolation/preflights.
5. Prove fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, schema audit, and zero DB leakage on that same exact candidate.
6. Resolve blocking review threads independently; complete dashboard/observability gates and publish the staged controlled-test plan.

No local tests or migrations were run for this documentation-only refresh. No production DB mutation, WAHA reconnection, or real WhatsApp send occurred. Private-media retention remains OFF.

Controlled sequence after all gates and explicit OWNER authorization: owner self-DM text → commands → media/view-once → one explicitly approved external contact.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh release verification — 2026-11-02 09:27 WAT

**Status: NOT TEST READY.** This recheck supersedes older status overlays below.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only. Latest main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08.
- The latest overall Tests run, [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`, is **cancelled**. Migrations and Compose helper tests passed; the runtime-role integration test was marked FAILED at 86%, followed by a 120-second faulthandler timeout during async fixture setup. No traceback, final test count, or coverage is available.
- The former migration-034 collision is resolved at branch allocation: #48=034, #50=035, #49=036–037, #60=038–040. No integrated fresh 001–040 / installed 033→040 / second-run no-op/checksum / schema-audit / DB-leakage proof exists.
- #48/#60 worker changes and #60/#62 deployment changes must be integrated into one reviewed candidate; neither deployment branch is safe to merge alone.
- P0 blockers remain: STOP reservation linearization needs OWNER acceptance; quiet-hours checks are bypassed by approval and scheduled-action paths; per-contact limits are keyed by chat alias rather than stable Contact identity.
- #50 still needs the introduction-copy scope and truthful legacy-provenance decisions. #49 remains foundation-only. Private-media retention remains OFF.
- The branch-protection endpoint returned 403 and the rulesets endpoint returned an empty list; branch protection / required checks could not be conclusively verified.
- No local tests or migrations were run for this documentation-only refresh. No production DB mutation, WAHA reconnection, or real send occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh release verification — 2026-11-02 08:32 WAT

**Status: NOT TEST READY.** This snapshot supersedes the 06:34 WAT verification and is based on fresh live refs, exact-head Actions runs, review threads, migration trees, workflow YAML, and deployment/source inspection.

- Main remains 5aadd725ed9da08a5eb84eb42b64f0f45f231c79, with migrations 001–033 only. Its exact-main Tests run 34219252390 succeeded on 2026-09-08; no newer run is associated with that exact SHA. Main currently reports protected=false and no required status checks.
- The former duplicate migration 034 has been reconciled across branches: #48=034, #50=035, #49=036–037, #60=038–040. No single candidate has passed fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, combined schema audit, and zero-leakage audit.
- PR #60 current head bcc34cdcd012e2735d5f51d899ff7a2274c018f9 has a symmetric runtime-role membership fix. Exact-head Tests run 41400297589 is CANCELLED, not green: migrations passed, Compose helper tests passed, test_runtime_role_cannot_mutate_or_disable_consent_history failed at 86%, then faulthandler timed out during async fixture setup. There is no assertion traceback, final test count, or coverage result.
- P0 policy is not complete: OWNER must decide whether a STOP committed after the final pre-transport reservation but before the WAHA request is considered too late; active OWNER approval and exact ScheduledAction paths currently bypass contact-policy quiet-hours evaluation; per-contact safety limits are scoped to exact chat_id rather than stable Contact identity across aliases.
- PR #48 and #60 both modify the sole outbound worker/authorization service. Integrate #48's exact-source OWNER view-once lock and post-success return audit with #60's external-contact consent, STOP, and final safety fence in one candidate.
- PR #60 and #62 must also be consolidated: preserve #62's pre-DDL target/seed/sequence preflights, schema audit, and leakage gate while retaining #60's runtime-role separation and service-specific Compose environments. No merge order alone is safe.
- PR #50 still needs the introduction-copy decision and a truthful legacy-provenance policy; timestamp equality is not reliable historical provenance. PR #49 remains foundation-only and has one active retired-key review thread.
- Exact active unresolved review counts remain: #60 6, #62 4, #50 3, #49 1, #59 1. Other open PRs have no active unresolved threads, although some outdated threads remain unresolved.

### Required before TEST READY

1. Resolve the STOP linearization and consent-evidence semantics with Fabian.
2. Close quiet-hours and cross-alias rate/backlog/duplicate gaps with PostgreSQL-backed regressions.
3. Diagnose and pass the isolated runtime-role integration test, then the full exact-head suite and 57% coverage gate.
4. Integrate #48/#50/#49/#60 and #62/#61/#57/#55 into one reviewed migration/deployment candidate; prove fresh 001–040 and installed 033→040 upgrade, no-op/checksum stability, schema audit, and zero DB leakage on that same candidate.
5. Resolve blocking reviews independently; preserve one router, one scheduler, one authority/dispatcher, and the sole WAHA transport.
6. Complete dashboard/observability gates and publish the staged controlled-test plan.

No local tests or migrations were run for this documentation-only refresh. No production DB mutation, WAHA reconnection, or real WhatsApp send occurred. Private-media retention remains OFF.

Controlled test sequence remains owner self-DM text → commands → media/view-once → one explicitly approved external contact, only after all gates pass and Fabian explicitly authorizes the live session.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh release verification — 2026-11-02 (after runtime-role hardening)

**Status: NOT TEST READY.** This snapshot is based on current live GitHub state, not the older 2026-09-08 main verification.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. Main contains migrations 001–033 only and is not branch-protected.
- Feature migration allocation is now contiguous by branch: #48=034, #50=035, #49=036–037, #60=038–040. This resolves the historical filename collision, not integrated validation. Fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, combined schema audit, and zero DB leakage remain unproved on one candidate.
- PR #60 current head is `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`; exact-head Tests run [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) is in progress. Its latest code patch closes the symmetric role-membership gap in provisioner + verifier and adds a disposable-PostgreSQL SET ROLE regression; no green result is claimed yet.
- PR #60 still has P0 blockers: the STOP final-read/transport-entry linearization point needs OWNER acceptance; quiet-hours checks are bypassed by active approval and scheduled-action paths; per-contact frequency/backlog/duplicate limits are keyed by chat ID rather than stable Contact identity.
- PR #60 and #62 must be consolidated so API receives only restricted runtime credentials, WAHA receives only its explicit variables, migrate alone receives owner credentials, and all #62 target/seed/sequence preflights remain before DDL. PR #48 and #60 must also be integrated without dropping either view-once source locking/return audit or external-contact consent/STOP enforcement.
- Independent review remains open on #60 (6 active unresolved), #62 (4 active unresolved), #50 (3 active unresolved), #49 (1 active unresolved), and #59 (1 active unresolved); other open PR thread state is recorded in the roadmap snapshot above.

No integrated release-candidate tests or controlled WhatsApp test stages are authorized by these branch-local checks. No production DB mutation, WAHA reconnection, or real WhatsApp send occurred. Private-media retention remains OFF.

---

## Cross-PR worker integration gate — 2026-11-02 01:15 WAT

This delta adds a verified dependency between the view-once and contact-consent branches. It is documentation-only and uses `[skip ci]`; no exact-head CI result is claimed for the resulting docs commit.

- PR #48 exact head: `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`, Tests run [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success, 0/15 unresolved threads.
- PR #60 exact head: `e0685c8bbeb380a684816b463ddd4f8eee4db10c`, Tests run [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) cancelled, 10/10 unresolved threads.
- Both change `background_workers.py` and `outbound_authorization_service.py`. #48 adds exact OWNER view-once source binding/locking and post-success return recording; #60 adds final external-contact authority/consent/STOP/safety checks. Neither branch contains the other's worker behavior. Integrate both in one reviewed candidate; do not rely on merge order.
- On #60, quiet hours still bypass exact OWNER approval and exact ScheduledAction binding paths; per-contact rate/backlog/duplicate controls still key by exact chat ID rather than stable Contact identity. The runtime-role verifier/provisioner still omit incoming memberships (`pg_auth_members.roleid = runtime_role`), and the latest runtime-role integration test is unexplained/cancelled.
- The #60/#62 deployment conflict remains: #60 has service-specific environment allowlists/runtime role but lacks #62's pre-DDL target/seed/sequence preflights; #62 has preflights/schema/leakage but still shares `.env.production` with API/WAHA/migrate and lacks the restricted runtime role.
- Migration numbers are contiguous by branch allocation (#48=034, #50=035, #49=036–037, #60=038–040), but no exact candidate proves fresh 001–040, installed 033→040, rerun/checksum stability, schema audit, and leakage together.

**Release status remains NOT TEST READY.** No local PostgreSQL/pytest or integrated migration execution was available; no Actions run was triggered; no production DB mutation or WAHA action occurred.

---

## Current release verification — 2026-11-01 23:22 WAT (NOT TEST READY)

This release-gate delta supersedes the 20:23 WAT snapshot below. It was rechecked against live GitHub heads, review-thread states, the main workflow, migration filenames, and PR #60 source/Actions logs. PR #59 was at `ac071ac25f7118717914bdb4956b62aa76830b7e` when this audit began; this docs-only refresh uses `[skip ci]`, so no exact-head CI result is claimed for the resulting documentation commit.

### Release gate summary

| Gate | Current evidence | Status |
|---|---|---|
| Main source baseline | `main` = `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; migrations 001–033 | Main only |
| Fresh integrated migrations 001–040 | Branch allocations are contiguous (#48=034, #50=035, #49=036–037, #60=038–040), but no single candidate applies all 001–040 | **NOT PROVED** |
| Installed upgrade 033→040 | No integrated upgrade/re-run/no-op/checksum evidence | **NOT PROVED** |
| Migration/schema preflight | #61 and #62 pass on their branch candidates; #62's latest exact-head run is 41073226073 | Candidate only |
| ORM schema audit | #62 run 41073226073 passed on 001–033 | Candidate only |
| DB leakage | #55 run 41026581000 passed on 001–033; #62 run 41073226073 passed on 001–033 | Candidate only; combined chain not checked |
| Full pytest/coverage | #62: 864 passed, 76.01%; #50: 828 passed, 76.52%; #49: 896 passed, 76.67%; #63: 803 passed, 76.08% | Branch-local only |
| P0 contact consent | Implemented only on open draft #60, not main; latest run 41311022671 cancelled | **NOT PROVED** |
| Runtime-role privilege boundary | #60's latest test marked failed; incoming role membership remains unchecked | **BLOCKED** |
| Quiet-hours/rate-limit safety | #60 has open findings for approval/scheduled quiet-hours bypass and per-chat rather than per-contact limits | **BLOCKED** |
| Independent review | #60 10 unresolved; #62 7; #50 3; #49 1; #59 3; #57 1; #63 1 | **BLOCKED** |
| Live transport | No real WAHA call is permitted in unattended engineering | NONE |

### P0 consent and runtime-role gates

- #60 run [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) is **cancelled**, not green. Migration application and the Compose helper tests passed, but `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%; the 120-second faulthandler fired and the job was cancelled at 20 minutes. The log contains no assertion traceback, final test count, or coverage result. The denial probes are visible in PostgreSQL logs, but they do not identify the failing assertion.
- The runtime-role provisioner and verifier must revoke/check `pg_auth_members` in both directions. Current code handles rows where runtime is the member, not rows where runtime is the granted role. Add a second temporary role granted `zina_runtime`, rerun provisioning, and prove the membership is removed and `SET ROLE zina_runtime` is denied.
- The final external-contact fence must apply quiet hours regardless of whether permission came from a one-use OWNER approval, ScheduledAction binding, or contact automation policy. Invalid timezone/window configuration must deny.
- Per-contact backlog/rate/duplicate ceilings must use stable Contact identity across mapped WhatsApp aliases, not only exact `chat_id`.
- The API runtime role must be a non-owner/non-superuser with no path to assume a privileged role. The API receives runtime-only DB credentials; WAHA receives no DB/admin/provider secrets; only migrate receives migration-owner credentials.

### Deployment/migration integration order

Do not merge #60 or #62 independently. #60 contains runtime-role isolation and service-specific environment allowlists but lacks #62's database-target, seed, and migration-sequence preflights. #62 contains those preflights, schema audit, and leakage gate but still exposes the shared production environment file to API/WAHA/migrate and has no restricted runtime role. Consolidate #60/#62/#61/#57/#55 into one candidate, preserving every gate before DDL and every service credential boundary.

The current migration allocation is no longer a duplicate-number collision: #48=034, #50=035, #49=036–037, #60=038–040. The remaining blocker is integration and proof, not numbering. Required evidence on the same exact candidate:
1. Fresh PostgreSQL 16 application of migrations 001–040.
2. Upgrade an isolated database already at 033 through 040.
3. Re-run migration runner and prove no-op/checksum stability.
4. Run ORM schema audit against the same endpoint/schema modified by migrations.
5. Run the complete DB-leakage audit after pytest on the combined schema.
6. Prove runtime-role SELECT/INSERT works while UPDATE/DELETE/TRUNCATE/ALTER/DISABLE TRIGGER/SET ROLE and sequence setval are denied.
7. Run the P0 adversarial matrix, including STOP races, alias remapping, exact payload binding, duplicate/restart, quiet hours, and uncertain-send no-retry.

### Human decisions still required

- Accept or revise the terminal STOP policy: a committed STOP before final transport reservation vetoes; once a single request enters WAHA it cannot reliably be recalled, but the attempt must never be retried/replayed and all later sends remain denied.
- Decide whether `.contact consent grant <exact-chat-id> <evidence-ref>` means OWNER attests that independent contact consent exists (with a durable external evidence reference), or whether it is only an OWNER automation permission. These are separate authorities and must not be conflated.
- Decide whether opt-out is permanently terminal or an explicit OWNER re-consent path is permitted. Current #60 code intentionally provides no override.
- Confirm the introduction-copy scope in #50: remove project/Datacube claims from the generic introduction (recommended) or require every named registry key to be available.
- Accept truthful `legacy_unknown` provenance for pre-upgrade Identity Registry rows rather than inferring origin from timestamps, or authorize a separate evidence-backed attestation process.

### Controlled test stage

**NOT TEST READY.** The main branch lacks the proposed contact-consent gate; the exact #60 run is cancelled; runtime-role, quiet-hours, alias-rate-limit, integration, and independent-review gates remain open. Do not connect/reconnect production WAHA, mutate a production database, or send any real WhatsApp message from this automation. The controlled test sequence remains: owner self-DM text → commands → media/view-once → one explicitly approved external contact, only after all gates pass and Fabian explicitly authorizes the live session.

**REAL WAHA ACTIONS: NONE.**

---

## Current release verification — 2026-11-01 20:23 WAT

This delta supersedes the older 2026-09-08 baseline below. It is a fresh review snapshot, not release approval.

- Main is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only. Its exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08; no newer run is associated with that SHA.
- Main's workflow still applies migration files lexically and runs pytest with a 57% coverage floor. Migration-sequence preflight, ORM schema audit, and post-test DB-leakage audit are not yet on main.
- The former 034 collision is renumbered across branches: #48=034, #50=035, #49=036–037, #60=038–040. This is filename reconciliation only. No integrated fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum, combined schema audit, or combined leakage proof exists.
- #60 and #62 must be consolidated before either is merged: #60 has runtime-role/service-environment isolation but lacks #62's pre-DDL target/seed/sequence checks; #62 has those checks but still mounts broad `.env.production` into API, WAHA, and migrate and has no restricted runtime role.
- PR #60's exact-head Tests run [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) is **cancelled**, not green. The Compose helper tests passed, but `test_runtime_role_cannot_mutate_or_disable_consent_history` failed at 86%; the 120-second faulthandler fired without a captured assertion traceback or final suite/coverage result. The runtime-role membership check is still one-directional; the current-head inline review [5729336758](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#pullrequestreview-5729336758) requires symmetric role-membership revocation/verification and a regression.
- Additional #60 P0 review findings remain open: owner-approved and scheduled external messages bypass the contact policy quiet-hours check; per-contact rate/backlog/duplicate limits use exact chat IDs rather than stable Contact identity across aliases. Consent/STOP is not on main.
- Exact live unresolved / total review threads: #48 0/15; #49 1/80; #50 3/11; #55 0/0; #57 1/1; #59 3/3; #60 10/10; #61 0/0; #62 7/7; #63 1/1. The preceding 18:21 roadmap table inverted the #48/#49 resolution counts; these values use GitHub's live `is_resolved` field.
- No local pytest, isolated PostgreSQL migration, schema audit, or DB-leakage audit was run in this verification update. No source code was changed. OWNER must decide whether STOP is permanently terminal or can be reversed by an explicit re-consent, and confirm the evidence semantics for OWNER-granted consent.
- **NOT TEST READY. REAL WAHA ACTIONS: NONE.** No production DB mutation, WAHA reconnection, real WhatsApp send, private-media retention activation, merge, approval, or review-thread resolution occurred.

---

## Current engineering verification — 2026-11-01 18:21 WAT

This delta supersedes the 16:25 WAT snapshot below. It rechecks main, all ten open PR heads, exact-head Tests associations, all review-thread resolution counts, the main workflow, and the migration/deployment branches. It records one new inline security review on PR #60; it does not approve or merge any PR.

### Main and workflow

- Main is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (commit time 2026-09-08 11:09:59 UTC), with migrations 001–033 only. No newer Tests run is associated with this exact main SHA; the last known main run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08.
- Main `.github/workflows/tests.yml` still triggers on pull requests and pushes to main/master, applies migration files lexically, and runs pytest with a 57% coverage floor. It has no migration-sequence preflight, schema audit, or post-test DB-leakage audit.
- Main deployment still uses the older shared environment-file contract. PR #62 still mounts `.env.production` into API, WAHA, and migrate; PR #60 instead uses service-specific allowlists and a restricted runtime role. Those branches are not interchangeable.

### All open PRs — exact heads, latest exact-head Tests result, review threads

| PR | Exact head | Latest exact-head Tests | Unresolved / total |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 15 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success | 80 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 11 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| [#57 deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 documentation refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `98ae809693dd5f5991c534c2dd8fd14597e4228d` before this docs-only update | No exact-head run; docs commits use `[skip ci]` | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `e0685c8bbeb380a684816b463ddd4f8eee4db10c` | [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) cancelled after runtime-role test failure at 86% and 120-second faulthandler timeout; no final count/coverage | 10 / 10 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All ten remain open. Green branch-local runs do not replace independent review or prove an integrated release candidate.

### Migration and deployment status

- Branch allocation is now contiguous: #48=034, #50=035, #49=036–037, #60=038–040. The former duplicate-034 collision is resolved by renumbering, but the branches are still independent.
- The CI runs for #48/#50/#49/#60 apply main's 001–033 plus only that branch's own migration(s); none proves 001–040 together. There is no disposable fresh 001–040 run, installed 033→040 upgrade, second-run no-op/checksum proof, combined schema audit, or combined DB-leakage proof.
- #60 and #62 cannot safely merge in either order: #60 has the restricted runtime role and service-specific API/WAHA environments but lacks #62's database-target, local-seed, and contiguous-sequence preflights; #62 has those preflights but still mounts broad `.env.production` into API/WAHA/migrate and lacks #60's restricted runtime-role provisioner. Consolidate #60/#62 with #61/#57/#55 into one candidate before any merge.

### New PR #60 security review

- On exact head `e0685c8bbeb380a684816b463ddd4f8eee4db10c`, the provisioner and verifier check only `pg_auth_members.member = runtime_role_oid`. They do not remove or detect rows where `pg_auth_members.roleid = runtime_role_oid`, so another role granted the runtime role can still `SET ROLE` into it. The integration test also checks only the first direction.
- An inline review was posted at [PR #60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) (review id `5729336758`) with the symmetric REVOKE/verification SQL and a disposable-PostgreSQL regression requiring a second temporary role granted the runtime role.
- The exact-head run's log shows the Compose regressions passed, then `test_runtime_role_cannot_mutate_or_disable_consent_history` failed at 86%; the 120-second faulthandler fired during pytest setup/fixture handling, and the job was cancelled. No assertion traceback or final suite/coverage result was captured. The test failure is not yet diagnosed.

### Remaining decisions and readiness

- OWNER decisions still required for #60: whether STOP is permanently terminal or an OWNER can re-consent, and what evidence-reference semantics are acceptable for an OWNER grant.
- #50 still needs the introduction-copy decision (remove project claims from generic introduction vs. make it honor all named project entries) and a safe legacy-provenance policy. Do not infer historical provenance from timestamps; ambiguous pre-upgrade rows should remain unknown.
- This run did not execute local pytest, disposable PostgreSQL, migrations, schema audit, or DB-leakage checks. No code was changed in this verification update; the only engineering action beyond inspection was the #60 review comment.
- **NOT TEST READY. REAL WAHA ACTIONS: NONE.** No production DB mutation, WAHA reconnection, real send, private-media retention activation, approval, merge, or review-thread resolution occurred.

---

## Release verification — 2026-11-01 16:25 WAT

This source-grounded gate review supersedes the 10:27 WAT snapshot below. It is not release approval. Branch-local green runs do not prove the integrated 001–040 migration chain.

### Mechanical engineering gates

| Gate | Current evidence | Release status |
|---|---|---|
| Main baseline | `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed 2026-09-08; main has migrations 001–033 | Stale; exact main suite must be rerun on the reviewed release candidate |
| Main workflow controls | Main workflow applies SQL files lexically and runs pytest at a 57% coverage floor | No sequence preflight, schema audit, or post-test leakage gate on main |
| Migration sequence | #61 head `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`, run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | Candidate only; not merged |
| Fresh integrated migrations | Main 001–033; #48=034, #50=035, #49=036–037, #60=038–040 | No single 001–040 chain proved |
| Installed upgrade / rerun | No disposable 033→040 upgrade plus second-run no-op/checksum result | Not proved |
| Deployment target / seed / sequence guards | #62 head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`, run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed 864 tests / 76.01% | Candidate only; not integrated with #60 runtime-role boundary |
| Schema audit / DB leakage | #55 run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) passed 815 / 76.01%; #62 reports schema and leakage checks passed on its branch | Candidate only; not integrated 001–040 evidence |
| Runtime DB-role isolation | #60 head `e0685c8bbeb380a684816b463ddd4f8eee4db10c`, run [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) cancelled after the runtime-role test failed and timed out | Not proved |
| Consent audit tamper resistance | Runtime role is intended to have SELECT/INSERT only; incoming memberships where runtime is the granted role remain unchecked | Not proved |
| P0 contact consent | Implemented only on open #60; absent from main | Not verified on main |
| Independent review | #60 9 unresolved; #62 7; #59 3; #50 3; #49 1; #57 1; #63 1 | Blocking review remains |
| OWNER policy decisions | STOP permanence and consent-grant evidence semantics remain undecided | Required before P0 acceptance |
| Controlled test plan | OWNER self-DM text → commands → media/view-once → one explicitly approved external contact | Do not start |

### Current blockers and next work

1. Reproduce `test_runtime_role_cannot_mutate_or_disable_consent_history` alone on disposable PostgreSQL. The latest run proves the Compose helper regressions now pass, but the runtime-role node still fails and the job times out; there is no captured assertion traceback or final coverage result.
2. Inspect role memberships in both directions: where the runtime role is `pg_auth_members.member` and where it is `pg_auth_members.roleid`. Add a regression using a second temporary role granted `zina_runtime`; revoke/reject that membership before runtime credentials are issued.
3. Consolidate #60 with #62/#61/#57/#55. Neither #60 nor #62 is independently mergeable: #60 lacks target/seed/sequence preflights; #62 still exposes broad `.env.production` to API/WAHA/migrate and lacks the restricted runtime role. Complete all preflights before DDL and preserve service-specific credentials.
4. Run one exact candidate through fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum, schema audit, DB leakage, P0 adversarial matrix, and runtime-role privilege proof.
5. Obtain independent review for the remaining inline threads. No approval or merge is implied by green branch-local CI or resolved-thread counts.
6. Obtain OWNER decisions on terminal STOP behavior and consent evidence. Resolve #50's introduction-copy scope and legacy provenance without timestamp inference.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.** No production DB operation, WAHA reconnection, real WhatsApp send, private-media retention activation, merge, or approval occurred in this run.

---

## Release verification — 2026-11-01 10:27 WAT

This live source-grounded gate review supersedes the 08:21 WAT overlay below. It is not release approval; green branch-local runs do not prove the integrated feature migration chain.

### Mechanical engineering gates

| Gate | Current evidence | Release status |
|---|---|---|
| Main exact-head suite | Main `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded 2026-09-08 | Stale; main has not moved since 2026-09-08 |
| Migration sequence | #61 head `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`, run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | Candidate only; not merged |
| Fresh integrated migrations | Main 001–033; branch allocation #48=034, #50=035, #49=036–037, #60=038–040 | No single 001–040 chain proved |
| Installed upgrade / rerun | No disposable 033→040 upgrade plus second-run no-op/checksum result | Not proved |
| Deployment target / seed / sequence guards | #62 head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`, run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success | Candidate only; not integrated with #60 runtime-role boundary |
| Schema audit / DB leakage | #55 is carried in #62; #62 run reports schema audit and leakage passed on its branch, migrations 001–033 only | Candidate only; not an integrated 001–040 result |
| Runtime DB-role isolation | #60 exact head `93f97fd192a3141869a419f5832df89b888ca9e2`; run [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) cancelled after two test failures and timeout | Not proved |
| Consent audit tamper resistance | Runtime role has SELECT/INSERT-only consent-event privileges and sequence UPDATE revoked in source; incoming `zina_runtime` memberships are not yet revoked/verified | Not proved |
| P0 contact consent | Implemented only on open #60; absent from main | Not verified on main |
| Independent review | #60 8 unresolved; #62 7; #59 3; #50 3; #49 1; #57 1; #63 1 | Blocking review remains |
| OWNER policy decisions | STOP permanence and `.contact consent grant` evidence semantics remain undecided | Required before P0 acceptance |
| Controlled test plan | OWNER self-DM text → commands → media/view-once → one explicitly approved external contact | Do not start |

### Live PR state

| PR | Exact head | Tests result | Unresolved / total threads |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 / 76.67% | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 / 76.52% | 3 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 / 76.01% | 0 / 0 |
| [#57 seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 docs refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `6150ff03c19bb52bc49afaf39b5c4e65058be9ea` before this refresh; this commit is docs-only `[skip ci]` | Parent code/test head `d8edcae5a8f16da22def88093a2573ab9ca8278f` run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250) passed 797 / 76.01%, migrations 001–033 only | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `93f97fd192a3141869a419f5832df89b888ca9e2` | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) cancelled; two failures + timeout; no final count/coverage | 8 / 8 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 / 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 / 76.08% | 1 / 1 |

All ten PRs remain open. No independent approval was found in the retrieved review submissions; comments and branch-local CI do not authorize merge.

### Blocking decisions and next engineering work

1. **Fix #60 CI first.** Correct the Compose helper so it selects the top-level `migrate` service, not `api.depends_on.migrate`. Isolate the runtime-role test failure on disposable PostgreSQL; the cancelled log has no assertion traceback, so no root cause is claimed.
2. **Complete role isolation.** The provisioner/validator inspect memberships where runtime is the member but not where runtime is the granted role. Revoke or reject memberships in both directions and test a temporary second role granted `zina_runtime`; keep the test guarded to disposable DBs with unique credentials and guaranteed cleanup.
3. **Integrate #60 with #62/#61/#57/#55.** Neither #60 nor #62 can be merged first: #60 lacks target/seed/sequence preflights; #62 still injects broad `.env.production` into API/WAHA/migrate and lacks the restricted runtime role. One candidate must preserve both sides before DDL and validate fresh 001–040, installed 033→040 upgrade, rerun/checksum, schema audit, DB leakage, and runtime privileges.
4. **OWNER must accept/revise the STOP policy.** Current behavior is terminal across a Contact's mapped aliases, with no re-consent/override. A STOP committed before final dispatch reservation vetoes; once a single WAHA request enters transport it cannot reliably be recalled, and uncertain sends must never be retried.
5. **OWNER must define consent-grant evidence.** `.contact consent grant` records an OWNER attestation and opaque evidence reference. Decide whether it identifies independently obtained contact consent (durable evidence outside Zina) or whether contact consent and OWNER automation permission remain separate authorities and both are required.
6. **Resolve #50 identity decisions.** `introduction_reply()` still mentions projects/Datacube AU while checking only Zina/Fabian; recommended fix is to keep the introduction minimal and route project facts through Identity Registry. Migration 035 still uses `updated_at = created_at` as historical provenance proof; leave ambiguous pre-033 rows unknown/NULL unless immutable evidence or explicit OWNER attestation exists.
7. **Keep #49 and #48 bounded.** #49 is a content-library foundation only, not live selection/producer/dashboard; it never grants send authority. #48 is metadata-only; private bytes and retention activation remain out of scope, with retention OFF.

**NOT TEST READY.** No integrated migration proof, installed-upgrade/no-op/checksum proof, combined schema/leakage proof, exact-head green #60 suite, independent review clearance, or OWNER policy decisions exist.

**REAL WAHA ACTIONS: NONE.** No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, merge, or approval occurred.

---
## Release verification — 2026-11-01 08:21 WAT

This is the current source-grounded gate review. It supersedes the 07:18 WAT snapshot below. It is not release approval. The documentation-only refresh commits use `[skip ci]`; the prior code/test head is not promoted to an exact-head result by these docs edits.

### Mechanical engineering gates

| Gate | Current evidence | Release status |
|---|---|---|
| Main exact-head full suite | Main `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), 2026-09-08 | Stale; re-run after reviewed integration |
| Fresh migration chain | Main has 001–033; feature branches allocate 034–040 | Not proved as one 001–040 candidate |
| Installed upgrade | No disposable 033→040 candidate proof | Not proved |
| Second-run no-op/checksums | No integrated candidate evidence | Not proved |
| Migration sequence guard | PR #61 exact head `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`, run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success; not merged | Candidate only |
| Schema audit / deployment preflight | PR #62 exact head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`, run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; not integrated with #60 | Candidate only |
| DB leakage | PR #55 exact head `3d35793ef72cfcfe1e188bc51df6d4e538679f7b`, run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success (815 passed, 76.01%); not merged | Candidate only |
| Runtime DB-role isolation | Implemented on PR #60, but exact-head run [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) was cancelled after two test failures and a fixture timeout | Not proved |
| Consent audit tamper resistance | Runtime role is intended to have SELECT/INSERT only; incoming `zina_runtime` memberships remain an open P2 review finding | Not proved |
| P0 contact consent | PR #60 only; absent from main | Not proved on main |
| Independent review | Open blocking threads remain on #49, #50, #57, #59, #60, #62, and #63 | Not cleared |
| Controlled test plan | Staged plan remains gated on the engineering/product criteria below | Do not start |

### Live PR and exact-head status

| PR | Head | Tests result | Unresolved / total threads |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 / 76.67% | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 / 76.52% | 3 / 11 |
| [#55 DB leakage](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 / 76.01% | 0 / 0 |
| [#57 seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 docs refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | Current docs refresh branch; this commit is docs-only `[skip ci]` | No exact-head test run | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `93f97fd192a3141869a419f5832df89b888ca9e2` | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) cancelled; 2 failures at 86%, 120s fixture timeout | 8 / 8 |
| [#61 migration sequence](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 / 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 / 76.08% | 1 / 1 |

All remain open. A green branch-local run is not an integrated release result; zero threads is not approval.

### Required integration and owner decisions

1. **#60/#62/#61 must be one candidate.** Migration allocation is now #48=034, #50=035, #49=036–037, #60=038–040, but no branch proves the complete chain. #60 has the restricted API runtime role and service-specific environments but lacks #62's target/seed/sequence preflights. #62 has those preflights but still exposes broad `.env.production` to API/WAHA/migrate and does not provision the restricted runtime role. Do not merge in either order.
2. **Repair current #60 CI before more hardening.** Run [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) is not green. The Compose allowlist test helper matches the nested `api.depends_on.migrate` key instead of the top-level migrate service; the exact fix is to parse YAML or anchor the service key at top-level indentation. The runtime-role test also failed, but its traceback was not emitted before cancellation; isolate it and verify cleanup before extending the timeout. Review note: [#6554967378](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6554967378).
3. **Role boundary:** prove runtime and migration roles are distinct, runtime owns no objects, cannot assume the migration role, and no other role can assume the runtime role unless explicitly allowed. Keep owner credentials out of API/WAHA.
4. **Consent policy:** OWNER must accept or revise terminal opt-out across mapped aliases and decide whether `.contact consent grant` is an attestation of independently obtained contact consent with durable external evidence, or whether contact consent and OWNER automation policy are separate authorities.
5. **Identity provenance:** preserve ambiguous pre-033 Identity Registry rows as unknown/NULL unless immutable evidence or explicit OWNER attestation proves their origin; do not infer provenance from `updated_at = created_at`. Decide whether generic introductions should mention only Zina/Fabian, with project facts routed through the registry.
6. **Product gates:** Identity lifecycle, FAQ per-entry CRUD, Knowledge edit/delete/disable, single Command Center authority, Scheduled Actions/Media/Conversation dashboard coverage, and accurate observability remain incomplete or candidate-only. #49 is not yet integrated into live producers/selection/dashboard. Private media byte retention must remain OFF.

### Readiness decision

**NOT TEST READY.** Do not begin Stage A–E controlled WhatsApp testing until an exact integrated candidate passes fresh 001–040, installed 033→040 upgrade, rerun/checksum, schema audit, DB leakage, runtime-role privilege tests, full pytest/coverage, P0 adversarial matrix, and independent review—and the OWNER decisions above are recorded.

**REAL WAHA ACTIONS: NONE.** No production DB mutation, WAHA reconnection, real send, approval, or merge occurred.

---

## Current verification — 2026-11-01 07:18 WAT

This overlay supersedes earlier snapshots. It is a source-grounded status review, not a test or release certification. Main and PR heads were re-fetched from GitHub for this update.

### Main and CI baseline

- Main remains 5aadd725ed9da08a5eb84eb42b64f0f45f231c79; its last commit is 2026-09-08. Main contains migrations 001–033 only.
- Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA on 2026-09-08. The checked-in workflow applies migrations lexically and runs pytest with a 57% coverage floor, but does not run migration-sequence preflight, schema audit, or the post-test DB-leakage audit.
- GitHub's rulesets endpoint returned an empty list, but the branch-protection read is not available to this integration. Do not assert current branch-protection state; the earlier unprotected finding remains historical/unverified.
- The latest exact-head run for PR #60, [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626), was cancelled at 2026-11-01 04:46 UTC on 93f97fd192a3141869a419f5832df89b888ca9e2. Migrations 001–033 and 038–040 completed, but pytest/coverage was cancelled; there is no exact-head test count or coverage result. Migrations 034–037 were skipped.

### Open PRs — exact current heads and review state

| PR | Exact head | Exact-head Tests evidence | Unresolved / total threads |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | 3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | 0a2b38c0ce72b3c4a8fdd49490be504facb34bac | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | bcd0033e024b177561b8afd41589afe1897ba4de | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | 3d35793ef72cfcfe1e188bc51df6d4e538679f7b | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| [#57 seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | d831ce4e3dd7e56f38d8563dc63abc44f8c37bba | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 docs refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | 61b8aa70b6137df5c0cf3e63ae4abcd5f23fa229 | No CI for docs-only [skip ci] commits; parent code/test head d8edcae5a8f16da22def88093a2573ab9ca8278f run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250) passed 797 tests / 76.01%, migrations 001–033 only | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | 93f97fd192a3141869a419f5832df89b888ca9e2 | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) cancelled during pytest/coverage; no count/coverage | 8 / 8 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | 8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | 13fad868affe01d6069f4288481f8cd8dd341c62 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All PRs remain open. The review submissions currently visible are comments, not independent approvals; zero threads is not approval.

### Migration and deployment integration

- The former duplicate migration 034 allocation is now renumbered at current branch heads: #48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040. The allocation is contiguous, but main still has only 001–033 and no candidate has proved a fresh integrated 001–040 chain plus installed 033→040 upgrade, second-run no-op/checksums, schema audit, and zero DB leakage.
- #60 and #62 remain unsafe to merge in either order. #60 has the restricted runtime-role/API/WAHA environment split but lacks #62's pre-DDL target, seed, and contiguous-sequence guards. #62 has those guards but still mounts broad .env.production into API/WAHA/migrate and does not provision the restricted runtime role. Consolidate both into one reviewed candidate.
- On #60, a new P2 review comment [6554387711](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6554387711) identifies an incomplete role-membership cleanup: the provisioner and validator check roles that zina_runtime belongs to, but do not check other roles that may be members of zina_runtime. Either revoke/fail on those incoming memberships and verify both directions, or prove the role is newly created with no prior grantees. This is review-only; no code or test result is claimed.

### P0 and OWNER decisions

- Main does not yet contain PR #60's contact-consent state, opt-out receipts, or final consent fence. Until #60 is integrated and independently reviewed, explicit contact consent/terminal opt-out is not a verified main-branch capability.
- #60's current policy makes opt-out terminal across the Contact's mapped aliases and has no owner re-consent/override command. OWNER must explicitly accept or revise this policy. A STOP committed before final dispatch reservation vetoes; once the single WAHA request has entered transport, it cannot reliably be recalled, and an uncertain attempt must never be replayed.
- The .contact consent grant command records an OWNER attestation plus an opaque evidence reference; OWNER must decide whether that means independently obtained contact consent exists and the reference points to durable external evidence, or whether contact consent and OWNER automation permission must be modelled as separate authorities.
- #50's registry-read failure path now returns a non-assertive fallback, but its generic introduction still names projects/Datacube AU without checking those registry keys. The outstanding recommendation is to keep the generic introduction limited to Zina/Fabian and answer project facts through Identity Registry.
- Migration 035 still uses updated_at = created_at as historical provenance evidence. That cannot reliably distinguish old default rows from administrator-edited rows whose timestamps were already advanced by pre-033 read/update behavior. Preserve ambiguous legacy rows as unknown/NULL unless OWNER-approved evidence exists; do not infer system provenance from that equality.

### Readiness

- No integrated migration proof, installed upgrade proof, combined schema/leakage proof, exact-head green test for #60, independent approvals, or OWNER policy decisions are present.
- Controlled-test plan remains staged OWNER self-DM text → commands → media/view-once → one explicitly approved external contact. Do not exercise live WhatsApp autonomously.
- **NOT TEST READY. No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, merge, approval, or review-thread resolution occurred in this verification.**

---

## Current release verification — 2026-11-01 06:21 WAT (NOT TEST READY)

This overlay supersedes the historical snapshots below. Verification is against current GitHub state; a green branch-local run is not an integrated release result.

### Current baseline and CI

- Main SHA: 5aadd725ed9da08a5eb84eb42b64f0f45f231c79; last main commit 2026-09-08; main migrations 001–033. Branch-protection/ruleset state could not be re-queried (GitHub API 403 Resource not accessible by integration); the earlier unprotected/no-required-checks finding remains historical only.
- Main workflow .github/workflows/tests.yml (blob 445b1fd628489b6a3b1c4f463880e4a1e709e978) applies migrations lexically and runs pytest with a 57% coverage floor. It does not include migration-sequence preflight, schema audit, or DB-leakage audit.
- Latest exact-head Tests run [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) on PR #60 head 93f97fd192a3141869a419f5832df89b888ca9e2 was CANCELLED at 2026-11-01T04:46:00Z. Migrations 001–033 and 038–040 completed, then pytest/coverage was cancelled; no test count or coverage result exists for this head. Feature migrations 034–037 were skipped.
- Latest completed successful run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250) ran on PR #59 parent head d8edcae5a8f16da22def88093a2573ab9ca8278f: 797 passed, 1 warning, 76.01% coverage; only migrations 001–033. It is not feature-chain or release proof.
- PR #60 commits d14d6eb6a7c0c3e7e382b0552b9e16e65fffe630 and 93f97fd192a3141869a419f5832df89b888ca9e2 narrow sequence privileges, test setval() denial, guard the runtime-role integration test to a disposable target, use unique credentials, clean up the temporary role/grants, and fix an undefined migration_runner reference. Exact-head CI was cancelled during pytest/coverage; independent review remains pending.
- This docs-only refresh is marked [skip ci]; no exact-head CI result is claimed for this docs commit.

### Open PRs — exact heads and unresolved / total review threads

| PR | Exact head (short) | Latest exact-head Tests run | Unresolved / total |
|---|---|---|---:|
| #48 PrivateMediaArtifact | 3acacbfe | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| #50 Identity Registry | 0a2b38c0 | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 |
| #49 Outbound Message Library | bcd0033e | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 |
| #55 DB-leakage CI gate | 3d35793e | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| #57 local seed safety | d831ce4e | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| #59 documentation refresh | Self-updating docs branch; see live PR | No CI for [skip ci] docs-only commits; prior code/test head d8edcae5 run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250) passed 797 tests, 76.01%, migrations 001–033 | 3 / 3 |
| #60 P0 contact consent | 93f97fd1 | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) CANCELLED during pytest/coverage after 001–033 and 038–040; no test count/coverage | 8 / 8 |
| #61 migration-sequence gate | 8a1c1dbf | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| #62 deployment integration | a8d032de | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| #63 conversation observability | 13fad868 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All PRs remain open. Zero review threads is not approval; unresolved threads require independent review.

### Blocking release gates

- [ ] One integrated migration candidate: feature allocation is #48=034, #50=035, #49=036–037, #60=038–040. Main has only 001–033. No exact candidate has proven fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum behavior, schema audit, and zero DB leakage together.
- [ ] Consolidate #60 and #62 before either merge: #60 has the runtime-role/API/WAHA environment split but lacks #62's pre-DDL target, local-seed, and sequence guards. #62 has those guards but still mounts .env.production into API, WAHA, and migrate and does not provision the restricted runtime role. Either merge order can undo the other's safety boundary.
- [ ] Verify #60's new runtime-role safeguards: the test is now guarded to the disposable CI database or explicit local *_test target, uses unique credentials and cleans up role grants/default ACLs; the consent-event sequence denies UPDATE/setval(). Exact-head run 41273052626 was cancelled during pytest/coverage after migrations 001–033 and 038–040; no test count or coverage result exists for this head.
- [ ] P0 STOP policy acceptance: current policy makes opt-out terminal across mapped aliases and has no owner re-consent/override. The OWNER must explicitly accept or revise it. A STOP committed before final reservation vetoes; an already in-flight WAHA attempt cannot reliably be recalled and must never be blindly retried/replayed.
- [ ] Identity Registry decisions (#50): decide whether generic introductions remove project/Datacube claims (recommended) or gate every named registry fact; leave unverifiable legacy provenance NULL/unknown rather than infer it from timestamps, unless OWNER attestation is approved.
- [ ] Independent review: #60 has 8 unresolved threads; #62 has 7; #50 has 3; #49 has 1; #59 has 3; #57 has 1; #63 has 1. No self-approval, self-resolution, or merge.
- [ ] Controlled-test plan and explicit authorization: stage OWNER self-DM text → commands → media/view-once → one explicitly approved external contact. Do not exercise live WhatsApp autonomously.

### Deferred work

- #48 remains metadata-only; private bytes are absent and retention must stay OFF.
- #49 remains a content library foundation, not a live producer/selector/dashboard; do not wire it into outbound until P0 and migration integration are cleared.
- True embedding-based FAQ/Knowledge retrieval, DerivedArtifact media intelligence, and Project Intelligence remain later work.

**NOT TEST READY.** The latest #60 exact-head workflow is in progress, the integrated feature migration chain is unproven, and blocking review/OWNER/operator decisions remain. No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, PR merge, or review-thread resolution occurred in this verification.

## Historical release-verification snapshot — 2026-10-31 21:18 WAT (superseded by the current overlay above)

This section supersedes older status snapshots below. Main and the open PRs were re-read from GitHub; branch-local CI is not treated as integrated release proof.

### Current baseline

- Main SHA: `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last commit 2026-09-08; migrations 001–033.
- Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA. The current main workflow applies migrations lexically and runs pytest/57% coverage; it lacks the migration-sequence preflight, schema audit, and post-test leakage audit.
- Latest observed Tests run [41202363597](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202363597) succeeded on PR #59 exact head `611c9d5528df16f5831fa970032237d4988fa52e`: 797 passed, 1 warning, 76.01% coverage, migrations 001–033 only.

### Exact open PR and review state

| PR | Head (short) | Latest exact-head run | Unresolved / total threads |
|---|---|---|---:|
| #48 PrivateMediaArtifact observation | `3acacbfe` | #40158094566 success | 0 / 15 |
| #50 Identity Registry lifecycle | `0a2b38c0` | #41202063757 success; 828 passed, 76.52% | 3 / 11 |
| #49 Outbound Message Library foundation | `bcd0033e` | #39920982545 success; 896 passed, 76.67% | 1 / 80 |
| #55 DB-leakage CI gate | `3d35793e` | #41026581000 success; 815 passed, 76.01% | 0 / 0 |
| #57 deployment seed safety | `d831ce4e` | #40169146406 success | 1 / 1 |
| #59 this documentation refresh | `611c9d55` | #41202363597 success; 797 passed, 76.01% | 1 / 1 |
| #60 P0 contact consent | `552a7ca0` | #41192776180 success; 927 passed, 76.41% | 5 / 5 |
| #61 migration sequence gate | `8a1c1dbf` | #40300425938 success | 0 / 0 |
| #62 deployment integration | `a8d032de` | #41073226073 success; 864 passed, 76.01% | 7 / 7 |
| #63 conversation observability | `13fad868` | #41080836429 success; 803 passed, 76.08% | 1 / 1 |

Zero review threads is not equivalent to an independent approval. The PRs remain open; no merge is implied.

### Blocking engineering and product gates

- [ ] **P0 consent-history privilege boundary:** #60's migration 038 triggers reject ordinary UPDATE/DELETE/TRUNCATE, but the table owner can disable triggers or alter the table. The sample config uses `postgres` for both `DATABASE_URL` and `DATABASE_URL_SYNC`; Compose supplies the same `.env.production` to API and migrate. Provision a distinct non-owner/non-superuser API role, keep migration-owner credentials out of the API container, grant only required runtime privileges, and prove denied ALTER/trigger-disable/UPDATE/DELETE/TRUNCATE on disposable PostgreSQL under that runtime role.
- [ ] **Explicit STOP policy acceptance:** #60 makes opt-out terminal with no owner override/re-consent command. A STOP committed before final reservation blocks dispatch; an already in-flight WAHA attempt cannot reliably be recalled, must never be retried/replayed, and subsequent sends remain denied. Obtain explicit owner acceptance or revise the policy before declaring P0 complete.
- [ ] **Identity Registry introduction contract:** #50's shared greeting checks assistant/owner identity but still names projects and Datacube AU. Decide to remove project claims from generic introductions (recommended; project facts remain owned by Identity Registry) or gate every named fact and test all combinations.
- [ ] **Truthful legacy provenance:** #50 must not infer seed origin from `updated_at = created_at`; earlier reads already changed timestamps. Leave unverifiable legacy rows unknown/NULL, stamp provenance for new default inserts, and require explicit owner attestation for any historical classification.
- [ ] **Integrated migration proof:** run one exact candidate with fresh contiguous migrations **001–040**, then an installed **033→040** upgrade and second-run no-op/checksum verification. Current allocation is #48=034, #50=035, #49=036–037, #60=038–040.
- [ ] **Exact-candidate verification:** on that same candidate run full pytest/coverage, P0 adversarial matrix, schema audit, and post-test DB-leakage audit. Existing branch-local runs skip feature prerequisites: #50 applies 035 without 034; #49 applies 036–037 without 034–035; #60 applies 038–040 without 034–037.
- [ ] **Independent review:** resolve blocking review threads through independent review; do not self-resolve, self-approve, or merge. #60 has 5 unresolved threads; #62 has 7; #50 has 3; #49 has 1; #57, #59, and #63 each have 1.
- [ ] **Deployment runner integration:** #62 is the draft integration candidate for #57 seed safety and #61 migration preflight. Its exact-head CI covered 001–033 plus schema/leakage checks, not 034–040. Keep #57/#61 coordinated with #62 rather than merging overlapping runner changes separately.
- [ ] **Controlled-test plan and explicit authorization:** stage owner self-DM text → commands → media/view-once → one explicitly approved external contact. No autonomous live WhatsApp test.

### Deferred / not required to clear the above gates

- Private media bytes remain absent and retention must stay OFF.
- Outbound Message Library #49 remains a content foundation only; it must not be wired to producers until P0 authority and migration integration are cleared.
- True embedding-based FAQ/Knowledge retrieval, DerivedArtifact media intelligence, and Project Intelligence remain separate later roadmap work.

**NOT TEST READY.** The latest successful branch CI is not a full release candidate. No production DB operation, production WAHA reconnection, real WhatsApp send, private-media retention activation, PR merge, or review-thread resolution occurred in this verification run.


---

## Live release-verification delta — 2026-10-31 (fresh re-query; partial; NOT TEST READY)

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08, with migrations 001–033 only. Branch protection is false and repository rulesets are empty. Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that SHA; the main workflow still lacks sequence preflight, schema audit, and post-test leakage audit.
- Latest exact-head Tests run [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) passed on PR #50 head `0a2b38c0ce72b3c4a8fdd49490be504facb34bac`: **828 passed, 1 warning, 76.52%**. It applied 001–033 and 035 only; it does not prove integrated migrations 001–040.
- Current open PR review threads (unresolved / total): #48 0/15; #49 1/80; #50 3/11; #55 0/0; #57 1/1; #59 1/1; #60 5/5; #61 0/0; #62 7/7; #63 1/1. Replies and green CI do not equal independent approval.
- Feature migration numbering is ordered across branches: #48=034, #50=035, #49=036–037, #60=038–040. No exact candidate proves fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, or combined leakage.
- #60 is still draft/unmerged. Its exact head `552a7ca0` passed [41192776180](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192776180): 927 passed, 1 warning, 76.41%; its workflow applied 001–033 and 038–040 only. Five review threads remain open.
- **P0 database security blocker:** migration 038's append-only consent-event triggers can be disabled by the table owner. Compose still gives API and migrate the same `.env.production`, and the sample uses the same `postgres` role for async/sync URLs. Separate the runtime login from the migration/table-owner login; prove the runtime role cannot ALTER/DISABLE TRIGGER/UPDATE/DELETE/TRUNCATE using disposable PostgreSQL before treating consent history as tamper-resistant.
- **Human STOP policy decision:** a STOP committed before the final reservation blocks dispatch; once one WAHA attempt has crossed the final reservation it cannot reliably be recalled, but it must never be retried/replayed and later sends must be denied. Fabian must explicitly accept or revise this linearization policy.
- #62 remains the draft deployment integration candidate with seven unresolved review threads. It includes seed safety, migration sequence preflight, schema audit, and leakage audit, but still lacks API/migration role separation. #57 and #61 should not be merged independently of this integration.
- #50's P1 registry-read failure now returns the non-assertive fallback on exceptions in both reply methods, with three regressions and green exact-head CI. Two decisions remain: whether introduction text may name projects/Datacube AU when only Zina/Fabian are gated, and how to identify historical default rows without timestamp equality.
- #49 remains a foundation only; #48 remains metadata-only with retention OFF. #63's observability correction is green but still has one independent-review thread.
- [ ] Fresh contiguous migrations 001–040 on one exact integration candidate.
- [ ] Installed 033→040 upgrade, second-run no-op, and checksum verification.
- [ ] Exact-candidate full pytest/coverage, P0 adversarial matrix, schema audit, and zero DB leakage.
- [ ] Independent resolution of blocking reviews and owner decisions; separate DB roles and prove runtime privilege restrictions.
- [ ] Staged controlled-test plan and explicit authorization.

**NOT TEST READY.** No production DB operation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred. The documentation head before this refresh passed run [41192933035](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192933035) (797 passed, 76.01%, migrations 001–033); this new documentation commit has no exact-head CI result yet.

## Live release-verification delta — 2026-10-31 (partial; NOT TEST READY)

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08; migrations 001–033 only. Branch protection is false and no repository rulesets were returned. Latest main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that SHA; the main workflow still lacks sequence preflight, schema audit, and post-test leakage audit.
- Latest overall Tests run [41192776180](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192776180) is **in progress** on PR #60 head `552a7ca0ce4104beeb3f38fa749c1e332118d8cb`; no test count or coverage is claimed. Latest completed run [41168835614](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41168835614) succeeded on PR #59 head `7df2055d5e1f28d32fa7c4b1c16b012289a639d9` (797 passed, 76.01%, migrations 001–033).
- Open PR review threads (unresolved / total): #48 0/15; #49 1/80; #50 3/11; #55 0/0; #57 1/1; #59 1/1; #60 5/5; #61 0/0; #62 7/7; #63 1/1. Replies and green CI do not equal independent approval.
- Feature migration numbering is now ordered across branches: #48=034, #50=035, #49=036–037, #60=038–040. The former duplicate 034 allocation is resolved, but no exact candidate proves fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, or combined leakage.
- PR #60 remains draft/unmerged and is the current P0 consent work. The new head adds anchored, conservative opt-out parsing and quoted/reported-phrase regressions; its exact-head Tests run is still in progress. Its predecessor's green run does not validate the new head. Five review threads remain unresolved.
- **Human policy decision:** accept or revise the STOP reservation boundary. A STOP visible before final reservation vetoes dispatch; an already-in-flight WAHA attempt cannot reliably be recalled, but must never be retried/replayed; all later sends must be denied.
- **Database security decision/blocker:** API and migrate still receive the same `.env.production`; `.env.example` uses the same `postgres` role for async and sync URLs. The API can own the consent audit table and disable its triggers. Provision a distinct migration/table-owner role and a restricted runtime role, then prove runtime cannot ALTER/DISABLE TRIGGER/UPDATE/DELETE/TRUNCATE in disposable PostgreSQL before calling consent history tamper-resistant.
- PR #62 remains the deployment integration candidate with seven unresolved review threads; it includes seed safety, migration-sequence preflight, schema audit, and leakage audit, but still lacks the API/migration role split.
- PR #50 has three unresolved identity decisions: introduction claim scope, reliable legacy-default provenance (do not use `updated_at = created_at`), and fail-closed behavior when Identity Registry reads fail.
- PR #49 is foundation-only, not integrated into a live producer/selector/dashboard. PR #48 is metadata-only; private byte storage is not implemented and retention stays OFF. PR #63's observability correction has green exact-head CI but one unresolved independent-review thread.
- [ ] Fresh contiguous migrations 001–040 on one exact integration candidate.
- [ ] Installed 033→040 upgrade, second-run no-op, and checksum verification.
- [ ] Exact-candidate full pytest/coverage, P0 adversarial matrix, schema audit, and zero DB leakage.
- [ ] Independent review of P0, identity, and deployment blockers; explicit owner decisions; staged controlled-test plan and authorization.

**NOT TEST READY.** No production database operation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred.

## Latest live release-verification delta — 2026-10-30 (after Tests run 41080836429; partial; NOT TEST READY)

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08, with migrations 001–033. Main reports `protected=false`; no repository rulesets were returned.
- Latest observed exact-head Tests run [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) passed on PR #63 head `13fad868affe01d6069f4288481f8cd8dd341c62`: 803 passed, 1 warning, 76.08% coverage; it applied 001–033 only. The PR #55 DB-leakage audit is not part of main's workflow.
- PR #63's malformed internet audit-value finding is fixed and exact-head CI is green; one review thread remains unresolved for independent review.
- Open PR review-thread counts (unresolved / total): #48 0/15; #49 1/80; #50 3/11; #55 0/0; #57 1/1; #59 1/1; #60 5/5; #61 0/0; #62 7/7; #63 1/1. No self-approval or thread resolution is implied.
- Migration order is now allocated as #48=034, #50=035, #49=036–037, #60=038–040. **No exact candidate has proved the integrated fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, or combined leakage gate.**
- PR #60's exact-head CI passed 915 tests at 76.43%, but its branch applies 001–033 plus 038–040 and skips 034–037. Contact consent is not yet a main-branch guarantee; five review threads remain unresolved.
- PR #62's exact-head CI passed 864 tests at 76.01% with migration preflight, 001–033, schema audit, and leakage audit. Seven deployment threads remain unresolved; API and migrate still share `.env.production`.
- **Restricted runtime database role remains a release blocker.** The API currently uses the table-owner credentials shown in `.env.example`; trigger guards can be disabled by the owner. A distinct restricted runtime role and disposable-PostgreSQL privilege proof are not implemented.
- **P0/architecture decisions:** accept or revise the STOP dispatch-reservation boundary; approve the migration-owner/runtime-role split and credential bootstrap; decide whether the shared introduction removes project/Datacube claims or gates them on `projects`/`datacube_au`; choose a trustworthy legacy-default provenance policy; and define fail-closed behavior for Identity Registry read failures after migration 033. PR #50 has three unresolved threads, including the new P1 finding that both shared reply boundaries fall back to hardcoded identity when registry reads raise.
- [ ] Fresh contiguous migrations 001–040 on one exact integration candidate.
- [ ] Installed 033→040 upgrade, second-run no-op, and checksum verification.
- [ ] Exact-candidate full pytest/coverage, P0 adversarial matrix, schema audit, and zero DB leakage.
- [ ] Restricted runtime role cannot UPDATE/DELETE/TRUNCATE or ALTER/disable consent-history triggers.
- [ ] Independent review of the five #60, seven #62, two #50, and remaining #49/#57/#59/#63 review threads.
- [ ] Main-branch required-review governance configured and verified.
- [ ] Controlled test plan written and explicitly authorized by Fabian.

**NOT TEST READY.** No production database operation, production WAHA reconnection, private-media retention activation, or real WhatsApp action occurred.

---

## Latest live release-verification delta — 2026-10-30 15:40 WAT (partial; NOT TEST READY)

This supersedes the 15:21 WAT snapshot below. All ten open PR heads, exact-head Tests runs, review-thread counts, main workflow YAML, migration allocation, and deployment configuration were re-queried after PR #62 gained the schema/leakage audit steps.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033 only; main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that SHA. Main branch endpoint reports `protected=false`.
- Latest overall Tests run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed on PR #62 exact head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`: **864 passed, 1 warning, 76.01% coverage**. Migration-sequence preflight, 001–033 migrations, ORM schema audit, full pytest, and post-test DB-leakage audit all passed.
- PR #59 exact head `05e4bfb` passed [41072066479](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41072066479): 797 passed, 76.01%, migrations 001–033 only.
- Main `.github/workflows/tests.yml` remains unchanged: lexical migrations + 57% pytest gate, without sequence preflight, schema audit, leakage audit, or job timeout. Main deployment runner still lacks sequence preflight and applies seeds unconditionally.

| PR | Exact head | Exact-head Tests run | Result | Unresolved / total threads |
|---|---|---:|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | success | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `f78bc9bb` | [40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) | success | 2 / 10 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793e` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | success | 0 / 0 |
| [#57 Deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | success | 1 / 1 |
| [#59 Release docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `05e4bfb` | [41072066479](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41072066479) | success | 1 / 1 |
| [#60 Contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9071c09d` | [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) | success | 5 / 5 |
| [#61 Migration sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | success | 0 / 0 |
| [#62 Deployment integration + CI audits](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) | success | 7 / 7 |
| [#63 Conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `c6c493d2` | [40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) | success | 0 / 0 |

All listed run records match current PR head SHAs. These remain branch-local checks; no single run proves the integrated feature migration chain.

### Mechanical release gates

- [ ] One exact integrated candidate applies contiguous migrations 001–040 from an empty PostgreSQL database.
- [ ] Installed database upgrade 033→040, second-run no-op, and checksum verification.
- [ ] Exact integrated-candidate full pytest/coverage and P0 adversarial matrix.
- [ ] Combined-candidate schema audit and zero DB leakage, including Contact and raw cleanup tables.
- [ ] API runtime DB role is distinct from migration/table owner and cannot UPDATE/DELETE/TRUNCATE or ALTER/disable consent-history triggers; prove with disposable PostgreSQL.
- [ ] Independent review of #60's five P0 threads, #62's seven deployment threads, #50's two Identity Registry decisions, and remaining #49/#57/#59 findings.
- [ ] Main-branch protection and required independent review configured and verified.

### Current P0/product blockers

- **#60** remains unmerged; exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed 915 tests at 76.43% but applied 001–033 plus 038–040, skipping 034–037. Current mapping/alias-opt-out/missing-ID/trigger regressions are present; all five review threads remain unresolved. The trigger owner can still disable it.
- **#62** now combines deployment seed safety, contiguous migration preflight, ORM schema audit, and Contact-inclusive post-test leakage audit; exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed 864 tests at 76.01% on 001–033. Seven review threads remain unresolved and API/migrate still share .env.production, so the restricted runtime-role boundary is absent.
- **STOP reservation semantics** need explicit product-owner acceptance: a STOP before final reservation vetoes the send; after reservation, the in-flight attempt may not be retractable, but later sends/replays must be blocked.
- Migration allocations are reconciled as #48=034, #50=035, #49=036–037, #60=038–040. The combined 001–040 fresh/upgrade/no-op proof remains unchecked.
- **#50** still needs decisions on project/Datacube introduction claims and legacy provenance. **#49** remains foundation-only. **#48** remains metadata-only; retention OFF.
- **#55**'s audit is now included in #62, but #55 remains open for history and must not be merged independently while #62 is reviewed. Its earlier exact-head audit run covered 001–033 only. **#63** remains unmerged without independent review.

### Human decision required

Choose the runtime-role provisioning/rotation contract for existing deployments; accept or revise STOP reservation semantics; decide whether introduction text must gate `projects` and `datacube_au`; approve a legacy provenance policy; and configure required independent review on main.

**NOT TEST READY.** Controlled WhatsApp testing remains unauthorized. No production database mutation, production WAHA reconnection, or real WAHA send occurred.

---

## Latest live release-verification delta — 2026-10-30 15:21 WAT (partial; NOT TEST READY)

This supersedes the 14:21 WAT snapshot below. The current main ref, all ten open PR heads, their exact-head workflow runs, review-thread counts, main workflow YAML, migrations, and deployment configuration were re-queried. No merge or live WhatsApp test is authorized by this snapshot.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033 only. Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that SHA on 2026-09-08. Main branch endpoint reports `protected=false`.
- Latest overall Tests run [41063661288](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41063661288) succeeded on PR #59's exact current head `805f3fdd8e92a5bd1fa4724913986a9ce4a93ec1`: **797 passed, 1 warning, 76.01% coverage**. The job log confirms it applied 001–033 only.
- Main `.github/workflows/tests.yml` applies migrations lexically and runs pytest with a 57% floor; it has no sequence preflight, schema audit, post-test leakage audit, or timeout. Main deployment runner still lacks sequence preflight and unconditionally applies seed files.

| PR | Exact head | Exact-head Tests run | Result | Unresolved / total threads |
|---|---|---:|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | success | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `f78bc9bb` | [40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) | success | 2 / 10 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793e` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | success | 0 / 0 |
| [#57 Deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | success | 1 / 1 |
| [#59 Release docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `805f3fdd` | [41063661288](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41063661288) | success | 1 / 1 |
| [#60 Contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9071c09d` | [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) | success | 5 / 5 |
| [#61 Migration sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | success | 0 / 0 |
| [#62 Deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `854439af` | [40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923) | success | 7 / 7 |
| [#63 Conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `c6c493d2` | [40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) | success | 0 / 0 |

All listed run records were checked against their current PR head SHA. Branch-local green checks do not prove an integrated candidate, resolve review threads, or constitute independent approval.

### Mechanical release gates

- [ ] One exact integrated candidate applies contiguous migrations 001–040 from an empty PostgreSQL database.
- [ ] Installed database upgrade 033→040, second-run no-op, and checksum verification.
- [ ] Exact integrated-candidate full pytest/coverage and P0 adversarial matrix.
- [ ] Combined-candidate schema audit and zero DB leakage, including Contact and raw cleanup tables.
- [ ] API runtime DB role is distinct from migration/table owner and cannot UPDATE/DELETE/TRUNCATE or ALTER/disable consent-history triggers; prove with disposable PostgreSQL.
- [ ] Independent review of #60's five P0 threads, #62's seven deployment threads, #50's two Identity Registry decisions, and remaining #49/#57/#59 findings.
- [ ] Main-branch protection and required independent review configured and verified.

### Current P0/product blockers

- **#60** exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed 915 tests at 76.43%, but applied 001–033 plus 038–040 and skipped 034–037. Current code covers exact mapping, alias-wide terminal opt-out, missing stable source IDs, and UPDATE/DELETE/TRUNCATE guards; all five review threads remain unresolved. The trigger can still be disabled by the table owner.
- **#62** exact-head run [40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923) passed 846 tests at 76.01% on 001–033 with sequence/seed checks. Seven review threads remain unresolved; the API and migrate services still share `.env.production`, so the restricted runtime-role boundary is absent.
- **STOP reservation semantics** need explicit product-owner acceptance: STOP committed before final reservation vetoes the send; after reservation, the one in-flight attempt may not be retractable, but subsequent sends/replays must be blocked.
- Migration allocations are reconciled as #48=034, #50=035, #49=036–037, #60=038–040. The combined 001–040 fresh/upgrade/no-op proof remains unchecked.
- **#50** still needs decisions on project/Datacube introduction claims and reliable legacy-default provenance. **#49** remains library foundation only. **#48** remains metadata-only; retention OFF.
- **#55** passed its Contact-inclusive leakage audit on 001–033 only; no combined-candidate leakage result exists. **#63**'s observability fix remains unmerged.

### Human decision required

Choose the runtime-role provisioning/rotation contract for existing deployments; accept or revise the STOP reservation boundary; decide whether introduction text must gate `projects` and `datacube_au`; approve a legacy provenance policy; and configure required independent review on main.

**NOT TEST READY.** Controlled WhatsApp testing remains unauthorized. No production database mutation, production WAHA reconnection, or real WAHA send occurred.

---



## Live release-verification delta — 2026-10-30 14:21 WAT (partial; NOT TEST READY)

This supersedes the 12:16 WAT snapshot below. Current main, all open PR heads, exact-head Actions runs, inline review-thread resolution state, workflow YAML, migration directories, and deployment/Compose configuration were re-queried.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033, last commit and latest main Tests run on 2026-09-08. Main run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that SHA. Branch endpoint: `protected=false`; rulesets: `[]`; classic protection endpoint is not accessible through this integration.
- Latest overall Tests run is [41047370340](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41047370340) on the pre-refresh PR #59 head `a2a9e9295cd04c98cbd397667a4e9fd5fb4d1f5b`: **797 passed, 1 warning, 76.01% coverage**, migrations 001–033 only. The new docs commit requires its own exact-head run.
- Current unresolved / total review threads: #48 0/15; #49 1/80; #50 2/10; #55 0/0; #57 1/1; #59 1/1; #60 5/5; #61 0/0; #62 7/7; #63 0/0. Replies do not resolve threads unless GitHub marks `is_resolved=true`.

### Mechanical release gates

- [ ] One exact integrated candidate applies contiguous migrations 001–040 from an empty PostgreSQL database.
- [ ] Installed database upgrade 033→040, second-run no-op, and checksum verification.
- [ ] Exact-candidate full pytest/coverage and P0 adversarial matrix.
- [ ] Combined-candidate schema audit and zero DB leakage, including Contact and raw cleanup tables.
- [ ] Restricted runtime DB role is distinct from migration/table owner and cannot UPDATE/DELETE/TRUNCATE or ALTER/disable consent-history triggers; verify with disposable PostgreSQL.
- [ ] Independent review of #60's five P0 threads, #62's seven deployment threads, #50's two Identity Registry decisions, and the remaining #49/#57/#59 threads.
- [ ] Main-branch governance/required independent review configured and verified.

### Current product/architecture blockers

- **Contact consent is only on unmerged PR #60.** Exact-head Tests run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed 915 tests at 76.43%, but applied 001–033 plus 038–040 and skipped 034–037. The five review threads include current mapping, contact-wide opt-out, missing source message ID, append-only event protection, and the still-unimplemented restricted runtime-role boundary.
- **Consent history is not tamper-resistant yet.** Current `.env.example` uses the same `postgres` role for `DATABASE_URL` and `DATABASE_URL_SYNC`; Compose gives API and migrate the same `.env.production`. A table owner can disable the trigger. The role split needs an explicit credential/provisioning decision and disposable-PostgreSQL permission tests.
- **Deployment/migration runner:** PR #62's exact head passed 846 tests at 76.01% on 001–033 and its sequence/seed-policy checks, but has seven unresolved review threads. It does not include the feature migrations or prove the 001–040 chain.
- **Identity Registry:** PR #50 has two unresolved decisions: introduction paths must consistently honor unavailable registry facts, and legacy default provenance must not use the unreliable `updated_at = created_at` heuristic.
- **Outbound Library:** #49 is still foundation-only; no live producer, selection, or dashboard integration. Private-media retention remains OFF.

### Migration order and evidence boundary

Current branch allocations are #48=034, #50=035, #49=036–037, #60=038–040. The old 034 collision is resolved across those branches, but no single run proves contiguous 001–040, installed 033→040 upgrade, second-run no-op/checksum behavior, or combined-candidate leakage.

PR #55's exact-head run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) passed 815 tests at 76.01%; migrations 001–033, schema audit, and the Contact-inclusive post-test leakage audit passed. This does not prove zero leakage on the combined feature candidate.

The main Tests workflow still applies migration files lexically and runs pytest with a 57% coverage floor; the main workflow has no sequence preflight or post-test leakage audit. The deployment PRs add guards on their own branches, not on main.

### Human decision required

Choose the restricted runtime-role credential/provisioning contract; explicitly accept or revise the STOP reservation boundary; decide whether introduction text must gate project/Datacube registry facts; approve a reliable legacy provenance policy; and configure branch protection/required independent review. Do not merge any branch or authorize WhatsApp testing from branch-local CI alone.

**NOT TEST READY.** The controlled WhatsApp test plan is not authorized. No production database mutation, production WAHA reconnection, or real WAHA send occurred.


## Live release-verification delta — 2026-10-30 12:16 WAT (partial; NOT TEST READY)

This supersedes the 2026-10-29 22:18 UTC snapshot above. The full PR-head and review-thread table is in [ZINA_IMPLEMENTATION_ROADMAP.md](ZINA_IMPLEMENTATION_ROADMAP.md); this checklist records the current release gate.

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033, last commit and latest main Tests run on 2026-09-08. The branch endpoint reports `protected=false`.
- Exact-head CI is green on all ten open PRs, but every result is branch-local. PR #60 (915 passed, 76.43%) applies 001–033 plus 038–040, not the integrated chain. PR #55's schema/leakage audit is green on 001–033 only. PR #62's migration preflight and 001–033 test are green, but it still has seven unresolved review threads.
- Current unresolved/total review threads: #48 0/15; #49 1/80; #50 2/10; #55 0/0; #57 1/1; #59 1/1; #60 5/5; #61 0/0; #62 7/7; #63 0/0. The #57/#62 deployment-runner overlap must remain coordinated.
- Ordered feature migrations are #48=034, #50=035, #49=036–037, #60=038–040. The original 034 collision is resolved in branch trees; the integrated 001–040 proof is not.

### Mechanical gates — current candidate

- [ ] Fresh contiguous PostgreSQL migrations 001–040.
- [ ] Installed database upgrade 033→040, second-run no-op, and checksum verification.
- [ ] Exact integrated-candidate full pytest/coverage and P0 adversarial matrix.
- [ ] Integrated schema audit and zero DB leakage, including Contact and raw cleanup tables.
- [ ] Restricted runtime DB role proven unable to alter/disable consent-history triggers or truncate the audit table.
- [ ] Independent review of the five P0 consent threads and seven deployment threads; independent review of the two Identity Registry policy decisions.
- [ ] Main-branch governance/protection configured and independently verified.

### Product/architecture gates

- [ ] Contact consent/terminal opt-out independently reviewed and integrated. Unknown, expired, revoked, ambiguous, or opted-out external recipients must fail closed at the final worker fence. The dispatch-reservation boundary must be explicitly accepted; a STOP after final reservation cannot retract a request already entering WAHA, but must veto later sends and replay.
- [ ] Runtime database role is separate from the migration/table-owner role. Current Compose still gives API and migrate the same `.env.production`; current example URLs both use `postgres`. A table owner can disable the trigger, so the append-only SQL trigger alone is not a security boundary.
- [ ] Identity Registry lifecycle is consistent across all introduction paths; legacy default provenance uses a trustworthy policy, not `updated_at = created_at`. Main already has delete/search/single-fetch and source/entity-type metadata from migration 033; dashboard management remains incomplete.
- [ ] Command Center governs all custom commands; FAQ per-entry CRUD; Knowledge Base edit/delete/disable; Scheduled Actions and Private Media dashboard management; Internet goes through the single Tool Registry/Authority path; conversation observability remains complete and explainable.
- [ ] Outbound Message Library remains foundation-only until P0 and migration integration pass. Private-media retention remains OFF.

The controlled WhatsApp test plan is not authorized. Do not perform owner self-DM or external-contact testing until every blocking gate above is satisfied and Fabian explicitly authorizes the staged plan. No real WAHA sends, production DB mutation, or production WAHA reconnection during unattended engineering. **NOT TEST READY.**

## Live release-verification delta — 2026-10-29 22:18 UTC (partial; NOT TEST READY)

The detailed checklist below contains historical domain assertions and must not override this fresh gate state. Current `main`, open PR heads, Actions, workflow YAML, migrations, deployment runner, and GitHub review-thread resolution flags were re-queried.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; migrations 001–033. Latest main Tests run [#34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed 2026-09-08 (797 tests, 75.98% coverage). No newer main run was returned. The branch endpoint reports `protected=false` and repository rulesets returned `[]`; the classic protection endpoint returned 403 to this integration. Keep independent review mandatory.
- **Latest overall observed CI:** PR #62 head `854439aff24c96a236f9b2fcf72c1993cee1ce5f`, [Tests run #40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923), succeeded 2026-10-29 21:25 UTC. It validates the migration preflight plus 001–033 only; no numeric test/coverage count is claimed here. PR #60's current head `84d2ff2bfce4b438c37bf8bcd906c8b32d038d2d`, [run #40940109653](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40940109653), also succeeded but applies 001–033 plus 038–040, skipping 034–037. Neither is an integrated-candidate result.
- **Current migration order:** #48=034, #50=035, #49=036–037, #60=038–040. The old 034 collision is reconciled in the current feature branches, but no current exact-head run proves contiguous fresh migrations 001–040, installed 033→040 upgrade, or second-run no-op.
- **Open review blockers (unresolved / total threads):** #48=0/15; #49=1/80; #50=2/10; #55=0/0; #57=1/1; #59=1/1; #60=4/4; #61=0/0; #62=6/6; #63=0/0. Replies do not resolve threads unless GitHub marks them resolved. #50's introduction lifecycle and legacy-provenance decisions remain open; #60 has no independent P0 approval; #62 has unresolved deployment-target/role/connection-safety review threads. #57 overlaps the #62 migration runner and must be coordinated rather than merged independently.
- **P0 candidate:** PR #60 adds explicit contact consent/terminal opt-out and a final dispatch fence. Unknown, expired, revoked, or opted-out external contacts must receive zero sends even with a one-use approval or owner policy. Exact-head CI is green, but its migration subset is non-contiguous and four review threads remain unresolved. No real WhatsApp send was attempted.
- **Other gates:** #48's review threads are resolved, but it is unmerged and private-media retention stays OFF. #49 remains foundation-only; do not wire it into live producers. #61's sequence gate is open and has no unresolved threads; #62's current head has a green branch-local run but six unresolved threads. The main deployment runner still lacks the #62 preflight until an independently reviewed integration is merged.
- **Still required before TEST READY:** fresh contiguous 001–040; installed 033→040 upgrade; second-run no-op; exact-candidate schema and DB-leakage audit; full P0 adversarial matrix; independent review of blocking consent/identity/deployment threads; controlled-test plan; explicit human sign-off. No local suite or database migration was run during this docs refresh. No production database operation, real WAHA send/reconnection, or private-media retention activation occurred. **NOT TEST READY.**


## Live release-verification delta — 2026-10-28 06:30 UTC (partial; NOT TEST READY)

See the [roadmap live-verification delta](ZINA_IMPLEMENTATION_ROADMAP.md) for the exact inspected PR heads and dependency notes. This checklist distinguishes branch-local tests from an integrated release candidate.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last commit and latest main Tests run [#405](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) were on 2026-09-08. October branch tests do not establish current main-green.
- **Latest P0 head:** PR [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) at `dd944fdff88afe6de64a82b3dff40786f99f8f26`; exact-head Tests [#622](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40643929083) passed on 2026-10-28: **900 passed, 1 warning, 76.41% coverage**. This workflow applied migrations 001–033 and 038–040, not the contiguous 001–040 chain.
- **Migration order still awaiting integration:** #48=034, #50=035, #49=036–037, #60=038–040. Sequence gate #61 and deployment preflight #62 remain open. #60 is draft with 3 unresolved inline review threads; #50 has two unresolved architectural decisions. A green CI result is not independent review or release approval.
- **Required before controlled testing:** fresh PostgreSQL chain 001–040; installed 033→040 upgrade and repeat/no-op run; exact-candidate DB-leakage audit; P0 adversarial matrix; independent review of blocking consent/identity findings; updated controlled-test plan.
- **Safety:** unknown/revoked consent and terminal opt-out must deny at the final worker fence. No real WhatsApp sends, production database mutations, production WAHA reconnection, or private-media retention activation during engineering.

## Engineering gates (mechanical — re-verify every run)

- [ ] Full contiguous migration chain (001 → 040) applies cleanly from an empty database — not yet verified on the combined candidate.
- [x] Full pytest suite green on PR #60 exact head — 911 passed, 1 warning; integrated-candidate suite remains unverified.
- [x] Coverage at or above the repository gate (57%) — 76.41% on PR #60 exact head; not an integrated-candidate result.
- [ ] DB leakage = 0 across all `CLEANUP_MODELS`/`CLEANUP_RAW_TABLES` tables — current combined-candidate audit outstanding.
- [ ] **No unresolved P0 outbound-authority gaps.** Issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open: exact-contact consent/opt-out must be authoritative and checked at final dispatch, with revocation serialized against the transport attempt. Commit [`18f03f2`](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/18f03f250786bd7af2ff67f2a4f10b75ed8deaf9) anchors the broad opt-out patterns and adds topic-qualified negative tests; exact-head CI is still in progress.
- [x] No duplicate outbound delivery paths (single fail-closed fence, confirmed)
- [x] No unsafe blind retries on uncertain delivery
- [x] Exactly one router, one scheduler, one tool dispatcher (confirmed, no duplicates found)
- [ ] Exact-head CI green on current `main` — last main run #405 was 2026-09-08.

## Product/architecture gates (real work remaining)

- [ ] **Command Center governs all commands.** `ReplyRule` currently absorbs owner-created custom commands (`/create-command` writes to `ReplyRule`, not `CommandCatalogEntry`) — this must be fixed before commands are "discoverable and governed" in the way the mission requires. See roadmap Phase 5.
- [ ] **P0 contact consent/opt-out is independently reviewed and integrated.** PR #60 adds exact-contact/chat consent state, auditable revocation, terminal opt-out, and a final worker fence with Contact-before-consent lock ordering; unknown/revoked consent and opt-out suppress sends even with an OWNER policy or one-use approval. The branch is not merged, and combined migration/P0/leakage validation is still outstanding. See issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56).
- [ ] **Identity Registry lifecycle is consistent across every reply path.** Main now has search/single-fetch/delete endpoints and `source`/`entity_type` columns from PR #47, but PR #50's introduction-reply bypass and legacy default-provenance backfill signal remain unresolved. See roadmap Phase 1 and PR #50.
- [ ] **FAQ has per-entry lifecycle management**, not just bulk document replace. See roadmap Phase 3.
- [ ] **Knowledge Base documents can be edited, deleted, and disabled** — currently only upload and reindex exist; once uploaded, a document is effectively permanent. See roadmap Phase 4.
- [ ] **Dashboard coverage for Scheduled Actions and Private Media Artifacts** — both have complete, tested backend APIs but zero UI. See roadmap Phase 6.
- [ ] **Tool Registry / Authority Engine covers Internet access.** `web.search` is registered but has no dispatcher adapter; `InternetService` is called directly by the reply planner, bypassing the deterministic authority boundary the mission requires for all tool execution. See roadmap Phase 9 / 15.
- [ ] **Conversation observability captures the outbound-authorization outcome in the same audit row as the rest of the decision**, and exposes a real `internet_used` flag and (once Tool Registry covers more than WhatsApp sends) tools-proposed-vs-executed. See roadmap Phase 7.

## Explicitly out of scope for TEST READY (deferred, not blocking)

- Private byte storage for media (Phase 11 layer 2) — retention stays OFF regardless; `.vv`/`.vvopen` already work against live WAHA-provided transient capabilities without needing durable storage.
- AI Media Intelligence / `DerivedArtifact` (Phase 12) — not started, not required for text/command-based controlled testing.
- Project Intelligence (Phase 14) — not started; Fabian's projects continue to answer via static Identity Registry entries in the meantime, which is a known, acceptable limitation for early testing.
- True embedding-based semantic retrieval for FAQ/Knowledge (currently lexical/fuzzy) — functional, just not literally "semantic."

## Staged test plan

Not yet written. `docs/ZINA_CONTROLLED_TEST_PLAN.md` should be produced once the product/architecture gates above are cleared, defining Stage A (OWNER self-DM text only) through Stage E (one explicitly approved external test contact), per the mission's explicit staging requirement. Do not skip stages.

## Live safety reminder

The main branch has foundational outbound payload binding and uncertain-send quarantine, but issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) is a real WhatsApp-facing P0 gap: unknown/revoked contact consent and opt-out are not yet enforced by an authoritative, race-safe final dispatch check. PR #48 adds important WAHA-origin and view-once source-binding/deletion-fence hardening, but remains unmerged; its green exact-head CI is not independent review or proof of the latest combined migration chain. Do not infer live-test readiness from the older Phase 0 checkbox. Until issue #56 is resolved, do not run a controlled external-contact test or wire the message library into live producers. Keep private-media retention OFF and perform no real WhatsApp sends during unattended engineering.

## Live release-verification delta — 2026-10-30 (partial; NOT TEST READY)

The previous 2026-10-29 snapshot is superseded by the following exact current state:

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033; latest main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed 2026-09-08. The main workflow still lacks the open PRs' migration-sequence preflight, schema audit, and leakage audit.
- Current P0 consent branch [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) head `9071c09d` passed exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297): **915 passed, 1 warning, 76.43% coverage**. It applies 001–033 plus 038–040, not 034–037. It remains draft with four unresolved inline threads.
- DB leakage gate [#55](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) head `3d35793e` passed exact-head run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000): **815 passed, 1 warning, 76.01% coverage**; 001–033 fresh migrations, schema audit, and post-test leakage audit passed. The audit now counts `Contact` independently of fixture cleanup membership and has a PostgreSQL regression proving a leaked Contact is reported.
- Migration numbering is ordered as #48=034, #50=035, #49=036–037, #60=038–040. The historical 001–037 integration/033→037 upgrade run does not cover the new 038–040 consent migrations. **001–040 fresh install, 033→040 installed upgrade, second-run no-op/checksums, and combined-candidate leakage are still unchecked.**
- Exact current review counts (unresolved / total): #48 0/15; #49 1/80; #50 2/10; #55 0/0; #57 1/1; #59 1/1; #60 4/4; #61 0/0; #62 6/6; #63 0/0. Review replies do not resolve threads unless GitHub marks them resolved.

### Product gate corrections

- **Identity Registry:** the old statement that delete/search/provenance do not exist is stale. Main now has tombstone delete, search, single-fetch, `source`, `entity_type`, and direct service tests from PR #47 / migration 033. Remaining release work is dashboard CRUD, dedicated create semantics, reliable legacy provenance, and introduction consistency. PR #50 still has two unresolved decisions: backfill provenance for historically read defaults, and whether introductions that mention projects/Datacube AU must honor those registry entries.
- **Contact consent:** PR #60 implements explicit contact/chat consent and terminal opt-out at the final worker fence, including the documented reservation boundary. It is not merged or independently reviewed; it is not yet a main-branch guarantee.
- **Deployment/migration:** PR #61 adds contiguous-number preflight; #62 integrates database-target, libpq, seed-policy, and migration safeguards. #62 still has six unresolved review threads. Neither branch proves the combined 001–040 feature chain.

### Remaining mechanical gates

- [ ] Integrated contiguous migrations 001–040 on one exact candidate from an empty PostgreSQL database.
- [ ] Installed-database upgrade 033→040, second-run no-op, and checksum verification.
- [ ] Exact-candidate full pytest/coverage run plus P0 adversarial matrix.
- [ ] Combined-candidate schema audit and zero-leakage audit, including Contact rows and raw tables.
- [ ] Independent resolution of blocking review threads and explicit acceptance of the STOP dispatch-reservation policy.
- [ ] Main-branch governance review; branch endpoint currently reports `protected=false`, rulesets are empty, and classic protection details are not accessible through this integration.

Controlled test readiness remains **NOT TEST READY**. Do not perform owner self-DM or external-contact tests until the integrated release gates and independent reviews are complete. Private-media retention remains OFF. No real WAHA sends, production database mutations, or production WAHA reconnection during unattended engineering.

## Fresh engineering delta — 2026-11-03 16:20 WAT

This is the current release gate and supersedes earlier checklist snapshots.

### Current verified state

- Main is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, migrations 001–033. Exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08 only.
- Latest overall Tests run [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) was **cancelled** on older #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`; the runtime-role integration test failed at 86% but its assertion traceback and final summary were not captured. Current #60 head `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` has no exact-head CI because its diagnostic-only workflow change uses `[skip ci]`.
- The ten open PR heads and review counts are recorded in the roadmap's 2026-11-03 16:20 WAT verification overlay. None has an APPROVED review submission.

### Release gates — current, not historical

- [ ] One candidate contains the ordered migrations 001–040: #48=034, #50=035, #49=036–037, #60=038–040.
- [ ] Fresh PostgreSQL 16 install of 001–040 passes; installed database upgrade 033→040 passes.
- [ ] Second migration-runner invocation is a no-op with checksum verification; schema audit passes after both fresh and upgrade paths.
- [ ] Exact-candidate full pytest/coverage passes and the P0 adversarial matrix passes on that same candidate.
- [ ] Combined-candidate DB-leakage audit reports zero rows, including Contact and all raw cleanup tables.
- [ ] #60 runtime-role integration test is isolated and green; prove API role cannot UPDATE/DELETE/TRUNCATE/ALTER/DISABLE TRIGGER/SET ROLE or mutate sequence state.
- [ ] #60's authority is rechecked after all blocking locks at the final pre-transport boundary: one-use approval expiry, policy expiry, contact-consent expiry, quiet hours (including approval and ScheduledAction paths), terminal opt-out, exact current mapping, contact-wide frequency/backlog, and media-aware duplicate identity.
- [ ] Explicit OWNER acceptance of the STOP reservation boundary is recorded; uncertain WAHA outcomes are never blindly retried.
- [ ] #60 and #62 deployment changes are reconciled: restricted runtime API role plus #62's target validation, migration sequence preflight, and local-seed opt-in; no broad `.env.production` injection into API/WAHA.
- [ ] Independent human reviews resolve blocking threads. Zero unresolved inline threads alone is not approval; no current PR has an APPROVED review.
- [ ] Classic branch protection is verified through an authorized repository-admin view; current connector request returns 403 and rulesets list is empty.
- [ ] Complete mobile dashboard CRUD/disable and the required observability/command-governance gates before controlled testing.

### Human decisions still required

1. Accept or revise the documented STOP linearization/reservation rule: a STOP arriving after the final reservation veto cannot recall an already-reserved one-time transport attempt, but must prevent retries and all subsequent sends.
2. Confirm the product policy that a terminal opt-out is Contact-wide across current mapped aliases and cannot be overridden by a new grant; any erasure/re-import workflow must preserve the veto or explicitly define a lawful replacement policy.
3. Resolve the #50 introduction scope: remove project claims from the generic introduction, or make project/Datacube AU facts obey Identity Registry lifecycle.
4. Choose a trustworthy provenance/backfill rule for legacy Identity Registry defaults; `updated_at = created_at` cannot reliably identify rows previously touched by old deployments.

Controlled test readiness remains **NOT TEST READY**. Do not start OWNER self-DM or external-contact stages until the integrated migration, exact-head test, leakage, P0, deployment, and independent-review gates above are all satisfied. Private-media retention remains OFF. REAL WAHA ACTIONS: NONE.


## Fresh exact-state release gate — 2026-11-04 07:28 WAT

This is the current release decision, superseding older verification overlays. The full source evidence and per-PR inventory are in the matching 2026-11-04 07:28 WAT section of `docs/ZINA_IMPLEMENTATION_ROADMAP.md`.

### Current state

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08. Main branch metadata currently reports `protected=false`.
- Latest overall Tests run [41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463) passed on exact #60 head `3496ff19b72609553ba51daebfdf0f0472298908`: **952 passed, 1 warning, 76.51% coverage**. It applies 001–033 plus 038–040 only. It does not validate 034–037, integrated 001–040, installed 033→040 upgrade, no-op/checksums, combined schema audit, or leakage.
- Current open PR heads and exact-head run records were re-read on 2026-11-04; ten PRs remain open, with no APPROVED review. Current unresolved review counts are recorded in the matching roadmap overlay.
- Branch-local migration allocation is ordered #48=034, #50=035, #49=036–037, #60=038–040. This is not integrated migration proof.

### Blocking release gates

- [ ] One candidate integrates #48/#50/#49/#60 in migration order and applies 001–040 cleanly from an empty PostgreSQL 16 database.
- [ ] The same candidate upgrades a representative installed 033 database through 040, verifies second-run no-op/checksums, and passes schema audit.
- [ ] The same candidate passes full pytest/coverage and the adversarial P0 matrix.
- [ ] The same candidate passes post-test zero-leakage audit, including Contact and raw tables.
- [ ] #48 and #60 worker changes are reconciled without losing exact view-once source locking/success-only return audit or the contact-consent/STOP/quiet-hours final fence.
- [ ] #60 revalidates the original exact approval/contact-policy authority after all final locks and immediately before transport; one-use reservation is atomic and uncertainty is quarantined without retry.
- [ ] #60 serializes ScheduledAction cancel/pause/reschedule/resume/run-now against the worker's final action-row reservation using a documented queue→action lock order and two-session mock-WAHA tests.
- [ ] OWNER explicitly accepts or revises the STOP reservation boundary; terminal opt-out/re-consent semantics are documented and tested.
- [ ] #60 and #62 are consolidated: migration-owner URL only in migrate; restricted runtime URL only in API; WAHA gets only WAHA variables; Postgres gets only bootstrap variables; target validation, seed opt-in, and migration-sequence preflights run before first DDL/psql.
- [ ] #55 schema/leakage gate and #61 contiguous migration validator run on the integrated candidate.
- [ ] Blocking review threads are independently resolved; no author self-approval or autonomous merge.
- [ ] Main required independent-review/CI governance is enabled and verified before merge.
- [ ] Identity Registry introduction and legacy-default provenance decisions in #50 are resolved independently.
- [ ] #49 permanent set-key retirement finding is independently verified; message library remains unintegrated into live producers and cannot grant send authority.

### OWNER decisions still required

1. Accept the STOP linearization contract: a STOP after the durable final dispatch reservation cannot recall that one already-reserved attempt, but it blocks subsequent sends and uncertain attempts are never replayed; otherwise require a redesigned atomic reservation protocol.
2. Confirm that terminal opt-out is Contact-wide across all current mapped WhatsApp aliases and cannot be overridden by a routine grant.
3. Decide whether generic introductions may mention project/Datacube AU facts when the corresponding Identity Registry entries are disabled/deleted; if not, use a neutral generic introduction.
4. Choose a reliable, auditable provenance/backfill primitive for legacy defaults; `updated_at = created_at` is not a valid historical seed detector.

Controlled testing remains **NOT TEST READY**. Do not start owner self-DM or external-contact stages until every integrated mechanical, P0, deployment, and independent-review gate above passes. Private-media retention remains OFF. **REAL WAHA ACTIONS: NONE.**

Environment note for this verification: no local `psql` or Docker executable was available, so no local PostgreSQL-backed test or migration run was performed. This docs-only update did not trigger Actions.


## Fresh source-review delta — 2026-11-05 00:25 WAT

- PR #50 remains at exact head `0a2b38c0ce72b3c4a8fdd49490be504facb34bac`; review state is **4 unresolved / 12 total** (4 current-diff, 3 outdated unresolved), not the earlier 3 / 11 snapshot.
- New P1: `BotConfigService.identity_reply()` can reintroduce a disabled/tombstoned Fabian through its aggregate-project fallback. `IdentityRegistryService._explicit_target_keys()` targets both `projects` and `fabian`, but the fallback checks only `projects`. A related “why do you exist” fallback names the owner while checking only `zina`. Review comment: [discussion_r4475073725](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50#discussion_r4475073725).
- No source edit, test run, migration, or CI run was performed for this finding. Keep #50 open for the requested regression and independent review; no merge or approval is implied.
- **NOT TEST READY. REAL WAHA ACTIONS: NONE.**


## Fresh review delta — 2026-11-05 10:35 WAT

- PR #62 remains at exact head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`. Its inline review state is now **8 unresolved / 8 total; 5 active** after a new source-grounded P2 review on `scripts/audit_zina_test_db_leakage.py:145`.
- The exact #62 audit checks raw-table existence with `to_regclass('public.<table>')`, but counts using unqualified `SELECT COUNT(*) FROM "<table>"`. A shadow schema earlier in `search_path` can therefore make the existence check inspect `public` while the count reads a different table and misses leaked rows.
- PR #55's current head `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` fixes this by counting the explicitly qualified `public` table in `collect_raw_table_leaks()` and adds `test_raw_table_audit_counts_public_rows_when_search_path_has_shadow_table`. The #62 copies of the audit script and test do not contain that fix/regression. The combined candidate must retain #55's correction while keeping #62's newer URL guards, Contact inventory, schema audit, and leakage workflow step.
- #62's exact-head Tests run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) remains **864 passed / 76.01%**, with schema and leakage audit steps reported successful; it applied migrations **001–033 only** and did not exercise the missing shadow-schema regression or the integrated 001–040 chain.
- The review comment is review-only. No application code, tests, migrations, Actions run, production database, deployment, or WAHA operation was changed or triggered by this finding.

The release gate remains **NOT TEST READY**. **REAL WAHA ACTIONS: NONE.**


## Fresh exact-head release gate — 2026-11-05 (post PR #60 P0 replay guard)

This release snapshot supersedes the 2026-11-04 and 2026-11-05 10:35 overlays above.

- Main: `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. Main remains unprotected.
- Latest overall Tests run [42019032673](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42019032673) succeeded on exact #60 head `4b36f8af3389a9270aefde4654f1e7b0a9270b3c`: 956 passed, 1 warning, 76.57%; migrations 001–033 + 038–040 only. PR #50 run [41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413) succeeded on `e543a704729cc69a859ea61e4e1afb0196d23fdb`: 841 passed, 1 warning, 76.50%; migrations 001–033 + 035 only.
- Current open heads and unresolved review counts:

| PR | Exact head | Unresolved review threads / total |
|---|---|---:|
| #63 | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 |
| #62 | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 8 / 8 |
| #61 | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 |
| #60 | `4b36f8af3389a9270aefde4654f1e7b0a9270b3c` | 19 / 19 |
| #59 | this documentation-refresh branch (self-referential) | 4 / 4 |
| #57 | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 |
| #55 | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 |
| #50 | `e543a704729cc69a859ea61e4e1afb0196d23fdb` | 5 / 13 |
| #49 | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 |
| #48 | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 |

No open PR has an `APPROVED` review submission. Review-thread counts include outdated threads where the API reports them unresolved; they are not a merge-readiness score.

PR #59 is the branch carrying this overlay; its current head is the commit containing this row. All other head SHAs above were re-read immediately before this docs-only update.

### Updated P0 evidence

- [x] PR #60 branch-local fix: ambiguous WAHA outcomes now leave a durable one-way marker; OWNER requeue and the final worker fence reject replay even if queue status is reset. Exact regression and full workflow passed on run 42019032673.
- [x] PR #60 branch-local ScheduledAction locking: worker exact binding and OWNER state mutations use row locks under the documented queue→action order; branch-local two-session regression is included.
- [ ] Exact approval/contact-policy expiry must be revalidated/reserved atomically after all final locks, before WAHA; the current quiet-hours helper is not sufficient authority revalidation.
- [ ] OWNER must accept or revise the STOP linearization contract.
- [ ] Resolve post-WAHA approval/queue lock ordering with two-session coverage.
- [ ] Independently review remaining contact mapping, runtime-role, consent-history privilege, and uncertain-delivery threads.

### Required integrated deployment and migration proof

- [ ] Consolidate #48/#50/#49/#60 in migration order 034–040 and run a fresh PostgreSQL 16 install for 001–040.
- [ ] Upgrade a representative installed 033 database through 040; verify second-run no-op/checksums and schema audit.
- [ ] Integrate #60 restricted runtime API role/service-specific Compose allowlists with #62 target validation, seed opt-in and contiguous-sequence preflight. API must receive runtime-only DB credentials; migrate alone receives owner credentials; WAHA receives only transport settings.
- [ ] Retain #55's schema-qualified raw-table leakage audit and #61's contiguous migration validator in the same candidate; reconcile #57 seed-safety runner changes.
- [ ] Run the P0 adversarial matrix, full pytest/coverage, combined schema audit, and zero-leakage audit on the exact integrated candidate.
- [ ] Independently resolve all blocking review threads; no open PR currently has an APPROVED review submission.
- [ ] Enable and verify main branch protection/required independent review before merge.
- [ ] Resolve #50's project/OWNER fallback lifecycle and legacy-default provenance decision; resolve #49's permanent set-key retirement review; do not integrate the message library into live producers before P0 is complete.

### Human decisions

1. Accept the STOP reservation contract or request a redesigned atomic protocol.
2. Confirm whether terminal opt-out is Contact-wide across current mapped aliases and cannot be overridden by routine grant.
3. Choose a reliable legacy Identity Registry provenance rule; timestamp equality cannot reliably reconstruct rows previously touched by old reads.
4. Confirm the generic introduction remains assistant/owner-only; project facts stay in their individual registry entries.

Controlled testing remains **NOT TEST READY**. Do not begin OWNER self-DM or external-contact tests until every integrated P0, migration, deployment, leakage, observability, and independent-review gate passes. Private-media retention remains OFF. **REAL WAHA ACTIONS: NONE.**
