# Contributing to DI Xpertia

## One ticket, one branch, one pull request

Every GitHub issue is handled in its own branch and lands through its own pull
request. No exceptions.

1. **Branch from `develop`**, never from `main`.
2. **Name the branch after the ticket**, following the existing convention:
   `feature/<slug>`, `fix/<slug>` or `chore/<slug>`.
   Example: issue #23 → `feature/ink-signal-lime-tokens`.
3. **One ticket per branch.** Do not bundle unrelated issues together, even
   when they touch the same files.
4. **Open the pull request against `develop`.** Write `Closes #<issue>` in the
   body so the ticket closes automatically when the PR is merged.
5. **Request a review from @Ihebdhouibi on every pull request.** This is
   manual: automatic code-owner review requests are not available for private
   repositories on the free plan. Use the *Reviewers* box when opening the PR,
   or `gh pr create --reviewer Ihebdhouibi`. When @Ihebdhouibi opens a PR
   himself, request the review from another team member.
6. **Do not merge your own pull request without his approval.**
7. **Never commit or push directly to `develop` or `main`.**

## Branch model

| Branch | Purpose |
|---|---|
| `develop` | Integration branch. All feature, fix and chore PRs target it. |
| `main` | Release branch. Updated from `develop` by @Ihebdhouibi only. |

`main` and `develop` have diverged: each contains commits the other does not.
Reconcile them before the next release. Check the current state with
`git rev-list --left-right --count origin/main...origin/develop`.

## Recording work on tickets

The trail lives in GitHub, not in private conversations:

- **When you start** — comment on the issue saying work has begun, and on
  which branch.
- **When you finish** — the pull request references the issue with
  `Closes #<issue>`, so merging closes it and links the work.
- **If a ticket is closed without a merge** (duplicate, obsolete, rejected) —
  comment with the reason first. Never close a ticket silently.

Anything you discover that changes a ticket's scope belongs in a comment on
that ticket.

## Conventions

- Issues, pull requests, commit messages and code comments are written in
  **English**.
- Commit messages use the prefixes already in the history: `feat:`, `fix:`,
  `chore:`, `design:`.

## Team

| GitHub | Role |
|---|---|
| @Ihebdhouibi | Admin — reviewer on every PR, owns releases to `main` |
| @abirchebbi45 | Write |
| @OmaymaAbdessamed | Write |

## Before you push

- Run `pre-commit install` once after cloning (see `.pre-commit-config.yaml`),
  so ruff and the repository hooks run on every commit.
- Every pull request runs the `lint` workflow (`.github/workflows/lint.yml`):
  ruff, the no-emoji check on Python files, `tsc --noEmit`, and the pre-commit
  hygiene hooks (trailing whitespace, final newline, YAML/JSON validity,
  private keys) on the files the PR changes. Fix any failure before asking for
  a review.

## A note on enforcement

Nothing in this repository *prevents* a direct push to `develop` or `main`, and
nothing blocks a merge without approval or with a failing check. Branch
protection and rulesets are not available for private repositories on the free
plan (GitHub returns "403 Upgrade to GitHub Pro"; see the header of
`.github/workflows/lint.yml`).

These rules therefore hold by team agreement. If the plan is upgraded, protect
`develop` and `main` with *Require a pull request before merging*, *Require 1
approval* and the `lint` jobs as required status checks.

## Stack

- **Frontend** — React 19, Vite, Tailwind CSS v4 (`src/`). Design tokens live
  in `src/index.css`.
- **Backend** — FastAPI, SQLAlchemy, Alembic (`app/`, `main.py`), PostgreSQL,
  proxied from Vite at `/api`.
