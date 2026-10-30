## Live verification delta — 2026-10-30 after exact-head run 41080836429 (partial; NOT TEST READY)

This is the newest repository-state snapshot. It supersedes earlier 2026-10-30 snapshots below; all ten open PR heads and review-thread resolution flags were re-queried.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, unchanged since 2026-09-08. Main has migrations 001–033 only; `main` reports `protected=false` and the repository rulesets endpoint returns an empty list. The classic protection endpoint is not accessible through this integration.
- **Main workflow/deployment:** `.github/workflows/tests.yml` remains blob `445b1fd6`: PostgreSQL 16, lexical migration application, pytest with a 57% coverage floor. It has no migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit. Main's `.env.example` gives `DATABASE_URL` and `DATABASE_URL_SYNC` the same `postgres` role, and `docker-compose.yml` supplies the same `.env.production` to both API and migrate services.
- **Latest observed Tests run:** [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded on PR #63 exact head `13fad868affe01d6069f4288481f8cd8dd341c62`: **803 passed, 1 warning, 76.08% coverage**. The workflow applied migrations **001–033**. It did not run the #55 DB-leakage audit and does not validate feature migrations 034–040 or an installed upgrade.
- **PR #63 observability:** commit [13fad868](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/13fad868affe01d6069f4288481f8cd8dd341c62) makes malformed internet audit values fail closed: only positive finite numeric hit counts and real boolean `internet_used` values are accepted. Exact-head CI is green; one inline review thread remains unresolved for independent review.
- **Current open PR heads (all target main):**
  - #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` — view-once/private-media metadata observation; review threads 0 unresolved / 15 total.
  - #49 `bcd0033e024b177561b8afd41589afe1897ba4de` — Outbound Message Library foundation only; 1 / 80 unresolved, including retired set-key lifecycle. No live producer, selector, or dashboard integration.
  - #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1` — Identity Registry lifecycle; 2 / 10 unresolved: introduction replies still bypass unavailable identity state, and legacy default provenance cannot be inferred safely from `updated_at = created_at`.
  - #55 `3d35793ef72cfcfe1e188bc51df6d6e538679f7b` — post-test DB-leakage audit; 0 / 0 review threads; exact-head run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) passed on 001–033.
  - #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` — local seed safety; 1 / 1 unresolved allowlist concern; keep coordinated with #62 because both change the migration runner.
  - #59 `a4fafa95ef67ad689b7256f0ed9d36c8bb7fd7aa` — this documentation refresh; 1 / 1 stale-snapshot thread remains unresolved. This current documentation head has no exact-head Actions run yet.
  - #60 `9071c09d8d55255bdb99eb6fa138ef08c911d5d0` — P0 contact-consent final fence; draft; 5 / 5 unresolved. Exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed **915 tests, 1 warning, 76.43%**, but applied 001–033 plus 038–040 and skipped 034–037.
  - #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` — contiguous migration-sequence preflight; 0 / 0 review threads; exact-head run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded.
  - #62 `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` — draft integration of #55/#57/#61 deployment and CI guards; 7 / 7 unresolved. Exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed **864 tests, 1 warning, 76.01%** with sequence preflight, migrations 001–033, ORM schema audit, and post-test leakage audit. It still passes the same `.env.production` to API and migrate.
  - #63 `13fad868affe01d6069f4288481f8cd8dd341c62` — observability audit; 1 / 1 unresolved for independent review; exact-head run [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) passed as above.
- **Migration order:** the former duplicate 034 allocation is reconciled in current branch trees: #48=034, #50=035, #49=036–037, #60=038–040. No exact candidate has yet proved a single fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksum behavior, and combined-candidate DB-leakage audit.
- **P0 risk:** main does not yet contain PR #60's explicit contact-consent check at the final outbound worker fence. PR #60 fails closed for unknown/expired/revoked/opted-out external contacts, but remains draft/unmerged and has five unresolved threads. The consent-event triggers are not tamper-resistant while API and migrate share the table-owner role; a runtime owner can disable triggers. A restricted runtime role separate from migration/table owner is not implemented.
- **Human decisions still required:** (1) approve a distinct migration-owner/runtime-role deployment contract and bootstrap/credential rollout; (2) explicitly accept the STOP dispatch-reservation boundary (a STOP after the final reservation cannot retract that one in-flight attempt but must block later sends/replays); (3) decide how all introduction paths honor deleted/disabled Identity Registry facts and how legacy default provenance is classified when timestamps were already changed by older reads.
- **Controlled testing:** **NOT TEST READY.** Require independent review, integrated 001–040 fresh/upgrade/re-run validation, exact-candidate full tests and P0 adversarial matrix, schema/leakage audit, restricted DB-role proof, main-branch governance, controlled test plan, and Fabian's explicit authorization. Private-media retention remains OFF. No production DB mutation, production WAHA reconnection, or real WhatsApp action occurred.

---

## Live verification delta — 2026-10-30 15:40 WAT (partial; NOT TEST READY)

This supersedes the 15:21 WAT snapshot below. Main, all ten open PR heads, exact-head Actions records, review-thread flags, workflow YAML, migration allocations, and deployment/Compose configuration were re-queried after the #62 integration candidate gained the schema/leakage CI gates.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last commit remains 2026-09-08. Main contains migrations 001–033 only. Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA. The main branch endpoint reports `protected=false`.
- **Main CI/deployment:** `.github/workflows/tests.yml` remains blob `445b1fd6`: PostgreSQL 16, lexical migration application, pytest with a 57% coverage floor. Main has no contiguous-sequence preflight, ORM schema audit, post-test DB-leakage audit, or job timeout. Main's deployment runner still lacks the migration-sequence preflight and unconditionally runs seeds. `.env.example` uses the same `postgres` role for `DATABASE_URL` and `DATABASE_URL_SYNC`; main Compose supplies the same `.env.production` to API and migrate.
- **Latest overall Tests run:** [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) succeeded on PR #62's exact head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`: **864 passed, 1 warning, 76.01% coverage**. The job log confirms migration-sequence preflight passed before SQL, migrations 001–033 applied, ORM schema audit passed, full pytest passed, and post-test DB-leakage audit passed (including Contact and raw cleanup tables). This is still the 001–033 main schema, not feature-migration integration.
- **PR #59 docs head:** `05e4bfb242940a786bd14fc8218770ffed224837` passed exact-head run [41072066479](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41072066479): **797 passed, 1 warning, 76.01% coverage**, migrations 001–033 only.

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

All listed run records were checked against their current PR head SHA. These are branch-local results, not one integrated feature-release candidate. Zero unresolved inline threads does not equal independent approval.

### P0 and architecture blockers

- **PR #60 contact consent:** exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed 915 tests at 76.43%, applying 001–033 plus 038–040 and skipping 034–037. Current source includes a locked current-contact/chat mapping check, contact-wide terminal opt-out checks across mapped aliases, and fail-closed rejection of ordinary/OWNER messages without a stable source ID. Migration 038 has UPDATE/DELETE and TRUNCATE event guards plus Contact delete/TRUNCATE protection. All five review threads remain unresolved. The table owner can still disable triggers; the API/migration runtime-role split is not implemented.
- **PR #62 integration candidate:** now combines #57 seed safety, #61 migration-sequence preflight, and #55 ORM schema + post-test leakage audit. Exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed 864 tests at 76.01% on migrations 001–033. It still has seven unresolved deployment review threads and still injects the same .env.production into API and migrate; no restricted runtime DB role is provisioned.
- **STOP reservation policy:** a STOP receipt committed before the worker's final pending-intent read must veto dispatch. Once that read reserves the single transport attempt, a later STOP cannot reliably retract a request already entering WAHA; it must veto subsequent sends/replays. This boundary still needs explicit product-owner acceptance and independent concurrency review.
- **Migration order:** the former duplicate 034 allocation is reconciled: #48=034, #50=035, #49=036–037, #60=038–040. No run proves a single fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, or leakage on the combined feature candidate.
- **PR #50 Identity Registry:** two decisions remain: whether disabled `projects` / `datacube_au` entries suppress corresponding introduction claims, and a trustworthy legacy-default provenance policy. Do not use `updated_at = created_at` as a legacy signal.
- **PR #49 Outbound Library:** foundation only, not integrated into a live producer, selector, or dashboard; one retired-set-key thread remains unresolved.
- **PR #48 media:** metadata/observation only; private byte storage is not implemented and retention remains OFF.
- **PR #63 observability:** audit-order / `internet_used` correction has a green exact-head run but remains unmerged and without independent review.

### Next safe engineering step and required decisions

First settle the restricted runtime-role credential/provisioning contract for existing deployments; then implement API/migration role separation on the existing #62 branch and add disposable-PostgreSQL privilege regressions. Only after independent review, integrate migrations 034–040 in the stated order and prove fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, full exact-head pytest/coverage, P0 adversarial matrix, schema audit, and zero leakage on one candidate.

Human decisions required: (1) how the runtime DB credential is provisioned and rotated separately from the migration owner; (2) accept or revise STOP reservation semantics; (3) whether introduction text must gate `projects` and `datacube_au`; (4) trustworthy legacy Identity Registry provenance; (5) enable required independent review/branch protection on main.

**NOT TEST READY.** No production database operation, production WAHA reconnection, or real WhatsApp action occurred.

---

## Live verification delta — 2026-10-30 15:21 WAT (partial; NOT TEST READY)

This supersedes the 14:21 WAT snapshot below. Main, all ten open PR heads, exact-head Actions runs, inline review-thread resolution flags, the main Tests workflow, migration allocation, and deployment/Compose configuration were re-queried immediately before this update. The older September phase audit remains historical; this overlay is the current evidence boundary.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest commit remains 2026-09-08. Main contains migrations 001–033 only. Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA on 2026-09-08. The main branch endpoint reports `protected=false`.
- **Main CI/deployment:** `.github/workflows/tests.yml` remains blob `445b1fd6`: PostgreSQL 16, lexical `bot_core/migrations/*.sql` application, then pytest with a 57% coverage floor. It has no migration-sequence preflight, schema audit, post-test DB-leakage audit, or job/step timeout. Main's `deploy/scripts/run-migrations.sh` still has no contiguous-sequence preflight and unconditionally runs seed files. `.env.example` uses the same `postgres` role for `DATABASE_URL` and `DATABASE_URL_SYNC`; main Compose supplies the same `.env.production` to API and migrate.
- **Latest overall Tests run:** [41063661288](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41063661288) completed successfully on this PR's exact current head `805f3fdd8e92a5bd1fa4724913986a9ce4a93ec1`. Its job log confirms migrations 001–033, **797 passed, 1 warning, 76.01% coverage**. This validates the docs branch against main's 001–033 only, not feature migrations 034–040.

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

All ten listed workflow runs were re-fetched and their `head_sha` values match the corresponding current PR heads. These are branch-local successes, not one integrated release-candidate run. Zero unresolved inline threads does not equal an independent approval.

### P0 and architecture blockers

- **PR #60 contact consent:** exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed **915 tests, 1 warning, 76.43% coverage**; it applied 001–033 plus 038–040 and skipped 034–037. Current source now contains a locked current-contact/chat mapping check, contact-wide terminal opt-out checks across mapped aliases, and fail-closed rejection of ordinary/OWNER messages without a stable source message ID. Migration 038 has UPDATE/DELETE and TRUNCATE event guards plus Contact delete/TRUNCATE protection. All five review threads remain unresolved. The table owner can still disable triggers: the API/migrate runtime-role split is not implemented.
- **Cross-PR database-role blocker:** PR #62 still injects the same `.env.production` into API and migrate. The documented `postgres` credentials therefore leave the API as table owner; a trigger is not a security boundary against its owner. PR #62 has seven unresolved review threads. Do not treat #60's append-only history as tamper-resistant until a distinct restricted runtime role is provisioned, granted only required runtime permissions, and proven unable to ALTER/DISABLE TRIGGER/TRUNCATE in disposable PostgreSQL.
- **STOP race policy:** a STOP receipt committed before the worker's final pending-intent read must veto dispatch. Once that read reserves the single transport attempt, a later STOP cannot reliably retract a request already entering WAHA; it must veto all subsequent sends/replays. This boundary still needs explicit product-owner acceptance and independent concurrency review.
- **Migration order:** the former duplicate 034 allocation is reconciled across branches: #48=034, #50=035, #49=036–037, #60=038–040. PR #61 adds the contiguous-sequence guard; #62 composes that guard with seed/deployment safety. No run yet proves a single fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, or combined-candidate leakage.
- **PR #55 leakage audit:** exact-head run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) passed **815 tests, 1 warning, 76.01% coverage** with schema and Contact-inclusive leakage audit on 001–033. It is not a leakage proof for the integrated 001–040 candidate.
- **PR #50 Identity Registry:** two decisions remain open. `introduction_reply()` gates `zina` and `fabian`, but its text also asserts project and Datacube AU context; decide whether `projects` and `datacube_au` unavailability must suppress those claims. Do not use `updated_at = created_at` as legacy-default provenance: earlier reads can mutate timestamps; choose an explicit `legacy_unknown`/provenance policy before changing the backfill.
- **PR #49 Outbound Library:** still a foundation, not integrated into a live producer, selector, or dashboard; one retired-set-key thread remains unresolved. Do not grant it send authority or wire it before P0 and migration integration.
- **PR #48 media:** metadata/observation wiring only; private byte storage is not implemented and retention remains OFF.
- **PR #63 observability:** the audit-order / `internet_used` correction passes its exact-head run but remains unmerged; its CI is not evidence of integrated observability.

### Next safe engineering step and required decisions

First settle the restricted runtime-role credential/provisioning contract for existing deployments; then implement the API/migration role split on the existing #62 integration branch and add disposable-PostgreSQL permission regressions. Only after that, integrate migrations 034–040 in the stated order and prove fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, full exact-head pytest/coverage, P0 adversarial matrix, schema audit, and zero leakage on one candidate. Keep all PRs open for independent review.

Human decisions required: (1) how the runtime DB credential is provisioned and rotated separately from the migration owner; (2) accept or revise the STOP reservation boundary; (3) whether introduction text must gate `projects` and `datacube_au`; (4) trustworthy legacy Identity Registry provenance; (5) enable required independent review/branch protection on main.

**NOT TEST READY.** No production database operation, production WAHA reconnection, or real WhatsApp action occurred.

---

# Zina Implementation Roadmap

## Live verification delta — 2026-10-30 14:21 WAT (partial; NOT TEST READY)

This snapshot supersedes the 12:16 WAT snapshot below. It was re-queried from GitHub at this timestamp: main ref/commit history, all open PR heads, exact-head Tests runs, GraphQL inline review-thread resolution flags, main workflow YAML, migration directories, deployment runner and Compose environment.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last commit 2026-09-08. Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA on 2026-09-08. Main contains migrations 001–033 only. The branch endpoint reports `protected=false`; repository rulesets returned `[]`; the classic branch-protection endpoint returned 403 to this integration, so no stronger protection is claimed.
- **Main workflow:** `.github/workflows/tests.yml` at blob `445b1fd6` uses PostgreSQL 16, applies `bot_core/migrations/*.sql` lexically, then runs pytest with a 57% coverage floor. Main's workflow does not yet include the sequence preflight, deployment schema audit, post-test DB-leakage audit, 20-minute timeout, or faulthandler diagnostics now present on feature branches. Main's deployment runner also has no contiguous-sequence preflight.
- **Latest overall observed Tests run:** [41047370340](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41047370340), exact PR #59 pre-refresh head `a2a9e9295cd04c98cbd397667a4e9fd5fb4d1f5b`: **797 passed, 1 warning, 76.01% coverage**. It applied migrations 001–033 only. This new documentation commit has not yet run; do not transfer the prior result to the new head.

| Open PR | Current exact head | Exact-head Tests run | Result | Unresolved / total threads |
|---|---|---:|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | success | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `f78bc9bb` | [40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) | success | 2 / 10 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793e` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | success | 0 / 0 |
| [#57 Deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | success | 1 / 1 |
| [#59 Release docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `a2a9e929` (pre-refresh) | [41047370340](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41047370340) | success | 1 / 1 |
| [#60 Contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9071c09d` | [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) | success | 5 / 5 |
| [#61 Migration sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | success | 0 / 0 |
| [#62 Deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `854439af` | [40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923) | success | 7 / 7 |
| [#63 Conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `c6c493d2` | [40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) | success | 0 / 0 |

These are branch-local successes, not one integrated release-candidate run. A green exact-head workflow does not resolve review threads or prove the combined migration chain.

### P0 and deployment findings

- **#60** adds contact-specific consent and terminal opt-out checks at the final outbound worker fence. Exact-head run #41019860297 passed **915 tests, 1 warning, 76.43% coverage**; its workflow applied 001–033 and 038–040, deliberately skipping 034–037. The current code/test follow-ups cover contact remapping, contact-wide alias opt-out, missing stable message IDs, and UPDATE/DELETE/TRUNCATE rejection, but all five inline threads remain unresolved for independent verification.
- **#60 append-only boundary is not yet tamper-resistant:** migration 038's triggers can be disabled by the table owner. The current `.env.example` assigns the same `postgres` role to `DATABASE_URL` and `DATABASE_URL_SYNC`; current Compose supplies the same `.env.production` to both `api` and `migrate`. PR #62's current Compose still does the same. A restricted runtime role and migration-owner separation have not been provisioned or tested. This is a cross-PR P1 blocker, not fixed by the successful #60 CI run.
- **STOP reservation semantics:** a STOP receipt committed before the worker's final pending-intent read blocks the send. Once that final read returns false, the one transport attempt is treated as reserved/in-flight and cannot be reliably cancelled after network entry; later queue attempts/replays must be blocked, and uncertain delivery is never blindly retried. Keep the PR draft until an independent reviewer verifies the two sides of this boundary and the product owner explicitly accepts the stated semantics.
- **#62** has seven unresolved deployment/migration review threads. Its latest exact-head run #40957674923 passed **846 tests, 1 warning, 76.01% coverage** on migrations 001–033 with migration-sequence and seed-policy checks. It does not prove feature migrations 034–040. Remaining review concerns include database URL/audit-target agreement, libpq target/session overrides, multi-host/role validation, and the shared API/migration environment.
- **#55** exact-head run #41026581000 passed **815 tests, 1 warning, 76.01% coverage**; migrations 001–033, schema audit, and the post-test leakage audit passed. The audit includes Contact rows. This is not a leakage result for the combined 001–040 candidate.
- **#50** retains two architectural decisions: propagate the unavailable-identity policy consistently through all introduction paths (including project/Datacube claims), and choose trustworthy provenance for legacy default rows. Do not infer legacy defaults from `updated_at = created_at`; pre-upgrade reads may already have changed timestamps.
- **#49** remains a foundation only: no live producer/selector/dashboard integration is evidenced; one retired-set-key review thread remains unresolved. **#48** remains metadata/observation only; private-byte retention stays OFF.

### Migration order and proof boundary

The branch migration directories currently establish the proposed order:
1. #48 — 034 `private_media_artifact_source_identity`
2. #50 — 035 `identity_registry_default_backfill`
3. #49 — 036 `outbound_message_library`, 037 `outbound_message_set_key_registry`
4. #60 — 038 `contact_messaging_consent`, 039 `contact_messaging_consent_sender_identity`, 040 `contact_messaging_consent_sender_contact_ids`

The original duplicate 034 allocation is reconciled in these feature branches. Main still has only 001–033. No exact-head run proves a single contiguous fresh 001–040 chain, an installed 033→040 upgrade, second-run no-op/checksum behavior, or schema/leakage audit on the combined candidate.

### Decisions and next safe work

- Human decisions: choose a restricted runtime-role credential/provisioning contract distinct from the migration/table-owner role; explicitly accept or revise the STOP dispatch-reservation boundary; decide whether introduction text must gate `projects` and `datacube_au` facts; approve a trustworthy legacy-provenance policy; and configure main branch protection/required independent review.
- Next engineering step: keep the existing PRs open; reconcile the runtime-role design with the #60 consent migration and #62 deployment runner before adding another migration or wiring outbound-library selection. Then build one integration candidate and run fresh 001–040, installed 033→040 upgrade, no-op/checksum, full tests, P0 matrix, and combined leakage audit on that exact head.
- This docs PR still has one stale-snapshot review thread. This refresh leaves it unresolved for independent review; it is not a self-approval or merge request.

**Release status: NOT TEST READY.** No production DB operation, production WAHA reconnection, or real WhatsApp send occurred.


## Live verification delta — 2026-10-30 12:16 WAT (partial; not release approval)

This snapshot supersedes the 11:17 WAT snapshot above. Main, all open PR heads, exact-head Actions runs, review-thread flags, workflow YAML, migration inventory, and deployment configuration were re-queried.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08); migrations 001–033 only. Main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA. The branch endpoint reports `protected=false`. No newer main run was found.
- **Workflow:** main `.github/workflows/tests.yml` uses PostgreSQL 16, applies migration files lexically, then runs pytest with a 57% coverage floor. It does not yet include the sequence preflight, schema audit, or post-test leakage audit on the open branches. `.github/workflows/strix-security.yml` is a separately bounded manual local-repository scan; no Strix scan was run.

| Open PR | Exact head (short) | Exact-head Tests run | Result | Unresolved / total review threads |
|---|---|---:|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | success | 0 / 15 |
| [#49 Outbound Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | success | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `f78bc9bb` | [40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) | success | 2 / 10 |
| [#55 DB leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793e` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | success | 0 / 0 |
| [#57 Seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | success | 1 / 1 (outdated) |
| [#59 Release docs](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `7d095b87` (pre-update) | [41027422226](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41027422226) | success | 1 / 1 (outdated) |
| [#60 Contact consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9071c09d` | [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) | success | 5 / 5 |
| [#61 Migration sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | success | 0 / 0 |
| [#62 Deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `854439af` | [40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923) | success | 7 / 7 |
| [#63 Conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `c6c493d2` | [40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) | success | 0 / 0 |

These are branch-local results, not one integrated release-candidate run. The latest observed overall Tests run is #41027422226 on the pre-update #59 docs head; the new documentation commit will require its own exact-head run.

### P0, deployment and migration blockers

- **PR #60** adds exact Contact/chat consent and terminal opt-out enforcement at the final worker fence. Its exact-head run reports 915 passed, 1 warning, 76.43% coverage, but applies 001–033 plus 038–040 and skips 034–037. Five threads remain unresolved, including the database-role boundary. The STOP reservation policy is explicit: a STOP committed before the final pending-intent read blocks; a STOP arriving after that read cannot retract the already-reserved single attempt but must block later sends/replays.
- **PR #62** has seven unresolved threads. Its current `docker-compose.yml` still supplies the same `.env.production` to both API and migration services; `.env.example` sets `DATABASE_URL` and `DATABASE_URL_SYNC` to the same `postgres` role. The migration preflight validates target/connection settings but does not create a restricted runtime database role. Therefore the append-only consent triggers in #60 are bypassable by a runtime table owner using `ALTER TABLE ... DISABLE TRIGGER`. This is a P1 cross-PR release blocker, not solved by the green #62 CI run.
- **Migration order:** #48=034, #50=035, #49=036–037, #60=038–040. The original 034 collision is reconciled in the current branches. No current run proves a fresh contiguous 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, or leakage on the integrated candidate.
- **PR #55** passes its own 001–033 schema and post-test leakage audit and explicitly counts Contact rows. This does not prove zero leakage on the combined 001–040 candidate.
- **PR #50** still requires two human decisions: (1) what trustworthy provenance to use for legacy default rows whose `updated_at` may have been changed by pre-upgrade reads; (2) whether introduction text that mentions projects/Datacube AU must be suppressed when those Identity Registry entries are disabled/deleted. Do not add another timestamp heuristic or patch introduction wording without choosing the policy.
- **PR #49** remains a library foundation only; no live producer/selector/dashboard integration. **PR #48** does not activate private-byte retention; retention remains OFF.

### Highest-value next safe work

Design and implement one restricted runtime DB role distinct from the migration/table-owner role, with explicit grants for required runtime DML/sequences and default privileges for future migrations. Add disposable-PostgreSQL tests proving the runtime role cannot ALTER/DISABLE TRIGGER/TRUNCATE consent history while the migration role can apply the full chain. Update Compose, environment examples, CI test roles and upgrade documentation together. The remaining operational choice is how the runtime credential is provisioned/rotated on existing deployments; no production credential or database was touched here.

No merge, approval, local test execution, migration execution, production database mutation, production WAHA reconnection, or real WhatsApp action occurred. **NOT TEST READY.**

## Live verification delta — 2026-10-29 22:18 UTC (partial; not release approval)

This is a fresh GitHub-state snapshot. The detailed domain audit below remains historical and must not be treated as current without re-verification. I re-queried `main`, all open PR heads, recent Actions runs, the Tests workflow, the migration inventory, deployment runner, and review-thread resolution state.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last commit 2026-09-08. The main branch contains migrations **001–033**. Latest main Tests run [#34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08 (797 tests, 75.98% coverage). No newer main-branch run was returned. The branch endpoint reports `protected=false`; repository rulesets returned `[]`, while the classic protection endpoint is not readable through this integration (403). Do not bypass independent review.

- **Current Tests workflow:** `.github/workflows/tests.yml` applies every `bot_core/migrations/*.sql` file in lexical order, then runs pytest with a 57% coverage floor. Main's runner does not yet have the deployment preflight from #62. A green branch-local workflow that applies a non-contiguous subset is not integrated migration proof.

- **Open PRs and latest observed exact-head CI evidence** (branch-local only):
  - #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` — [run #40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) succeeded; 856 passed, 76.26%; branch applies 001–034. Review threads: **0 unresolved / 15 total**.
  - #49 `bcd0033e024b177561b8afd41589afe1897ba4de` — [run #39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded; 896 passed, 76.67%; branch applies 001–033 plus 036–037. Review threads: **1 / 80** unresolved. This remains a library foundation, not live producer/selection/dashboard integration.
  - #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1` — [run #40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) succeeded; 825 passed, 76.47%; branch applies 001–033 plus 035. Review threads: **2 / 10** unresolved, both architectural blockers described below.
  - #55 `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2` — [run #40010785239](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40010785239) succeeded; 814 passed, 76.01%; schema and DB-leakage audits passed on that exact head, using 001–033. Review threads: **0 / 0**.
  - #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` — [run #40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) succeeded; 811 passed, 76.01%; 001–033. Review threads: **1 / 1**. It overlaps the deployment runner changes in #62.
  - #59 (this docs PR), previous head `05c3fae1187cb9a9f5a2fae5faeeac7e51a715f8` — [run #40911530153](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40911530153) succeeded; 797 passed, 76.01%; 001–033 only. This snapshot update is documentation-only and needs its own exact-head CI before merge. Review threads: **1 / 1**; the stale-snapshot thread remains unresolved until GitHub records resolution.
  - #60 `84d2ff2bfce4b438c37bf8bcd906c8b32d038d2d` — [run #40940109653](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40940109653) succeeded on the exact head. The branch applies 001–033 plus 038–040, skipping 034–037. Review threads: **4 / 4** unresolved; no independent P0 approval.
  - #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` — [run #40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded; 809 passed, 76.01%; 001–033. Review threads: **0 / 0**.
  - #62 `854439aff24c96a236f9b2fcf72c1993cee1ce5f` — latest observed Actions run [#40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923) succeeded on the exact head at 2026-10-29 21:25 UTC; migration preflight and 001–033 passed. No numeric test/coverage count is claimed from the returned run metadata. Review threads: **6 / 6** remain unresolved; several findings have code changes on the current branch, but they still require independent review.
  - #63 `c6c493d28c1e27a267867cfe8be7a5005f777a28` — [run #40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) succeeded; 801 passed, 76.04%; 001–033. Review threads: **0 / 0**.

- **Migration order:** the current feature trees are #48=034, #50=035, #49=036–037, and #60=038–040. The historical duplicate 034 is reconciled in the current branches, but the combined contiguous **001–040** chain has not been verified on the current candidate. The old integration run that covered 001–037 does not cover 038–040 or a second-run no-op. PR #61 supplies the sequence guard; #62 adds deployment preflight and seed/target safeguards. Keep #57 and #62 coordinated because they touch the same runner.

- **P0 and architecture blockers:** #60 must deny external sends for unknown, expired, revoked, or opted-out consent at the final worker fence; it also now fails closed for ordinary messages/OWNER commands without a stable source ID. Its current exact-head CI is green but skips migrations 034–037 and all four review threads remain unresolved. #50 still has two unresolved decisions: all introduction paths (first greeting, `/start`, and reply-rule introductions) must honor disabled/deleted identity; and legacy default provenance cannot safely be inferred from `updated_at = created_at` because older reads may already have changed that timestamp. Do not patch the migration heuristic again without choosing an explicit legacy-unknown policy with human approval. #49 must remain foundation-only until P0 and migration integration are complete. Private-media retention remains OFF.

- **Required before TEST READY:** independent review of blocking threads; fresh contiguous 001–040; installed 033→040 upgrade; a second runner invocation proving no-op; exact-candidate schema and DB-leakage audits; the full P0 adversarial matrix; updated controlled-test plan and explicit human sign-off. No local tests or database migration were run during this documentation refresh. No production database or real WAHA action was used.


## Live verification delta — 2026-10-28 06:30 UTC (partial; not release approval)

This delta records the latest inspected state; the full domain audit below was written against September code and must not be treated as current without re-verification.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last commit 2026-09-08. Latest main Tests run [#405](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08; no newer main-branch run was returned by the branch-filtered Actions query. This does not establish current main-green for the October feature set.
- **Current P0 candidate:** PR [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60), exact head `dd944fdff88afe6de64a82b3dff40786f99f8f26`. Tests run [#622](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40643929083) completed successfully on 2026-10-28: **900 passed, 1 warning, 76.41% coverage** (57% gate). The workflow applied migrations 001–033 and 038–040 only; the missing predecessors 034–037 mean this is not a contiguous integrated migration test.
- **Open feature heads:** #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`; #49 `bcd0033e024b177561b8afd41589afe1897ba4de`; #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1`; #55 `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2`; #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba`; #59 (this documentation PR; see its live PR page for the moving head); #60 `dd944fdff88afe6de64a82b3dff40786f99f8f26`; #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`; #62 `4ab17cc6beee2a658304eafaf438cf9d511bbb26`; #63 `c6c493d28c1e27a267867cfe8be7a5005f777a28`. All remain open.
- **Migration plan:** #48=034, #50=035, #49=036–037, #60=038–040. The old duplicate 034 in #49 is absent from its current tree. PR #61's contiguous-sequence gate passes on its own branch but is unmerged; PR #62's deployment preflight is also unmerged. The current #60 workflow does not validate the combined 001–040 chain.
- **P0 review:** #60 remains draft with 3 unresolved inline threads covering consent/mapping concurrency and the append-only consent-history database guard. The current exact-head suite is green, but independent review has not approved the current head. Do not infer approval from owner replies or prior-head tests. #50 still has two architectural decisions open: all introduction paths must honor unavailable identity records, and legacy seed provenance cannot safely be inferred from timestamps already mutated by old reads. #49 has one unresolved retired-key-registry thread; #62 has one unresolved deployment-guard thread.
- **Still unproven for a release candidate:** contiguous fresh migrations 001–040; installed 033→040 upgrade and safe second run; exact-candidate DB-leakage audit; full P0 adversarial matrix; independent review of blocking threads; controlled-test readiness.
- **Safety posture:** unknown/revoked contact consent and terminal STOP must deny external delivery at the final worker fence. Preserve one authoritative outbound dispatcher, exact payload binding, and no blind retry after uncertain WAHA outcome. No live WhatsApp action is part of engineering verification.

## Phase 0 — Foundational Safety Work

**Status: PARTIAL for release readiness — the core outbound fence is present, but a required contact-policy gate remains open.**

- P0 outbound authority (owner + external payload binding, recipient/text/media-locator/kind/caption/MIME/filename all bound into the authorization digest): merged via PR #43 (`05be9d9`), post-merge CI green.
- View-once/private-media pipeline reconciled against P0 and merged via PR #41 (`0c312f2`), post-merge CI green (main @ `7846331`).
- `.vv`/`.vvopen` command handler: implemented, wired into `CommandControlService`, 92 passing tests. (A stale claim in `docs/VIEW_ONCE_MEDIA_PIPELINE.md` that this was unimplemented was corrected in PR #44.)
- PrivateMediaArtifact metadata foundation (layer 1 only — no byte storage): merged via PR #44 (`3912cd5`→`0034587`). A follow-up hardening PR #45 fixes two P2 findings from an automated Codex review (unbounded field lengths could crash `flush()`; `transport_provenance` needed a closed allowlist rather than arbitrary text) — see Phase 11.

**Dependencies:** none. **Active PRs:** #60 (draft/unmerged P0 consent gate) and #61 (migration-sequence CI guard, open for independent review). **Testing status:** #60 exact head `06973c39a495108a22ba6d8ad446b1f734567f02`, run [40146341322](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40146341322), passed 819 tests at 75.96% coverage with one existing Starlette/httpx TestClient deprecation warning (57% gate). Its branch applies 001–033 plus 038 only. Integrated 001–038, installed 033→038 upgrade, P0 adversarial matrix, and current DB-leakage evidence remain unverified.

**Release blocker:** issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open pending independent review and integrated validation of PR #60 at head `06973c39a495108a22ba6d8ad446b1f734567f02`. Exact-head run [40146341322](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40146341322) passed 819 tests, 75.96% coverage, one existing Starlette/httpx TestClient deprecation warning. The current mapping fence denies stale recipient mappings; the new consent-event TRUNCATE finding remains unresolved. Combined migrations, P0 adversarial matrix, and DB-leakage validation remain outstanding. Unknown/revoked consent and terminal opt-out must fail closed; no OWNER override or re-consent command exists.

**Next step:** obtain independent review of #60's OWNER-attested evidence model and terminal opt-out policy and #61's sequence guard; run the exact combined migration chain and installed upgrade; rerun the P0 adversarial matrix and DB-leakage audit; only then decide whether #56 can be closed. Keep the existing single delivery fence; do not add a second sender or run live WhatsApp tests autonomously.

---

## Phase 1 — Identity Registry

**Status: PARTIAL — lifecycle API/service support and direct tests are present on main; dashboard management, dedicated create semantics, a real relationship model, and consistent introduction behavior remain incomplete.**

Files: `bot_core/app/services/identity_registry_service.py`, `bot_core/app/models/schema.py` (`IdentityRegistryEntry`), and `bot_core/app/api/admin.py`. Current main baseline: `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; migration 033 is integrated.

| Capability | Status | Evidence |
|---|---|---|
| Create | PARTIAL | `POST /admin/identity/registry` is an upsert; there is no separate create operation that rejects duplicate keys. |
| Read | PARTIAL | List supports `q` and `include_disabled`; single-key GET includes disabled entries but excludes tombstoned rows. |
| Update | DONE | Existing upsert endpoint updates an entry. |
| Delete | DONE | `DELETE /admin/identity/registry/{registry_key}` tombstones `deleted_at`, disables the row, and audits the operation. |
| Disable | DONE | Enabled state is managed through the upsert; disabled entries remain inspectable through search/single-key GET. |
| Search | DONE | Substring search across key, name, category, and description, with optional disabled entries. |
| Provenance/source | PARTIAL | The `source` column exists and newly seeded defaults use `system_default`; pre-migration rows can remain NULL until PR #50's backfill policy is resolved. |
| Timestamps | PARTIAL | `created_at`/`updated_at` exist, but current main's scored `answer()` path updates `updated_at` on reads. It is not a reliable edit-history or provenance signal. |
| Aliases | DONE | JSON aliases are used by identity scoring. |
| Entity type | PARTIAL | Typed `entity_type` exists; legacy-row backfill remains unmerged and must not rely on the timestamp heuristic. |
| Relationships | MISSING | `entities` remains a flat JSON list, not a relational entity model. |
| Dashboard | STUB | Only a read-only count is exposed; there is no registry management UI. |
| Tests | PARTIAL | 14 direct tests cover seeding/idempotency, special and scored answers, scoring, reference resolution, single fetch, search, and tombstone behavior. Dashboard and every introduction caller are not covered by this service suite. |

**Acceptance criteria:** dedicated create/read/update/delete/disable/search, trustworthy provenance, timestamps, aliases, entity type, relationships where appropriate, dashboard management, direct tests, and consistent conversation integration.

**Current blockers and next steps:**

1. **Fix introduction lifecycle at one authoritative boundary.** PR #50's unresolved finding is valid: `BotConfigService.introduction_reply()` still builds the configured introduction directly, while first-time greetings, `/start`, and identity-like reply rules can call it without consulting the registry. Route those paths through a shared tombstone/disable-aware decision; add regressions for each caller. A guard confined to `identity_reply()` is insufficient.
2. **Choose a safe legacy-provenance policy before merging migration 035.** The current `updated_at = created_at` heuristic cannot prove a row was never edited: historical scored reads already advanced `updated_at` before migration 033 existed. Recommended safe default: preserve ambiguous pre-existing NULL provenance as `legacy_unknown`; set `system_default` only for new defaults inserted by the current seeder. Backfill `entity_type` separately from provenance where the key mapping is trustworthy. Human approval is required before changing this migration's semantics.
3. After the P0 contact-consent gate in issue #56 and the two PR #50 decisions, implement dashboard CRUD and decide whether a dedicated create endpoint is needed. Do not repeat delete/search/single-fetch/provenance-column work already present on main.

---
 
## Phase 2 — Memory Engine

**Status: PARTIAL, close to production-ready.**

Files: `services/memory_service.py` (1194 lines), `memory_compaction_policy.py`, models `UserMemory`/`UserMemoryTimeline`. Dashboard: memory tab in `admin.html`, fully wired.

| Capability | Status | Evidence |
|---|---|---|
| Create/Read/Update/Delete/Disable/Search/Export | DONE | Full CRUD + `is_enabled` toggle + `q`/`status` search + `/admin/memory/export` |
| Source/provenance | PARTIAL | Exists on `UserMemoryTimeline.source` only, not on the core `UserMemory` profile row |
| Confidence | PARTIAL | Exists on timeline only, not on the profile row |
| Visibility | MISSING | No `visibility` field anywhere |
| Entity/project association | PARTIAL | `UserMemory.projects` is free text, not a real FK (blocked on Phase 14 not existing yet) |
| Observability | DONE | `memory_used`/`memory_hits` surfaced in conversation-inspector analytics |

**Acceptance criteria:** Create, Read, Update, Delete, Disable, Search, Export, source/provenance, visibility, timestamps, confidence, entity/project association; visible in AI Control Center; conversation responses expose memory use (already true).

**Dependencies:** entity/project association is capped until Phase 14 (Project Intelligence) exists.

**Next implementation step:** Add `visibility` and promote `source`/`confidence` to the `UserMemory` profile row itself (currently timeline-only). This is a small, additive migration + service change.

---

## Phase 3 — FAQ Semantic Layer

**Status: PARTIAL.**

Files: `services/faq_service.py` (1001 lines), models `FAQEntry`/`FAQImportCandidate`. Genuinely wired into the router (`reply_planner.py:225`).

| Capability | Status | Evidence |
|---|---|---|
| Categories/intents/variations/keywords/entities | DONE | Real columns, populated by `infer_category`/`infer_intent`/etc. |
| Semantic retrieval | PARTIAL | Lexical normalization + Jaccard/`difflib` fuzzy scoring — **not embedding-based**, despite the "semantic" naming |
| Analytics/usage counts | DONE | `usage_count`/`success_count`/`failed_count`, exposed via `/admin/faq/analytics` |
| Confidence/relevance | DONE | Per-entry `confidence_threshold` |
| Create/Read/Update/Delete/Disable | PARTIAL | No per-entry CRUD route — only bulk document replace (`/admin/faq/save\|replace\|upload`) and import-candidate approve/reject; no route to toggle a single entry's `is_enabled` |

**Acceptance criteria:** categories, intents, variations, keywords, entities, semantic retrieval, analytics, usage counts, confidence/relevance, Create/Read/Update/Delete/Disable; influence identity/help/project responses and Router (already true for identity/help/router).

**Dependencies:** none blocking.

**Next implementation step:** Add per-entry CRUD routes (edit a single entry's answer/category/variations without a full document replace; a direct enable/disable toggle). True embedding-based semantic retrieval is a larger, separate investment — not blocking for TEST READY, but should be logged as a known limitation in the release checklist rather than silently left as "semantic" in name only.

---

## Phase 4 — Knowledge Base

**Status: PARTIAL, stub-leaning on lifecycle.**

Files: models `KnowledgeDocument`/`KnowledgeChunk`, `chunking_service.py`, `retrieval_service.py`, API `api/knowledge.py`.

| Capability | Status | Evidence |
|---|---|---|
| Upload | DONE | `/admin/knowledge/upload` + `/text`, though the dashboard UI only wires the `/text` path |
| Edit | MISSING | No update/replace endpoint for existing content |
| Delete | MISSING | No DELETE route anywhere |
| Disable | MISSING | Model field exists (`is_enabled`), shown as a read-only badge, but no route/button to toggle it |
| Reindex | DONE | `/admin/knowledge/reindex/{id}`, wired to a UI button |
| Replace | MISSING | Same gap as edit |
| Extraction status | MISSING | Conflated with indexing `status` |
| Indexing status | DONE | Set by `index_document()` |
| Provenance | PARTIAL | `source_type`/`metadata_json` exist but no dedicated author/URL provenance fields |
| Searchable content | DONE | Lexical/fuzzy token-overlap scoring (not embeddings) |
| Metadata | DONE | `metadata_json` on both document and chunk |

**Acceptance criteria:** upload, edit, delete, disable, reindex, replace, extraction status, indexing status, provenance, searchable content, metadata; never immutable.

**Dependencies:** none blocking.

**Next implementation step:** This is the biggest lifecycle gap in the four knowledge-hierarchy domains — once uploaded, a document can currently only be reindexed, never edited, replaced, disabled, or deleted. Add delete (with `KnowledgeChunk` cascade or tombstone, consistent with other domains), disable-toggle route, and a replace/edit path that re-triggers reindexing.

---

## Phase 5 — Command Center

**Status: PARTIAL — real architecture violation found.**

Files: `services/command_catalog_service.py`, `command_control_service.py`, model `CommandCatalogEntry`.

| Capability | Status | Evidence |
|---|---|---|
| Command name/description/permission/enabled/category/analytics/help | DONE | All real columns, actively used |
| Aliases | PARTIAL | Only one `trigger_syntax` per catalog row; real aliases (`.commands`/`.cmd`, `.vv`/`.vvopen`/`.vvretain`, etc.) live as hardcoded Python dicts in `CommandControlService`, disconnected from the catalog model |
| Handler | PARTIAL | `handler_target` is descriptive metadata only — actual dispatch is hand-written `if/elif` chains, not resolved dynamically from it |
| Categories | PARTIAL | User/Admin/Internet/Media/Memory Commands all exist; **"Experimental Commands" does not exist anywhere** |

**Architecture violation (real duplication, not hypothetical):** `ReplyRule` (table `reply_rules`, evaluated in `RulesEngine._resolve_reply_rule` before AI/FAQ) is a second, parallel command-like system. Worse: the Command Center's own `/create-command`, `/edit-command`, `/delete-command` owner commands write directly into `ReplyRule`, **not** `CommandCatalogEntry` (`owner_command_service.py:544`). This means user-created custom commands bypass Command Center governance entirely — no permission level, no usage analytics, no `/cmdon`/`/cmdoff` enable/disable. This is exactly the "commands hidden inside Reply Rules" pattern the mission explicitly forbids.

**Acceptance criteria:** command, aliases, description, permission level, enabled/disabled, handler, category, analytics, help text; distinct categories including Experimental; nothing hidden in Reply Rules.

**Dependencies:** none blocking, but this should be fixed before Phase 6 dashboard work builds more UI on top of the wrong model.

**Next implementation step:** Migrate `/create-command`/`/edit-command`/`/delete-command` to write into `CommandCatalogEntry` instead of `ReplyRule`, add an "Experimental Commands" category, and move hardcoded alias dicts into the catalog's own alias support (may need a new `aliases` JSON column, matching the Identity Registry pattern). This is a real correctness/architecture fix, not a nice-to-have.

---

## Phase 6 — AI Control Center

**Status: PARTIAL — no unified concept yet, several capable APIs stranded without UI.**

There is no single "AI Control Center." `admin.html` (2134 lines) is a genuine, tabbed dashboard covering the older/core subsystems well, but has not kept pace with newer services.

| Area | Status |
|---|---|
| Identity, Memory, FAQ, Knowledge, Commands, Outbound Queue, AI/Router diagnostics | DONE (real tabs) |
| Conversations | PARTIAL — only a read-only inspector tab; takeover/export/analysis APIs exist with no UI |
| Scheduled Actions | MISSING UI — full CRUD API exists (`scheduled_actions_admin.py`), zero dashboard tab; `action_queue.html` is a separate, unlinked static page |
| Rules/Policies | PARTIAL — `ReplyRule` tab only; owner outbound-approval and contact-automation policies have no dashboard surface at all (WhatsApp-command-only) |
| Media Artifacts | MISSING — `private_media_artifact_service.py` has no admin API or UI whatsoever |
| Mobile-friendly | PARTIAL — viewport meta present and an overflow self-check exists in JS, suggesting genuine (if unverified) responsive intent |

**Acceptance criteria:** every page explains what/why/depends-on/health; management pages for Identity, Memory, FAQ, Knowledge, Commands, Conversations, Scheduled Actions, Outbound Queue, Rules/Policies, Media Artifacts, AI/Router diagnostics; CRUD where appropriate; mobile-friendly.

**Dependencies:** benefits from Phase 5's fix (don't build a Rules/Policies tab that further entrenches `ReplyRule` duplication).

**Next implementation step:** Add dashboard tabs for the three capabilities that already have full backend APIs but zero UI: Scheduled Actions, Media Artifacts (once Phase 11's admin API exists), and Conversation Takeover/Export. This is UI-only work riding on existing, tested services — low risk, high observability payoff.

---

## Phase 7 — Conversation Observability

**Status: PARTIAL, close — a real single-message dashboard exists, but the accountability layer has gaps.**

`recent_router_decisions()` (`admin.py:254-390`, aka `GET /conversation-inspector`) already surfaces: contact/phone/whatsapp_id, inbound message + timestamp, intent, decision_type/reason/confidence, identity_used/memory_used/faq_used/knowledge_used, ai_tokens/model/latency, selected_source/route/rejected_routes, final_response, fallback_reason. This is real, not aspirational.

**Missing:**
- No `internet_used` boolean parallel to the other `*_used` flags (only a hit count).
- **Outbound authorization/approval result is captured too late to be audited** — `router.py._save_audit_log` flushes the `RouterDecision` row *before* `outbound_authority` (approval_id, response_category) is added to the same dict later in the function. The persisted, queryable trail predates the authority decision.
- Tools proposed vs. executed: no mechanism exists at all (no function-calling/tool-proposal code found anywhere); `ToolDispatcherService`'s own audit entries use a different `AuditLog.action` that this endpoint never joins on.
- `project_context` field exists in the response dict but is always empty — no upstream source populates it (blocked on Phase 14).

**Acceptance criteria:** every inspection view exposes contact, phone/chat id, inbound message, timestamp, intent, route, Identity/Memory/FAQ/Knowledge/Project-Intelligence/Internet used, AI reasoning source, tools proposed/executed, authority decision, outbound authorization, response source, failure/block reason.

**Dependencies:** tools-proposed/executed needs Phase 9's authority generalization first; project_context needs Phase 14.

**Next implementation step:** Fix the ordering bug so `outbound_authority` is captured in the same audit row as the rest of the decision (small, local fix in `router.py`), and add a real `internet_used` boolean. These are both bounded, high-value fixes independent of the larger Phase 9/14 work.

---

## Phase 8 — Router + Conversation Engine

**Status: PARTIAL, close to production.**

Architecture is a deterministic, explainable staged waterfall (Identity → Memory → FAQ → Knowledge → Cache → Internet → OpenRouter last-resort), not a giant if/else tree and not literally "AI-first" (AI is explicitly last-resort by design — the mission's "AI-first but explainable" framing doesn't match the code, though the explainability half is real). `RouterDecision` rows are genuinely persisted and surfaced (confirmed, not dead code). `ConversationTakeoverService` and `ConversationOpenLoopService` are real state machines, not stubs.

**Acceptance criteria:** AI-first but explainable; Router coordinates rather than owns; Conversation Engine maintains context/takeover; decisions persisted.

**Dependencies:** none blocking.

**Next implementation step:** No urgent gap. If "AI-first" is meant literally (AI reasons over retrieved context rather than being a last-resort fallback), that's a deliberate architecture change to weigh with the user, not a bug to silently fix — flag for a decision rather than implementing unilaterally.

---

## Phase 9 — Tool Registry + Authority Engine

**Status: PARTIAL — one dispatcher confirmed (good), but Authority Engine is WhatsApp-outbound-scoped only, and one real bypass found.**

`ToolDispatcherService.execute()` is confirmed to be the single dispatch chokepoint — no duplication. But:
- The "Authority Engine" role is split across `RouterOutboundAuthorityService` + `OutboundAuthorizationService`/`_delivery_authorized`, and is **scoped only to outbound WhatsApp message delivery**. There is no general-purpose deterministic approve/deny layer for arbitrary tool calls — `ToolDispatcherService`'s own check is a simple permission-rank comparison, no human-in-the-loop step.
- **Real bypass found:** the Tool Registry has a `web.search` entry (`handler_target: "internet.search"`), but `ToolDispatcherService` has no adapter for it — calling it raises `"tool has no executable adapter"`. In practice `reply_planner.py` instantiates `InternetService` directly and calls it, **completely bypassing the Tool Registry/Authority boundary** for internet access. This directly contradicts the mission's Phase 15 requirement ("safe tool authorization" for Internet).

**Acceptance criteria:** one dispatcher (confirmed); AI proposes, Authority Engine deterministically approves/denies; execution supports permission/ownership/target/capability/audit/idempotency/retry; AI never the authority.

**Dependencies:** Phase 15 (Internet) is blocked on this being fixed to make "safe tool authorization" true rather than aspirational.

**Next implementation step:** Either add a real `ToolDispatcherService` adapter for `web.search` that calls `InternetService` (closing the bypass), or explicitly decide Internet is intentionally routed outside Tool Registry and document why — don't leave it as an unexplained gap. The former is more consistent with the stated architecture.

---

## Phase 10 — WhatsApp Outbound Safety

**Status: DONE for merged payload binding and uncertain-send quarantine; release readiness remains PARTIAL while Phase 0 contact consent is unmerged.**

The merged fence remains the single authority path: scheduled actions and router replies converge on the same outbound worker, and recipient/text/media locator/kind/MIME/filename/caption remain bound into the authorization digest. The newer exact-contact consent/opt-out check is still on draft PR #60 and must not be treated as deployed. Final delivery fence (`background_workers._delivery_authorized`) is fail-closed by design; confirmed scheduled actions and router replies cross the *same* fence (`scheduled_action_service.release_due` creates a plain `OutboundMessage`, `_delivery_authorized` recognizes it via `_is_exact_scheduled_action_binding` — one authority path, not a parallel one). Content/media identity (locator, kind, MIME, filename, caption) all bound into the authorization digest per PR #43.

**Next implementation step:** none — regression-only. Any future producer of `outbound_queue` rows must be audited against this fence before shipping (see Phase 0's fail-closed-by-default policy).

---

## Phase 11 — Private Media / View-Once

**Status: PARTIAL.**

- `.vv`/`.vvopen`/`.vv info`/`.vv list`/`.vv delete` command family: DONE, tested.
- `PrivateMediaArtifact` PostgreSQL metadata layer: DONE (PR #44), currently being hardened for two Codex-review findings (PR #45 — bounded-field validation, closed `transport_provenance` allowlist).
- Private byte storage (layer 2): NOT STARTED. `storage_locator` stays `NULL` on every row.
- No admin API or dashboard surface for `PrivateMediaArtifact` at all (confirmed by Phase 6 audit).
- `.vvretain on`: correctly refused — must stay refused until byte storage/TTL/quota exist.

**Acceptance criteria:** OWNER-only view-once (done); one shared `PrivateMediaArtifact` for image/video/audio/voice/view-once (metadata layer done, byte storage not started); PostgreSQL metadata authority, private byte storage abstraction, artifact id, source message id, content hash, MIME, filename, type, size, provenance, owner authorization, TTL, quota, size limits, delete, disable, cleanup, restart safety, audit (metadata-side items done; storage-side items not started).

**Dependencies:** PR #45 must merge before further Phase 11 work builds on the service.

**Active PR:** #45 (hardening), open.

**Next implementation step:** After #45 merges — (a) add an admin API + dashboard tab for `PrivateMediaArtifact` (list/disable/delete by OWNER), which is pure UI/API work on an already-tested service; (b) design the private byte storage abstraction (layer 2) as a separate, larger PR — this needs quota/TTL/cleanup/restart-safety design before any code, per the mission's explicit gate ("only after storage/retention policy tests are defined").

---

## Phase 12 — AI Media Intelligence

**Status: MISSING entirely.** Confirmed by direct search: zero matches for vision/transcription/frame-extraction/multimodal/DerivedArtifact anywhere in `bot_core/app`.

**Dependencies:** blocked on Phase 11's private byte storage existing (nothing to analyze without stored bytes) — although image-only vision analysis on an ephemeral WAHA-provided URL, without persistent storage, may be feasible sooner if scoped carefully (analyze-then-discard, never store).

**Next implementation step:** Not started, and should not start before Phase 11's byte storage design is settled, since `DerivedArtifact` needs a source artifact to reference. Lowest priority of the currently-unstarted domains.

---

## Phase 13 — Scheduled Actions

**Status: PARTIAL, close to production.**

Create/Read/Disable/Schedule/Target/Owner/Authority-policy/Failures/Next-run/Audit: all DONE and confirmed routed through the same outbound authority fence as everything else (no second scheduler, no bypass). Gaps: Update is reschedule-only (no payload/target edit), Delete is soft-cancel only (row persists forever), execution history is a single mutable JSON blob rather than an append-only log. No dashboard UI tab despite a complete API (see Phase 6).

**Next implementation step:** Add a dashboard tab (low-risk, API already exists and is tested) and consider whether true delete/payload-edit are actually needed before TEST READY, or can be deferred — soft-cancel may be an acceptable permanent design given the audit-trail requirement.

---

## Phase 14 — Project Intelligence

**Status: MISSING entirely.** No `Project` table/model exists in any of the 32 migrations. "Datacube AU"/"ZinaX"/"Moxiz Gateway" exist only as static, hardcoded Identity Registry entries with no status/goals/tasks/files/activity tracking. `contact_intelligence_service.py` tracks WhatsApp contacts (people), not projects. `UserMemory.projects`/`.goals` are free-text columns on a *contact's* profile, not a project domain.

**Dependencies:** this is a from-scratch build — new model, migration, service, and cross-references to Identity/Knowledge/Memory. Several other phases (Memory's entity/project association, Conversation Observability's `project_context`) are capped on this not existing.

**Next implementation step:** Design a `projects` table (project identity, current goals/status, associated knowledge/memory references, task/decision log, activity timeline) as a new domain owned by a new `ProjectIntelligenceService`, analogous in shape to Identity Registry but with its own lifecycle. This is a larger vertical slice — plan it as its own PR, not a quick add-on.

---

## Phase 15 — Controlled Internet Capability

**Status: PARTIAL — functionally real, but not tool-authorized.**

`InternetService` (354 lines, genuinely non-trivial: multi-provider fallback, quota checks, TTL cache) has real provenance tracking, auditability (`InternetUsageEvent`), and result attribution. Explicit routing is enforced by pipeline ordering (Internet only reached after Identity/Memory/FAQ/Knowledge fail), not by an independent guard. **Gap shared with Phase 9:** it is called directly by `reply_planner.py`, bypassing the Tool Registry/Authority boundary entirely — the registered `web.search` tool has no dispatcher adapter.

**Dependencies:** blocked on Phase 9's fix (add the missing dispatcher adapter, or explicitly document why Internet is exempt).

**Next implementation step:** Tracked under Phase 9 — this phase's only real gap is that one.

---

## Phase 16 — Testing Readiness

**Status: NOT YET.** Tally against the mission's TEST READY checklist, as of this run:

| Requirement | Status |
|---|---|
| Clean fresh database migration (001→latest) | DONE (verified to 032) |
| Full pytest green | DONE (783 passed) |
| Coverage above gate | DONE (75.12% vs 57% gate) |
| DB leakage = 0 | DONE |
| No unresolved P0 regressions | DONE |
| No duplicate outbound paths | DONE (confirmed single fence) |
| No unsafe retries | DONE (fail-closed, quarantines uncertain delivery) |
| No second router/scheduler/dispatcher | DONE (confirmed single instances of each) |
| All key dashboard CRUD working | **NOT DONE** — Knowledge (no edit/delete/disable), Identity (no delete/search), FAQ (no per-entry CRUD), Scheduled Actions/Media Artifacts (no UI at all) |
| Commands discoverable | PARTIAL — `/help`/`/commands` work, but the `ReplyRule` duplication (Phase 5) means some owner-created commands aren't governed by Command Center |
| Conversation observability functional | PARTIAL — real but missing tool-proposal and correctly-timed authority-outcome fields (Phase 7) |
| Mock WAHA integration green | DONE (existing suite is mock-based throughout) |
| Exact CI on main green | DONE |
| Deployment/startup docs updated | NOT VERIFIED this run |

**Not TEST READY yet.** Dashboard CRUD completeness and the Command Center/`ReplyRule` duplication remain product blockers. In addition, the explicit contact-consent/opt-out gate is still unmerged on main; do not run controlled external-contact tests until PR #60 is independently reviewed and the combined migration/P0/leakage gates pass.

**Next implementation step:** Work Phases 1, 5, then 3/4/6/13 dashboard gaps, in that order, before attempting `docs/ZINA_CONTROLLED_TEST_PLAN.md`.

## Live verification delta — 2026-10-30 (partial; not release approval)

Fresh verification against current main, all ten open PR heads, exact-head Actions runs, migration files on each feature branch, workflow YAML, and review-thread resolution flags:

- **Main remains** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; migrations 001–033 only. Latest main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08. Main `.github/workflows/tests.yml` still runs PostgreSQL 16, migrations, pytest and the 57% coverage gate, but does not yet include the migration-sequence preflight, schema audit, or post-test leakage audit now present on open feature branches.
- **Main governance:** `GET /branches/main` reports `protected=false`; repository rulesets are empty. The classic branch-protection endpoint returns 403 to this integration, so no stronger protection is evidenced. Keep independent review mandatory.

| Open PR | Exact head | Latest exact-head Tests run | Result | Unresolved / total threads |
|---|---|---:|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | success | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `f78bc9bb` | [40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) | success | 2 / 10 |
| [#55 DB leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793e` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | success | 0 / 0 |
| [#57 Seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | success | 1 / 1 |
| [#59 Release documentation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `c58a3370` | [40965554240](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40965554240) | success | 1 / 1 |
| [#60 Contact consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9071c09d` | [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) | success | 4 / 4 |
| [#61 Migration sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | success | 0 / 0 |
| [#62 Deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `854439af` | [40957674923](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40957674923) | success | 6 / 6 |
| [#63 Conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `c6c493d2` | [40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) | success | 0 / 0 |

All listed successes are branch-local exact-head evidence, not a single integrated release-candidate run.

### Migration order and proof boundary

The original duplicate 034 numbering is resolved in the current feature branches:

1. #48 — 034 `private_media_artifact_source_identity`
2. #50 — 035 `identity_registry_default_backfill`
3. #49 — 036 `outbound_message_library`, 037 `outbound_message_set_key_registry`
4. #60 — 038–040 `contact_messaging_consent` and sender-identity/contact evidence

No branch currently proves the combined 001–040 chain. #60's workflow applies 001–033 plus 038–040; #55/#61/#62 apply 001–033. Historical separate integration evidence covers 001–037 and an installed 033→037 upgrade only; it does not cover 038–040. Fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum verification, and combined-candidate leakage remain release blockers.

### Current P0 and architecture decisions

- #60 exact head `9071c09d` passed **915 tests, 1 warning, 76.43% coverage**. Its new two-session regression documents the dispatch-reservation policy: once the worker's final pending-STOP read returns false, one attempt is in-flight; a later STOP may not cancel that attempt, but it must commit terminal opt-out before later queue rows can send. An uncertain result is not replayed. This is not a guarantee that STOP can cancel a reserved network attempt. Four inline review threads remain unresolved; the PR is still draft and unmerged.
- #55 exact head `3d35793e` passed **815 tests, 1 warning, 76.01% coverage**. Migrations 001–033 and schema audit passed; the post-test leakage audit passed. The audit now counts `Contact` independently of `CLEANUP_MODELS`, so PR #60's consent-history-before-contact teardown ordering cannot silently remove contacts from the leakage inventory.
- #50's introduction method now suppresses disabled/deleted `zina` and `fabian`, but its introduction text still names projects and Datacube AU. Human scope decision remains: remove those claims or also gate the `projects`/`datacube_au` registry facts. Migration 035's `updated_at = created_at` legacy backfill signal remains unreliable for rows touched by pre-upgrade reads; choose a trustworthy provenance policy before merge.
- #49 remains a foundation only; no live producer, selector, or dashboard integration is evidenced. #48's metadata observation work does not activate private-byte retention; retention remains OFF.
- #62 has six unresolved deployment/migration review threads; #57 and #59 each have one. A green CI result does not resolve a review thread or substitute for an independent reviewer.

No merge, self-approval, production database mutation, production WAHA reconnection, or real WhatsApp action occurred. Release remains **NOT TEST READY**.