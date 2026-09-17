# Contributing to DIXpertIA

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
5. **Request a review from @Ihebdhouibi on every pull request.**
   `.github/CODEOWNERS` does this automatically, but check that it happened.
6. **Do not merge your own pull request without his approval.**
7. **Never commit or push directly to `develop` or `main`.**

## Branch model

| Branch | Purpose |
|---|---|
| `develop` | Integration branch. All feature, fix and chore PRs target it. |
| `main` | Release branch. Updated from `develop` by @Ihebdhouibi only. |

`main` and `develop` are currently divergent — `main` is 1 commit ahead,
`develop` is 13 ahead. This should be reconciled before the next release.

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

## A note on enforcement

Nothing in this repository currently *prevents* a direct push to `develop` or
`main`, and nothing blocks a merge without approval. These files make the rule
visible and automatic; they do not make it binding.

Making it binding requires branch protection on `develop` and `main`
(*Require a pull request before merging* + *Require 1 approval*), which only
@Ihebdhouibi can enable.

## Stack

- **Frontend** — React 19, Vite, Tailwind CSS v4 (`src/`). Design tokens live
  in `src/index.css`.
- **Backend** — FastAPI, SQLAlchemy, Alembic (`app/`, `main.py`), proxied from
  Vite at `/api`.
