# Dev-deploy sandbox credentials

Synthetic identity seed accounts for local and labeled sandbox/dev deploy only.
Not production. Never use these passwords on a live payment or customer system.

Set `IDENTITY_DEMO_PASSWORD=demo-password` before `sentinel-identity seed` / serve so
hashes match this table. Web login UI lists the same accounts.

| Email                   | Password      | Portal role      |
| ----------------------- | ------------- | ---------------- |
| customer@example.test   | demo-password | Customer         |
| merchant@example.test   | demo-password | Merchant         |
| operator@example.test   | demo-password | Support Operator |
| supervisor@example.test | demo-password | Supervisor       |
| risk@example.test       | demo-password | Risk Officer     |
| admin@example.test      | demo-password | Platform Admin   |

## Non-loopback bind

Demo passwords and identity session projection refuse `0.0.0.0` / public binds by
default. For a labeled sandbox VM (AWS Lightsail/EC2 free-tier demo):

```sh
export SENTINEL_SANDBOX_PUBLIC_BIND=1
export IDENTITY_DEMO_PASSWORD=demo-password
export IDENTITY_SANDBOX=1
export SENTINEL_V1_SANDBOX=1
```

Copy [`.env.example`](.env.example) to a host-local `.env` (gitignored). Do not commit
real secrets. Rotate or disable these accounts before any external pilot.
