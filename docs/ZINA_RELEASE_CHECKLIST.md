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