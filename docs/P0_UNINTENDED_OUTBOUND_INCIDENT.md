# P0 unintended outbound incident

Status: **containment required; live WhatsApp sending must remain disabled until the authorization fence is implemented and validated.**

## Proven repository evidence

Current `main` is `10773193bbf11bd4238583825a9f31cd45904776`.

The current authenticated WAHA gateway accepts both `message` and `message.any`. It builds one durable idempotency key from session/chat/message ID, so duplicate deliveries with the same identifiers are intended to collapse. `fromMe` traffic is split into owner-control handling and Zina-originated echo rejection.

The critical unsafe default is in `bot_core/app/core/router.py`: for an external inbound DM, `wait_for_fabian_first` depends on `ConversationTakeoverService.should_wait_for_fabian_first()`. When that returns false, a planned reply is assigned delivery policy `immediate`, an `OutboundMessage` is created with status `pending`, and the router reports the reply as queued. Therefore the current architecture does **not** require an OWNER approval or per-contact automation policy before ordinary external replies become deliverable.

The router can also start WAHA typing presence before planning when `wait_for_fabian_first` is false. Typing presence is therefore currently coupled to the old immediate-response policy rather than to a durable outbound authorization decision.

`message.any` is required by the current owner-control design so owner-authored `fromMe` commands can reach Zina. Removing it blindly would regress `.push`, `.dm`, owner natural actions and lifecycle behavior. The fix must classify events and enforce outbound authority rather than simply removing `message.any`.

## Not yet proven

The repository evidence inspected so far does **not** prove which exact event caused the reported fan-out, nor that WhatsApp restricted the account specifically because of Zina. In particular, this investigation has not yet proven that read receipts were delivered to the subscribed gateway as `message`/`message.any`, that a quoted historical message was normalized as a fresh inbound message, or that a retry/scheduler path duplicated a send. Those remain hypotheses until payload/audit evidence or a deterministic regression reproduces them.

## Required containment design

Normal external contacts must become approval-only by default:

`authenticated WAHA event -> classify genuine new external inbound -> durable idempotency -> persist/draft -> pending OWNER approval -> final authorization fence -> existing Outbound Queue -> WAHA`

The final delivery boundary must reject a non-system outbound row unless one of these durable authorities is present and valid:

1. exact single-use OWNER approval bound to source message, exact recipient and approved content/version;
2. explicit OWNER command/capability invocation bound to the exact target/action; or
3. active OWNER-created Contact Automation Policy for the exact durable contact identity and allowed response category.

Contact automation is opt-in per exact contact. Display-name-only authorization is forbidden. Disabled, expired, ambiguous, stale, duplicated or mismatched authority fails closed.

## Event rules

These events/states must never create an autonomous normal reply: read receipt, delivery receipt, typing/presence, status update, revocation, `fromMe` owner message, Zina outbound echo, duplicate `message`/`message.any`, and historical quoted/reply snapshots. Quote metadata may identify context but must never itself become fresh conversational intent.

## Live safety

Do not validate this incident fix against the restricted real WhatsApp account or real contacts. Use unit/integration fixtures and isolated local/test containers. Preserve database/audit/session evidence; do not delete rows or WAHA state as a shortcut.

## Required regression gate

Before review-ready, tests must prove: non-message events do not draft/send; `fromMe` and Zina echoes do not reply; duplicate webhook events do not duplicate; ordinary external inbound creates approval-only state; no WAHA send occurs before exact OWNER approval; approval is single-use/idempotent/expiring/target-bound; USER/ADMIN cannot approve OWNER actions; exact-contact automation policies are opt-in and category-bounded; disabled/expired policies block; the Outbound Queue delivery worker independently rejects unauthorized rows; scheduler/retry/reconciliation cannot bypass the fence; `.push`/`.dm` exact OWNER flows remain valid; formatting preserves WhatsApp blockquotes/backticks/italics; typing presence starts only after authorization and always stops on completion/error/timeout.

## Next implementation slice

Implement the durable approval/contact-policy schema and the final Outbound Queue authorization fence first. Then change the ordinary inbound router from `immediate` to approval-only and move typing presence behind successful authorization. Only after targeted tests, the full migration chain and full pytest/coverage are green should live reconnection be considered.