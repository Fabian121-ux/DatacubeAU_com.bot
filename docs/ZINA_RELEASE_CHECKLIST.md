# Zina Release Checklist

## Live release-verification delta — 2026-10-29 12:17 WAT (partial; NOT TEST READY)

This snapshot supersedes the 2026-10-28 13:25 UTC overlay. The older checklist below is historical; do not use it as evidence of current readiness. The exact heads/runs were checked before this documentation update, and the resulting PR #59 docs commit needs its own exact-head CI check.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests run [#34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) succeeded on 2026-09-08. This is historical, not current October release-candidate proof.
- **Latest integrated deployment-preflight candidate:** PR #62 head `97f30242198cd78097983c74ff0062c96c016605`; [Tests #40857332668](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40857332668) succeeded on 2026-10-29: **843 passed, 1 warning, 76.01% coverage**. The sequence preflight passed and migrations 001–033 applied on isolated CI PostgreSQL. This does not cover feature migrations 034–040 as a single chain.
- **Current P0 candidate:** PR #60 head `1644e2a338b53c7ec709d91163187d9d0b4af940`; [Tests #40849618517](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40849618517) succeeded. It remains draft with 3 unresolved inline review threads and is not merged. Unknown/revoked consent and terminal opt-out must remain denied at the final worker fence; the contact-wide STOP policy and current-mapping lock/fence are not yet release-proven.
- **Migration plan:** #48=034, #50=035, #49=036–037, #60=038–040. The old duplicate migration number is reconciled on the current feature branches, but the combined chain remains unverified. PR #61's contiguous-numbering gate and PR #62's deployment preflight are open. PR #57's seed-policy changes overlap with #62 and should not merge separately while the integrated candidate is under review.
- **Review state:** unresolved inline threads remain on #49 (1), #50 (2), #57 (1), #59 (1 stale-snapshot thread), #60 (3), and #62 (5). #48, #55, #61, and #63 have no unresolved inline threads; this is not equivalent to independent approval.
- **Identity decisions:** PR #50 still needs an explicit decision for tombstone-aware behavior across all introduction callers and a reliable legacy provenance policy. Do not use timestamp equality as proof a default row was never touched.
- **Mechanical gates still open:** fresh PostgreSQL migrations 001–040; installed 033→040 upgrade and second-run no-op; exact-candidate DB-leakage audit; full P0 adversarial matrix; independent review of blocking consent/identity/deployment findings; controlled-test plan and readiness sign-off. Main's workflow still only applies 001–033 and the DB-leakage CI PR #55 is not merged.
- **Safety:** no real WhatsApp sends, production DB mutations, production WAHA reconnection, private-media retention activation, or PR merges occurred. **NOT TEST READY.**

## Live release-verification delta — 2026-10-28 06:30 UTC (partial; NOT TEST READY)

See the [roadmap live-verification delta](ZINA_IMPLEMENTATION_ROADMAP.md) for the exact inspected PR heads and dependency notes. This checklist distinguishes branch-local tests from an integrated release candidate.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; last commit and latest main Tests run [#405](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) were on 2026-09-08. October branch tests do not establish current main-green.
- **Latest P0 head:** PR [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60) at `dd944fdff88afe6de64a82b3dff40786f99f8f26`; exact-head Tests [#622](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40643929083) passed on 2026-10-28: **900 passed, 1 warning, 76.41% coverage**. This workflow applied migrations 001–033 and 038–040, not the contiguous 001–040 chain.
- **Migration order still awaiting integration:** #48=034, #50=035, #49=036–037, #60=038–040. Sequence gate #61 and deployment preflight #62 remain open. #60 is draft with 3 unresolved inline review threads; #50 has two unresolved architectural decisions. A green CI result is not independent review or release approval.
- **Required before controlled testing:** fresh PostgreSQL chain 001–040; installed 033→040 upgrade and repeat/no-op run; exact-candidate DB-leakage audit; P0 adversarial matrix; independent review of blocking consent/identity findings; updated controlled-test plan.
- **Safety:** unknown/revoked consent and terminal opt-out must deny at the final worker fence. No real WhatsApp sends, production database mutations, production WAHA reconnection, or private-media retention activation during engineering.

## Engineering gates (mechanical — re-verify every run)

- [ ] Full contiguous migration chain (001 → 040) applies cleanly from an empty database — not yet verified on the combined candidate.
- [x] Full pytest suite green on PR #60 exact head — 900 passed; integrated-candidate suite remains unverified.
- [x] Coverage at or above the repository gate (57%) — 76.41% on PR #60 exact head; not an integrated-candidate result.
- [ ] DB leakage = 0 across all `CLEANUP_MODELS`/`CLEANUP_RAW_TABLES` tables — current combined-candidate audit outstanding.
- [ ] **No unresolved P0 outbound-authority gaps.** Issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open: exact-contact consent/opt-out must be authoritative and checked at final dispatch, with revocation serialized against the transport attempt.
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
