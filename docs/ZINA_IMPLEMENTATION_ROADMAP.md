# Current verification overlay — 2026-11-06 12:35 WAT

This snapshot supersedes repository, PR, review, CI, migration, and deployment status below. The historical per-domain product tables still reflect the 2026-09-08 audit and are not current code evidence. This is not release certification.

## Main, workflow, and access

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08 11:09:59 UTC. The latest push-to-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on that exact SHA on 2026-09-08.
- Main contains migrations **001–033**. Main `.github/workflows/tests.yml` applies SQL files lexically, runs pytest with a 57% coverage floor, and does not include the contiguous-migration preflight, ORM schema audit, or post-test database-leakage audit now present on open PR branches.
- The repository rulesets endpoint returned an empty list. The branch-protection endpoint returned 403 `Resource not accessible by integration`; branch-protection state therefore could not be independently confirmed in this verification.
- Latest overall Tests run: [42210751706](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42210751706), successful on PR #62 exact head `6bf7619656543829641b806b4b5488cdf8ace56e`: **866 passed, 1 warning, 76.01% coverage**. Its migration preflight, migrations 001–033, ORM schema audit, and post-test leakage audit all passed. It does not exercise feature migrations 034–040.

## All ten open PRs

Thread counts are unresolved / total; outdated threads remain included. All review submissions currently show COMMENTED; **no open PR has an APPROVED review**.

| PR | Exact head | Latest known exact-head Tests | Unresolved / total threads |
|---|---|---|---:|
| #63 observability audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 / 76.08% | 1 / 1 |
| #62 migration/seed integration | `6bf7619656543829641b806b4b5488cdf8ace56e` | [42210751706](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42210751706) success; 866 / 76.01% | 9 / 9 |
| #61 contiguous migration gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success; 809 / 76.01% | 0 / 0 |
| #60 contact-consent P0 | `afbafbfaa4789fd5f209ad63ff4a2cc71ea5ddc2` | [42184294902](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42184294902) success; 961 / 76.56% | 20 / 21 |
| #59 verification docs | `febd4844fb9889ebaa65d368cfff0f6d98171291` (before this refresh) | docs-only `[skip ci]`; no exact-head run | 4 / 4 |
| #57 local seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success; 811 / 76.01% | 1 / 1 |
| #55 DB leakage audit | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success | 1 / 1 |
| #50 Identity Registry lifecycle | `2dc4225465c41a0aa47b2a762b7d37bf8e34764a` | [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success; 855 / 76.53% | 5 / 13 |
| #49 outbound message library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 / 76.67% | 1 / 80 |
| #48 private-media observation wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 |

Every green result above is branch-local. It is not independent approval or proof of the integrated migration/deployment chain.

Review-thread requery — 2026-11-06 12:45 WAT: GitHub now reports PR #48 with 0 unresolved of 15 threads and PR #49 with 1 unresolved of 80. All PR #48 threads are resolved, but its review submissions remain COMMENTED, not APPROVED; PR #49's remaining P2 retired-set-key thread is unresolved. This changes review-thread counts only; it does not authorize merge or change the integrated migration/deployment gates.


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

## Fresh engineering verification — 2026-11-06

This snapshot supersedes the previous 2026-11-06 04:20 WAT overlay for repository/PR/CI state only. The historical per-domain product tables below still carry their older 2026-09-08 audit date and are not current implementation evidence. This is not release certification.

### Main, workflow and current CI

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC). Latest push-to-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on that exact SHA at 2026-09-08 11:10 UTC. No newer main push run is visible.
- Main contains migrations **001–033**. Main `.github/workflows/tests.yml` applies the checked-in SQL files lexically and runs pytest with a 57% coverage floor; it does not yet enforce contiguous numbering, run the ORM schema audit, or run the post-test DB-leakage audit.
- Branch allocation is now unique: **034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60)**. The duplicate-034 allocation has been reconciled in the branch trees. No candidate yet proves the complete fresh 001–040 chain or installed 033→040 upgrade.
- Exact #60 head [afbafbf](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/afbafbfaa4789fd5f209ad63ff4a2cc71ea5ddc2) passed [Tests run 42184294902](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42184294902): **961 passed, 1 warning, 76.56% coverage**. Its disposable workflow DB applied 001–033 + 038–040 only; it did not run the integrated sequence, schema or leakage gates.

### All ten open PRs — exact heads, exact-head Tests, review threads

Thread counts are unresolved / total, with active and outdated unresolved counts shown separately. Every submitted review state is COMMENTED; **no open PR has an APPROVED review**.

| PR | Exact head | Latest exact-head Tests | Threads unresolved / total (active / outdated) |
|---|---|---|---:|
| #63 observability | `13fad868` | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success | 1 / 1 (0 / 1) |
| #62 deployment seed guards | `a8d032de` | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success | 8 / 8 (5 / 3) |
| #61 migration sequence gate | `8a1c1dbf` | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success | 0 / 0 (0 / 0) |
| #60 contact consent P0 | `afbafbf` | [42184294902](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42184294902) success; 961 / 76.56% | 20 / 21 (9 / 11) |
| #59 verification docs | `e9821606` | no run on this docs-only head | 4 / 4 (1 / 3) |
| #57 seed safety | `d831ce4e` | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success | 1 / 1 (0 / 1) |
| #55 DB leakage audit | `b5cb5ff4` | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success | 1 / 1 (0 / 1) |
| #50 Identity Registry | `2dc42254` | [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success; 855 / 76.53% | 5 / 13 (4 / 1) |
| #49 outbound message library | `bcd0033e` | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 / 76.67% | 1 / 80 (1 / 0) |
| #48 private media metadata | `3acacbfe` | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success | 0 / 15 (0 / 0) |

All successful runs above are branch-local. None proves the integrated migration/deployment contract or substitutes for independent approval.

### Current P0 and architecture state

- #60 now preserves and rechecks the original authority type and exact contact-policy ID after final consent, STOP, safety and delivery-window waits; policy expiry/replacement regressions assert zero mocked WAHA calls. Exact one-use OWNER approvals are reserved/consumed before WAHA, and uncertain outcomes remain quarantined. The latest 961-test run is green, but the PR still has **9 active unresolved inline threads**.
- **OWNER decision required:** a STOP committed after the final dispatch reservation cannot recall the one request already entering transport; it blocks subsequent sends. Fabian must accept that linearization contract or require a stronger atomic reservation protocol.
- **OWNER decision required:** terminal opt-out is currently Contact-wide across mapped aliases with no routine re-consent/override. Also decide whether `.contact consent grant`'s OWNER attestation plus opaque `evidence_ref` is adequate evidence of external contact consent, or whether contact consent and OWNER automation permission are separate authorities.
- #60 and #62 deployment changes must be integrated, not merged in an order that restores broad `.env.production` credentials to API/WAHA or drops DB-target/seed/sequence preflights. Keep #55's schema-qualified leakage audit, #57 seed-safety behavior and #61's contiguous migration gate in the same candidate.
- #50 still needs a human decision to keep generic introduction text limited to assistant/OWNER identity or gate every project fact it names. Its `updated_at = created_at` legacy backfill heuristic is not reliable historical provenance; ambiguous legacy rows should remain unknown unless Fabian approves an attestation/evidence strategy.
- #49 remains a foundation only: no live producer selection or dashboard integration before P0 and migration reconciliation. #48 metadata observation does not authorize private-byte retention; retention remains OFF.

### Next safe engineering step

Keep #60 open for independent review and the STOP/consent policy decisions. Then build one disposable integration candidate containing migrations 034–040 plus the #60/#62/#55/#57/#61 deployment and audit gates; prove fresh 001–040, installed 033→040 upgrade, second-run checksum/no-op, schema audit, zero DB leakage and restricted runtime-role privileges before any merge decision. **Controlled-test readiness: NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

## Fresh exact-state verification — 2026-11-06 04:20 WAT (03:20 UTC)

This is a fresh GitHub source, PR/review-thread, workflow, migration-inventory, and Actions snapshot. It is not release certification. The older per-domain product tables below still carry their 2026-09-08 audit date and must not be treated as current code status.

### Main, CI, and deployment

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last committed 2026-09-08 11:09:59 UTC. The latest push-to-main Tests run is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), success, 2026-09-08 11:10:02 UTC. No newer push-to-main run is visible.
- The branch-protection endpoint returned 403 `Resource not accessible by integration` in this run. A prior snapshot reported `protected=false`; that historical claim could not be independently re-verified here.
- Main contains migrations **001–033** only. Current feature-branch allocation is unique: **034 (#48), 035 (#50), 036–037 (#49), 038–040 (#60)**. The old duplicate-034 allocation has been reconciled in branch trees, but no reviewed candidate contains and proves the complete 001–040 chain.
- Main `.github/workflows/tests.yml` applies whatever `bot_core/migrations/*.sql` files are present in lexical order, then runs pytest with a 57% coverage floor. It does not itself enforce contiguous numbering, run the ORM schema audit, or run the post-test DB-leakage audit. The sequence gate is still a PR, not main.
- Main `deploy/scripts/run-migrations.sh` does not run the database-target/seed/migration-sequence preflights or sanitize inherited libpq target/session overrides. Main Compose mounts `.env.production` into postgres, API, WAHA, and migrate; it does not separate the migration-owner DB credential from a restricted API runtime role.
- #60 contains the restricted runtime-role provisioner and service-specific environment allowlists, but lacks #62's target/seed/sequence preflights. #62 contains those preflights but still has broad `.env.production` injection. They must be reconciled into one deployment candidate, not merged in an order that can reintroduce the other's security gap.

### All ten open PRs — exact heads, review threads, and Tests

Thread counts are **unresolved / total**; active and outdated unresolved counts are shown separately. All submitted review states are currently `COMMENTED`; **no open PR has an APPROVED review**.

| PR | Exact head | Threads (unresolved / total; active / outdated) | Latest exact-head Tests |
|---|---|---:|---|
| #48 PrivateMediaArtifact observation | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15; 0 / 0 | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success; 856 passed, 76.26%; 001–034 |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80; 1 / 0 | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67%; 001–033 + 036–037 |
| #50 Identity Registry follow-up | `2dc4225465c41a0aa47b2a762b7d37bf8e34764a` | 5 / 13; 4 / 1 | [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success; 855 passed, 76.53%; 001–033 + 035 |
| #55 DB-leakage CI gate | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1; 0 / 1 | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success; 816 passed, 76.01%; 001–033 + schema/leakage audit |
| #57 deployment seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1; 0 / 1 | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success; 001–033 |
| #59 verification docs | `936195612b1b33eee84d9ea84b84566ea2a7c6ff` | 4 / 4; 1 / 3 | No run on this exact docs-only head; commits use `[skip ci]` |
| #60 contact-consent P0 | `f24c8318aa79e0c7519b91a52d0461a2bfed9730` | 20 / 21; 11 / 9 | [42096178533](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42096178533) success; 958 passed, 76.55%; 001–033 + 038–040 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0; 0 / 0 | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success; 001–033 |
| #62 deployment preflight integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 8 / 8; 5 / 3 | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success; 864 passed, 76.01%; preflight + 001–033 + schema/leakage audit |
| #63 router/conversation audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1; 0 / 1 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success; 803 passed, 76.08%; 001–033 |

The latest visible overall Tests run is #60 run **42096178533**, successful on its exact head. This is branch-local evidence only: its migration step covers 001–033 plus 038–040, not 034–037 or the integrated 001–040 chain.

### Current P0, architecture, and integration blockers

1. **#60 — contact-policy authority expiry remains P0.** Exact one-use OWNER approval consumption now occurs before WAHA, after the final consent/safety/STOP/delivery-window fences, with a database-side `clock_timestamp()` predicate and exact queue/inbound/recipient/content binding. An uncertain WAHA outcome leaves the approval consumed and queue quarantined. However, the worker discards the original `authority_type` and `policy_id` returned by `AuthorizationDecision`. A later quiet-hours lookup filters expired/disabled policies out and treats no row as “no quiet-hours restriction.” Preserve the original policy ID/contact/chat/category binding and, after all final locks, re-read that same row; require enabled, not disabled, exact identity, category still allowed, and `expires_at IS NULL OR expires_at > clock_timestamp()`. Missing, disabled, expired, or no-longer-authorizing policy must deny before WAHA.
2. **#60 — policy lock-order inversion remains P1.** `authorize()` locks a policy row before the worker obtains the exact-chat advisory lock in the later delivery-window check; OWNER policy upsert/disable takes advisory lock → policy row. This is a row→advisory versus advisory→row cycle. Acquire the shared exact-chat lock before the first policy-row lock and add two-session regressions for both lock winners.
3. **#60 — STOP linearization needs OWNER acceptance.** A STOP committed before the durable final dispatch reservation blocks the send. A STOP arriving after that reservation cannot reliably retract a network attempt already entering/in flight; it must veto subsequent attempts. Repeated pre-send reads cannot remove this boundary. This is an explicit product decision, not a code-only patch.
4. **Deployment integration remains blocked.** #60's runtime-role/service allowlists must be combined with #62's target validation, local-seed allowlist, libpq environment fence, public search-path pin, and contiguous migration preflight. #62's leakage audit still checks existence in `public` but counts an unqualified quoted table; a `search_path=shadow,public` can count the shadow table and miss the public row. Port #55's `SELECT COUNT(*) FROM public."<table>"` implementation and shadow-schema regression into the integrated candidate.
5. **#50 — two identity policy decisions remain open.** Recommended introduction contract: keep the shared greeting to the Zina/OWNER relationship and do not repeat project/Datacube claims; project facts belong to their individually governed registry keys. Recommended provenance contract: leave pre-033 rows with unknown source/entity type unclassified unless immutable evidence or explicit OWNER attestation exists; do not infer origin from `updated_at = created_at`.
6. **#49 remains foundation-only.** The message library is not integrated into live producer/selection/dashboard flows. Do not connect it to delivery until P0 authority, migration, and review gates are satisfied.
7. **#48 view-once wiring is source-reviewed with all 15 inline threads resolved, but the PR remains open.** Preserve its exact source-row lock, source/chat/command binding, deletion fence, success-only return audit, and uncertain-send no-retry behavior when composing the worker with #60. Private-media retention remains OFF.
8. **#55/#57/#61/#63 contain useful isolated hardening**, but their branch-local green runs are not integrated release proof and their remaining outdated review threads still require independent review.

### Readiness

- **NOT TEST READY.** No open PR has an APPROVED review; no PR has been merged in this run.
- Missing combined proof: fresh 001–040 chain; installed 033→040 upgrade with representative rows; second-run checksum/no-op; integrated target/seed/sequence preflight; schema audit; zero DB leakage using schema-qualified raw-table counts; restricted runtime-role ownership/privilege proof; and resolution of blocking P0 reviews/product decisions.
- Controlled testing remains gated. Once the engineering/review gates pass, use the staged order: OWNER self-DM text → OWNER commands → media/view-once → one explicitly approved external contact. No live WhatsApp test was performed here.
- **REAL WAHA ACTIONS: NONE.**

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

## Fresh verification delta — 2026-11-05 19:44 UTC

This snapshot supersedes earlier overlays for the current GitHub state. It is a source/review/CI inspection plus documentation refresh only; it does not certify release readiness.

### Main and CI baseline

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (latest commit 2026-09-08 11:09:59 UTC). The live branch endpoint reports `protected=false`.
- Main contains migrations 001–033 only. Exact-main Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08.
- Main `.github/workflows/tests.yml` triggers on pull requests and pushes to main/master, provisions PostgreSQL 16, applies available `bot_core/migrations/*.sql` in lexical order, and runs pytest with a 57% coverage floor. Main does not yet enforce migration continuity, ORM schema audit, or post-test DB-leakage audit.

### All open PRs — exact heads and latest Tests association

Review counts below are unresolved / total GitHub review threads; unresolved totals include outdated threads. CI references are exact-head associations, not integrated migration evidence.

| PR | Exact head | Unresolved / total | Latest exact-head Tests |
|---|---|---:|---|
| #48 PrivateMediaArtifact observation | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 / 15 | [40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 / 80 | [39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success |
| #50 Identity Registry follow-up | `2dc4225465c41a0aa47b2a762b7d37bf8e34764a` | 5 / 13 | [42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) success |
| #55 DB-leakage CI gate | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 / 1 | [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) success |
| #57 deployment seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 / 1 | [40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success |
| #59 verification docs (before this commit) | `7288927d68c60413af577c2c7ce812b955273f75` | 4 / 4 | [42085916713](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085916713) success |
| #60 contact-consent P0 | `f24c8318aa79e0c7519b91a52d0461a2bfed9730` | 20 / 20 (11 active) | [42096178533](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42096178533) success — 958 passed, 1 warning, 76.55% |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 / 0 | [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success |
| #62 deployment preflight integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 8 / 8 | [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) success |
| #63 router/conversation audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 / 1 | [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) success |

No open PR has an independent APPROVED review submission. PR #60 remains draft/open. The latest overall Tests run is #60 run 42096178533 on its exact head.

### P0 contact-consent status — PR #60

The current #60 source has made meaningful progress since the older snapshots:

- Exact one-use OWNER approval is now conditionally consumed **before** the single WAHA attempt, after the final consent/safety/STOP/window fences. The update binds approval ID, queue ID, inbound ID, recipient, content digest, approved state, and `expires_at > clock_timestamp()`.
- An uncertain transport outcome is durably marked; both the worker authorization boundary and OWNER `requeue()` reject replay of that row. The approval remains consumed on uncertainty.
- Contact consent is refreshed after the later safety and pending-STOP locks. The exact queued ScheduledAction is locked through the one attempt and durable outcome.

Exact-head Tests run 42096178533 passed 958 tests at 76.55% coverage. Its disposable migration set is 001–033 plus 038–040 only; it does not prove 034–040 integrated, an installed 033→040 upgrade, schema audit, or DB-leakage audit.

Two source-grounded blockers remain on the exact current head:

1. **P0 — contact-policy expiry is still treated as permission.** `authorize()` can return contact-policy authority, but the final `check_contact_delivery_window()` query filters expired/disabled policies out and returns `allowed=True` when no active row exists. Preserve the original authority type and policy ID, then re-lock/revalidate that same policy's exact contact/chat, enabled state, category rules, and expiry using `clock_timestamp()` after all final waits. A missing/disabled/expired policy that supplied authority must deny before WAHA. This exact-head finding was added to the existing #60 review thread.
2. **P1 — policy lock order can deadlock.** Worker authorization locks the policy row before it acquires the exact-chat advisory lock in the later delivery-window check. OWNER policy upsert/disable takes advisory lock before the policy row. Make the shared order advisory-lock → policy-row-lock by acquiring the mapping lock before the first policy `FOR UPDATE` in `authorize()`; add a two-session regression for both lock winners. An inline review comment was added on #60.

STOP linearization still needs OWNER acceptance: the committed pending-STOP check is the durable dispatch reservation point. A STOP committed before that point blocks; a STOP arriving after the reservation may be too late to cancel the one network attempt already entering transport. Define this contract explicitly; another pre-send read cannot make an in-flight network request cancellable.

### Migration and deployment integration

Migration numbers are now unique across the feature branches: #48=034, #50=035, #49=036–037, #60=038–040. The historical duplicate 034 is reconciled, but no branch contains the integrated 001–040 chain.

- #61 supplies a migration-continuity preflight but its branch-local test applies only 001–033.
- #62 supplies database-target, seed-policy, libpq, and sequence preflights before DDL, plus schema/leakage checks. Its current Compose still mounts broad `.env.production` into API/WAHA/migrate.
- #60 supplies a restricted non-owner API runtime role and service-specific environment allowlists, but its runner does not yet include #62's complete target/seed/libpq/sequence preflights.

Do not merge #60 or #62 independently or choose an arbitrary merge order. One integrated candidate must retain all #61/#62 preflights before the first DDL, owner credentials only in migrate, runtime-only DB credentials in API, WAHA-only environment, and post-migration role provisioning. Prove fresh 001–040, installed 033→040 upgrade, second-run no-op/checksums, schema audit, zero DB leakage, runtime-role privilege/sequence tests, and rendered Compose environment isolation on disposable PostgreSQL.

### Other roadmap decisions and readiness

- #50 still needs a human provenance decision: pre-033 legacy rows whose timestamps were advanced by old reads cannot be reliably classified using `updated_at = created_at`. Leave unverifiable rows NULL/legacy-unknown, or require explicit OWNER-attested provenance; do not add another timestamp heuristic.
- #48's exact-source view-once worker fence is present on its branch; its remaining release blocker is migration integration/independent review. Private-media retention remains OFF.
- #49 remains a content-library foundation only; no live producer selection, contact targeting, or dashboard integration before P0 and migration reconciliation.

**NOT TEST READY.** No integrated 001–040 fresh/upgrade/no-op run, no full schema/leakage/runtime-role proof on one candidate, no completed independent review, and unresolved P0 policy/STOP decisions remain. No production DB access/mutation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred. **REAL WAHA ACTIONS: NONE.**

---

## Fresh verification delta — 2026-11-05 18:33 UTC

This delta supersedes the older PR #50 and CI snapshots below. Main, all ten open PR heads/review threads, the main workflow, migration inventory, and deployment files were rechecked. It does not certify release readiness.

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (2026-09-08 11:09:59 UTC), with migrations 001–033 only. Main's latest exact-head Tests run is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. Main's `.github/workflows/tests.yml` still applies available SQL files lexically and runs pytest with a 57% coverage floor; it has no contiguous-migration preflight, ORM schema audit, or post-test DB-leakage audit. The live branch endpoint reports `protected=false`.
- PR #50 is now at `2dc4225465c41a0aa47b2a762b7d37bf8e34764a`. Its Identity Registry changes keep active project facts available in owner-neutral wording when the `fabian` identity is disabled/tombstoned, while explicit OWNER/ownership queries fail closed. The shared BotConfig project fallback also suppresses OWNER-attributed claims.
- Exact-head [Tests run 42085040529](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42085040529) succeeded on that exact #50 SHA: **855 passed, 1 warning, 76.53% coverage** (57% gate). The disposable database applied 001–033 plus 035 only. It did not validate integrated 001–040, installed 033→040 upgrade, second-run checksum/no-op behavior, ORM schema audit, or DB-leakage audit. Two intermediate heads failed against stale expectations during this change; the current exact head is green.
- #50 still has **5 unresolved / 13 total** review threads, including the migration-035 historical-provenance decision. The migration still uses `updated_at = created_at`; this cannot recover pre-upgrade defaults whose timestamp was already advanced by old read paths, and it cannot safely distinguish every historical administrator edit. Do not add more timestamp heuristics. Human choice: leave unverifiable legacy rows unclassified (`legacy_unknown`/NULL provenance) or require an explicit OWNER-attested backfill.
- Current open PR heads: #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`; #49 `bcd0033e024b177561b8afd41589afe1897ba4de`; #50 `2dc4225465c41a0aa47b2a762b7d37bf8e34764a`; #55 `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c`; #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba`; #59 `143bec38ab826df3e2b694cc568e7c8326d81491` before this documentation commit; #60 `4b36f8af3389a9270aefde4654f1e7b0a9270b3c`; #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`; #62 `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`; #63 `13fad868affe01d6069f4288481f8cd8dd341c62`.
- Unresolved review threads / total: #48 0/15; #49 1/80; #50 5/13; #55 1/1; #57 1/1; #59 4/4; #60 19/19; #61 0/0; #62 8/8; #63 1/1. Counts include outdated threads; this update resolved none.
- Migration allocation is unique across branches: #48=034, #50=035, #49=036–037, #60=038–040. The historical 034 collision is reconciled by renumbering #49, but no branch contains the full 001–040 chain. #61 adds a continuity gate; its green branch-local run covers only 001–033.
- PR #60's latest exact-head Tests run [42019032673](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42019032673) succeeded: **956 passed, 1 warning, 76.57% coverage**. The uncertain-delivery replay marker and OWNER requeue denial are present. Remaining P0 blockers are the approval-expiry window before transport and the contact-policy-expiry race after later fence waits. STOP linearization remains a human policy decision.
- PR #60 and #62 remain an incompatible deployment pair. #60 has the restricted non-owner API DB role and service-specific environment allowlists but lacks #62's DB-target/seed/libpq/sequence preflights. #62 has those preflights and schema/leakage checks, but its Compose still mounts broad `.env.production` into API/WAHA/migrate and does not provision/use #60's restricted runtime role. Do not merge either independently or in arbitrary order. The integrated candidate must preserve preflight-before-DDL, owner credentials only in migrate, runtime-only DB credentials in API, WAHA-only environment, and post-migration runtime-role provisioning.
- PR #48's exact-source view-once return fence is present; its remaining gates are ordered migration integration and independent review. Private-media retention remains OFF. PR #49 is still only the Outbound Message Library foundation; no live selection/producer/dashboard integration before P0 and migration reconciliation.
- **NOT TEST READY.** No integrated migration/deployment candidate, complete P0 adversarial proof, independent review completion, mobile CRUD/observability completion, or staged controlled-test evidence exists. Human decisions: (1) STOP after durable dispatch reservation cannot reliably cancel the already-entering single request; decide the exact linearization contract; (2) choose truthful legacy identity provenance rather than another timestamp heuristic. No production DB operation, production WAHA reconnection, real WhatsApp send, or retention activation occurred.

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
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 3 / 11 total | [41202063757](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) success |
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

## Fresh P0 safety verification — 2026-11-04 22:15 WAT

This supersedes the 18:24 UTC verification overlay below. It records a newly confirmed replay path on the unchanged exact PR #60 head; it is not a code fix, approval, or release authorization.

### Exact state rechecked

- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; main still contains migrations 001–033 only. The main Tests workflow still applies the lexical migration glob and enforces the 57% coverage floor; the sequence preflight (#61) and schema/DB-leakage audit (#55) are not on main.
- PR #60 remains at exact head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`. Exact-head Tests run [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978) succeeded on 2026-11-04: **955 passed, 1 warning, 76.53% coverage**. Its disposable database applied 001–033 and 038–040 only. It did not apply 034–037, validate integrated 001–040, prove installed 033→040 upgrade/second-run checksum no-op, or run the integrated schema and DB-leakage gates.
- All ten open PR heads and review threads were re-queried. Unresolved threads (active / outdated): #48 0 (0/0), #49 1 (1/0), #50 3 (3/0), #55 1 (0/1), #57 1 (0/1), #59 3 (1/2), #60 19 (10/9), #61 0, #62 7 (4/3), #63 1 (0/1). No open PR has an APPROVED review submission.
- Branch-local migration allocation remains sequential: #48=034, #50=035, #49=036–037, #60=038–040. The historical 034 collision is resolved by allocation only; main and the integrated 001–040 chain are not validated.
- #60's restricted API runtime role/service-specific environment boundary and #62's migration-target/seed/libpq/sequence preflights remain separate, conflicting deployment candidates. They require one cumulative candidate; do not merge either independently.

### Newly confirmed P0 — OWNER requeue can replay an uncertain send

On exact #60 head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`, the worker consumes an exact approval only in the WAHA-success branch. An ambiguous `WahaClientError` instead marks the queue row `deferred` with an uncertain-delivery reason while leaving the approval `approved`. `OwnerOutboundApprovalService.requeue()` accepts an approved approval when the queue is `deferred` or `failed`, so the OWNER requeue command can move an uncertain row back to `pending` and authorize a second WAHA attempt. This is a concrete manual replay path, not merely an automatic retry concern.

- Source-grounded review finding: [PR #60 discussion](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4472932656).
- Required correction: first establish one deadlock-free queue→approval lock order across the worker and OWNER mutation service; do not add an approval row lock while OWNER mutations still take approval→queue.
- After every final consent, safety, STOP, and delivery-window fence, atomically consume/reserve the same approval with a database-side `expires_at > clock_timestamp()` predicate and exact approval ID, queue ID, inbound ID, recipient, and content digest. Reservation failure must block before transport.
- Keep the approval consumed on success, ambiguous transport failure, or interrupted-send recovery. Make `requeue()` explicitly reject durable uncertain-delivery evidence even if a stale approval is present.
- Add a PostgreSQL/mock-WAHA regression: one ambiguous send leaves the approval consumed and queue quarantined; OWNER requeue is denied; a second worker pass performs zero additional mock-WAHA calls. Also retain pre-expiry exactly-once and expiry-during-final-lock-wait tests.

### Other P0 gates still open

- Contact-policy authority can expire while later final fences wait; the final quiet-hours lookup currently treats an expired/missing policy as absence of a restriction. Preserve and revalidate the original authority source/policy ID after all locks using a fresh database clock; an expired authority policy must deny.
- Exact one-use approval expiry/revocation must be checked at the actual final reservation boundary, not only before consent/safety/STOP locks.
- Fabian must explicitly accept or revise the STOP linearization contract: a STOP committed before durable dispatch reservation blocks; a STOP after reservation blocks later sends but cannot reliably retract the one network attempt already entering transport.
- Reconcile #48's exact view-once source lock and success-only return audit with the same final worker. Private-media byte retention remains OFF.
- The #60/#62 deployment changes and the full 001–040 migration chain still require one reviewed integration candidate and disposable PostgreSQL fresh/upgrade/no-op/schema/leakage proof.

**Release decision: NOT TEST READY.** No controlled-test stage is authorized. No code was changed in this verification, no tests or migrations were run by this documentation update, no production DB operation occurred, and **REAL WAHA ACTIONS: NONE**.

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
## Fresh engineering verification overlay — 2026-11-04 16:21 UTC

This overlay supersedes the 14:23 UTC snapshot below. It is a source-state record, not merge or release authorization.

### Main, CI, and governance

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last main commit 2026-09-08 11:09:59 UTC). No newer main commit appeared in the fresh commit listing.
- Latest Tests run is [41846567978](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41846567978), successful on exact PR #60 head `9a1865cad05114770fe4c8ffeae3b12eed8b34ca`: **955 passed, 1 warning, 76.53% coverage**. Its fresh disposable PostgreSQL step applied 001–033 and 038–040 only. It did not apply 034–037, execute an integrated 001–040 chain, run installed 033→040 upgrade/no-op/checksum proof, or run the ORM schema/DB-leakage audits.
- The preceding successful Tests run is [41838149298](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41838149298), exact PR #59 head `bf6e4975d304744147d0306123176004f4d605ce`: **797 passed, 1 warning, 76.01% coverage**. That documentation-branch run also applied only main's 001–033 chain.
- Main's `.github/workflows/tests.yml` still uses the lexical migration glob and 57% coverage floor; PR #61's contiguous-sequence gate and PR #55's post-test DB-leakage audit are not on main.
- Review submissions were re-fetched for all ten open PRs: **zero APPROVED submissions**. Comments and green CI are not independent approval. GitHub rulesets returned an empty list; the branch-protection endpoint returned 403, so current branch-protection state remains unverified.

### Open PR inventory — exact heads and unresolved review threads

Counts below are unresolved inline threads, with active/outdated split; the final column in parentheses is total returned thread history.

| PR | Exact head | Unresolved | Current significance |
|---|---|---:|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 0 (0 active / 0 outdated; 15 total) | Observation/return metadata wiring only; private bytes/retention remain OFF. |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 1 (1 / 0; 80 total) | Content-library foundation only; no live producer/selector/dashboard integration. |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 3 (3 / 0; 11 total) | Introduction-copy scope and trustworthy legacy provenance remain human decisions. |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 (0 / 1; 1 total) | Exact-head run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) passed 816 tests / 76.01%; schema and leakage audits passed on 001–033. |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 (0 / 1; 1 total) | Open; one outdated review thread. |
| [#59 roadmap/checklist refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | this documentation branch | 3 (1 / 2; 3 total) | Documentation-only; still needs independent review. |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `9a1865cad05114770fe4c8ffeae3b12eed8b34ca` | 19 (10 / 9; 19 total) | Draft/open. Exact-head run 41846567978 is green; remaining P0 authority issues still block readiness. |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 (0 / 0; 0 total) | Exact-head run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) passed on 001–033 only. |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 7 (4 / 3; 7 total) | Draft/open. Exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed 864 tests / 76.01% plus schema/leakage audits on 001–033, but Compose conflicts with #60's runtime-role boundary. |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 (0 / 1; 1 total) | Open; one outdated review thread. |

### P0 engineering delta — ScheduledAction final reservation

- Commit [9a1865c](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/9a1865cad05114770fe4c8ffeae3b12eed8b34ca) on #60 locks and refreshes the exact ScheduledAction row in `_is_exact_scheduled_action_binding()` with `FOR UPDATE` + `populate_existing=True`, after the worker's existing outbound-queue lock. The action lock remains held through the one mock/WAHA attempt and durable reconciliation commit; OWNER mutations continue to lock only the action row (queue → action).
- Added a two-session PostgreSQL regression that blocks the mock WAHA text attempt, starts an OWNER cancel from a session with a cached queued row, proves the mutation waits, then verifies the worker commits `completed` and the stale mutation re-reads/rejects the terminal state.
- Exact-head run 41846567978 passed the new regression within the 955-test suite. This is not a live WAHA test.

### Remaining P0 blockers — NOT PASSED

1. **Contact-policy expiry can become permission.** `authorize()` captures its timestamp before waiting on the policy row lock; the final `check_contact_delivery_window()` filters expired rows and treats no row as an allowed absence of quiet-hours policy. For a queue row whose authority came from that policy, this can convert expiry into permission. Preserve authority source/policy ID and revalidate enabled/disabled/expiry/category with a fresh database clock (prefer `clock_timestamp()`) after all blocking fences; expired policy authority must deny.
2. **Exact one-use OWNER approval is not reserved at the final fence.** Current approval consumption occurs after WAHA success. Make reservation/consumption atomic after consent, safety, STOP, and delivery-window waits, binding exact queue/inbound/recipient/content and DB-side expiry. First reconcile the lock-order inversion: worker owns queue→approval, while OWNER approval mutation currently locks approval→queue. Do not add an approval row lock in the worker until one deadlock-free order is established. An uncertain WAHA outcome must stay terminal/quarantined and never replay.
3. **STOP linearization requires OWNER acceptance.** A STOP committed before durable dispatch reservation must block. A STOP after reservation blocks later sends, but cannot reliably retract the one network attempt already reserved/entering transport. Repeated reads cannot close this network boundary; Fabian must accept this contract or require a redesigned reservation/transport state machine.
4. **View-once worker integration remains cumulative.** #48's exact source lock and success-only return audit must be carried into the one delivery worker; a queue-created return must not mark the artifact returned before WAHA acceptance. Retention stays OFF.

### Additional P1 source review — current approval-consumption lock cycle

- After the 14:23 snapshot, a fresh exact-head review of #60 (`9a1865cad05114770fe4c8ffeae3b12eed8b34ca`) identified a lock-order hazard on the existing post-send success path. The worker holds `outbound_queue` through WAHA, then updates `outbound_approvals` in `consume_approval()`. OWNER approval mutations take the per-approval advisory lock and then `_load_exact(lock=True)` locks both approval and queue (`FOR UPDATE OF a, q`). An overlapping OWNER edit/reject can therefore hold approval while waiting for the worker's queue lock, while the worker waits to update approval after WAHA has accepted the message.
- If PostgreSQL aborts the worker transaction after the external side effect, the already-accepted send can be left as a stale `sending` row and later quarantined as uncertain; the five-minute quarantine prevents replay, but approval consumption/sent audit are not durably reconciled.
- Actionable review note posted on #60: [P1 approval-consumption lock-cycle finding](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6635969882). Required next step: establish one lock order across worker and OWNER approval mutations, then add a two-session PostgreSQL/mock-WAHA regression that pauses after transport acceptance and races an OWNER edit/reject. No code or test was changed/run for this finding.

### Migration and deployment reconciliation

Branch-local migration allocation is sequential: #48=034, #50=035, #49=036–037, #60=038–040. The former 034 collision is resolved in allocation, but no candidate contains and validates 001–040. Main remains 001–033.

Deployment work remains non-cumulative:
- #60 has explicit service environment allowlists and a restricted non-owner API DB role, but lacks #62's pre-DDL DB-target, seed-policy, libpq, and migration-sequence preflights.
- #62 has those preflights, but still injects broad `.env.production` into API/WAHA/migrate and does not provision #60's restricted runtime role.
- Main `docker-compose.yml` still mounts `.env.production` into API, WAHA, and migrate; main `run-migrations.sh` has no current #62 target/seed/sequence preflight. Neither branch can safely merge first and assume the other composes.

### Identity Registry and content library

- #50's generic `introduction_reply()` still names projects and Datacube AU while its lifecycle guard checks only Zina/Fabian. Recommendation: keep the generic introduction identity-only; route project facts through the Identity Registry. Fabian's alternative is to gate every named registry key and test all combinations.
- Migration 035's `updated_at = created_at` predicate cannot reconstruct rows already touched by the pre-upgrade read-side timestamp mutation. Recommendation: preserve ambiguous legacy rows as `legacy_unknown` (NULL provenance/type) unless immutable evidence or explicit OWNER attestation proves origin; keep provenance stamping for new defaults. Human decision: accept unknown legacy provenance or require an explicit attestation workflow.
- #49 remains a WHAT-could-be-said library, not send authority. Do not integrate selection/producer/dashboard until P0 and migration reconciliation pass.
- #48 remains metadata-only; no private-byte retention or retention activation.

### Release readiness

**NOT TEST READY.** No integrated fresh 001–040, installed 033→040 upgrade, second-run checksum/no-op, combined schema/leakage/runtime-role proof, independent review clearance, or controlled WhatsApp test is established.

**REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering verification overlay — 2026-11-04 14:19 WAT

This source-state overlay supersedes the 10:31 WAT verification below. It is not release authorization.

### Fresh repository and CI state

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; its merge commit is dated 2026-09-08 11:09:59 UTC. No newer main commit was returned by the repository commit listing.
- The latest visible Tests run in the repository is [41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463), successful on PR #60 parent `3496ff19b72609553ba51daebfdf0f0472298908`: 952 passed, 1 warning, 76.51% coverage. It applied 001–033 and 038–040 only; it did not apply 034–037 or run the integrated schema/leakage gates.
- Current PR #60 head is `77f229c1a67e6049ea54e2a0803255c915ad3a15`. There is no Actions run associated with this exact head (the new commits use `[skip ci]`). The 952-pass result is parent-only evidence; no local tests or migrations were run for the current head.
- Main's Tests workflow still applies the lexical migration glob and runs pytest at the 57% floor. PR #61's sequence preflight and PR #55's post-test leakage audit are not on main.
- The branch-protection endpoint could not be rechecked through the current GitHub connection (403); no assumption about current protection is made and no main write was attempted.

### Current open PRs — exact heads and unresolved inline-thread counts

| PR | Exact head | Unresolved threads | State / significance |
|---|---|---:|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | 15 | Metadata observation/return only; no private-byte retention. |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | 80 | Content-library foundation only; no live producer/selector/dashboard integration. |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | 11 | Introduction-copy scope and legacy provenance still require resolution. |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | 1 | Exact-head run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) succeeded; schema/leakage audit applies to 001–033. |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | 1 | Open; one unresolved thread. |
| [#59 roadmap/checklist refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | updated by this documentation commit | 3 | Documentation-only; still requires independent review. |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `77f229c1a67e6049ea54e2a0803255c915ad3a15` | 19 | Draft/open; exact-head CI absent; P0 authority races remain. |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | 0 | Exact-head run [40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) succeeded on 001–033 only. |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | 7 | Draft/open; exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) succeeded on 001–033, but Compose still conflicts with #60's restricted-role boundary. |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | 1 | Exact-head run [41080836429](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) succeeded; one unresolved thread. |

No open PR has an independent APPROVED review submission. Passing CI and author comments are not approval.

### Migration and deployment reconciliation

Branch-local allocation is now sequential: #48=034, #50=035, #49=036–037, #60=038–040. The former 034 collision is resolved in branch allocation, but no cumulative candidate contains and validates 001–040. Main remains at 001–033.

The deployment changes are still non-cumulative: #60 has a restricted non-owner API DB role and service-specific Compose environment allowlists, but lacks #62's pre-DDL target/seed/libpq/sequence preflights. #62 has those preflights but still injects broad `.env.production` into API/WAHA/migrate and does not provision #60's runtime role. Do not merge either branch first and assume the other composes safely.

### P0 final-dispatch findings — NOT PASSED

1. **New contact-policy expiry bypass, filed on exact #60 head.** `authorize()` captures its timestamp before the policy `FOR UPDATE` wait and selects a policy with `expires_at > :instant`. After the worker's later consent/safety/STOP waits, `check_contact_delivery_window()` excludes an expired policy and treats `row is None` as an allowed absence of quiet-hours policy. For a policy-authorized row, expiry can therefore become permission. An exact-head inline review was filed on [PR #60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60): preserve the authority source/policy ID and revalidate enabled/disabled/expiry/category predicates at the final boundary using PostgreSQL `clock_timestamp()`; expired policy authority must deny. Add a deterministic PostgreSQL/mock-WAHA regression with zero calls.
2. **Exact one-use OWNER approval remains unreserved at the final boundary.** Reserve atomically after every blocking fence with exact queue/inbound/recipient/content binding and DB-side expiry. First make worker and OWNER mutation row-lock order consistent: worker already owns queue→approval, while OWNER mutation currently locks approval before updating queue. Do not add a worker approval `FOR UPDATE` without fixing this inversion. An uncertain WAHA result must leave the approval terminal and the queue quarantined; never replay.
3. **ScheduledAction worker-side lock remains missing.** PR #60 now row-locks OWNER cancel/pause/resume/reschedule/run-now mutations, but `_is_exact_scheduled_action_binding()` still reads the action without `FOR UPDATE`. Add the worker's exact action lock after the queue lock, preserve queue→action ordering, and test cancel-wins (zero WAHA calls) and worker-reservation-wins with two independent PostgreSQL sessions.
4. **STOP linearization needs OWNER decision.** A STOP committed before the final durable dispatch reservation must block. A STOP after reservation must block later attempts, but cannot reliably retract the already-reserved single network attempt. Fabian must explicitly accept this in-flight-attempt contract or require a redesigned reservation/transport state machine.
5. Preserve #48's exact view-once source lock and success-only return audit when integrating the worker. Retention stays OFF.

### Identity Registry and content-library decisions

- #50's current `introduction_reply()` still says it helps with projects and Datacube AU while its lifecycle guard checks only Zina/Fabian. The review recommendation is to make the generic introduction identity-only and leave project claims to the Identity Registry.
- Migration 035 still uses `updated_at = created_at` as historical provenance evidence. That cannot recover pre-upgrade rows already touched by old read-side timestamp updates. Safest bounded rule: leave ambiguous legacy rows as `legacy_unknown` (NULL provenance/type) unless immutable evidence or an explicit OWNER-attested action proves their origin; keep provenance stamping for new rows. Do not add another timestamp heuristic.
- #49 remains a reusable-content domain, not send authority; do not integrate producer/selection until P0 and migration reconciliation are complete. #48 remains metadata-only; private-media retention remains OFF.

### Release readiness

**NOT TEST READY. Stage A is not authorized.** No integrated fresh 001–040 chain, installed 033→040 upgrade, second-run checksum/no-op, combined schema/leakage/runtime-role proof, exact-head full suite, independent review clearance, or controlled WhatsApp test is established.

**REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering verification overlay — 2026-11-04 10:31 WAT

This overlay supersedes the 2026-11-04 06:23 WAT snapshot below. It is a source-state record, not a release approval.

### Main, workflow, and governance

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last main commit 2026-09-08 11:09:59 UTC). Main's Tests run [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08 and is historical only.
- Main's `.github/workflows/tests.yml` still applies `bot_core/migrations/*.sql` lexically and runs pytest at the 57% coverage floor. It does not include PR #61's contiguous-sequence preflight or PR #55's post-test DB-leakage audit.
- No open PR has an APPROVED review submission. All recorded submissions remain COMMENTED; a green branch-local suite is not independent approval.
- Latest successful overall Tests run before this update was [41741201463](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463) on PR #60 parent `3496ff19b72609553ba51daebfdf0f0472298908`: 952 passed, 1 warning, 76.51% coverage. Its disposable database applied 001–033 and 038–040 only; 034–037 were absent, and that workflow did not run the schema or DB-leakage audits.

### Current open PR inventory — exact heads at this verification

| PR | Exact head | State / current significance |
|---|---|---|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | Open; 15 review threads resolved. Metadata observation/return only; no private-byte retention. |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | Open; 1 active unresolved thread. Foundation only; no live producer/selector/dashboard integration. Retired set keys must remain non-reusable after hard deletion. |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | Open; 3 active unresolved threads. Introduction-copy scope, fail-closed registry errors, and trustworthy legacy provenance remain review items. |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | Open; exact-head run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) passed 816 tests / 76.01%, with schema and DB-leakage audits on 001–033. One outdated review thread remains unresolved. |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | Open; one outdated review thread. |
| [#59 roadmap/checklist refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | this documentation branch | Open; this commit refreshes its verification overlay. |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `77f229c1a67e6049ea54e2a0803255c915ad3a15` | Draft/open; 18 unresolved threads (9 active / 9 outdated). New ScheduledAction lock fix is committed but has no exact-head CI run. |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | Open; no unresolved review threads. Its successful run covers 001–033 only. |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | Draft/open; 7 unresolved threads (4 active / 3 outdated). Exact-head run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) passed 864 tests / 76.01%, schema audit and leakage audit on 001–033. |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | Open; one outdated review thread. |

### New source change — ScheduledAction mutation serialization

- On PR #60, commit [77f229c](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/77f229c1a67e6049ea54e2a0803255c915ad3a15) adds a shared `SELECT ... FOR UPDATE` loader with `populate_existing=True`. All five OWNER mutations (`cancel`, `pause`, `resume`, `reschedule`, `run_now`) now validate status only after acquiring the ScheduledAction row lock. These mutations do not acquire the outbound queue row, preserving the worker's queue→action order.
- Added two separate-session PostgreSQL regressions for both race orderings: OWNER cancellation holds the row and the scheduler skips it; scheduler release holds the row and a stale preloaded OWNER session waits, refreshes to `queued`, then rejects cancellation. Follow-up commit `77f229c` gives these tests their own disposable async engine/session factory and deterministic disposal.
- Commit message includes `[skip ci]` because Actions quota availability could not be verified. No test, migration, schema audit, or DB-leakage audit ran for `77f229c`. The previous 41741201463 result applies only to parent `3496ff1`; the new tests are not yet proven. PR #60 remains draft/open and this review finding remains unresolved pending exact-head CI and independent review.
- A top-level PR #60 engineering note records the exact change and verification limitation: [comment 6627448111](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6627448111).

### Migration and deployment reconciliation

Branch-local migration allocation is sequential but not integrated:

1. #48 — 034 `private_media_artifact_source_identity`
2. #50 — 035 `identity_registry_default_backfill`
3. #49 — 036 `outbound_message_library`, 037 `outbound_message_set_key_registry`
4. #60 — 038–040 contact consent and sender identity/contact evidence

Main still contains only 001–033. No candidate has proved fresh 001–040, installed 033→040 upgrade with representative existing rows, second-run checksum/no-op, combined schema audit, zero DB leakage, and restricted runtime-role privileges together.

Deployment changes remain non-cumulative: #60 has service-specific environment allowlists and a restricted API runtime DB role but lacks #62's database-target, local-seed, libpq, and contiguous-sequence preflights. #62 has those preflights but still mounts broad `.env.production` into API/WAHA/migrate and does not provision #60's restricted runtime role. A single integrated candidate must preserve every preflight before DDL, give owner credentials only to migrate, give API only the runtime URL, and give WAHA only explicit transport settings.

### P0 and architecture blockers

- #60 still needs a consistent final exact-approval/policy-expiry reservation after all blocking locks. Do not add a worker approval row lock in the current queue→approval order while OWNER approval mutations take approval→queue; first define one deadlock-free order. Consume/reserve exact approval once before transport; on uncertain WAHA outcome quarantine and never replay.
- OWNER must explicitly accept or reject the STOP linearization contract: STOP committed before durable dispatch reservation blocks; STOP after reservation blocks all later attempts but cannot reliably retract the one already-reserved network attempt. Repeated reads do not close that network-entry race.
- #48's exact-source view-once lock and success-only return audit must be integrated with #60's worker; preserve one worker/dispatcher and uncertain-send quarantine.
- #62/#60 deployment integration and full migration-chain proof remain release blockers.
- #50 must not infer historical provenance from `updated_at = created_at`; pre-upgrade rows already touched by older reads need a conservative `legacy_unknown` treatment unless immutable evidence proves origin. Generic introductions should not duplicate project/Datacube facts owned by the Identity Registry.
- #49 remains a content-library foundation, not send authority. Do not integrate its selector/producer/dashboard before P0 and migration reconciliation. #48 remains metadata-only; private-media byte retention stays OFF.

### Release readiness

**NOT TEST READY. Stage A is not authorized.** No integrated migration candidate, exact-head full suite, combined schema/leakage/runtime-role proof, independent approval, or controlled WhatsApp test is established. No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, or destructive cleanup occurred. **REAL WAHA ACTIONS: NONE.**

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
- **ScheduledAction cancellation race — 2026-11-04 04:17 WAT:** on #60 exact head `3496ff19b72609553ba51daebfdf0f0472298908`, `_is_exact_scheduled_action_binding()` performs an unlocked status read and `ScheduledActionService.cancel()`, `pause()`, and `reschedule()` load with `session.get()` rather than a shared row lock. An OWNER cancellation can therefore commit after the worker observes `queued`/enabled but before WAHA, while the worker still sends. Added an exact-head inline review on the final worker recheck ([review comment](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#discussion_r4463201277)): establish one queue/action lock order, serialize the worker's final action check and OWNER mutations, and prove both orderings with two-session PostgreSQL/mock-WAHA tests. No source fix or test is claimed; #60 now has 9 active / 9 outdated unresolved threads and remains draft.
- Still open on #60: final approval/policy expiry revalidation after all blocking locks, and explicit OWNER acceptance of the STOP reservation/linearization point.
- PR #50 still needs the human decision whether generic introductions may assert project/Datacube AU facts after registry tombstones, and a trustworthy legacy-default provenance rule. The `updated_at = created_at` heuristic cannot reconstruct rows already touched by pre-upgrade reads. Registry read failures must not fall back to stale identity assertions.
- PR #49 remains only a library foundation; do not integrate it into a producer before P0 and migration reconciliation. PR #48 remains metadata-only; private-media retention stays OFF.

### Release readiness

**NOT TEST READY. Stage A is not authorized.** No integrated migration candidate, exact-head full suite, combined schema/leakage/runtime-role proof, unresolved-review clearance, or controlled WhatsApp test exists. The controlled test plan is not yet approved for execution. No production DB mutation, production WAHA reconnection, real WhatsApp send, private-media retention activation, or destructive cleanup occurred. **REAL WAHA ACTIONS: NONE.**

---

## Exact-head CI follow-up — 2026-11-03 22:24 WAT

This follow-up supersedes the 22:17 WAT statement that PR #60's latest run was still in progress.

- PR #60 current exact head remains `fb9693014579283566358f30d80fcc2cc5581795`. Tests run [41721001922](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41721001922) completed successfully: **942 passed, 1 warning, 76.44% coverage**.
- Its disposable PostgreSQL job applied migrations **001–033 and 038–040**. It did not contain 034–037; it also did not run the ORM schema audit or post-test DB-leakage audit. This is branch-local CI, not integrated 001–040 or installed 033→040 proof.
- The new exact OWNER approval quiet-hours regression cases passed as part of the 942-test suite. `authorize()` now locks/evaluates the active exact-chat Contact policy before approval lookup, so a one-use OWNER approval cannot bypass an active quiet-hours window or malformed quiet-hours configuration.
- PR #60 remains draft with 10 active + 7 outdated unresolved threads. ScheduledAction quiet-hours, alias-wide safety budgets, final authority expiry after locks, media duplicate identity, and STOP/dispatch linearization remain unresolved.
- PR #55 remains exact-head green on [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314): 816 passed / 76.01%, migrations 001–033, schema audit and leakage audit passed. Its raw-table count is schema-qualified and the shadow-schema regression is present; one outdated review thread remains open.
- All other review counts and branch-local migration allocation in the 22:17 WAT overlay are unchanged. No open PR has an APPROVED review.
- **NOT TEST READY.** No integrated fresh/upgrade 001–040, no-op/checksum, schema/leakage/runtime-role proof, or controlled WhatsApp test has been established. **REAL WAHA ACTIONS: NONE.**

---
## Fresh engineering delta — 2026-11-03 22:17 WAT

This snapshot supersedes the 21:34 WAT overlay below. It is a source-state update, not a release approval.

### Main, workflow, and governance

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last main commit 2026-09-08 11:09:59 UTC); main currently reports `protected=false`.
- Latest Tests run associated with exact main remains [34219252390 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) from 2026-09-08. Treat it as historical only.
- Main `.github/workflows/tests.yml` still applies the lexical migration glob and runs pytest at the 57% coverage floor. The main workflow does not yet include #55's post-test leakage audit or #61's migration-sequence gate.
- Latest overall Tests run is [41721001922](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41721001922), **in progress** on exact PR #60 head `fb9693014579283566358f30d80fcc2cc5581795`. No result is claimed.
- PR #55's exact-head run [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) succeeded on `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c`: **816 passed, 1 warning, 76.01% coverage**; migrations 001–033, ORM schema audit, and post-test leakage audit passed.

### Current open PR inventory

Counts below distinguish active current-diff threads from outdated threads. All open PR review submissions are COMMENTED; none is APPROVED.

| PR | Exact head | Latest exact-head Tests | Unresolved threads (active / outdated / total) |
|---|---|---|---:|
| #48 PrivateMediaArtifact wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 0 / 15 |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | 1 / 0 / 80 |
| #50 Identity Registry lifecycle/backfill | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) | 3 / 0 / 11 |
| #55 DB-leakage CI gate | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | [41713366314 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) | 0 / 1 / 1 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 0 / 1 / 1 |
| #59 roadmap/checklist | Current docs branch; this update is documentation-only and will use `[skip ci]` | No exact-head Tests expected | 1 / 2 / 3 |
| #60 contact-consent P0 | `fb9693014579283566358f30d80fcc2cc5581795` | [41721001922 in progress](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41721001922) | 10 / 7 / 17 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 / 0 / 0 |
| #62 deployment/seed preflight | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) | 4 / 3 / 7 |
| #63 conversation observability | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) | 0 / 1 / 1 |

### P0 and architecture status

- **New #60 correction:** commits [b552521](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/b552521814943f5da551aad6174be12e75b6a30b) and [fb96930](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/fb9693014579283566358f30d80fcc2cc5581795) move the active exact-chat Contact policy lock and quiet-hours validation ahead of the one-use OWNER approval lookup. Exact approval still authorizes outside quiet hours; active quiet hours or malformed configuration now deny it. Regressions cover active and invalid quiet-hours denial plus approval success outside the window. Exact-head CI is still in progress.
- Remaining #60 P0 findings: ScheduledAction's authority-specific path still needs the same quiet-hours check; per-contact backlog/rate/duplicate limits must be contact-wide across mapped aliases; approval/policy expiry must be revalidated after the final locks; duplicate suppression must bind media locator/kind/transport metadata; and STOP receipt versus WAHA-entry linearization still needs an OWNER decision.
- #60's consent worker is not yet cumulative with #48's exact OWNER view-once source lock and success-only return audit. Keep uncertain WAHA outcomes quarantined; never blind-retry.
- #50 still has three active review threads, including introduction-copy scope and legacy identity provenance. Do not infer provenance from timestamps; unverifiable legacy rows should remain unknown unless immutable evidence or explicit OWNER attestation exists.
- #49 remains a content-library foundation only; no live producer selection or dashboard integration is authorized before P0 and migration integration are complete.

### Migration and deployment reconciliation

- Branch-local migration allocation is now contiguous: main 001–033; #48=034; #50=035; #49=036–037; #60=038–040. The old duplicate-034 filename collision is reconciled **only across branches**.
- No single candidate has passed a combined fresh 001–040 install, installed 033→040 upgrade, second-run checksum/no-op check, ORM schema audit, zero-leakage audit, and runtime-role privilege matrix. #55 and #60 branch runs exercise different migration subsets; do not combine their results into an integrated claim.
- #60's runtime-role/service environment boundary and #62's pre-DDL target/seed/sequence preflights are not cumulative. #62's current Compose still injects the entire `.env.production` file into Postgres, API, WAHA, and migrate. Postgres should receive only `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`; API should use the restricted runtime DB credential; WAHA should receive only WAHA-specific settings; migrate alone should receive migration-owner credentials. Neither PR is safe to merge independently.
- #55's schema-qualified raw-table counting fix is present and exact-head CI passed, but its review thread remains unresolved/outdated for independent review. #57 and #61 deployment/migration guards remain branch-local.

### Release disposition

**NOT TEST READY. Stage A is not authorized.** Private-media byte retention remains OFF. No production DB mutation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred. No PR was approved or merged.

Human decisions still required: STOP/dispatch linearization; whether terminal opt-out is irreversible or allows a separately defined OWNER re-consent path; introduction-copy scope; and policy for unverifiable legacy identity provenance.

Highest-value next step: finish the remaining #60 P0 fences, obtain the STOP contract decision, then integrate #48/#60 worker behavior and #60/#62/#55/#57/#61 deployment controls into one independently reviewed candidate. Prove the complete 001–040 fresh/upgrade/no-op/schema/leakage/runtime-role matrix on disposable PostgreSQL.

**REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering delta — 2026-11-03 21:34 WAT

This update supersedes the PR #55 row in the 20:40 snapshot below; it does not change the release disposition.

- **Main remains** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59 UTC); its latest exact-main Tests run is still [34219252390 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390). Main reports `protected=false`.
- **Latest overall Tests run:** [41713366314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314), on PR #55 head `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c`, completed successfully: **816 passed, 1 warning, 76.01% coverage**. The available 001–033 migration step, ORM schema audit, and post-test DB-leakage audit all passed; this is not integrated 001–040 or installed-upgrade evidence.
- **PR #55 source change:** commit [b5cb5ff](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c) schema-qualifies raw-table counts as `public.<quoted identifier>` and adds a PostgreSQL regression with a same-named shadow table in a leading `search_path` schema. Its existing P2 review thread remains unresolved pending independent review and exact-head CI.
- **PR #60 remains the P0 priority:** exact head `56ddd10ca7f315937c3f597fd2175fafe610f5ed`; [41695211554 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41695211554) reported 939 passed, 1 warning, 76.42%, but applied only 001–033 and 038–040. It still has 17 unresolved threads. A new source-grounded review comment [6614706465](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6614706465) consolidates the quiet-hours bypass, no-row policy-creation race, and post-lock authority-expiry recheck requirements. No source commit was made to #60 in this run.
- **Migration allocation remains branch-local:** main 001–033; #48=034; #50=035; #49=036–037; #60=038–040. No integrated fresh 001–040 or installed 033→040 upgrade has passed.
- **Deployment integration remains blocked:** #60's service-specific DB-role boundary is not cumulative with #62's pre-DDL target/seed/sequence checks; #62 still passes broad `.env.production` to API/WAHA/migrate. Neither merge order is safe.
- **Readiness:** NOT TEST READY. No production DB mutation, live WhatsApp send, WAHA reconnection, or private-media retention activation occurred. **REAL WAHA ACTIONS: NONE.**

---

## Fresh engineering delta — 2026-11-03 (after the 17:18 WAT snapshot)

This source-verified update supersedes the 17:18 snapshot above. Exact heads, review-thread flags, Actions runs, migration filenames, and deployment files were rechecked.

### Main, workflow, and governance

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; its latest branch-associated Tests run remains [34219252390 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) from 2026-09-08. The branch endpoint currently reports `protected=false`.
- The main workflow still runs the lexical `bot_core/migrations/*.sql` loop and pytest at the 57% coverage floor. It does not include the separate #55 leakage audit or #61 migration-sequence preflight.
- Latest overall Tests is now [41695211554 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41695211554), exact PR #60 head `56ddd10ca7f315937c3f597fd2175fafe610f5ed`: **939 passed, 1 warning, 76.42% coverage**. Its disposable PostgreSQL workflow applied 001–033 and 038–040 only. It did not apply 034–037 and is not an integrated 001–040 or installed 033→040 upgrade test.

### Current open PR heads and review state

| PR | Exact head | Exact-head Tests | Unresolved / total inline threads |
|---|---|---|---:|
| #48 PrivateMediaArtifact wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 15 |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | 1 / 80 |
| #50 Identity Registry lifecycle/backfill | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) | 3 / 11 |
| #55 DB-leakage CI gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | **1 / 1** |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 1 / 1 |
| #59 roadmap/checklist | This documentation branch; this commit is marked `[skip ci]` | No Tests run expected | 3 / 3 |
| #60 contact-consent P0 | `56ddd10ca7f315937c3f597fd2175fafe610f5ed` | [41695211554 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41695211554) — 939 passed, 76.42% | 17 / 17 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 / 0 |
| #62 deployment/seed preflight integration | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) — 864 passed, 76.01% | 7 / 7 |
| #63 conversation observability | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) — 803 passed, 76.08% | 1 / 1 |

No open PR has an APPROVED review submission. The earlier 17:18 overlay incorrectly listed #55 as 0 / 0; the live review-thread API shows one unresolved P2 in `scripts/audit_zina_test_db_leakage.py`: the audit checks existence in `public` but counts an unqualified table name, so a shadow schema earlier in `search_path` can hide public rows. The requested fix is to count from `public."{table}"` (or the resolved public regclass) and test with `search_path = shadow, public`.

### PR #60 engineering completed on this run

- Commit [4ed639b](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/4ed639b0f31286595bf5c420d149dd49785cc2c3) moved consent-expiry evaluation until after exact-chat mapping, Contact, and consent-row locks; it refreshes the locked ORM row and reads the clock after the lock acquisition.
- The worker now refreshes/revalidates the exact consent row after the final safety reservation and pending-STOP boundary, immediately before the one transport attempt.
- Added PostgreSQL regressions for expiry during mapping/consent lock acquisition and for expiry while later worker locks are acquired. Both passed; the latter asserts zero mocked WAHA calls.
- The first exact-head run [41694675082](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41694675082) passed 815 tests before exposing a separate test-cleanup bug: asyncpg `Transaction` has no `.is_active` attribute. Commit [56ddd10](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/56ddd10ca7f315937c3f597fd2175fafe610f5ed) now tracks successful `start()` and rolls back only when started. The subsequent exact-head run 41695211554 passed all 939 tests and the 57% coverage gate at 76.42%.
- The #60 PR description and consent-expiry review thread now record this evidence. The thread remains unresolved for independent review; no approval or merge occurred.

### Remaining integration and P0 blockers

1. #60 still has 17 unresolved threads: approval and ScheduledAction quiet-hours bypasses; approval/policy expiry at the final boundary; alias-wide rate/backlog/duplicate budgets; media duplicate identity missing locator/kind/MIME/filename; and the STOP-receipt/WAHA-entry linearization contract.
2. #60's worker is still not cumulative with #48: the exact OWNER view-once source lock and success-only return audit in #48 are absent from #60's worker. Uncertain WAHA outcomes must remain quarantined with no automatic retry.
3. #60 and #62 remain mutually non-cumulative. #60 has service-specific environment allowlists and the non-owner API DB role, but lacks #62's pre-DDL database-target, seed-policy, and sequence preflights. #62 has those preflights but still passes broad `.env.production` to Postgres, API, WAHA, and migrate. #57 and #61 safeguards also remain branch-local.
4. #50 still needs human decisions on generic introduction scope (remove project claims or gate every named registry fact) and unknown legacy provenance (do not infer from timestamps; leave unverifiable rows unknown unless OWNER-attested or supported by immutable evidence).
5. #49 remains foundation-only; no live producer selection or dashboard integration before P0 and migration integration.
6. No integrated fresh 001–040 chain, installed 033→040 upgrade, checksum/no-op second run, ORM schema audit, zero-leakage audit, and runtime-role privilege matrix has passed together.

### Release disposition

**NOT TEST READY. Stage A is not authorized.** The only new code verification is PR #60's branch-local 001–033 + 038–040 workflow. No production DB mutation, production WAHA reconnection, real WhatsApp send, or private-media retention activation occurred. Private-media byte retention remains OFF.

Human decisions still required: whether a STOP committed after the final dispatch reservation but before the WAHA request must veto; whether terminal opt-out is Contact-wide and irreversible or permits a separately defined OWNER re-consent; the introduction-copy scope; and whether unverifiable legacy identity provenance may remain unknown.

Highest-value next engineering step: finish the remaining #60 P0 authorization/quiet-hours/alias/media fences and resolve the STOP linearization contract, then construct one cumulative independently reviewed worker/deployment candidate preserving #48 + #60 and #55/#57/#61/#62 controls. Prove fresh 001–040, installed 033→040, second-run checksum/no-op, schema audit, zero DB leakage, and runtime-role privileges on disposable PostgreSQL.

**REAL WAHA ACTIONS: NONE.**


---

## Fresh engineering delta — 2026-11-03 17:18 WAT (current source-verified snapshot)

This overlay supersedes earlier dated status snapshots below. Historical checkboxes and branch-local test results are not evidence that the integrated release candidate is ready.

### Main, CI, and governance

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last main commit 2026-09-08 11:09:59 UTC); it contains migrations 001–033. The live branch endpoint reports `protected=false`.
- Latest Tests run associated with exact main: [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), success on 2026-09-08. This is historical main evidence.
- Latest overall Tests run observed: [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589), **cancelled** on PR #60's older head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`. Its runtime-role integration test was marked failed at 86%; the captured log had no assertion traceback, final test summary, or coverage result.
- Current PR #60 head `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` has **no associated Tests run**. Its diagnostic workflow change uses `pytest -vv -x --tb=long -o faulthandler_timeout=30` and `[skip ci]`; it has not established that the earlier failure is fixed.
- Main `.github/workflows/tests.yml` still applies the lexical migration glob and uses the 57% coverage floor. Main does not yet contain PR #61's migration-sequence preflight, PR #55's post-test DB-leakage gate, or PR #62's deployment target/seed preflights.

### Open PR inventory — exact heads and latest observed Tests

Review counts are unresolved / total inline threads, using GitHub's current `is_resolved` flags. Branch-local success is not integrated migration proof or approval.

| PR | Exact head | Latest exact-head Tests evidence | Unresolved / total |
|---|---|---|---:|
| #63 observability audit | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) — 803 passed, 76.08% | 1 / 1 |
| #62 deployment/seed preflights | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) — 864 passed, 76.01% | 7 / 7 |
| #61 migration-sequence gate | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938); preflight, migration, and pytest steps succeeded | 0 / 0 |
| #60 contact-consent P0 | `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` | No exact-head run; prior [41400297589 cancelled](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589) on parent head | 17 / 17 |
| #59 roadmap/checklist | Current documentation snapshot on this PR branch (this commit; no exact-head run because commits use `[skip ci]`) | Documentation-only; no Tests run expected | 3 / 3 |
| #57 local-seed safety | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 1 / 1 |
| #55 DB-leakage gate | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) — 815 passed, 76.01% | 0 / 0 |
| #50 Identity Registry lifecycle/backfill | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) — 828 passed, 76.52% | 3 / 11 |
| #49 Outbound Message Library foundation | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) — 896 passed, 76.67% | 1 / 80 |
| #48 PrivateMediaArtifact wiring | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 15 |

### Migration and deployment integration

The historical duplicate 034 allocation is now **reconciled by separate branch numbering**, but no integrated chain is verified:

- Main: 001–033.
- #48: 034 `private_media_artifact_source_identity`.
- #50: 035 `identity_registry_default_backfill`.
- #49: 036–037 Outbound Message Library.
- #60: 038–040 contact-consent / sender-identity / sender-contact evidence.

The branch trees are separate main-based candidates. No single candidate has proven fresh 001–040, installed 033→040 upgrade, second-run checksum/no-op behavior, schema audit, zero DB leakage, and runtime-role privileges together.

Deployment branches are not cumulative:
- #60 has service-specific Compose allowlists and a non-owner API runtime DB role, but its runner does not include #62's database-target and seed-policy preflights or #61's contiguous-sequence preflight.
- #62 includes pre-DDL database-target, seed-policy, and migration-sequence safeguards, but its current Compose still injects `.env.production` into Postgres, API, WAHA, and migrate; it does not preserve #60's restricted runtime-role boundary.
- #61's validator rejects malformed, duplicate, or non-contiguous migration filenames before the first `psql` call. Its exact-head CI passed, but main does not yet contain it.
- #60 and #62 both change Compose, migration runner, workflow, and README. Neither merge order is safe; produce one cumulative candidate rather than merging either branch independently.

### P0 and architecture blockers

1. **PR #60 remains dispatch-unsafe.** Its 17 inline threads include OWNER-approval and ScheduledAction quiet-hours bypasses; alias-local backlog/rate/duplicate limits; media duplicate checks that do not bind locator/kind/MIME/filename; approval, policy, and consent expiry races across final locks; and a STOP receipt vs WAHA-entry linearization gap. The latest source review still finds consent expiry compared against a timestamp captured before contact/mapping locks.
2. **PR #48 and #60 are not cumulative in the worker.** #48 locks the exact OWNER view-once source row before transport and marks it returned only after confirmed success. #60's current worker lacks that source lock/return-audit path. The integrated worker must preserve both consent/STOP fences and view-once source identity; uncertain WAHA outcomes remain quarantined with no blind retry.
3. **Runtime-role validation is not green on current #60.** The previous run failed/cancelled without a traceback; the diagnostic-only current head has no run. Do not infer a fix from the PostgreSQL permission-denial log lines.
4. **PR #62 still exposes broad production environment configuration to every service.** Keep the service-specific credential allowlists and the pre-DDL target/seed/sequence guards in one candidate.
5. **PR #50 still needs human architecture decisions.** Generic introduction copy must either avoid project claims or read those claims through Identity Registry lifecycle. Historical default provenance must not be inferred from `updated_at = created_at`; unverifiable legacy rows need an explicit unknown/OWNER-attested policy.
6. **PR #49 remains foundation-only.** It has no live producer selection or dashboard integration; do not connect it to external sending before P0 and migration integration are complete.

### Current release disposition

- **NOT TEST READY. Do not start Stage A.**
- No integrated fresh/upgrade/no-op/schema/leakage/runtime-role proof exists for migrations 001–040.
- Private-media byte retention remains OFF.
- Human decisions still required: the STOP reservation/linearization rule; whether terminal opt-out is Contact-wide and irreversible; the scope of project claims in generic introductions; and the provenance policy for legacy defaults.
- Highest-value next step after the STOP contract is accepted: create one cumulative, independently reviewed worker/deployment candidate preserving #48 + #60 outbound invariants and #55/#57/#61/#62 deployment controls, then run the complete fresh 001–040, installed 033→040, checksum/no-op, schema, leakage, and runtime-role matrix on disposable PostgreSQL.
- This snapshot is documentation-only. No application source or migration was changed; no tests, migrations, schema audit, DB-leakage audit, or real WAHA action were run.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

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

## Fresh engineering delta — 2026-11-03 08:24 WAT

This delta supersedes only the PR #60 CI-diagnostic state in the 07:20 WAT snapshot below. Re-fetched `main`, all ten open PR heads, exact-head Tests associations, workflow YAML, migration allocation, and the PR #60 Actions job log before making the following change.

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; no new main commit was returned.
- PRs #48/#49/#50/#55/#57/#59/#61/#62/#63 remain at the heads recorded in the 07:20 snapshot. PR #60 now points to `1f1c85a3a56924d098085a54f9cd90a5d26a2be2`, a diagnostic-only workflow commit on its existing branch.
- The PR #60 workflow now runs `pytest -vv -x --tb=long -o faulthandler_timeout=30`. `-x --tb=long` should print the first failing assertion before pytest starts a later async fixture; the shorter faulthandler interval gives a quicker trace if a test itself hangs.
- The commit message contains `[skip ci]` deliberately, so no Actions run was triggered. This is **not tested**. The latest run remains [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589), cancelled on parent head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`; its runtime-role integration test was marked FAILED at 86%, but the artifact contains no assertion traceback, final suite count, or coverage result.
- No application source, migration, deployment configuration, database, or WAHA path changed in this diagnostic commit. The contact-consent P0 review findings and #48/#60 worker integration blocker remain open.
- Migration allocation is unchanged: main 001–033; #48 034; #50 035; #49 036–037; #60 038–040. No exact candidate has proven fresh 001–040, installed 033→040 upgrade, second-run checksum/no-op behavior, schema audit, and zero DB leakage together.

**Next step:** after Actions capacity is confirmed, run the isolated `test_runtime_role_cannot_mutate_or_disable_consent_history` first on the disposable CI PostgreSQL database; capture its traceback, fix the actual assertion/cleanup defect, then run the full suite and integrated migration/leakage matrix. Keep #60 draft/open and do not merge it or #62 independently.

**NOT TEST READY. REAL WAHA ACTIONS: NONE.**

---

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

## Fresh engineering delta — 2026-11-03 16:20 WAT

This snapshot supersedes the 11:21 WAT overlay. I re-fetched the default-branch ref/history, all ten open PRs and their exact heads, inline review threads and review submissions, the latest 100 visible Tests runs, main and PR #60 workflow YAML, migration trees for #48/#49/#50/#60, and main/#60/#62 deployment configuration.

### Main and CI

- `main` remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last commit 2026-09-08 11:09:59 UTC. The main migration directory ends at 033.
- Latest Tests run on exact main remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. This is historical main evidence.
- Latest overall Tests run remains [41400297589](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41400297589), **cancelled** on PR #60's earlier head `bcc34cdcd012e2735d5f51d899ff7a2274c018f9`. Its job marked `test_runtime_role_cannot_mutate_or_disable_consent_history` failed at 86%, then hung during a later async-generator fixture setup and was cancelled at the 20-minute limit. The log did not preserve the original assertion traceback, final pytest summary, or coverage.
- Current #60 head `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` changes the workflow to `pytest -vv -x --tb=long -o faulthandler_timeout=30` to expose the first failure. Its commit deliberately includes `[skip ci]`; **there is no exact-head run**. Do not call the branch green.
- Main `.github/workflows/tests.yml` still applies a lexical migration glob and runs the 57% coverage floor; it has no #61 contiguous-sequence preflight or #55 schema/post-test leakage audit. Main `deploy/scripts/run-migrations.sh` still reapplies every seed SQL file, including local fixtures. Main `docker-compose.yml` still mounts `.env.production` into the API and WAHA services.

### All ten open PRs — exact current heads

Counts are unresolved inline threads / total inline threads. No open PR currently has an `APPROVED` review submission; all recorded submissions are comments, not approvals.

| PR | Exact head | Latest exact-head Tests evidence | Unresolved / total |
|---|---|---|---:|
| [#48 PrivateMediaArtifact wiring](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 15 |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) | 1 / 80 |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757), 828 passed / 76.52% | 3 / 11 |
| [#55 DB-leakage CI gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `3d35793ef72cfcfe1e188bc51df6d4e538679f7b` | [41026581000 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41026581000) | 0 / 0 |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 1 / 1 |
| [#59 roadmap/checklist refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `160cfb62fe498a92b9cbf4f2b7b8f329ff3c0730` before this documentation update | No exact-head run; docs-only commits use `[skip ci]` | 3 / 3 |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `1f1c85a3a56924d098085a54f9cd90a5d26a2be2` | No exact-head run; prior 41400297589 cancelled | 17 / 17 |
| [#61 migration-sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 / 0 |
| [#62 deployment/seed integration](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073), 864 passed / 76.01% | 7 / 7 |
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429), 803 passed / 76.08% | 1 / 1 |

These are branch-local results only. #48 having zero unresolved inline threads does not resolve its dependency on the combined worker/migration candidate. #49 remains a library foundation with no live selector, producer integration, or dashboard. #50's current open decisions are still the introduction's project claims and reliable provenance for legacy defaults.

### Migration and deployment reconciliation

The numbering collision is resolved in branch naming, not yet in an integrated release candidate:

1. #48 — 034 `private_media_artifact_source_identity`
2. #50 — 035 `identity_registry_default_backfill`
3. #49 — 036 `outbound_message_library`, 037 `outbound_message_set_key_registry`
4. #60 — 038–040 contact consent and sender-identity/contact evidence

No current branch or run proves fresh migrations 001–040 plus installed 033→040 upgrade, second-run no-op/checksum verification, combined schema audit, and zero leakage. Historical 001–037 integration evidence does not cover 038–040.

Deployment work is also split across incompatible branch snapshots: #60 now uses explicit Compose environment allowlists and a distinct restricted API runtime DB role, but its migration runner does not yet contain #62's database-target/local-seed/contiguous-sequence preflights. #62 contains those deployment guards but its current Compose still mounts `.env.production` into API/WAHA/migrate and does not provision #60's restricted runtime role. These changes must be reconciled into one candidate; neither PR's branch-local CI proves the combined deployment.

### Current P0 blockers on #60

The exact-head source/review recheck still identifies independent send-safety gaps:

- Exact one-use approval returns before the shared quiet-hours check; the ScheduledAction fast path in `background_workers._delivery_authorized()` also bypasses contact quiet hours.
- Approval/policy expiry is not revalidated at the final transport boundary after later safety-reservation and STOP/mapping locks. Contact consent expiry is also compared against a timestamp captured before mapping/Contact/consent locks, with no fresh expiry check after the worker's later waits.
- Contact rate/backlog and duplicate suppression remain alias-local rather than keyed by stable Contact identity. The duplicate fingerprint omits media locator/kind/MIME/filename, allowing identical uncaptained media to evade duplicate suppression and treating different media with the same caption as duplicates.
- The STOP reservation boundary needs explicit owner acceptance: a STOP committed after the final reservation veto cannot recall an already-reserved single transport attempt; that uncertain attempt must never be retried and all later rows must remain denied.
- The current exact head has 17 unresolved review threads. The most recent runtime-role integration run failed without a captured traceback; the isolated disposable-Postgres test must be diagnosed before another full suite.

Do not wire the message library into producers, run external-contact tests, merge, or treat #60 as P0-complete on this evidence. Next safe implementation priority is to isolate the runtime-role failure, then close the time-bound authority/quiet-hours/Contact-wide duplicate and frequency fences with deterministic two-session PostgreSQL/mock-WAHA regressions.

### Governance and readiness

- The current integration returns HTTP 403 for classic branch-protection details; the repository rulesets endpoint returns an empty list. Classic protection therefore cannot be verified in this run; do not rely on the earlier `protected=false` snapshot.
- No independent APPROVED review is present on any of the ten open PRs. Do not self-approve, merge, or bypass human review.
- Controlled-test readiness remains **NOT TEST READY**. No production DB operation, production WAHA reconnection, real WhatsApp send, private-media retention activation, or destructive cleanup was performed.


## Fresh exact-state verification — 2026-11-04 07:28 WAT

This overlay supersedes older run snapshots below for current refs and readiness. It is documentation-only; it does not approve, resolve, or merge any PR.

### Main and CI

- `main` is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (last commit 2026-09-08 11:09:59Z). No later commit exists on main.
- Main branch metadata currently reports `protected=false`; do not rely on required reviews/checks being enforced by branch protection.
- Latest exact-main Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on that same SHA at 2026-09-08 11:10:02Z. There is no newer main-branch CI run.
- Main contains SQL migrations **001–033** only. The main `.github/workflows/tests.yml` still applies the globbed migration files and runs pytest/coverage; the contiguous-sequence, deployment-target, seed-policy, schema-audit, and post-test leakage additions remain on unmerged PR branches.

### Live open PR inventory

All ten currently open PRs were re-read from GitHub. Review counts are GraphQL inline-thread counts: total unresolved / unresolved on the current diff. An outdated unresolved thread is not treated as a current code finding, but remains open for independent review.

| PR | Current head | Exact-head Tests run | Review threads unresolved / current |
|---|---|---|---:|
| [#63 conversation observability](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/63) | `13fad868affe01d6069f4288481f8cd8dd341c62` | [41080836429 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41080836429) | 1 / 0 |
| [#62 deployment/seed preflights](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/62) | `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc` | [41073226073 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) | 7 / 4 |
| [#61 migration sequence gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61) | `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` | [40300425938 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) | 0 / 0 |
| [#60 contact-consent P0](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) | `3496ff19b72609553ba51daebfdf0f0472298908` | [41741201463 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41741201463): 952 passed, 1 warning, 76.51% coverage | 18 / 9 |
| [#59 roadmap/checklist refresh](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/59) | `b3b6c8053c93ab194ab50fd42b55ce8333ab2ad2` | Docs-only; no exact-head run | 3 / 1 |
| [#57 local-seed safety](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57) | `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` | [40169146406 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) | 1 / 0 |
| [#55 DB-leakage/schema audit gate](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55) | `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` | [41713366314 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41713366314) | 1 / 0 |
| [#50 Identity Registry fixes](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50) | `0a2b38c0ce72b3c4a8fdd49490be504facb34bac` | [41202063757 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41202063757) | 3 / 3 |
| [#49 Outbound Message Library foundation](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49) | `bcd0033e024b177561b8afd41589afe1897ba4de` | [39920982545 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545): 896 passed, 1 warning, 76.67% coverage | 1 / 1 |
| [#48 PrivateMediaArtifact observation/return](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48) | `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` | [40158094566 success](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) | 0 / 0 |

No open PR has an `APPROVED` review submission. A green branch-local workflow is evidence for that exact branch only, not independent approval or merge authorization.

### Migration and deployment integration

The original duplicate-034 allocation has been renumbered across feature branches, but the sequence is only contiguous by allocation:

1. #48 — 034 `private_media_artifact_source_identity`
2. #50 — 035 `identity_registry_default_backfill`
3. #49 — 036 `outbound_message_library`, 037 `outbound_message_set_key_registry`
4. #60 — 038–040 contact consent and sender-identity/contact evidence

No single candidate has yet proved fresh **001–040**, installed **033→040** upgrade with representative existing rows, second-run no-op/checksum behavior, combined schema audit, and zero DB leakage.

The deployment work must also be consolidated rather than merged in an arbitrary order:
- #60 contains the restricted non-owner API DB role and service-specific Compose environment allowlists, but lacks #62's database-target, local-seed, and contiguous-migration preflights.
- #62 contains those preflights and seed controls, but its current Compose still injects the shared `.env.production` into services and does not preserve #60's runtime-role boundary.
- #48 and #60 both change the outbound worker/authorization path. The integrated worker must preserve #48's exact view-once source lock and success-only return audit together with #60's consent/STOP/quiet-hours final fence.
- #55's schema/leakage checks and #61's sequence validator must run on that same integrated candidate, not only on 001–033.

### Current P0 source/review findings on #60

The latest exact-head Tests run is green, but the current source/review state is **not P0-complete**:

1. **Time-bounded authority can expire while the worker waits.** The final `_delivery_authorized()` call currently occurs before later Contact/consent, global safety-reservation, mapping, STOP, and delivery-window locks. The exact one-use approval is checked before those waits and consumed only after the WAHA attempt; a post-send expiry check can therefore discover expiry after an external send. The delivery-window query filters expired policies out and treats no active row as “no quiet-hours restriction,” which is not a revalidation of the policy that supplied authority. Required fix: revalidate the same authority source after all locks, using database time at an atomic reservation boundary. For exact approvals, use a conditional one-use reservation bound to approval ID, queue ID, inbound ID, recipient, exact payload digest, approved status, and `expires_at > clock_timestamp()`; preserve a consistent queue→approval lock order and quarantine uncertain outcomes without replay. For contact-policy authority, lock the matching policy row even when expired, then evaluate enabled/disabled/expiry/category after acquiring the lock.
2. **ScheduledAction cancellation race remains.** `_is_exact_scheduled_action_binding()` reads the queued action without `FOR UPDATE`; `cancel()`, `pause()`, `reschedule()`, `resume()`, and `run_now()` load through `session.get()`. A cancellation can commit after the worker's check but before transport, while the already-claimed queue row still sends. Required fix: keep worker queue→action lock order; lock the exact ScheduledAction row in the final binding check and hold it through one attempt/outcome commit; make OWNER mutations lock that same action row without then locking the queue. Add two-session mock-WAHA tests for mutation-wins (zero calls) and worker-reservation-wins (mutation waits and observes completed/uncertain state).
3. **STOP semantics require OWNER acceptance.** The current contract treats the final pending-STOP check/dispatch reservation as the in-flight boundary. STOP committed before it blocks; STOP arriving after it cannot reliably retract that already-reserved single network attempt, but must block all subsequent sends and no uncertain attempt may be retried. Repeated reads cannot close the network-entry race. Record Fabian's explicit acceptance or redesign the reservation/state machine before calling this complete.
4. The exact-head suite now includes contact-wide mapping/consent and rate/duplicate checks, canonical media-aware duplicate binding, final quiet-hours checks for approval and ScheduledAction paths, missing-source-ID ingress rejection, and runtime-role privilege regressions. Those improvements do not close the expiry, ScheduledAction cancellation, STOP decision, or integrated migration/deployment gates above.

The latest exact-head run does not include a combined 001–040 chain, installed upgrade, schema audit, or DB-leakage proof. Do not start external-contact tests or integrate the message library into live producers before these P0 and integration gates pass.

### Identity Registry and Outbound Message Library

- #50 still has four current unresolved review threads. `introduction_reply()` now consults Identity Registry availability, but the generic introduction scope/project claims and fail-closed behavior on registry read errors require independent verification. The migration's `updated_at = created_at` eligibility heuristic remains unreliable for rows touched by pre-upgrade reads; do not keep patching timestamp edge cases. Choose an explicit provenance primitive (e.g. a dedicated immutable seed marker or an auditable migration decision) and obtain OWNER/product agreement on whether generic introductions must suppress project claims when those registry facts are disabled/deleted.
- #49 has one current unresolved thread on permanent set-key retirement after hard deletion. The branch adds an append-only key registry and regression, but the current exact-head review thread remains open. The library is still a content-selection foundation: no live producer/selection integration or dashboard. It must remain downstream of P0 authorization and must never itself grant send authority.

### Local validation limits and readiness

- This execution environment has GitHub read/write access but no local `psql` or Docker executable, so it cannot reproduce the PostgreSQL lock/role/migration tests locally. No local pytest, migration, schema, or leakage run was performed in this verification.
- No Actions run was triggered by this documentation refresh. The exact-head results above are fetched historical/current GitHub run records, not tests run in this execution.
- Main branch metadata reports `protected=false`; configure required independent review and CI checks before any future merge.
- Controlled-test readiness remains **NOT TEST READY**. Private-media retention remains OFF. **REAL WAHA ACTIONS: NONE.**


### Fresh source-review delta — 2026-11-05 00:25 WAT

- Rechecked PR #50 exact head `0a2b38c0ce72b3c4a8fdd49490be504facb34bac`. Its review state is now **4 unresolved threads / 12 total** (4 current-diff, 3 outdated unresolved); this supersedes the earlier three-thread snapshot above.
- Added a new P1 review finding at [PR #50 discussion](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50#discussion_r4475073725): the `identity_reply()` aggregate-project fallback checks only the `projects` key even though the same request explicitly targets both `projects` and `fabian`. If Fabian is disabled/tombstoned while `projects` remains active, the fallback still emits “Fabian’s core projects”. The adjacent “why do you exist” fallback also names the owner while checking only `zina`. Requested fail-closed guards and regression coverage.
- This is review-only: no application source, tests, migration, or CI run changed. The #50 exact-head Tests evidence remains run 41202063757 on this branch (001–033 + 035 only); no integrated 001–040 proof is implied.
- Main remains `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`. No merge, approval, production DB operation, or WAHA action occurred. **NOT TEST READY. REAL WAHA ACTIONS: NONE.**


## Fresh review delta — 2026-11-05 10:35 WAT

- PR #62 remains at exact head `a8d032de4eb52f2c4baf31d197a5a856a6d7d4bc`. Its inline review state is now **8 unresolved / 8 total; 5 active** after a new source-grounded P2 review on `scripts/audit_zina_test_db_leakage.py:145`.
- The exact #62 audit checks raw-table existence with `to_regclass('public.<table>')`, but counts using unqualified `SELECT COUNT(*) FROM "<table>"`. A shadow schema earlier in `search_path` can therefore make the existence check inspect `public` while the count reads a different table and misses leaked rows.
- PR #55's current head `b5cb5ff4691b2b9caa293c95e4d562daa8e0e55c` fixes this by counting the explicitly qualified `public` table in `collect_raw_table_leaks()` and adds `test_raw_table_audit_counts_public_rows_when_search_path_has_shadow_table`. The #62 copies of the audit script and test do not contain that fix/regression. The combined candidate must retain #55's correction while keeping #62's newer URL guards, Contact inventory, schema audit, and leakage workflow step.
- #62's exact-head Tests run [41073226073](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41073226073) remains **864 passed / 76.01%**, with schema and leakage audit steps reported successful; it applied migrations **001–033 only** and did not exercise the missing shadow-schema regression or the integrated 001–040 chain.
- The review comment is review-only. No application code, tests, migrations, Actions run, production database, deployment, or WAHA operation was changed or triggered by this finding.

The release gate remains **NOT TEST READY**. **REAL WAHA ACTIONS: NONE.**


## Fresh exact-state verification — 2026-11-05 (post PR #60 P0 replay guard)

This overlay supersedes the 2026-11-05 10:35 WAT snapshot above. It was checked against the current GitHub branch heads and Actions records; older roadmap checkboxes are not treated as proof of current code.

### Main and CI

- `main` is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (latest commit 2026-09-08 11:09:59Z). The latest verified main-branch Tests run remains [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on that exact SHA on 2026-09-08. No later main commit or main-branch Tests run was found.
- Latest overall Tests run is [42019032673](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/42019032673), successful on PR #60 exact head `4b36f8af3389a9270aefde4654f1e7b0a9270b3c`: **956 passed, 1 warning, 76.57% coverage**. The workflow applied migrations **001–033 and 038–040 only**.
- PR #50 exact head `e543a704729cc69a859ea61e4e1afb0196d23fdb` has [Tests run 41981156413](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/41981156413) successful: **841 passed, 1 warning, 76.50% coverage**; it applied **001–033 and 035 only**.
- The main Tests workflow still runs a plain sorted SQL-file loop and pytest with a 57% coverage floor. It does not itself prove contiguous migration numbering, an installed-database upgrade, schema audit, or post-test DB-leakage audit.

### Current open PR inventory

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

The repository still reports `main` as unprotected. Configure and independently verify required reviews and CI before any merge. No autonomous self-approval or merge is permitted.

### Fresh PR #60 P0 implementation delta

Commit [4b36f8a](https://github.com/Fabian121-ux/DatacubeAU_com.bot/commit/4b36f8af3389a9270aefde4654f1e7b0a9270b3c) closes one concrete replay path: an OWNER could previously requeue a deferred row after an ambiguous WAHA outcome while its exact approval remained approved. The current branch now:
- persists a one-way `delivery_outcome_uncertain` marker on uncertain queue rows;
- rejects marked rows at the shared worker authorization boundary (including OWNER self-DM) and at `OutboundAuthorizationService.context_from_queue_message()`;
- refuses OWNER requeue when that marker exists;
- tests an approved external row, one mocked ambiguous send, denied requeue, and a forced status reset that still cannot pass the worker fence.

The regression passed in exact-head run 42019032673. The evidence reply is recorded on the existing P0 review thread; the thread remains unresolved for independent review.

The earlier 10:35 snapshot said the ScheduledAction cancellation race remained. That specific implementation gap has since been addressed on #60: the worker's exact action binding now uses `FOR UPDATE` with `populate_existing`, and OWNER cancel/pause/resume/reschedule/run-now all use `_get_for_update()`. The two-session regression is present in the branch-local test suite. The thread still requires independent review.

### Remaining P0 and integration blockers

1. **Original authority expiry is still open.** The initial `_delivery_authorized()` check can precede consent/safety/STOP/window lock waits. `check_contact_delivery_window()` filters expired policies out and treats no active row as no quiet-hours restriction; it does not revalidate the policy that supplied send authority. Exact approvals are consumed only after WAHA success. Required: one atomic final reservation of the same approval bound to queue ID, inbound ID, recipient, exact payload digest, and `expires_at > clock_timestamp()`; revalidate/lock the original contact policy after all other final fences. Preserve a consistent queue→approval lock order and two-session expiry tests.
2. **STOP linearization requires OWNER acceptance.** The current contract treats the final pending-STOP check/reservation as the in-flight boundary: a STOP committed before it blocks; a STOP arriving after it cannot recall the already-reserved network attempt, but blocks subsequent sends. Record explicit OWNER acceptance or redesign the reservation protocol.
3. **Post-acceptance lock order remains under review.** Worker queue→approval and OWNER approval→queue paths need a consistent lock order and a two-session regression for the post-WAHA success/consumption path.
4. **Contact mapping, runtime-role test safety, consent-event privilege, and cross-PR deployment findings remain independently reviewable.** Do not infer resolution from a green suite alone.
5. **#60/#62 deployment work is still split.** #60 has service-specific environment allowlists and a restricted runtime API role, but lacks #62's target/seed/contiguous-migration preflights. #62 has those preflights but still mounts broad `.env.production` into API/WAHA/migrate. #55's schema-qualified leakage-audit fix and #61's sequence validator must be retained in the same reviewed candidate; #57 seed safety overlaps the same runner.

### Migration and release evidence

Feature allocation remains #48=034, #50=035, #49=036–037, #60=038–040. The two recent green runs above intentionally validate only their branch-local migration subsets; neither proves a fresh contiguous **001–040** chain or an installed **033→040** upgrade. No single candidate has yet demonstrated second-run no-op/checksums, combined schema audit, and zero DB leakage. #48/#60 worker integration must preserve view-once source locking and success-only return audit alongside contact consent, STOP, quiet-hours, and uncertainty fences.

Controlled-test readiness remains **NOT TEST READY**. Private-media retention remains OFF. No local `psql` or Docker executable was available in this execution environment; the cited validation is GitHub Actions evidence only. **REAL WAHA ACTIONS: NONE.**
