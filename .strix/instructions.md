# Zina Strix Authorized Security Scope

You are performing a defensive security assessment of Zina, Fabian's own WhatsApp assistant.

## Authorized target

- Only the checked-out `Fabian121-ux/DatacubeAU_com.bot` repository content supplied as the Strix target.
- The scan target is the repository root on an ephemeral CI runner so application code under `bot_core/` and repository-level dependency, Docker, Compose, environment-template, deployment and CI configuration can be reviewed together.
- Synthetic/local test execution created from this checkout is permitted when Strix needs it for validation.

## Explicitly out of scope

Do not scan, connect to, probe, enumerate, exploit, brute-force, or send test traffic to:

- production Zina services, production databases, or production WAHA sessions;
- real WhatsApp accounts, chats, contacts, groups, or WhatsApp infrastructure;
- WAHA public infrastructure;
- OpenAI, OpenRouter, GitHub, or other third-party services;
- arbitrary domains, IP addresses, localhost services not created from this checkout, or any network target not explicitly supplied as a dedicated Zina staging target.

Do not perform destructive data deletion, persistence/backdoors, credential harvesting, real-secret or PII exfiltration, denial-of-service/load flooding, or lateral movement.

## Priority review areas

Prioritize webhook authentication/session binding, USER/ADMIN/OWNER authorization, owner self-DM authority, Tool Dispatcher bypass, IDOR, SSRF, SQL/command/template injection, replay/idempotency bypass, unsafe media/file handling, path traversal, secrets exposure, insecure admin/config mutation, contact/chat data leakage, deleted-message lifecycle privacy, rate-limit abuse, dependency risk, and container/runtime misconfiguration.

## Evidence and remediation

For each finding, distinguish validated exploit evidence from a static hypothesis. Prefer minimal proof-of-concept validation using only local/synthetic data. Do not apply autofixes directly. Report affected component, likely CWE/OWASP class, severity, impact, confidence, reproduction evidence, and remediation so a separate reviewed patch can add regression coverage.
