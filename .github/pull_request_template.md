<!--
Thanks for contributing to NyayaSetu! Please fill out the sections below.
For security-sensitive changes, see SECURITY.md before opening this PR.
-->

## Summary

<!-- 1–3 sentences: what does this PR change, and why? Focus on the *why*. -->

## Type of change

- [ ] feat — new user-visible feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] chore — tooling / repo plumbing
- [ ] refactor — internal change, no user-visible delta
- [ ] test — tests only
- [ ] perf — performance work
- [ ] BREAKING CHANGE (explain in summary)

## Linked issues

<!-- e.g. Closes #123, Refs #456 -->

## How was this tested?

<!-- Specific commands or steps. "Looks good on my machine" is not enough. -->

- [ ] `python tests/test_db_parity.py` passes
- [ ] `cd desktop && npm run build:web` passes
- [ ] Manual: <describe>
- [ ] CI green

## Screenshots / recordings

<!-- For any user-visible UI change. Before / after if possible. -->

## Checklist

- [ ] Branch name follows `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`,
      `test/`, or `perf/` convention.
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- [ ] No secrets, real PII, or real grievances are committed.
- [ ] Updated relevant docs (`README.md`, `CHANGELOG.md`, `docs/RUNBOOK.md`).
- [ ] If this introduces a DB migration, it's idempotent and tested against
      both SQLite and Postgres.
- [ ] If this touches the auth / security path, I have re-read
      [SECURITY.md](../SECURITY.md).
