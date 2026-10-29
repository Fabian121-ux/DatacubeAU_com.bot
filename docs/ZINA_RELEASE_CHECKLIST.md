# Zina Release Checklist

## Live release-verification delta — 2026-10-29 15:37 WAT (partial; NOT TEST READY)

This replaces the 15:34 WAT snapshot. The detailed checklist below contains historical domain assertions and must not override this current gate state. PR heads, recent exact-head workflow runs, workflow YAML, migration inventory, and review-thread resolution state were re-queried. Counts below distinguish total threads from threads whose GraphQL `is_resolved` flag is still false. The prior documentation head's run [#40882297507](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40882297507) passed on `dcda2dbbea7d45745ce53df3cdc145d785cf80c7`; this refresh changes the docs again, so only a new exact-head run can validate it.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests run [#34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08 (797 passed, 75.98% coverage; migrations 001–033). No newer main-branch run is present. The branch endpoint reports `protected=false`, repository rulesets are empty, and issue [#54](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/54) remains open; the classic protection endpoint is not readable through this integration.

- **Current P0 candidate:** PR [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60), head `18f03f250786bd7af2ff67f2a4f10b75ed8deaf9`; [Tests #40892840458](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40892840458) passed **911 tests, 1 warning, 76.41% coverage**. The parser fix adds topic-qualified negative regressions and keeps exact STOP positives. The workflow applies 001–033 plus 038–040, not a contiguous migration chain. PR remains draft with 3 unresolved inline threads. Independent review of Contact-before-consent locking, append-only audit protection, contact-wide terminal STOP semantics, and the new parser regression matrix is still required. Review finding: [comment #6499327781](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6499327781).

- **Migration order:** #48=034, #50=035, #49=036–037, #60=038–040. The original duplicate-number collision is resolved on these feature heads, but no current exact-head run validates all 001–040 together.

- **Current branch-local CI:** #48 head `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`, [#40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success (856 passed, 76.26%, 001–034); #49 `bcd0033e024b177561b8afd41589afe1897ba4de`, [#39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success (896 passed, 76.67%, 001–033 plus 036–037); #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1`, [#40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) success (825 passed, 76.47%, 001–033 plus 035).

- **Deployment and leakage candidates:** #55 head `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2`, [#40010785239](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40010785239) success (814 passed, 76.01%; migrations 001–033, schema and leakage audits pass on this exact head). #57 head `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba`, [#40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success (811 passed, 76.01%; 001–033). #61 head `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`, [#40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success (809 passed, 76.01%; 001–033). #62 head `97f30242198cd78097983c74ff0062c96c016605`, [#40857332668](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40857332668) success (843 passed, 76.01%; sequence preflight plus 001–033). #63 head `c6c493d28c1e27a267867cfe8be7a5005f777a28`, [#40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) success (801 passed, 76.04%; 001–033).

- **Separate historical integration run:** [#39940318940](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39940318940) on temporary validation head `8a2e6cc604f9d744d0f95a9126360b0a4364db9f` passed 956 tests at 77.24% and validated fresh 001–037, installed 033→037 upgrade, schema audit and leakage audit. It is not the current #55 head and does not cover 038–040 or prove the second-run no-op.

- **Review blockers (unresolved / total threads):** #48=0/15; #49=1/80; #50=2/10; #55=0/0; #57=1/1; #59=1/1; #60=3/3; #61=0/0; #62=5/5; #63=0/0. #48's threads are resolved; #49 has one unresolved retired-key thread; #50 has two unresolved architectural findings. Some comments have replies but remain unresolved until GitHub records resolution. Zero unresolved threads is not independent approval. #49 is still foundation-only; do not connect it to live producers. #50 needs human decisions on introduction-path tombstones and legacy provenance. #62 has five unresolved deployment-safety threads; #57 overlaps its runner and must not merge independently.

- **Required before TEST READY:** fresh contiguous 001–040; installed 033→040 upgrade and a second no-op run; exact-candidate schema and DB-leakage audit; full P0 adversarial matrix; independent review of consent, identity, and deployment blockers; updated staged controlled-test plan and explicit human sign-off. Private-media retention remains OFF.

- **Safety:** documentation only. No application/migration code change, production database operation, real WAHA send/reconnection, PR merge, or review-thread resolution occurred. **NOT TEST READY.**

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
