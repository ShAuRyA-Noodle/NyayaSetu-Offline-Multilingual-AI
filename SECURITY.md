# Security Policy

## Supported Versions

NyayaSetu is currently in its first public release line. Only the most recent
1.x release line receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

If you are running a fork or a pre-1.0 build, please upgrade before reporting.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security problems.**

Please email **security@nyayasetu.example** with:

- A clear description of the vulnerability and its impact.
- Reproduction steps or a proof-of-concept (no live exploitation against
  production users).
- The commit SHA / Docker image tag you tested against.
- Your suggested CVSS severity, if you have one.

> TODO: replace `security@nyayasetu.example` with the project's real
> security contact once the domain is provisioned. Until then, you may also
> contact the maintainers directly via the GitHub repo.

### PGP

A PGP key for encrypted reports will be published here once the security
contact is finalized.

> TODO: PGP fingerprint goes here.

## Disclosure timeline

We follow a **coordinated 90-day disclosure** model:

| Day | Event |
| --- | --- |
| 0   | Report received; we acknowledge within 72 hours. |
| 1–7 | Triage, severity assessment, reproduction. |
| 7–60 | Fix developed, reviewed, and tested. |
| 60–90 | Fix released; advisory drafted. |
| 90   | Public disclosure if not already coordinated. |

If a fix lands sooner, we publish sooner. If a fix needs more time and the
reporter agrees, we extend.

## Scope

In-scope:

- The FastAPI backend in `src/api/` and its routes.
- The auth + session layer (JWT, bcrypt, rate limiting).
- The RAG / generation pipeline (`src/core/`, `src/generation/`).
- The voice engine (`src/modules/nyayavaani/`).
- The frontend in `desktop/src/` (XSS, auth handling, token leakage).
- Default deployment configuration (Dockerfile, docker-compose,
  HF Spaces / Vercel templates).

Out of scope:

- Third-party services (Groq, Sarvam AI, Neon, Vercel, Hugging Face) —
  report those to the respective vendors.
- DDoS / volumetric attacks — handled at the Cloudflare / hosting layer.
- Issues that require a compromised end-user device.
- Denial-of-service via free-tier resource exhaustion (the deploy is
  intentionally on free tiers; that is a known trade-off).

## Safe harbor

Good-faith security research is welcome. As long as you:

- Do not access data you do not own,
- Do not degrade service for other users,
- Give us reasonable time to fix before public disclosure,

we will not pursue legal action and will credit you in the advisory if you
wish.
