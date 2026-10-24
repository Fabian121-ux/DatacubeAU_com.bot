# Zina Release Checklist

What remains before Fabian can begin controlled real-world WhatsApp testing (see `docs/ZINA_IMPLEMENTATION_ROADMAP.md` for the full per-domain detail behind each line here, and `docs/ZINA_CONTROLLED_TEST_PLAN.md`, once written, for the staged test procedure itself).

Last full phase-by-phase audit: 2026-09-08, against `main` @ `0034587a90bb8d5a79bda41e85091cfea33b969d`. The dated branch-state snapshot below is partial, not a fresh full release audit.

## Current branch-state snapshot — 2026-10-24 (not a full phase-by-phase audit)

The last full roadmap/checklist audit above is historical. The live `main` branch is still `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, with migrations 001–033. Its latest `Tests` push run is [34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390), successful on 2026-09-08. The checkboxes below must not be treated as fresh release approval, and open feature branches are not part of `main`.

Current open feature PRs and exact-head evidence:

- **[#48](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/48)** current head `02aeabc937e8d38070748bb3adbcb9d7f6bf166f`: [Tests run 40094090968](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40094090968) succeeded on 2026-10-24. The run metadata available in this audit does not expose a test count or coverage percentage. Beyond exact WAHA-origin/path validation and hostile-locator regressions, the latest head binds the quoted source chat/message and OWNER command ID into the approval digest, serializes conflicting source replays, rejects a missing command ID before queue/artifact creation, and reports partial artifact cleanup truthfully. The branch remains unmerged and requires independent review.
- **[#49](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/49)** head `bcd0033e024b177561b8afd41589afe1897ba4de`: [Tests run 39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) succeeded — 896 passed, 76.67% coverage; this branch applies 001–033 and 036–037, not 034/035. Fresh review-thread inspection finds 80 total threads and exactly 1 unresolved thread, concerning reservation of retired `set_key` values across hard deletion; the other 79 threads are resolved, including outdated historical findings. Do not treat green CI as independent approval; resolve the remaining current finding before integrating the library.
- **[#50](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/50)** head `40f5139cb6c0dbfcee3e26771a06dafa0850bf62`: [Tests run 34312518958](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34312518958) succeeded — 820 passed, 76.44% coverage on 2026-09-09. Two architectural review threads remain unresolved: introduction paths bypass disabled/deleted identity state, and `updated_at = created_at` cannot reliably identify every legacy default for provenance backfill.
- **[#55](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/55)** draft head `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2`: [Tests run 40010785239](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40010785239) succeeded — 814 passed, 76.01% coverage; schema and post-test database-leakage audits passed.
- **[#57](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/57)** draft exact head `492bfdeb056da11cb83b50a9472928fe5c937bd5`: [Tests run 40108792756](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40108792756) succeeded on 2026-10-24. The current runner accepts the exact local `zina_disposable` target or a CI-only `zina_seed_policy_*` name tied to the active GitHub run/attempt, and rejects broad `test_*`/`dev_*` names. This run's summary does not expose a test count or coverage figure, so figures from the prior head are not carried forward.
- **[#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60)** draft head `dff7b67e4ed76f4442725ecb350a384ff0bbec51`: exact-head [Tests run 40138283407](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40138283407) completed successfully; migration application and pytest-with-coverage passed, including the configured 57% coverage gate. The API summary does not expose exact test count or coverage percentage. This commit adds a locked predicate requiring the Contact's current `whatsapp_id` or `chat_id` to match the exact recipient and worker regressions for inbound-reply and scheduled-action rows remapped after queue creation; both assert zero mocked WAHA calls. The branch applies 001–033 plus 038 only, not the combined 034–038 chain. Independent review remains required.
- **[#61](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/61)** head `180852b98c8b1bcb2072c1e4d0bc6e1a4ebccf7d`: [Tests run 40125154693](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40125154693) succeeded — 798 passed, 1 warning, 76.01% coverage on migrations 001–033. It adds a CI test requiring unique, contiguous migration numbers from 001 and is ready for independent review, not merged.

Migration numbering is structurally unique across the current feature branches: #48 uses 034, #50 uses 035, #49 uses 036–037, and #60 uses 038; `main` remains at 001–033. PR #61 adds a proposed CI guard requiring contiguous migration numbers on each PR merge ref; its current-head CI is green on 001–033, but it is not merged. Temporary integrated validation head `8a2e6cc604f9d744d0f95a9126360b0a4364db9f` passed [run 39940318940](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39940318940): fresh 001–037, installed upgrade 033→037, 956 tests, 77.24% coverage, and zero DB leakage. That evidence is stale for the latest PR #48 head and predates migration 038. A new integrated run must use the exact current heads, apply 001–038 from empty, upgrade 033→038 on an installed-schema fixture, rerun the migration runner to prove checksum/no-op behavior, run the full P0 adversarial matrix, and verify zero DB leakage. It must also settle PR #50's unresolved legacy provenance policy.

**Current release state: NOT TEST READY.** P0 issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open pending independent review and integrated validation. PR #60 is at head `dff7b67e4ed76f4442725ecb350a384ff0bbec51`; exact-head run [40138283407](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40138283407) completed successfully, with migration and pytest-with-coverage steps passing and the 57% coverage gate green. The job metadata does not expose the exact test count or coverage percentage. Its new mapping-fence regressions cover inbound and scheduled sources and assert zero mocked WAHA calls; the branch still tests migrations 001–033 plus 038 only. PR #61's migration-sequence guard is green on 001–033 but not merged; a fresh combined 001–038 run, installed 033→038 upgrade, current P0 adversarial matrix, and DB-leakage audit are still required. PR #50 still needs the introduction-path and legacy-provenance decisions; PR #49 has one unresolved review thread; PR #48's exact-head CI is green but integrated release gates and independent review remain required. `main` remains unprotected. No real WAHA action was performed; private-media retention remains OFF.


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
