# Security policy

## Supported version

Only the latest commit on the default branch is considered for security fixes.
This is a research prototype, not a production farm-control or plant-diagnosis
service.

## Report a vulnerability

Use GitHub's private vulnerability-reporting interface for this repository
rather than opening a public issue. Include the affected endpoint or file,
impact, reproduction steps, and a minimal proof of concept. Do not include real
farmer data, credentials, or harmful payloads.

## Known deployment boundary

The default setup is intentionally convenient for a localhost demonstration:

- there is no end-user authentication or tenant isolation;
- `IRIS_DEVICE_TOKEN` is optional in demo mode;
- mutating demo, water, leaf, confirmation, and assistant endpoints are not a
  production authorization boundary;
- chat content and derived image/plot metadata are stored in SQLite;
- no production rate limiter or retention/deletion workflow is included; and
- the optional external assistant sends configured prompts and images to the
  selected model provider.

`IRIS_DEMO_MODE=1` (the default) allows the interactive demo. With
`IRIS_DEMO_MODE=0` the application refuses to start when `IRIS_DEVICE_TOKEN`
is empty, and interactive plot/leaf/chat/confirmation routes return
`403 non_demo_user_auth_required` because the production authentication layer
is not part of this research prototype. There is no supported Internet-facing
deployment mode.

Do not expose the default API to an untrusted network. Before deployment,
disable demo mode, require and rotate strong secrets, add user authentication
and authorization, terminate TLS at a trusted reverse proxy, restrict CORS,
limit request rates and body sizes, define data retention and deletion, secure
backups, review provider privacy terms, and complete a deployment-specific
threat model.

Never commit `.env`, databases, uploaded images, production logs, access
tokens, or exported farmer records. If a secret is exposed, revoke or rotate
it first; deleting it in a later commit is insufficient because Git history
retains earlier content.
