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
