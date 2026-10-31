# Zina Release Checklist

## Follow-up verification — 2026-10-31 21:26 WAT

- Previous documentation head `1263981056c73b73b9b4105537f16a04d623a81a` passed exact-head Tests run [41238486600](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238486600): 797 passed, 1 warning, 76.01% coverage; migrations 001–033 only. This does not validate feature migrations 034–040 or release readiness. The addendum commit itself needs its own exact-head run; no result is claimed yet.
- [ ] **Service-secret isolation:** main and PR #62 `docker-compose.yml` mount the full `.env.production` into WAHA. Remove broad environment-file inheritance; pass WAHA only its explicit transport/session/webhook settings. API must not receive migration-owner credentials; migrate must not receive runtime credentials unnecessarily; WAHA must receive neither database URL, admin token, nor AI/provider secrets. Test the rendered Compose service environments.
- [ ] **Consent audit privilege proof:** separate a non-owner API runtime role from the migration/table owner and prove the API role cannot ALTER/disable triggers/UPDATE/DELETE/TRUNCATE the consent event table on disposable PostgreSQL.
- PR #62 remains draft with seven unresolved threads; its successful 001–033 runner CI is not integrated 001–040 or production deployment proof.


## Live release-verification delta — 2026-10-31 21:18 WAT (fresh re-query; NOT TEST READY)

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

# Zina Release Checklist

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