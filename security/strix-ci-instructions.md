# Zina Strix CI Rules of Engagement

## Authorized target

The only authorized target for this run is the checked-out source tree of `Fabian121-ux/DatacubeAU_com.bot` inside the ephemeral GitHub Actions runner.

Do not target, probe, crawl, authenticate to, or send exploit traffic to any live URL, IP address, external hostname, WhatsApp service, WAHA deployment, GitHub service, OpenAI/OpenRouter service, production Zina service, production database, real WhatsApp account, or third-party system.

## Scan intent

Perform a bounded white-box security review of the local Zina code diff against `origin/main`. Focus on security-relevant code paths and configuration, especially:

- WAHA webhook authentication and configured-session binding
- owner/admin/user command authorization and self-DM authority
- Tool Dispatcher permission enforcement and bypass resistance
- replay/idempotency and stale-claim generation fencing
- IDOR and cross-contact/chat data leakage
- SSRF, SQL injection, command injection, path traversal, unsafe redirects
- unsafe file/media handling and deleted-message lifecycle privacy
- secrets exposure and unsafe configuration mutation
- admin API authentication, XSS/CSRF where applicable
- dependency/container/runtime misconfiguration
- rate-limit and resource-abuse risks that can be assessed without load testing

## Prohibited actions

Do not perform destructive data deletion, denial-of-service or load flooding, credential harvesting, secret exfiltration, persistence, backdoors, lateral movement, brute-force attempts, external network scanning, or exploitation outside the local ephemeral sandbox.

Do not use any discovered credential, token, URL, phone number, or secret to connect to a real service. Treat configuration values and fixtures as evidence for code review only.

Do not modify the repository automatically. Report findings only. Any remediation must be reviewed separately, implemented through Zina's existing architecture, covered by regression tests, and submitted in a dedicated PR.

## Reporting expectations

For each finding, provide severity, confidence, affected file/component, CWE/OWASP category when possible, local reproduction evidence, impact, and recommended remediation. Clearly distinguish validated local findings from hypotheses that require a separate authorized staging test.
