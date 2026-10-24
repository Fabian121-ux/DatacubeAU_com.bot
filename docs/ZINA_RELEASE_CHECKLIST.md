# Zina Release Checklist

What remains before Fabian can begin controlled real-world WhatsApp testing (see `docs/ZINA_IMPLEMENTATION_ROADMAP.md` for the full per-domain detail behind each line here, and `docs/ZINA_CONTROLLED_TEST_PLAN.md`, once written, for the staged test procedure itself).

Last full phase-by-phase audit: 2026-09-08, against `main` @ `0034587a90bb8d5a79bda41e85091cfea33b969d`. The dated branch-state snapshot below is partial, not a fresh full release audit.

## Current branch-state snapshot — 2026-10-24 (not a full phase-by-phase audit)

The last full roadmap/checklist audit above is historical. The live `main` branch is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033. Its latest `Tests` push run is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. The checkboxes below must not be treated as fresh release approval, and open feature branches are not part of `main`.

Current open feature PRs and exact-head evidence:

- **[#48](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48)** current head `02aeabc937e8d38070748bb3adbcb9d7f6bf166f`: [Tests run 40094090968](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40094090968) succeeded on 2026-10-24. The run metadata available in this audit does not expose a test count or coverage percentage. Beyond exact WAHA-origin/path validation and hostile-locator regressions, the latest head binds the quoted source chat/message and OWNER command ID into the approval digest, serializes conflicting source replays, rejects a missing command ID before queue/artifact creation, and reports partial artifact cleanup truthfully. The branch remains unmerged and requires independent review.
- **[#49](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49)** head `bcd0033e024b177561b8afd41589afe1897ba4de`: [Tests run 39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded — 896 passed, 76.67% coverage; this branch applies 001–033 and 036–037, not 034/035. Its permanent-key review thread remains unresolved.
- **[#50](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50)** head `40f5139cb6c0dbfcee3e26771a06dafa0850bf62`: [Tests run 34312518958](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34312518958) succeeded — 820 passed, 76.44% coverage on 2026-09-09. Two architectural review threads remain unresolved: introduction paths bypass disabled/deleted identity state, and `updated_at = created_at` cannot reliably identify every legacy default for provenance backfill.
- **[#55](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55)** draft head `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2`: [Tests run 40010785239](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40010785239) succeeded — 814 passed, 76.01% coverage; schema and post-test database-leakage audits passed.
- **[#57](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57)** draft exact head `492bfdeb056da11cb83b50a9472928fe5c937bd5`: [Tests run 40108792756](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40108792756) succeeded on 2026-10-24. The current runner accepts the exact local `zina_disposable` target or a CI-only `zina_seed_policy_*` name tied to the active GitHub run/attempt, and rejects broad `test_*`/`dev_*` names. This run's summary does not expose a test count or coverage figure, so figures from the prior head are not carried forward.

Migration numbering is now structurally unique across those branches: #48 uses 034, #50 uses 035, and #49 uses 036–037. Temporary integrated validation head `8a2e6cc604f9d744d0f95a9126360b0a4364db9f` passed [run 39940318940](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39940318940): fresh 001–037, installed upgrade 033→037, 956 tests, 77.24% coverage, and zero DB leakage. This is integration evidence, not final-head approval: PR #48 has since advanced beyond the blob set in that run, so the latest source-binding/locator-hardening commits still need to be included in a fresh integrated-chain validation. The run also does not establish a second-run migration-runner no-op, the no-ledger legacy-install path, a separately reported P0 adversarial matrix, or a resolved legacy provenance policy.

**Current release state: NOT TEST READY.** P0 issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open: external-contact consent/opt-out is not authoritative state checked by the final outbound authorization path. Do not wire the message library into live producers until unknown/revoked consent and opt-out fail closed with race-safe worker enforcement. PR #50 still needs the introduction-path and legacy provenance decisions; PR #49 retains an unresolved review thread. PR #48's current exact-head CI is green, but integrated release gates and independent review remain required. The current GitHub API reports `main` as unprotected (`protected: false`, required status checks off). No real WAHA action was performed; private-media retention remains OFF.


## Engineering gates (mechanical — re-verify every run)

- [x] Full migration chain (001 → latest) applies cleanly from an empty database
- [x] Full pytest suite green
- [x] Coverage at or above the repository gate (57%; currently 75.12%)
- [x] DB leakage = 0 across all `CLEANUP_MODELS`/`CLEANUP_RAW_TABLES` tables
- [ ] **No unresolved P0 outbound-authority gaps.** Issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open: exact-contact consent/opt-out must be authoritative and checked at final dispatch, with revocation serialized against the transport attempt.
- [x] No duplicate outbound delivery paths (single fail-closed fence, confirmed)
- [x] No unsafe blind retries on uncertain delivery
- [x] Exactly one router, one scheduler, one tool dispatcher (confirmed, no duplicates found)
- [x] Exact-head CI green on `main`

## Product/architecture gates (real work remaining)

- [ ] **Command Center governs all commands.** `ReplyRule` currently absorbs owner-created custom commands (`/create-command` writes to `ReplyRule`, not `CommandCatalogEntry`) — this must be fixed before commands are "discoverable and governed" in the way the mission requires. See roadmap Phase 5.
- [ ] **P0 contact consent/opt-out is authoritative and race-safe.** Add exact-contact/chat consent state with provenance and auditable revocation; unknown/revoked consent and opt-out must suppress sends even with an OWNER policy or one-use approval unless a separately reviewed re-consent rule is adopted. Enforce it in the final worker fence with revocation/dispatch race semantics. See issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56).
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
