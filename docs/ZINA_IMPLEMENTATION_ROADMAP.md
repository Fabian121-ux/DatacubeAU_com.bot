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

## Fresh live verification — 2026-11-02 (current engineering pass)

This overlay supersedes the 11:23 WAT snapshot below. It rechecks the default branch, all ten open PR heads, review-thread state, exact-head Actions associations, migration allocation, deployment/workflow source, and the P0 worker/authority code. Review comments added to PR #60 are comment-only; they are not independent approval.

### Default branch and CI

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; no newer main commit was found. Main still contains migrations 001–033 only.
- Exact-main Tests run `34219252390` remains the latest associated run (success, 2026-09-08). The main workflow still applies the SQL files present in that checkout and runs pytest with a 57% coverage floor; it does not run the newer migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit.
- Latest overall Tests run is [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`: **cancelled**. Migration application and Compose helper tests passed; `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%, then the 120-second faulthandler fired during async fixture setup and the job reached its 20-minute cancellation. The logs contain no assertion traceback, final suite count, or coverage result. Do not infer that the runtime-role integration test passed.
- The branch-protection endpoint returned 403 `Resource not accessible by integration`; the repository rulesets endpoint returned an empty list. Classic branch protection and required checks remain unverified in this pass.

### Active PRs, exact heads, and review state

| PR | Current head | Migration allocation | Unresolved review threads | Exact-head Tests |
|---|---|---:|---:|---|
| #63 observability | `13fad868affe01d6069f4288481f8cd8dd341c62` | — | 1 | 41080836429 success |
| #62 migration/deployment preflights | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | — | 7 | 41073226073 success |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | — | 0 | 40300425938 success |
| #60 contact-consent P0 | `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` | 038–040 | 16 | 41400297589 cancelled |
| #59 roadmap/checklist | this documentation PR (head changes with this commit) | — | 3 | no exact-head run |
| #57 seed policy | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | — | 1 | 40169146406 success |
| #55 DB leakage gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | — | 0 | 41026581000 success |
| #50 Identity Registry | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 035 | 3 | 41202063757 success |
| #49 Outbound Message Library | `bcd0033e024b177561b8afd41589afe1897ba4de` | 036–037 | 1 | 39920982545 success |
| #48 PrivateMediaArtifact | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 034 | 0 | 40158094566 success |

No PR has an APPROVED review state in the current review responses; COMMENTED reviews and zero-thread counts are not independent approval. #48 has no unresolved threads but remains unmerged.

### Migration and deployment integration

- The former duplicate migration-034 allocation is resolved **at branch allocation only**: #48=034, #50=035, #49=036–037, #60=038–040. Main remains 001–033.
- No single candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, ORM schema audit, and zero DB leakage together.
- #60 and #62 remain unsafe to merge independently or in either order. #60 has the restricted non-owner API DB role and service-specific Compose environment allowlists, but its migration runner lacks #62's pre-DDL target, local-seed, and migration-sequence preflights. #62 has those preflights plus schema/leakage gates, but still mounts the broad production environment file into API/WAHA/migrate and does not provision the restricted runtime role. Build one integrated candidate preserving all preflights before DDL and the API/WAHA/migrate credential boundaries.
- #60's current workflow applies only the migrations present on that branch (001–033 plus 038–040); it does not prove the integrated 001–040 chain.

### Current P0 and architecture blockers

1. **Quiet hours are not authority-independent.** Exact one-use OWNER approval returns before reading the active contact policy's `quiet_hours_json`; exact ScheduledAction binding also returns allowed without the shared quiet-hours check. Both paths must deny active quiet hours and malformed timezone/window data.
2. **Contact safety budgets are alias-local.** Backlog, rate, and duplicate checks key on `OutboundMessage.chat_id`, while consent resolves a stable Contact ID. Current aliases for one Contact can therefore consume separate limits and bypass contact-wide duplicate suppression.
3. **STOP boundary needs an explicit contract.** A STOP receipt can commit after the worker's pending-intent read but before the WAHA POST. The current implementation treats the final read/reservation as the linearization point. Add a deterministic two-session race test and obtain OWNER acceptance of that boundary, or change the shared lock protocol.
4. **Time-bounded authority can expire while final locks are acquired.** The final authorization check precedes consent, global safety-reservation, and mapping locks. An approval or policy may expire during those waits; the worker can still POST and only then fail approval consumption. A new source-anchored review comment requests a post-lock, immediately pre-transport expiry check/reservation and clock-controlled zero-WAHA regressions.
5. **Media duplicate suppression is not media-aware.** The duplicate key is caption/text only. Blank-caption identical media bypasses suppression; different attachments sharing a caption can be falsely treated as duplicates. A new source-anchored review comment requests the canonical locator/kind/caption/MIME/filename digest plus media regressions.
6. **Runtime-role test remains unresolved.** The latest exact-head run is cancelled after the new disposable-PostgreSQL role test was marked failed and the async fixture timed out. Obtain the actual assertion traceback and fix the fixture/test isolation before treating audit-history protection as proven.
7. **Identity Registry (#50):** the prior registry-read fallback concern now fails closed on the current head. Still unresolved: keep generic introduction copy limited to Zina/Fabian rather than project claims, and do not infer historical provenance from `updated_at = created_at`; preserve ambiguous pre-033 rows as `legacy_unknown` unless immutable evidence proves origin.
8. **Outbound Message Library (#49):** foundation only; no live producer selection or dashboard. Do not integrate into external sends before P0 and integrated migration gates pass. Private-media retention remains OFF.

### Work in this pass and release state

- Added two source-anchored P0 review comments to PR #60: [time-bounded approval/policy expiry at the final worker fence](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4442435895) and [media-aware duplicate identity](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4442484093). Both are unresolved review findings, not approvals.
- No application source or migration was changed. No local pytest, PostgreSQL migration, schema audit, or DB-leakage audit was run. No Actions run was triggered. No production DB mutation, WAHA reconnection, real WhatsApp send, or private-media retention activation occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh live verification — 2026-11-02 11:23 WAT

This overlay supersedes the 09:27 WAT snapshot below. It was checked against the current default branch, all open PR heads, review threads, recent Actions runs, workflow YAML, and the relevant outbound/deployment source. The new PR #60 inline review is comment-only and is not approval.

### Default branch and CI

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59Z), with migrations 001–033 only.
- Latest exact-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. Main's `.github/workflows/tests.yml` applies the SQL files present in that checkout lexically and runs pytest with a 57% coverage floor; it does not itself run the newer migration-sequence preflight, schema audit, or post-test DB-leakage gate.
- The latest overall Tests run is [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`: **cancelled** at 2026-11-02 06:50:28Z. Migrations and Compose helper tests passed; `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%, followed by a 120-second faulthandler timeout during async fixture setup. The job reached its 20-minute cancellation. No assertion traceback, final suite count, or coverage result is available.
- The branch-protection endpoint returned 403 `Resource not accessible by integration`. Current branch protection and required checks therefore remain **unverified**; do not rely on the historical unprotected-main observation.

### All ten open PRs — exact heads, exact-head Tests associations, unresolved / total threads

| PR | Exact head | Exact-head Tests | Unresolved / total |
|---|---|---|---:|
| #48 PrivateMediaArtifact | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| #49 Outbound Message Library | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success | 1 / 80 |
| #50 Identity Registry | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success | 3 / 11 |
| #55 DB-leakage gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success | 0 / 0 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| #59 release documentation | this verification branch | docs-only commits use `[skip ci]`; no exact-head Tests run expected | 3 / 3 |
| #60 contact-consent P0 | `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` | [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) cancelled | 14 / 14 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| #62 deployment preflight/seed integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success | 7 / 7 |
| #63 conversation observability | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success | 1 / 1 |

### Migration and integration state

- Branch-level migration allocation is contiguous: main 001–033; #48 adds 034; #50 adds 035; #49 adds 036–037; #60 adds 038–040. The historical duplicate-034 allocation is resolved at branch level only.
- No single candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, combined schema audit, and zero DB leakage together.
- #48 and #60 both change the sole outbound worker and authorization service. One reviewed candidate must preserve #48's exact OWNER view-once source binding/lock and post-success return audit together with #60's external-contact consent, STOP, and final safety fence.
- #60 and #62 cannot be merged in either order. #60 contains runtime-role provisioning and a WAHA environment allowlist but lacks #62's pre-DDL target/seed/sequence preflights and integrated schema/leakage gates. #62 contains those deployment preflights but still injects the broad production env file into API/WAHA/migrate and lacks #60's restricted runtime-role boundary. Consolidate the two in one candidate.

### Current P0 / architecture blockers

1. **STOP linearization requires OWNER acceptance.** A STOP receipt may commit after the worker's final pending-intent read but before the WAHA request begins. The current code treats that read as the dispatch reservation/in-flight boundary. Fabian must accept or revise that contract; the transport request cannot be recalled once network entry has begun.
2. **Quiet hours are not universal.** Exact one-use OWNER approval returns before checking the active contact policy's `quiet_hours_json`; the exact ScheduledAction branch also returns allowed without that check. On 2026-11-02, review [#5735157529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) added source-anchored comments requiring one shared authority-independent quiet-hours fence, invalid timezone/window rejection, and mock-WAHA regressions.
3. **Per-contact limits are alias-local.** `OutboundSafetyLimitService` keys backlog, rate, and duplicate checks by `OutboundMessage.chat_id`, although consent/STOP is contact-wide across current aliases. Aggregate by stable Contact identity under the exact-chat mapping lock.
4. **Runtime-role integration test is not green.** Isolate `test_runtime_role_cannot_mutate_or_disable_consent_history` on the disposable PostgreSQL target, preserve the assertion traceback, and diagnose the subsequent fixture-setup timeout before another full-suite run.
5. **Identity Registry (#50):** three review decisions remain: whether generic introduction copy should mention projects/Datacube AU (recommended: remove project claims and keep them in registry answers); do not infer historical seed provenance from `updated_at = created_at`; and independently verify the fail-closed registry-read behavior.
6. **Outbound Message Library (#49):** foundation only; no live producer selection or dashboard. Do not wire it into external sends before P0 and integrated migration gates pass. Private-media retention remains OFF.

No application code or migration changed in this verification. No local tests, migrations, schema audit, or leakage audit were run. No production DB mutation, WAHA reconnection, or real WhatsApp send occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh live verification — 2026-11-02 09:27 WAT

This overlay supersedes older snapshots below. It was rechecked against the live default branch, all ten open PRs, exact-head Tests associations, review-thread resolution state, workflow YAML, deployment files, and recursive migration trees.

### Default branch and CI

- `main` is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59Z); no newer main commit was found. Main still contains migrations 001–033.
- Main's latest recorded Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. The checked-in `.github/workflows/tests.yml` applies the migrations present on its checkout and runs pytest with a 57% coverage floor; it does not itself run the newer schema-audit or post-test DB-leakage gates.
- The latest visible overall Tests run is [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on PR #60 head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`: **cancelled** at 2026-11-02 06:50:28Z. Migration application and Compose helper tests passed; `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%, then a 120-second faulthandler timeout occurred during async fixture setup. The job was cancelled at its 20-minute limit. No assertion traceback, final test count, or coverage result is available.
- The branch-protection endpoint returned 403 `Resource not accessible by integration`; the repository rulesets endpoint returned an empty list. Therefore branch protection / required status checks cannot be conclusively verified in this run. Do not repeat the historical “main is unprotected” claim as a current fact.

### All ten open PRs — live heads, exact-head Tests association, unresolved / total review threads

| PR | Exact head | Exact-head Tests | Unresolved / total |
|---|---|---|---:|
| #48 PrivateMediaArtifact | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| #49 Outbound Message Library | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success | 1 / 80 |
| #50 Identity Registry | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success | 3 / 11 |
| #55 DB-leakage gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success | 0 / 0 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| #59 release documentation | this verification branch | documentation-only commits use `[skip ci]`; no exact-head Tests run expected | 3 / 3 |
| #60 contact-consent P0 | `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` | [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) cancelled | 11 / 11 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| #62 deployment preflight/seed integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success | 7 / 7 |
| #63 conversation observability | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success | 1 / 1 |

### Migration and integration state

- The historical duplicate-034 allocation is resolved at branch level. Live trees show main 001–033; #48 adds 034; #50 adds 035; #49 adds 036–037; #60 adds 038–040. #62 still carries 001–033 only.
- No single candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, combined schema audit, and zero DB leakage together.
- #48 and #60 both change the sole outbound worker and OutboundAuthorizationService. One reviewed candidate must preserve #48's exact OWNER view-once source binding/lock and post-success return audit together with #60's contact-consent, STOP, and final worker fence.
- #60 and #62 cannot be merged in either order. #60 has API-only runtime DB credentials, WAHA-only environment allowlists, and a runtime-role provisioner, but lacks #62's pre-DDL database-target, local-seed, and migration-sequence preflights. #62 has those preflights plus schema/leakage gates, but still injects the broad production env file into API/WAHA/migrate and does not provision the restricted runtime role. Consolidate these in one reviewed candidate.

### Remaining P0 and architecture blockers

1. **STOP linearization:** a STOP receipt may commit after the worker's final pending-intent read but before the WAHA request begins. The implementation treats the final read as the reservation/in-flight boundary. Fabian must explicitly accept or revise that contract; no database transaction can recall a network request once transport entry is underway.
2. **Quiet hours:** the current #60 authorization path returns early for an exact OWNER approval before checking contact-policy quiet hours; the ScheduledAction delivery branch also accepts an exact binding without the same policy check. Use one shared final external-contact policy fence and deny malformed timezone/window configuration.
3. **Alias-local limits:** `OutboundSafetyLimitService` keys per-contact backlog, rate, and duplicate suppression by `OutboundMessage.chat_id`, although consent is contact-wide across mapped aliases. Aggregate by stable Contact identity under the exact-chat mapping lock.
4. **Runtime-role CI:** isolate `test_runtime_role_cannot_mutate_or_disable_consent_history` on disposable PostgreSQL, capture the assertion traceback, and diagnose the subsequent fixture-setup timeout before another full-suite run.
5. **Identity Registry (#50):** decide whether generic introduction copy should mention projects/Datacube AU (recommended: remove those claims and keep project facts in Identity Registry answers). Do not infer historical seed provenance from `updated_at = created_at`; keep ambiguous pre-033 rows unknown unless immutable seed evidence or explicit OWNER attestation exists.
6. **Outbound Message Library (#49):** foundation only; no producer selection or dashboard. It must not be wired into live outbound before P0 and integrated migration gates pass. Private-media retention remains OFF.

No application code or migration was changed in this verification. No local tests, migrations, schema audit, or leakage audit were run. No production DB mutation, WAHA reconnection, or real WhatsApp send occurred.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh cross-PR verification — 2026-11-02 08:32 WAT

This snapshot supersedes the 06:34 WAT verification below. It was checked against live branch refs, exact-head Actions queries, GraphQL review threads, recursive migration trees, workflow YAML, deployment files, and the relevant outbound worker/authorization source. The documentation-only update does not certify release readiness.

### Main and workflow state

- Main remains 5aadd725ed9da08a5eb84eb42b64f0f45f231c79 (last commit 2026-09-08 11:09:59 UTC). The current branch endpoint reports protected=false and no required status checks.
- Main contains migrations 001–033 only. Its latest exact-head Tests run is 34219252390, successful on 2026-09-08; no newer run is associated with this exact main SHA.
- Main workflow blob 445b1fd628489b6a3b1c4f463880e4a1e709e978 applies all present SQL migrations lexically and runs pytest with a 57% coverage floor. It does not run the migration-sequence preflight, ORM schema audit, or post-test leakage audit.
- PR #60 workflow blob 66820c36fb2590226e8fc80f63c630da763804d1 adds a 20-minute job timeout and verbose pytest with a 120-second faulthandler timeout. It still applies only the migrations present on that branch.
- PR #62 adds the migration-sequence preflight, ORM schema audit, and post-test DB-leakage audit. Those gates are not yet integrated with PR #60's runtime-role/service-environment boundary.

### All open PRs — exact heads, exact-head Tests, review threads

Counts are unresolved / total; the final number in parentheses is active unresolved (not outdated).

| PR | Exact head | Latest exact-head Tests | Unresolved / total (active) |
|---|---|---|---:|
| #48 PrivateMediaArtifact | 3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca | 40158094566 success | 0 / 15 (0) |
| #49 Outbound Message Library | bcd0033e024b177561b8afd41589afe1897ba4de | 39920982545 success; 896 passed, 76.67% | 1 / 80 (1) |
| #50 Identity Registry | 0a2b38c0ce72b3c4a8fdd49490be504facb34bac | 41202063757 success; 828 passed, 76.52% | 3 / 11 (3) |
| #55 DB-leakage gate | 3d35793ef72cfcfe1e188bc51df6d4e538679f7b | 41026581000 success | 0 / 0 (0) |
| #57 local-seed safety | d831ce4e3dd7e56f38d8563dc63abc44f8c37bba | 40169146406 success | 1 / 1 (0) |
| #59 release documentation | 5821703c351ed949b0034e2b07779b287a7fcf54 before this update | No run; documentation commits use [skip ci] | 3 / 3 (1) |
| #60 contact-consent P0 | bcc34cdcd012e2735d5f51d899ff7a2274c018f9 | 41400297589 cancelled | 11 / 11 (6) |
| #61 migration-sequence gate | 8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f | 40300425938 success | 0 / 0 (0) |
| #62 deployment preflight/seed integration | a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc | 41073226073 success; 864 passed, 76.01% | 7 / 7 (4) |
| #63 conversation observability | 13fad868affe01d6069f4288481f8cd8dd341c62 | 41080836429 success; 803 passed, 76.08% | 1 / 1 (0) |

### Migration allocation and integration

The former duplicate-034 filename collision has been renumbered across the live feature branches. Recursive trees confirm main 001–033, #48 adds 034, #50 adds 035, #49 adds 036–037, and #60 adds 038–040. #62's branch still carries 001–033 only. This is now an integration/proof gap, not a duplicate-number collision.

No single candidate has proved all of the following together: fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum stability, schema audit against the modified schema, and zero DB leakage.

PR #48 and #60 both modify the sole outbound worker and OutboundAuthorizationService. #48 adds exact OWNER view-once source-message/chat/command binding, locks the active source immediately before dispatch, and records return only after successful transport. #60 adds external-contact consent, refreshed authorization/safety checks, current-contact mapping checks, and pending-STOP veto. Neither branch contains the other's complete worker behavior. They must be reconciled in one reviewed candidate; merge order alone is unsafe.

PR #60 and #62 also conflict in deployment. #60's Compose uses service-specific environment allowlists (API runtime DB URL, WAHA-only variables, migration-owner URLs only in migrate) and provisions a non-owner runtime role, but its runner lacks #62's pre-DDL database-target, local-seed, and migration-sequence preflights. #62 contains those preflights plus schema/leakage gates, but still mounts .env.production into API, WAHA, and migrate and does not provision the restricted runtime role. Neither branch is safe to merge independently.

### PR #60 latest source and CI evidence

- Commit bcc34cd changes the runtime-role provisioner, runtime URL verifier, and disposable-PostgreSQL test. It now revokes and verifies pg_auth_members edges in both directions and tests that neither a secondary login nor the runtime login can retain a SET ROLE path.
- Exact-head run 41400297589 completed as cancelled at 2026-11-02T06:50:28Z. Migration application passed. The Compose helper tests passed. Pytest marked test_runtime_role_cannot_mutate_or_disable_consent_history FAILED at 86%; the 120-second faulthandler then fired while pytest was in async fixture setup, and the job was cancelled at its 20-minute timeout. No assertion traceback, final suite count, or coverage result was produced.
- PostgreSQL logs show the intended denial probes for both SET ROLE directions, sequence setval, consent-event UPDATE/DELETE/TRUNCATE, ALTER TABLE DISABLE TRIGGER, CREATE TABLE, and SET ROLE to the migration owner. Those log lines do not identify which assertion failed; do not infer that the test passed.
- No newer exact-head Tests run exists for bcc34cd.

### Remaining P0 and architecture blockers

1. STOP linearization: a STOP receipt can commit after the worker's final pending-intent read but before the WAHA request begins. The current implementation treats that final read as the reservation point; an attempt already entering transport cannot reliably be recalled. Fabian must accept or revise this contract.
2. Quiet hours are not universal. OutboundAuthorizationService returns immediately for an exact active OWNER approval before loading the contact policy/quiet-hours row. The ScheduledAction exact-binding path also returns from the worker authorization helper without checking that policy. The final worker fence must apply current contact quiet hours to every external recipient, regardless of authority path, and deny invalid timezone/window configuration.
3. Per-contact backlog, rate, and duplicate suppression in OutboundSafetyLimitService filter by exact OutboundMessage.chat_id. Current aliases for one durable Contact can therefore consume separate limits. Aggregate against stable Contact identity and its current mapped aliases.
4. The API runtime role is now more strongly constrained on #60, but the exact-head integration test is cancelled and the runtime-role/deployment changes are not yet integrated with #62's preflight/schema/leakage gates.
5. PR #50's old introduction_reply lifecycle concern has been changed to fail closed on registry read errors. The remaining active review decisions are introduction-copy scope (recommended: remove project/Datacube claims from the generic greeting and keep project facts in Identity Registry answers) and truthful provenance for pre-033 rows. The migration's updated_at = created_at heuristic cannot reliably distinguish historical defaults from rows whose timestamps were advanced by earlier reads; preserve ambiguous legacy rows as legacy_unknown unless immutable evidence proves origin.
6. PR #49 remains a content-library foundation, not live producer/selection/dashboard integration. Its active review thread concerns permanent reservation of retired set keys; the current migration 037 registry and exact-head CI evidence are present, but the integrated 034–037 chain remains unverified.

### Next safe engineering step

On a disposable PostgreSQL 16 database, isolate test_runtime_role_cannot_mutate_or_disable_consent_history by itself with verbose output and fixture teardown tracing, capture the actual assertion traceback, and resolve that exact failure before another full suite. Then build one integrated reviewed candidate containing #48, #60, #62, #61, #57, and #55 behavior, preserving all worker and deployment invariants above. Do not merge any candidate without independent human review and authorization.

No local pytest, migration execution, schema audit, or DB-leakage audit was run for this documentation refresh. No production database mutation, WAHA reconnection, real send, or private-media retention activation occurred. Private-media retention remains OFF.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh cross-PR verification — 2026-11-02 (after runtime-role hardening)

This snapshot supersedes the 01:15 WAT snapshot below. GitHub state was re-queried from live branch refs, review threads, workflow runs, migration directories, and deployment files. Main itself has not advanced.

### Main and exact-head CI

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last commit 2026-09-08 11:09:59 UTC. Main is not branch-protected (`protected=false`).
- Main's latest visible Tests run for that exact SHA is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. No newer run for that exact main SHA was found.
- Main still contains migrations 001–033 and its deployment example still uses the same `postgres` login for `DATABASE_URL` and `DATABASE_URL_SYNC`; Compose injects `.env.production` into API, WAHA, and migrate.

### All open PRs — current heads, latest visible Tests, unresolved review threads

Counts are GitHub's unresolved threads / total threads; active excludes outdated unresolved threads.

| PR | Exact head | Latest visible Tests | Unresolved / total (active) |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 (0) |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success | 1 / 80 (1) |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success | 3 / 11 (3) |
| [#55 DB-leakage gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success | 0 / 0 (0) |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 (0) |
| [#59 release documentation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `36940ee92256f46a12916ddc48ca7675f74bfa6c` | No run (documentation commits use `[skip ci]`) | 3 / 3 (1) |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `bcc34cdcd012e2735d5f51d899ff7a2274c018f9` | [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) in progress; migration step passed, pytest/coverage still running | 11 / 11 (6) |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 (0) |
| [#62 deployment preflight/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success | 7 / 7 (4) |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success | 1 / 1 (0) |

### Migration and deployment integration

The historical 034 collision has been renumbered on the live feature branches. Current allocation is contiguous: #48=034, #50=035, #49=036–037, #60=038–040; main remains 001–033. No single candidate has proved the combined 001–040 fresh chain, installed 033→040 upgrade, second-run no-op/checksum stability, schema audit, and zero DB leakage.

The deployment branches still conflict: #60 separates API runtime credentials from migration-owner credentials and uses service-specific Compose environment allowlists, but its runner does not include #62's pre-DDL database-target, local-seed, and migration-sequence preflights. #62 has those preflights and seed guards but still mounts `.env.production` into API/WAHA/migrate and does not provision the restricted runtime role. Do not merge either branch independently or assume merge order preserves both.

PR #48 and #60 both change the sole outbound worker and authorization service. One integration candidate must preserve #48's OWNER view-once exact-source lock/return-after-success behavior and #60's external-contact consent/STOP/final safety fence. Do not merge by order alone.

### Latest #60 source work and remaining P0 blockers

- Commit [bcc34cd](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/bcc34cdcd012e2735d5f51d899ff7a2274c018f9) updates the runtime-role provisioner, runtime URL verifier, and disposable-PostgreSQL regression. It revokes/checks `pg_auth_members` in both directions and tests that a secondary login cannot `SET ROLE` into the runtime role after re-provisioning, while the runtime login cannot retain a parent-role `SET ROLE` path.
- Exact-head Tests run [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) is still in progress; do not claim a pass yet. The preceding exact-head run [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) was cancelled after the runtime-role integration test was marked failed at 86%; it produced no assertion traceback, final suite count, or coverage result.
- The new source change does not resolve the latest P0 policy question: a STOP receipt may commit after the worker's final pending-intent read but before the WAHA POST. The current contract treats the final read as the reservation/linearization point; an already-in-flight single attempt cannot reliably be recalled. OWNER must explicitly accept or revise that boundary.
- Current source review also finds quiet-hours checks can be bypassed by the exact OWNER-approval branch and exact ScheduledAction binding path; the final worker fence must enforce quiet hours for every external recipient and fail closed on invalid configuration.
- Per-contact backlog/rate/duplicate controls still key by exact chat ID, not stable Contact identity, so current aliases can consume separate limits. Aggregate these limits across a Contact's current mapped aliases before P0 completion.

**Release remains NOT TEST READY.** No integrated migration/schema/leakage candidate, no complete P0 adversarial matrix, no independent resolution of blocking review threads, and no controlled live test authorization. No local PostgreSQL/pytest execution, production DB mutation, WAHA reconnection, or real WhatsApp send occurred.

---

## Cross-PR worker integration verification — 2026-11-02 01:15 WAT

This source recheck adds one integration dependency not recorded in the 2026-11-01 23:22 snapshot. The live PR heads and exact-head workflow associations were re-queried; no code branch head changed during this audit. This is a documentation-only delta and uses `[skip ci]`; no exact-head CI result is claimed for the resulting documentation commit.

### Shared outbound worker changes: PR #48 + PR #60

- PR #48 is at `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`; exact-head Tests run [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) succeeded; review threads 0/15 unresolved.
- PR #60 is at `e0685c8bbeb380a684816b463ddd4f8eee4db10c`; exact-head Tests run [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) is cancelled; review threads 10/10 unresolved.
- Both branches change `bot_core/app/workers/background_workers.py` and `bot_core/app/services/outbound_authorization_service.py`. Their worker blobs are different from main and from each other (main `ea1e8b03`, #48 `bf4333eb`, #60 `42bc7fbc`); their authorization blobs are also different (main `37547232`, #48 `4812c993`, #60 `8d81190b`).
- #48 adds the OWNER view-once source-row lock before transport and records the return only after successful delivery; its authorization change binds exact source message/chat/command IDs into the OWNER payload digest. #60 adds the refreshed queue-row check, final authority recheck, external-contact consent fence, safety reservation, and pending-STOP veto; its authorization change locks the current contact-policy row.
- Neither branch contains the other's worker behavior. One integrated candidate must preserve both: external-contact authority/consent/STOP/safety before the single WAHA attempt; OWNER view-once exact source binding and active-source lock before the attempt; mark the source returned only after confirmed success. Do not choose a merge order that drops either path.
- This overlap is separate from the #60/#62 deployment-runner conflict. The same reviewed candidate must also combine #62's pre-DDL target/seed/sequence preflights and schema/leakage gates with #60's runtime-role and service-environment boundary.

### Exact-head P0 findings rechecked on #60

- Comparing #60's previous head `93f97fd192a3141869a419f5832df89b888ca9e2` to current `e0685c8bbeb380a684816b463ddd4f8eee4db10c` shows only `tests/unit/test_runtime_db_role.py` changed. The current authorization, worker, and safety-limit implementation files remain byte-identical to the previous head.
- Quiet hours still are not universal: an exact active OWNER approval returns before policy quiet-hours evaluation, and the exact ScheduledAction binding path returns without invoking that policy check. The worker's later consent and rate-limit checks do not evaluate quiet hours.
- The nominal per-contact backlog/rate/duplicate limits still filter by exact `OutboundMessage.chat_id`, so two current aliases of one Contact can consume separate limits and evade cross-alias duplicate suppression.
- The runtime-role provisioner and URL verifier still inspect membership where the runtime role is the member, not where it is the granted role. A second role granted `zina_runtime` can retain a `SET ROLE` path. The current runtime-role test also remains unexplained: run 41311022671 marked it FAILED at 86%, then emitted a 120-second faulthandler timeout and was cancelled; no assertion traceback, final suite count, or coverage was captured.
- These source-grounded findings were refreshed in existing #60 comment [6557906754](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6557906754); the #48/#60 worker overlap was recorded in [6566210443](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6566210443). Both are owner-authored engineering notes, not independent approval.

### Migration/release status unchanged

Migration numbering is allocated contiguously: #48=034, #50=035, #49=036–037, #60=038–040. Main remains 001–033. No single candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, combined schema audit, and zero DB leakage. The current #60 workflow applies 001–033 plus 038–040 and skips 034–037.

No source code or migration was changed, no test or migration was run locally, no Actions run was triggered, and no production DB or WAHA action occurred. Keep all affected PRs open for independent review.

---

## Current engineering verification — 2026-11-01 23:22 WAT

This delta supersedes the earlier 20:23 WAT snapshot below. It was checked against the live repository and all ten open pull requests. PR #59 was at `ac071ac25f7118717914bdb4956b62aa76830b7e` when this audit began; the two documentation commits that append this delta intentionally use `[skip ci]`. No exact-head CI result is claimed for the resulting docs head.

### Main and workflow

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (latest main commit: 2026-09-08 11:09:59 UTC). Its migration directory contains 001–033 only.
- The latest visible Tests run associated with main is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. No newer run is associated with this exact main SHA.
- Main `.github/workflows/tests.yml` triggers on pull requests and pushes to main/master, uses PostgreSQL 16, applies `bot_core/migrations/*.sql` lexically, and runs pytest with a 57% coverage floor. Main does not yet contain the sequence preflight, schema audit, or post-test DB-leakage gate now proposed in #61/#62/#55.

### All live open PRs — exact heads, latest visible exact-head Tests, unresolved / total review threads

| PR | Exact head | Latest visible exact-head Tests | Unresolved / total |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| [#57 deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 documentation refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `ac071ac25f7118717914bdb4956b62aa76830b7e` at audit start | No run for this exact head; documentation commits use `[skip ci]` | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `e0685c8bbeb380a684816b463ddd4f8eee4db10c` | [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) **cancelled**; runtime-role test marked failed at 86%, then faulthandler timeout; no final count/coverage | 10 / 10 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All ten PRs remain open. A green branch-local run is not integrated release proof and does not replace independent review. Thread counts are live GitHub `is_resolved` counts, not comment counts.

### Migration and deployment reconciliation

- Migration numbering is now contiguous at branch level: #48 owns 034; #50 owns 035; #49 owns 036–037; #60 owns 038–040. The former duplicate-034 filename collision is resolved by renumbering.
- The branches remain separate. Main has 001–033. #60's latest workflow applied 001–033 plus 038–040 and skipped 034–037. No candidate has proved a fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksum behavior, combined schema audit, and zero DB leakage together.
- #60 and #62 cannot safely merge in either order. #60 contains the restricted runtime API role and service-specific API/WAHA environment allowlists, but lacks #62's database-target, local-seed, and contiguous-sequence preflights. #62 contains those preflights plus schema/leakage checks, but still mounts broad `.env.production` into API, WAHA, and migrate and does not provision the restricted runtime role. Consolidate #60 with #62/#61/#57/#55 into one independently reviewed candidate before any merge.

### Current source and review blockers

- **P0 contact consent is not on main.** Explicit contact consent and terminal STOP enforcement at final dispatch exist only on open #60. Main still has the older outbound authority path without this proposed consent domain.
- **Runtime-role membership is one-directional on #60.** `deploy/scripts/provision-runtime-role.sql`, the runtime verifier, and the disposable integration test inspect memberships where `pg_auth_members.member = runtime_role`, but do not revoke/check where `pg_auth_members.roleid = runtime_role`. A second role granted `zina_runtime` may still `SET ROLE zina_runtime`. The current-head security review [5729336758](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#pullrequestreview-5729336758) requires symmetric revocation, two-direction verification, and a second-role PostgreSQL regression.
- **The #60 runtime-role test remains unexplained.** Run 41311022671 applied its branch migrations and the two Compose helper tests passed. `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%; a 120-second faulthandler timeout followed and the job was cancelled at the 20-minute limit. The log shows the runtime-role denial probes for sequence mutation, UPDATE/DELETE/TRUNCATE, trigger disable, schema CREATE, and SET ROLE; it does not include the assertion traceback or final suite/coverage. Do not infer the failed assertion. Reproduce the single test on disposable PostgreSQL with bounded, robust cleanup before another full run.
- **Quiet hours are not a universal final external-delivery fence on #60.** `OutboundAuthorizationService.authorize()` returns for an exact OWNER approval before loading the contact policy and checking `quiet_hours_json`. The open review comment [6557906754](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6557906754) also identifies the ScheduledAction worker branch accepting an exact binding without the policy quiet-hours check. Move this to one shared final external-contact fence covering owner approvals, scheduled actions, and contact policies; malformed timezone/window configuration must deny. Add zero-mock-WAHA tests for overnight and invalid configurations.
- **Per-contact limits are alias-local on #60.** `OutboundSafetyLimitService` counts backlog, recent sends, and duplicates by `OutboundMessage.chat_id`; the consent domain explicitly supports multiple mapped aliases for one Contact. A second alias can therefore consume a separate nominal per-contact budget and avoid duplicate suppression. Aggregate those reservations by stable Contact identity under the established exact-chat mapping lock; add a two-alias regression.
- **#50 still has three unresolved Identity Registry decisions.** `introduction_reply()` now checks availability of `zina` and `fabian` and fails closed on registry read errors, but its generic copy still claims “his projects” and “Datacube AU” without checking `projects` / `datacube_au`. Recommended bounded contract: remove project claims from the generic introduction and answer project facts only through Identity Registry. Migration 035 still cannot infer legacy default provenance from `updated_at = created_at`; leave historically ambiguous rows unclassified (`legacy_unknown`) unless immutable seed evidence or explicit OWNER attestation exists.
- **#49 remains a foundation only**: no live producer selection or dashboard integration. It answers what Zina could say, never whether a send is authorized. Keep it out of live outbound until P0 and migration integration are cleared. #48 remains metadata/observation only; private bytes are absent and retention remains OFF.
- #63's malformed internet-observability parsing is fixed on its current head, but one independent review thread remains unresolved.

### Work and readiness

This run re-queried main, all ten open PRs, review threads, workflow YAML, migration filenames, exact-head run associations, PR #60's current consent/runtime-role source, and the failed Actions job log. No source code or migration was changed; only this durable verification snapshot is being refreshed. No local pytest, fresh/upgrade migration, schema audit, or DB-leakage run was available in this run.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Current engineering verification — 2026-11-01 20:23 WAT

This delta supersedes the 18:21 WAT snapshot below. It re-queries the current main SHA, all ten open PR heads, exact-head Tests runs, review-thread resolution flags, migration filenames, the checked-in workflow, and the current deployment branches. It also corrects the #48/#49 unresolved-thread counts in the preceding 18:21 table: GitHub's live GraphQL `is_resolved` values are 0/15 and 1/80, not 15/15 and 80/80.

### Main and workflow

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; its tree contains migrations 001–033 only.
- Exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. No newer run is associated with this exact main SHA.
- Main `.github/workflows/tests.yml` still applies `bot_core/migrations/*.sql` lexically and runs pytest with a 57% coverage floor. It has no migration-sequence preflight, schema audit, or post-test DB-leakage audit.
- The live branch API currently reports `main.protected=false`; required status checks are therefore not enforced by the branch-protection setting.

### All open PRs — exact heads, exact-head Tests, unresolved / total review threads

| PR | Exact head | Latest exact-head Tests | Unresolved / total |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success | 3 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success | 0 / 0 |
| [#57 deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 documentation refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `50165b4eaba55c1b8b14ce66efe8bb58f7cb7ddb` before this update | No exact-head run; documentation commits use `[skip ci]` | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `e0685c8bbeb380a684816b463ddd4f8eee4db10c` | [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) cancelled; pytest marked the runtime-role integration test failed at 86%, then the 120-second faulthandler fired; no traceback, final count, or coverage | 10 / 10 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success | 1 / 1 |

All ten PRs remain open. A successful branch-local run does not establish integrated release readiness or replace independent review. This documentation update itself is `[skip ci]`; no exact-head run is claimed for the new docs commit.

### Migration and deployment reconciliation

- Branch migration filenames were re-fetched: #48 owns 034; #50 owns 035; #49 owns 036–037; #60 owns 038–040. The old duplicate-034 filename collision has been renumbered at branch level.
- The branches remain separate. Main has 001–033; #60's own workflow run applied 001–033 plus 038–040 and skipped 034–037. No candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum behavior, combined schema audit, and zero DB leakage together.
- #60 and #62 are still unsafe to merge in either order. #60 has the restricted runtime API role and service-specific Compose environment allowlists, but lacks #62's database-target, local-seed, and migration-sequence preflights. #62 has those preflights, but its current Compose file still mounts `.env.production` into API, WAHA, and migrate; it lacks #60's restricted runtime-role provisioner. Consolidate #60/#62 with #61/#57/#55 into one independently reviewed candidate before merge.
- #61's migration-sequence gate has a green branch-local run, but it does not by itself integrate migrations 034–040. #55's DB-leakage gate is also green only on its own head; combined leakage proof remains outstanding.

### P0 review findings and blockers

- Contact consent and terminal STOP enforcement are still only on open PR #60, not main. Main therefore does not yet have the proposed explicit consent/opt-out gate at final external dispatch.
- On exact #60 head `e0685c8...`, the provisioner, runtime verifier, and integration test still check role memberships only where `pg_auth_members.member = runtime_role`. They do not revoke or reject the reverse edge where another role has been granted `zina_runtime` and could `SET ROLE` into it. The current-head inline security review [5729336758](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#pullrequestreview-5729336758) asks for symmetric revocation, verification, and a disposable-PostgreSQL regression.
- Quiet-hours enforcement is not universal on that same head: `OutboundAuthorizationService.authorize()` returns at line 351 for an exact OWNER approval before reading the contact policy's quiet-hours configuration; `background_workers.py::_delivery_authorized()` accepts an exact ScheduledAction binding at lines 396–401 without calling that policy check. The worker's consent/pending-STOP checks do not substitute for quiet-hours enforcement. The earlier #60 review finding remains applicable to this head.
- `OutboundSafetyLimitService` still keys per-contact rate, backlog, and duplicate queries by exact `chat_id`, while the consent code supports multiple aliases for one stable Contact. A second alias can therefore evade the nominal per-contact ceiling and duplicate suppression; the existing #60 review finding remains open.
- The current #60 Actions log confirms the Compose helper regressions passed, then `test_runtime_role_cannot_mutate_or_disable_consent_history` was marked FAILED at 86%. The 120-second faulthandler dump contains no assertion traceback; the job was cancelled before a final summary. Do not infer the failure cause or treat this as green. Reproduce that test alone on disposable PostgreSQL with bounded cleanup and preserve its traceback.
- OWNER decisions still required on #60: whether STOP is permanently terminal or can be reversed by an explicit OWNER re-consent, and what evidence-reference semantics are acceptable for an OWNER grant.
- #50 still has three unresolved review threads; retain fail-closed handling for registry-read errors and do not infer legacy provenance from timestamp equality. Any generic introduction project claims must be backed by the Identity Registry or removed.

### This run and readiness

No source code was edited, no local pytest or migration run was performed, and no schema/leakage audit was executed in this run. The work was a fresh source/CI/review inspection plus correction of the stale review-count snapshot in these existing documentation files. No merge, approval, review-thread resolution, production DB operation, WAHA reconnection, or real send occurred.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**

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

## Current engineering verification — 2026-11-01 16:25 WAT

This snapshot supersedes the 10:27 WAT overlay below. It was checked against the live main ref, all ten open PR heads, their review threads, exact-head Actions associations, workflow YAML, migration trees, and deployment files. It is an engineering status snapshot, not release approval. The documentation PR itself is the only work changed by this commit.

### Main baseline and workflow

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC). Main has migrations 001–033 only.
- Main's latest exact-SHA Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. The checked-in `.github/workflows/tests.yml` runs PostgreSQL 16, applies every `bot_core/migrations/*.sql` file lexically, then runs pytest with a 57% coverage floor. Main's workflow has no migration-sequence preflight, schema audit, or post-test DB-leakage audit.
- Main `docker-compose.yml` still mounts `.env.production` into postgres, API, WAHA, and migrate. Main's `deploy/scripts/run-migrations.sh` has no local-seed opt-in guard or restricted API runtime role; it applies every seed on each invocation and then runs the schema audit.
- The branch-protection endpoint returned 403 (`Resource not accessible by integration`). The rulesets endpoint returned an empty list, but that does not prove that branch protection is disabled. Protection state is therefore unverified in this run.

### Open PRs — exact heads and review state

| PR | Exact head at audit | Latest exact-head Tests evidence | Unresolved / total threads |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| [#57 deployment seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 documentation refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `7a56ce9cb4e94453b00514c1555e57f946d4ba8c` before this docs-only refresh | No run on this exact docs head; parent code/test head `d8edcae5a8f16da22def88093a2573ab9ca8278f` passed [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250): 797 passed, 76.01%, migrations 001–033 only | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `e0685c8bbeb380a684816b463ddd4f8eee4db10c` | [41311022671](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41311022671) cancelled; `test_runtime_role_cannot_mutate_or_disable_consent_history` failed at 86%, followed by a 120-second faulthandler timeout and 20-minute job cancellation; no final count/coverage | 9 / 9 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All ten PRs remain open. Zero unresolved threads on a PR is not an approval. No PR was merged, approved, or had a review thread resolved in this run.

### Migration allocation and deployment integration

The former 034 filename collision has been renumbered at branch level, but the branches are still not one tested release candidate:

- #48 owns migration 034.
- #50 owns migration 035.
- #49 owns migrations 036–037.
- #60 owns migrations 038–040.
- Main, #55, #57, #61, and #62 contain only 001–033.

No candidate has proved fresh migrations 001–040, installed upgrade 033→040, second-run no-op/checksum behavior, schema audit, and DB-leakage audit together.

PR #60 and #62 remain unsafe to merge in either order:
- #60 introduces the restricted API runtime role and service-specific environment allowlists, but does not carry #62's migration-target, local-seed, and contiguous-sequence preflights.
- #62 carries those preflights and schema/leakage controls, but its Compose file still injects broad `.env.production` into API, WAHA, and migrate and does not provision the restricted runtime role.
- Consolidate #60 with #62/#61/#57/#55 in one reviewed candidate. All database-target, role, seed, and sequence checks must complete before the first DDL. Only migrate receives owner credentials; API receives the restricted runtime URL; WAHA receives transport-only settings.

### P0 and architecture blockers

- Main has the existing recipient- and payload-bound outbound delivery fence, but contact consent and terminal STOP enforcement at final dispatch exist only on open PR #60, not main.
- On #60's latest run, both Compose helper tests passed, so the previously documented nested-service-key helper defect is corrected on the current head. The remaining observed failing node is `test_runtime_role_cannot_mutate_or_disable_consent_history`; the captured log has no final assertion traceback. PostgreSQL logs show expected privilege denials, but they do not establish why pytest marked the node failed. Reproduce the test alone on disposable PostgreSQL before claiming a root cause.
- #60's provisioner and test inspect memberships where `zina_runtime` is the member, but not where it is the granted role (`pg_auth_members.roleid`). A pre-existing role granted `zina_runtime` could still be able to assume that runtime role. Revoke or reject memberships in both directions and test a second temporary role that is granted `zina_runtime`.
- #60 still needs OWNER decisions on terminal STOP semantics (currently terminal across mapped aliases, with no re-consent/override) and on whether the opaque consent evidence reference attests independently obtained contact consent or whether contact consent and OWNER automation permission remain separate requirements.
- #50's registry-read failure path now fails closed on its current head. Two identity decisions remain: remove project/Datacube claims from the generic introduction and route those facts through Identity Registry; stop using `updated_at = created_at` as historical provenance proof and leave ambiguous pre-033 rows unknown unless immutable evidence or explicit OWNER attestation exists.
- #49 remains a content-library foundation, not live producer selection or dashboard integration; it never grants send authority. #48 remains metadata observation only; private bytes are absent and retention must remain OFF.

### Highest-value next safe step

Reproduce and isolate the #60 runtime-role integration failure, close the two-direction role-membership check, then consolidate #60 with #62/#61/#57/#55 and run the full disposable-PostgreSQL fresh/upgrade/no-op/checksum/schema/leakage/P0 matrix. Keep all PRs open for independent review.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.** No local PostgreSQL test, local pytest run, migration execution, or leakage audit was available in this documentation-only run. No production DB mutation, WAHA reconnection, real send, private-media retention activation, merge, or approval occurred.

---

## Current engineering verification — 2026-11-01 10:27 WAT

This snapshot supersedes the 08:21 WAT overlay below. It is a live source/PR verification, not release approval. Exact-head CI on one feature branch does not prove the integrated migration chain.

### Main baseline and workflow

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC). The branch API reports `protected=false` / protection disabled and the repository rulesets list is empty; required checks are not enforced by the current branch metadata.
- Main contains migrations 001–033 only. Its latest exact-SHA Tests run is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on `5aadd725...` at 2026-09-08 11:10 UTC. The current main combined-status endpoint reports no individual status contexts.
- Main workflow `.github/workflows/tests.yml` (blob `445b1fd628489b6a3b1c4f463880e4a1e709e978`) applies migration files lexically and runs pytest with a 57% coverage floor. It has no migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit.
- Latest repository Tests run is PR #60 run [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626), cancelled at 2026-11-01 04:46 UTC on head `93f97fd192a3141869a419f5832df89b888ca9e2`. Migrations 001–033 and 038–040 completed; 034–037 were skipped. Pytest reached 86%, reported two failed nodes, emitted a 120-second faulthandler timeout, and the 20-minute job was cancelled. There is no final test count or coverage result.
- Confirmed #60 failure 1: `_compose_service_block(compose, "migrate")` matches the nested `api.depends_on.migrate` key instead of the top-level `services.migrate` block. Parse Compose YAML structurally or anchor top-level keys (for example `(?m)^  migrate:$`) and add a regression for nested-vs-top-level service names. See [comment 6554967378](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6554967378).
- #60 failure 2, `test_runtime_role_cannot_mutate_or_disable_consent_history`, has no captured assertion traceback because the job was cancelled. PostgreSQL logs show the runtime connection received permission denials for `setval`, UPDATE, DELETE, TRUNCATE, trigger alteration, CREATE, and SET ROLE, but that is not proof the test passed; reproduce it alone on disposable PostgreSQL and inspect cleanup/fixture teardown before inferring a root cause.

### Open PRs — exact current heads and review threads

| PR | Exact head | Exact-head Tests evidence | Unresolved / total threads |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| [#57 seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 documentation refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `6150ff03c19bb52bc49afaf39b5c4e65058be9ea` | No exact-head run (`[skip ci]` docs-only commit); predecessor code/test head `d8edcae5a8f16da22def88093a2573ab9ca8278f` run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250) succeeded: 797 passed, 76.01%, migrations 001–033 only | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `93f97fd192a3141869a419f5832df89b888ca9e2` | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) cancelled; two failed nodes and fixture timeout; no final count/coverage | 8 / 8 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All ten PRs remain open. No independent approval was found in the retrieved review submissions; comments and green branch-local runs are not approvals.

### Migration allocation and deployment integration

Current branch trees allocate migrations without a filename collision: #48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040. Main remains 001–033. #61 and #62 contain only 001–033. The old duplicate-034 allocation has been renumbered at branch level, but no branch proves fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, schema audit, and DB leakage together.

PR #60 and #62 are unsafe in either merge order:
- #60 has the restricted runtime role and service-specific environment allowlists (API gets only `DATABASE_URL_RUNTIME`; WAHA gets transport settings; migrate gets owner URLs), but its runner lacks #62's pre-DDL database-target, local-seed, and contiguous-sequence preflights.
- #62 carries the #57 seed guard, #61 sequence preflight, and #55 schema/leakage controls, but still mounts broad `.env.production` into API, WAHA, and migrate and does not provision the restricted runtime role.
- Consolidate the two into one reviewed candidate. Every target/role/seed/sequence preflight must execute before the first DDL; only migrate receives owner credentials; API receives the non-owner runtime URL; WAHA receives only transport variables. Then prove fresh 001–040, installed 033→040 upgrade, rerun/checksum behavior, schema audit, DB leakage, and runtime-role privileges on disposable PostgreSQL.

### P0 and architecture decisions

- Main has the existing exact-payload outbound authorization fence, but not PR #60's contact-consent state, durable STOP receipts, or final consent fence. Explicit contact consent and terminal opt-out are not yet verified main-branch capabilities.
- PR #60's current STOP policy is terminal across a Contact's mapped WhatsApp aliases and has no owner re-consent/override command. OWNER must explicitly accept or revise this policy. A STOP committed before final dispatch reservation vetoes; once a single WAHA request enters transport it cannot reliably be recalled, and an uncertain attempt must never be replayed.
- `.contact consent grant <exact-chat-id> <evidence-ref>` records an OWNER attestation plus an opaque evidence reference. OWNER must decide whether that reference proves independently obtained contact consent (and points to durable external evidence), or whether contact consent and OWNER automation permission must remain separate authorities and both be required at dispatch.
- PR #60's runtime-role provisioner/validator currently checks memberships where `zina_runtime` is the member, but not memberships where `zina_runtime` is the granted role. A pre-existing role granted `zina_runtime` could still assume its DML privileges. Revoke or fail on those incoming memberships too; verify both `pg_auth_members.member` and `pg_auth_members.roleid`, and test a second temporary role granted `zina_runtime`. See [comment 6554387711](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6554387711).
- PR #50 now fails closed on registry-read errors and its prior deleted/disabled identity guard has been expanded. The remaining introduction decision is architectural: `introduction_reply()` still says “his projects, and Datacube AU” while checking only `zina`/`fabian`; the recommended single-authority fix is to limit the generic introduction to Zina/Fabian and answer project facts only through Identity Registry.
- Migration 035 still backfills `source`/`entity_type` when `updated_at = created_at`. That timestamp equality is not immutable proof for pre-033 rows because earlier reads/edits could have advanced `updated_at`. Preserve ambiguous legacy rows as unknown/NULL; stamp only new defaults, and classify old rows only through immutable evidence or explicit OWNER attestation.
- PR #49 is a content-library foundation, not live producer selection or dashboard integration. It answers what could be said, never whether an exact send is authorized. Do not wire it into live outbound until P0 and migration integration are cleared. PR #48 remains metadata/observation work; private bytes are absent and retention stays OFF.

### Next safe step and readiness

Fix the #60 Compose service-block regression and reproduce the runtime-role integration test independently; close the incoming-membership gap with a two-direction privilege regression. Then create one #60/#62/#61/#57/#55 integration candidate and run the complete disposable PostgreSQL fresh/upgrade/no-op/schema/leakage/P0 matrix. Keep all PRs open for independent review.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.** No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, merge, or approval occurred.

---
## Current engineering verification — 2026-11-01 08:21 WAT

This snapshot was re-fetched from GitHub and checked against the live source/PR heads. It is a verification delta, not a release certification. It supersedes the older 07:18 WAT snapshot below; branch-local CI is not integrated migration proof.

### Main baseline and workflow

- Main is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest commit is 2026-09-08 11:09:59 UTC. The branch endpoint reports `protected=false` and `protection.enabled=false`.
- Main contains SQL migrations 001–033 only. The main Tests run is still [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), green on that exact SHA at 2026-09-08 11:10 UTC.
- Main `.github/workflows/tests.yml` applies `bot_core/migrations/*.sql` lexically, then runs pytest with a 57% coverage floor. It has no migration-sequence preflight, schema audit, or post-test DB-leakage audit. PR #61, #62, and #55 add those controls on separate unmerged branches.
- The latest repository workflow run is PR #60 Tests [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626), cancelled at 2026-11-01 04:46 UTC. Its migration step applied 001–033 and 038–040, skipping 034–037. Pytest reached 86%, reported two failures, then emitted a 120-second async-fixture faulthandler timeout; the 20-minute job ended without a final failure summary, test count, or coverage result. The first failure's source-level cause is now documented in [PR #60 comment 6554967378](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6554967378); the second failure still needs an isolated reproduction.
- Main's latest CI result remains the 2026-09-08 run above. The latest successful run visible among current PR snapshots is PR #59's predecessor code/test head `d8edcae5a8f16da22def88093a2573ab9ca8278f`, run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250): 797 passed, 76.01%; it applied only 001–033. The live PR #59 head is now `1c5438955c07e54e95f0e63fa18851798f525c73` and has no exact-head run.

### Open PRs — live heads and review threads

| PR | Exact head | Exact-head Tests evidence | Unresolved / total threads |
|---|---|---|---:|
| [#48 PrivateMediaArtifact](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |
| [#49 Outbound Message Library](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 |
| [#50 Identity Registry](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 |
| [#55 DB-leakage audit](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 |
| [#57 seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 |
| [#59 docs refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `1c5438955c07e54e95f0e63fa18851798f525c73` | No exact-head run; docs-only `[skip ci]` update | 3 / 3 |
| [#60 P0 contact consent](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `93f97fd192a3141869a419f5832df89b888ca9e2` | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) cancelled; two test failures and fixture timeout; no count/coverage | 8 / 8 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 |
| [#62 deployment preflight/seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 |

All ten PRs remain open. Zero unresolved threads is not an approval; no PR was approved or merged in this run.

### Migration and deployment integration

The actual branch trees now allocate migrations without a filename collision: #48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040. Main remains 001–033. This resolves the old duplicate-number allocation at branch level only; no candidate has yet proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, schema audit, and DB leakage together.

PR #60 and #62 are unsafe in either merge order:
- #60 has the API runtime-role and API/WAHA/migrate environment split, but its runner lacks #62's pre-DDL database-target validation, local-seed opt-in/allowlist, and contiguous-sequence preflight.
- #62 has target/seed/sequence guards, but still mounts broad `.env.production` into API, WAHA, and migrate and does not provision the restricted runtime role.
- Consolidate both into one reviewed candidate. Keep every target/role/sequence/seed preflight before the first database mutation; API receives only the non-owner runtime URL; WAHA receives only transport settings; migrate alone receives owner credentials; then prove fresh 001–040, installed 033→040 upgrade, rerun/checksum behavior, schema audit, leakage, and runtime-role privileges on disposable PostgreSQL.

### P0, identity, and product blockers

- Main contains the existing exact-payload outbound fence, but not PR #60's contact-consent state, terminal opt-out receipts, or final consent fence. Contact-specific consent is therefore not yet a verified main capability.
- PR #60's current STOP policy is terminal across a Contact's mapped aliases and has no re-consent/override command. OWNER must accept or revise that policy. A STOP committed before final dispatch reservation vetoes; after a single WAHA request enters transport it cannot reliably be recalled, and an uncertain send must never be replayed.
- OWNER must decide whether `.contact consent grant <chat> <evidence-ref>` means an attestation that independently obtained contact consent exists (with a durable external evidence reference), or whether contact consent and OWNER automation permission must be separate authorities.
- PR #60 also has an unresolved least-privilege finding about incoming memberships granted *to* `zina_runtime` (comment [6554387711](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6554387711)); both directions of `pg_auth_members` need explicit treatment.
- PR #50 now fails closed when the registry read fails, but its generic introduction still names projects/Datacube AU without gating those Identity Registry entries. The open recommendation is to keep the introduction limited to Zina/Fabian and let project claims come from the registry.
- Migration 035 still uses `updated_at = created_at` as historical provenance evidence. That cannot reliably classify pre-033 rows whose timestamps were already advanced by earlier reads/edits. Preserve ambiguous legacy rows as unknown/NULL unless immutable evidence or an explicit OWNER attestation proves provenance.
- PR #49 remains a message-library foundation, not live producer selection or dashboard integration. It answers what could be said, never whether sending is authorized. PR #48 remains metadata/observation work; private byte retention stays OFF.

### Next safe engineering step and readiness

First fix the two failing #60 runtime-role tests (the Compose helper's nested `depends_on.migrate` match is a confirmed root cause; the runtime-role test still needs isolated reproduction), then build one integrated #60/#62/#61 candidate and run the complete disposable-PostgreSQL matrix. Do not start controlled real-world testing until exact-head tests, integrated migrations, upgrade/no-op/checksum, schema audit, leakage, runtime-role restrictions, P0 adversarial tests, and independent reviews are all green.

**Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.** No production DB mutation, WAHA reconnection, send, merge, or approval occurred.

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

## Current verification — 2026-11-01 06:21 WAT

This overlay supersedes the historical snapshots below. The detailed phase-by-phase inventory later in this file still originates from the 2026-09-08 audit; it is not a fresh code inventory.

### Main, branch protection and workflow

- Main remains 5aadd725ed9da08a5eb84eb42b64f0f45f231c79 (last commit 2026-09-08); main contains SQL migrations 001–033 only. Branch-protection/ruleset state could not be re-queried in this run (GitHub API returned 403 Resource not accessible by integration); the earlier unprotected/no-required-checks finding is historical, not reconfirmed.
- Main Tests run 34219252390 succeeded on that exact SHA. The checked-in tests workflow (blob 445b1fd628489b6a3b1c4f463880e4a1e709e978) provisions PostgreSQL 16, applies migrations lexically, and runs pytest with a 57% coverage floor. It does not run migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit.
- The Strix workflow is a local-repository-only manual scan plus PR policy validation; no Strix scan was run in this verification.
- Latest exact-head Tests run 41273052626 on PR #60 head 93f97fd192a3141869a419f5832df89b888ca9e2 was CANCELLED at 2026-11-01T04:46:00Z. The migration step completed for 001–033 plus 038–040, but the pytest/coverage step was cancelled; no test count or coverage result exists for this head. It skipped feature migrations 034–037, so it is not an integrated-chain result.
- PR #60 engineering update: commits d14d6eb6a7c0c3e7e382b0552b9e16e65fffe630 and 93f97fd192a3141869a419f5832df89b888ca9e2 remove UPDATE from the runtime sequence grant/default ACL, explicitly revoke it from the consent-event BIGSERIAL sequence, and verify UPDATE is absent. The disposable role test now uses a guarded test target, unique per-run credentials, grant/default-ACL cleanup and role deletion; it checks setval() denial. The Compose test's undefined migration_runner reference is also fixed. The exact-head run was cancelled during pytest/coverage at 04:46 UTC; only the migration step completed. Independent review remains pending.
- Latest completed successful Tests run remains 41238779250 on PR #59 parent head d8edcae5a8f16da22def88093a2573ab9ca8278f: 797 passed, 1 warning, 76.01% coverage. Its job applied migrations 001–033 only; it did not exercise feature migrations 034–040, schema audit, migration preflight, or DB-leakage audit.
- This documentation-only refresh is marked [skip ci]; no exact-head CI result is claimed for the new docs commit.

### Open PRs — exact heads and review state

| PR | Exact head | Latest exact-head Tests evidence | Unresolved / total threads | Current scope / limitation |
|---|---|---|---:|---|
| [#48](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | 3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 | PrivateMediaArtifact observation/return metadata only; no private byte store; retention remains OFF. Migration 034. |
| [#50](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | 0a2b38c0ce72b3c4a8fdd49490be504facb34bac | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 | Identity Registry lifecycle; registry-read failures fail closed. Introduction-copy scope and truthful legacy provenance remain human decisions. Migration 035. |
| [#49](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | bcd0033e024b177561b8afd41589afe1897ba4de | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 | Outbound Message Library data foundation only; no live producer, selector, or dashboard, and no send authority. Migrations 036–037. |
| [#55](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | 3d35793ef72cfcfe1e188bc51df6d4e538679f7b | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 | Adds post-test database-leakage auditing; incorporated into deployment candidate #62. |
| [#57](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | d831ce4e3dd7e56f38d8563dc63abc44f8c37bba | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 | Local fixture-seed safety; coordinate with #62 rather than merge overlapping runner changes independently. |
| [#59](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | This self-updating docs branch; see live PR | No CI for [skip ci] docs-only commits; prior code/test head d8edcae5 run [41238779250](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41238779250) passed 797 tests at 76.01% on migrations 001–033 | 3 / 3 | Documentation refresh; no exact-head CI is claimed. |
| [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | 93f97fd192a3141869a419f5832df89b888ca9e2 | [41273052626](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41273052626) CANCELLED during pytest/coverage after 001–033 and 038–040; no test count/coverage | 8 / 8 | Draft P0 contact-consent fence; migrations 038–040. Runtime-role sequence/test hardening is on this head but not yet CI-verified; deployment integration with #62 remains blocking. |
| [#61](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | 8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 | Contiguous migration-sequence preflight; branch-local run does not prove the integrated feature chain. |
| [#62](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 | Draft integration of seed safety, sequence preflight, schema audit, and leakage audit. Compose still injects broad .env.production into API/WAHA/migrate and lacks #60's runtime-role split. |
| [#63](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | 13fad868affe01d6069f4288481f8cd8dd341c62 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 | Conversation-observability audit correction; malformed internet counters fail closed, but independent review remains open. |

Zero review threads is not equivalent to independent approval. All ten PRs remain open; no approval or merge is implied by branch-local CI.

### Migration order and integration blocker

- Feature migration allocation is contiguous by branch: #48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040. The former duplicate 034 allocation is renumbered. Main still has only 001–033.
- Branch-local migration tests are not an integrated chain: #50 runs 035 without 034; #49 runs 036–037 without 034–035; #60 runs 038–040 without 034–037. No exact candidate has proved fresh 001–040, installed 033→040 upgrade, second-run no-op/checksum behavior, schema audit, and zero DB leakage together.
- #60 and #62 cannot safely be merged in either order. #60 has the runtime-role/API/WAHA environment split but lacks #62's pre-DDL migration-target, local-seed, and contiguous-sequence guards. #62 has those deployment guards but still mounts .env.production into API, WAHA, and migrate and does not provision the runtime role. Consolidate both into one reviewed candidate before either merge.

### P0 and architectural blockers

1. Runtime-role test safety and consent-sequence least privilege: the fixes are present on #60 head 93f97fd; exact-head Tests run 41273052626 was cancelled during pytest/coverage after the migration step; no test count or coverage result exists. The corresponding review threads remain unresolved. Do not call the privilege boundary verified until the runtime-role integration test passes.
2. STOP policy (#60): opt-out is terminal across current mapped aliases; there is no owner re-consent/override command. The OWNER must explicitly accept or revise this product policy. A STOP committed before final reservation vetoes; an already in-flight WAHA attempt cannot reliably be recalled and must never be blindly retried/replayed.
3. Deployment/operator contract (#60/#62): consolidate the restricted runtime role with the pre-DDL target, local-seed and sequence checks. Keep owner URLs/bootstrap secret only in migrate, runtime URL only in API, and WAHA-only settings in WAHA. Validate existing-install credential rotation without exposing either credential to the wrong container.
4. Introduction copy (#50): the generic greeting still needs a human scope decision because it names projects/Datacube AU as well as Zina/Fabian. Preferred choice: remove project claims from the generic greeting and leave project facts to Identity Registry; otherwise gate every named key and test every combination.
5. Legacy provenance (#50): do not infer historical seed origin from updated_at = created_at. Earlier scored reads changed timestamps; leave unverifiable legacy rows NULL/unknown, stamp provenance on new default inserts, and use explicit OWNER attestation if historical classification is required.

### Highest-value next safe step

First obtain the exact-head result for #60 head 93f97fd. If green, consolidate #60's service-secret/runtime-role changes with #62's pre-DDL target, local-seed and contiguous-sequence guards in one dedicated candidate. Then prove fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, schema audit, zero DB leakage, and actual runtime-role privileges on disposable PostgreSQL. Keep it open for independent review. Do not wire #49 into a live producer before P0 and migration integration are cleared.

**Release state: NOT TEST READY.** The latest #60 exact-head run was cancelled during pytest/coverage; no test count or coverage result exists. No candidate proves the integrated migration chain and all release gates. Blocking review threads and OWNER/operator decisions remain. No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, PR merge, or review-thread resolution occurred.

## Historical verification snapshot — 2026-10-31 21:18 WAT (superseded by the current overlay above)

This section supersedes the older live-verification snapshots below. The detailed phase audit still begins with a **2026-09-08** code review and must not be treated as a current inventory. This update re-queried main, all open PR heads, review-thread resolution state, Actions runs, the main workflow YAML, deployment runner, and migration directory.

### Main and CI baseline

- **main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest commit remains 2026-09-08. Checked-in SQL migrations are **001–033**.
- **Main Tests:** [run 34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact main SHA at 2026-09-08 11:12 UTC. This is old CI, not evidence for today's open feature branches.
- **Current main workflow:** `.github/workflows/tests.yml` applies migration files lexically and runs pytest with a 57% coverage floor. It does **not** run the migration-sequence preflight, ORM schema audit, or post-test database-leakage audit that appear on some feature branches.
- **Latest overall Tests run observed:** [41202363597](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202363597), successful on PR #59 exact head `611c9d5528df16f5831fa970032237d4988fa52e`: **797 passed, 1 warning, 76.01% coverage**. Its job applied **001–033 only**. This is documentation-branch CI, not integrated-feature or release proof.

### Open PRs — exact current heads

| PR | Exact head | Latest exact-head Tests evidence | Unresolved / total threads | Current scope / limitation |
|---|---|---|---:|---|
| [#48](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 | View-once observation/return writes PrivateMediaArtifact metadata; no private byte store, retention remains OFF. |
| [#50](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success; 828 passed, 76.52% | 3 / 11 | Identity Registry lifecycle/backfill. Registry-read exceptions now fail closed; two human decisions remain on introduction copy and truthful legacy provenance. |
| [#49](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67% | 1 / 80 | Outbound Message Library foundation only; no live producer, selector, or dashboard, and no send authority. |
| [#55](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) success; 815 passed, 76.01% | 0 / 0 | Adds post-test database-leakage auditing to CI; no review threads is not an approval. |
| [#57](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 | Local fixture-seed safety; coordinate with integration candidate #62. |
| [#59](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `611c9d5528df16f5831fa970032237d4988fa52e` | [41202363597](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202363597) success; 797 passed, 76.01% | 1 / 1 | This documentation refresh; exact-head run applies 001–033 only. The stale-snapshot thread remains open for independent review. |
| [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `552a7ca0ce4104beeb3f38fa749c1e332118d8cb` | [41192776180](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192776180) success; 927 passed, 76.41% | 5 / 5 | Draft P0 contact-consent fence. Its workflow applies 001–033 and 038–040, skipping 034–037; consent-history DB-role boundary and human STOP-policy decision remain blockers. |
| [#61](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 | Contiguous migration-sequence preflight; branch-local run does not prove the integrated feature chain. |
| [#62](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01% | 7 / 7 | Draft integration candidate combining #57 seed safety and #61 migration preflight; its run covered 001–033, schema audit, and leakage audit, not feature migrations 034–040. Keep #57/#61 coordinated with #62. |
| [#63](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08% | 1 / 1 | Conversation-observability audit correction; malformed internet counters now fail closed, but independent review remains open. |

A green branch-local workflow proves only the files and database chain that workflow actually exercised. The above PRs remain open; no merge or independent approval is implied by CI or by replies in review threads.

### Migration order and release proof

- Current feature allocation is contiguous by design: **#48 = 034; #50 = 035; #49 = 036–037; #60 = 038–040**. Main itself still contains only 001–033.
- The former duplicate 034 allocation is now renumbered, but **no current exact candidate has proven one fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksum verification, schema audit, and zero DB leakage together**.
- Historical temporary validation [run 39940318940](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39940318940) covered 001–037 and an installed 033→037 simulation only; it does not cover 038–040 or a complete current release candidate.
- The main deployment runner still reapplies seed SQL files. #57 contains the local-fixture opt-in correction; #62 combines it with sequence preflight and is the review candidate for that overlapping deployment-runner work.

### P0 and architecture decisions — do not patch around these

1. **Consent audit privilege boundary (#60):** migration 038 blocks ordinary UPDATE/DELETE/TRUNCATE, but the table owner can disable triggers or alter the table. Current `.env.example` uses the `postgres` role for both async and sync URLs, and Compose injects the same `.env.production` into both API and migrate. The workflow's superuser tests do not prove a deployed runtime role is restricted. Before calling consent history tamper-resistant, separate a non-owner/non-superuser API role from migration-owner credentials, grant only required runtime privileges, and prove the restrictions on disposable PostgreSQL (including inability to ALTER or disable triggers).
2. **STOP semantics (#60):** the branch treats contact opt-out as terminal; there is no owner override/re-consent command. The intended reservation boundary is that a STOP committed before final dispatch reservation vetoes a send; an already in-flight WAHA attempt cannot reliably be recalled, must never be blindly retried/replayed, and later sends must be denied. Fabian must explicitly accept or revise this product policy.
3. **Introduction copy (#50):** the shared introduction guard checks `zina` and `fabian`, while the text also names “his projects” and “Datacube AU”. Recommended single-authority choice is to remove project claims from the generic greeting and let Identity Registry answer project facts; alternatively every named registry key must be gated and tested.
4. **Legacy provenance (#50):** do not infer historical default provenance from `updated_at = created_at`. Older scored reads already advanced timestamps, while timestamp heuristics can misclassify edited legacy rows. Safest truthful default is to leave unprovable legacy rows unknown/NULL, stamp provenance only on new default inserts, and use explicit owner attestation if historical classification is required.
5. **Deployment candidate (#62):** seven inline threads remain unresolved. Its latest exact-head run proves the runner safeguards against main's 001–033 chain, not the feature-migration integration or production deployment. Keep the candidate draft/open for independent review.

### Highest-value next engineering step

Resolve the **#60 runtime-role/migration-owner boundary** as a reviewed deployment contract, then add disposable-PostgreSQL privilege regressions that run as the actual non-owner API role. Do not weaken the consent fence or treat trigger tests executed as `postgres` as proof. The STOP reservation policy requires explicit owner acceptance before P0 can be declared complete.

**Release state: NOT TEST READY.** No production DB operation, production WAHA reconnection, real WhatsApp send, private-media retention activation, PR merge, or review-thread resolution occurred in this verification run.


---

## Live verification delta — 2026-10-31 (fresh re-query; NOT TEST READY)

This snapshot supersedes the earlier 2026-10-31 overlay below. It was refreshed from the live main branch, all ten open PR heads, review threads, exact-head workflow runs, current workflow YAML, and migration directories. The documentation branch before this refresh was `9dd86ab4548ca5ac6b180d89daa5af942285d1c4`; its exact-head Tests run [41192933035](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192933035) passed (797 passed, 1 warning, 76.01%, migrations 001–033 only). This new documentation commit has no exact-head CI result yet.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08); migrations 001–033 only. `main` is not protected (`protected=false`); repository rulesets are empty.
- **Main CI/workflow:** Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on that main SHA on 2026-09-08. Current `.github/workflows/tests.yml` applies checked-in migrations lexically and runs pytest with a 57% coverage floor; it does not run the sequence preflight, ORM schema audit, or post-test DB-leakage audit present on some feature branches.
- **Latest overall CI:** Tests run [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) passed on PR #50 exact head `0a2b38c0ce72b3c4a8fdd49490be504facb34bac`: **828 passed, 1 warning, 76.52% coverage**. That branch run applied 001–033 and 035 only; it did not validate 034, 036–040, the integrated chain, schema audit, or leakage.
- **Open PR heads and unresolved / total review threads:**
  - #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` — PrivateMediaArtifact observation/return; 0/15. Exact-head Tests [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) succeeded. Metadata only; private byte storage is absent and retention remains OFF.
  - #49 `bcd0033e024b177561b8afd41589afe1897ba4de` — Outbound Message Library foundation; 1/80. Exact-head Tests [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded (896 passed, 1 warning, 76.67%). No live producer, selector, or dashboard integration; it grants no send authority.
  - #50 `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` — Identity Registry lifecycle; 3/11. Exact-head Tests [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) succeeded (828 passed, 76.52%). The P1 registry-read fallback is now logged and fail-closed in both shared reply methods, with three PostgreSQL regressions. Two architectural decisions remain: introduction text names projects/Datacube AU while the guard only checks Zina/Fabian; legacy default backfill must not infer seed provenance from `updated_at = created_at`.
  - #55 `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` — post-test DB leakage audit; 0/0. Exact-head Tests [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) succeeded (815 passed, 76.01%); the Contact-inclusive leakage audit passed.
  - #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` — local fixture-seed safety; 1/1. Exact-head Tests [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) succeeded. Keep coordinated with #62; both touch migration-runner behavior.
  - #59 `9dd86ab4548ca5ac6b180d89daa5af942285d1c4` — this documentation refresh; 1/1 stale-snapshot thread. Previous exact-head Tests [41192933035](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192933035) passed on 001–033 only; the new refresh commit has no result yet.
  - #60 `552a7ca0ce4104beeb3f38fa749c1e332118d8cb` — draft P0 contact-consent final fence; 5/5. Exact-head Tests [41192776180](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192776180) succeeded: **927 passed, 1 warning, 76.41%**. Its workflow applied 001–033 and 038–040, skipping 034–037.
  - #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` — contiguous migration-sequence preflight; 0/0. Exact-head Tests [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded.
  - #62 `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` — draft deployment integration; 7/7. Exact-head Tests [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) succeeded: **864 passed, 1 warning, 76.01%**; sequence preflight, 001–033, schema audit, and Contact-inclusive leakage audit passed. API and migrate still receive the same `.env.production`; restricted runtime/migration roles are not implemented.
  - #63 `13fad868affe01d6069f4288481f8cd8dd341c62` — conversation observability; 1/1. Exact-head Tests [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded (803 passed, 1 warning, 76.08%); independent review remains open.
- **Migration allocation:** the former duplicate 034 is resolved across current branches: #48=034, #50=035, #49=036–037, #60=038–040. The exact filenames were rechecked. No candidate proves one fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, and combined-candidate leakage.
- **P0 consent:** main still lacks the contact-specific final consent fence. #60 is green at its exact head, but its five review threads remain unresolved. Migration 038's append-only triggers are bypassable by the table owner; Compose still supplies the same `.env.production` to API and migrate, and `.env.example` uses the same `postgres` role for both DB URLs. A restricted runtime role plus separate migration-owner credentials and disposable-PostgreSQL privilege proof are still required. The OWNER must explicitly accept/revise the STOP reservation boundary: a STOP committed before final reservation vetoes; a WAHA attempt already in flight cannot reliably be recalled and must never be retried/replayed.
- **Deployment integration:** #62 remains draft with seven unresolved threads. Do not merge #57 or #61 independently while #62 is the integration candidate.
- **Release:** **NOT TEST READY.** No integrated 001–040/033→040 migration proof, no exact-candidate combined leakage result, unresolved blocking reviews and owner decisions, and no controlled-test authorization. No production DB mutation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred.

## Live verification delta — 2026-10-31 (partial; NOT TEST READY)

This overlay supersedes the 2026-10-30 snapshot immediately below it. The main branch, all ten open PR heads, review-thread resolution flags, current workflow YAML, exact-head Actions runs, and feature-migration filenames were re-queried. The newest consent-parser commit is included below; its exact-head workflow is still running.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08. Main still contains migrations 001–033 only. The branch endpoint reports `protected=false`; the repository rulesets endpoint returned an empty list.
- **Main CI:** latest main-branch Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on the same main SHA on 2026-09-08. The current `.github/workflows/tests.yml` applies the checked-in migrations lexically and runs pytest with a 57% coverage floor; it has no migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit.
- **Latest overall CI:** Tests run [41192776180](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192776180) is **in progress** on PR #60 exact head `552a7ca0ce4104beeb3f38fa749c1e332118d8cb`. Do not claim a test count or coverage result yet. The latest completed run is [41168835614](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41168835614), success on PR #59 exact head `7df2055d5e1f28d32fa7c4b1c16b012289a639d9`: 797 passed, 1 warning, 76.01% coverage, migrations 001–033 only.
- **Current open PR heads and review threads (unresolved / total):**
  - #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` — PrivateMediaArtifact observation/return; 0/15. Exact-head Tests [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) succeeded. Metadata/observation only; private byte storage is absent and retention remains OFF.
  - #49 `bcd0033e024b177561b8afd41589afe1897ba4de` — Outbound Message Library foundation; 1/80. Exact-head Tests [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded (896 passed, 76.67%). No live producer, selector, or dashboard integration; it does not grant send authority.
  - #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1` — Identity Registry lifecycle; 3/11. Exact-head Tests [40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) succeeded. Three unresolved decisions remain: introduction text names projects/Datacube AU while only gating Zina/Fabian; legacy default provenance cannot safely use `updated_at = created_at`; and registry-read failures must not fall through to hardcoded identity.
  - #55 `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` — PostgreSQL post-test leakage audit; 0/0. Exact-head Tests [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) succeeded (815 passed, 76.01%) on 001–033.
  - #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` — local fixture-seed safety; 1/1. Exact-head Tests [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) succeeded. Keep coordinated with #62; both change the migration runner.
  - #59 `7df2055d5e1f28d32fa7c4b1c16b012289a639d9` — this documentation refresh; 1/1 stale-snapshot thread. Exact-head Tests [41168835614](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41168835614) succeeded (797 passed, 76.01%) on 001–033 only.
  - #60 `552a7ca0ce4104beeb3f38fa749c1e332118d8cb` — draft P0 contact-consent final fence; 5/5. Latest exact-head Tests [41192776180](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41192776180) is in progress. The previous head `9071c09d` passed [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) (915 passed, 76.43%), but that result is not evidence for the new head.
  - #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` — contiguous migration-sequence preflight; 0/0. Exact-head Tests [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded.
  - #62 `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` — draft integration of #55/#57/#61 deployment and CI guards; 7/7. Exact-head Tests [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) succeeded (864 passed, 76.01%) with sequence preflight, 001–033, schema audit, and leakage audit. It still passes the same `.env.production` to API and migrate.
  - #63 `13fad868affe01d6069f4288481f8cd8dd341c62` — conversation observability; 1/1. Exact-head Tests [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded (803 passed, 76.08%); the unresolved malformed-counter thread remains open for independent review.
- **Migration allocation:** the former 034 collision is reconciled in current branch trees: #48=034, #50=035, #49=036–037, #60=038–040. The exact filenames were checked on each branch. No candidate has proved a single fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksums, and combined-candidate DB-leakage audit.
- **P0 contact consent:** main does not contain the final contact-consent fence. PR #60 now includes a parser correction: the remaining opt-out phrase regexes are anchored to the start of the normalized message, preventing quoted/reported third-party wording from becoming a terminal sender opt-out; negative and positive regressions were added. The exact-head workflow is still in progress. Five review threads remain unresolved.
- **P0 policy and database boundary:** the owner must explicitly accept or revise the linearization policy: a STOP committed before the final reservation blocks the send; one attempt already inside WAHA may complete because transport cancellation is not reliable; no later retry/replay is allowed. Separately, migration 038's append-only triggers are bypassable by the table owner. `.env.example` still uses the same `postgres` role for both URLs, and Compose gives the same `.env.production` to API and migrate. A restricted runtime role and migration-owner/runtime-role separation with disposable-PostgreSQL privilege proof are not implemented.
- **Deployment/migration integration:** #62 still has seven unresolved threads. Do not merge #57 or #61 independently while #62 is the integration candidate.
- **Release status:** **NOT TEST READY.** No integrated 001–040/033→040 migration proof, no exact-candidate combined leakage result, unresolved blocking reviews and owner decisions, and no controlled-test authorization. No production DB mutation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred.

## Live verification delta — 2026-10-30 after exact-head run 41080836429 (partial; NOT TEST READY)

This is the newest repository-state snapshot. It supersedes earlier 2026-10-30 snapshots below; all ten open PR heads and review-thread resolution flags were re-queried.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, unchanged since 2026-09-08. Main has migrations 001–033 only; `main` reports `protected=false` and the repository rulesets endpoint returns an empty list. The classic protection endpoint is not accessible through this integration.
- **Main workflow/deployment:** `.github/workflows/tests.yml` remains blob `445b1fd6`: PostgreSQL 16, lexical migration application, pytest with a 57% coverage floor. It has no migration-sequence preflight, ORM schema audit, or post-test DB-leakage audit. Main's `.env.example` gives `DATABASE_URL` and `DATABASE_URL_SYNC` the same `postgres` role, and `docker-compose.yml` supplies the same `.env.production` to both API and migrate services.
- **Latest observed Tests run:** [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded on PR #63 exact head `13fad868affe01d6069f4288481f8cd8dd341c62`: **803 passed, 1 warning, 76.08% coverage**. The workflow applied migrations **001–033**. It did not run the #55 DB-leakage audit and does not validate feature migrations 034–040 or an installed upgrade.
- **PR #63 observability:** commit [13fad868](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/13fad868affe01d6069f4288481f8cd8dd341c62) makes malformed internet audit values fail closed: only positive finite numeric hit counts and real boolean `internet_used` values are accepted. Exact-head CI is green; one inline review thread remains unresolved for independent review.
- **Current open PR heads (all target main):**
  - #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` — view-once/private-media metadata observation; review threads 0 unresolved / 15 total.
  - #49 `bcd0033e024b177561b8afd41589afe1897ba4de` — Outbound Message Library foundation only; 1 / 80 unresolved, including retired set-key lifecycle. No live producer, selector, or dashboard integration.
  - #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1` — Identity Registry lifecycle; 3 / 11 unresolved: (1) product scope for the shared introduction text, which checks `zina` and `fabian` but still names `projects` and `datacube_au`; (2) a reliable legacy-default provenance/backfill rule for rows whose timestamps may have been touched by pre-upgrade reads; and (3) a new P1 finding: both `identity_reply()` and `introduction_reply()` catch registry read failures and fall through to hardcoded `bot_config` identity, potentially resurrecting disabled/tombstoned facts after migration 033 is active.
  - #55 `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` — post-test DB-leakage audit; 0 / 0 review threads; exact-head run [41026581000](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) passed on 001–033.
  - #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` — local seed safety; 1 / 1 unresolved allowlist concern; keep coordinated with #62 because both change the migration runner.
  - #59 (this documentation refresh) — 1 / 1 stale-snapshot thread remains unresolved; no exact-head Tests result is included in this snapshot.
  - #60 `9071c09d8d55255bdb99eb6fa138ef08c911d5d0` — P0 contact-consent final fence; draft; 5 / 5 unresolved. Exact-head run [41019860297](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41019860297) passed **915 tests, 1 warning, 76.43%**, but applied 001–033 plus 038–040 and skipped 034–037.
  - #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` — contiguous migration-sequence preflight; 0 / 0 review threads; exact-head run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded.
  - #62 `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` — draft integration of #55/#57/#61 deployment and CI guards; 7 / 7 unresolved. Exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed **864 tests, 1 warning, 76.01%** with sequence preflight, migrations 001–033, ORM schema audit, and post-test leakage audit. It still passes the same `.env.production` to API and migrate.
  - #63 `13fad868affe01d6069f4288481f8cd8dd341c62` — observability audit; 1 / 1 unresolved for independent review; exact-head run [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) passed as above.
- **Migration order:** the former duplicate 034 allocation is reconciled in current branch trees: #48=034, #50=035, #49=036–037, #60=038–040. No exact candidate has yet proved a single fresh 001–040 chain, installed 033→040 upgrade, second-run no-op/checksum behavior, and combined-candidate DB-leakage audit.
- **P0 risk:** main does not yet contain PR #60's explicit contact-consent check at the final outbound worker fence. PR #60 fails closed for unknown/expired/revoked/opted-out external contacts, but remains draft/unmerged and has five unresolved threads. The consent-event triggers are not tamper-resistant while API and migrate share the table-owner role; a runtime owner can disable triggers. A restricted runtime role separate from migration/table owner is not implemented.
- **Human decisions still required:** (1) approve a distinct migration-owner/runtime-role deployment contract and bootstrap/credential rollout; (2) explicitly accept the STOP dispatch-reservation boundary (a STOP after the final reservation cannot retract that one in-flight attempt but must block later sends/replays); (3) decide whether to remove project/Datacube claims from the shared introduction or also require the `projects` and `datacube_au` registry facts to be available; (4) choose a trustworthy legacy-default provenance policy; and (5) define fail-closed behavior when the Identity Registry cannot be read after migration 033 is active, so transient failures cannot revive legacy identity fallbacks.
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