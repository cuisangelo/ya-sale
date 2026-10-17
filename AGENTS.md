# AGENTS.md — Kekero

Rules for any coding agent working in this repo. Event facts (schedule, submission, rubric,
credits) live in [GUIDE.md](GUIDE.md); read it before planning work.

## Context

- Hack the Andes, Lima, 17–18 Oct 2026. Team **Kekero**, solo (Cuisangelo), track
  **Movilidad y Transporte** (`transport`): Lima public transit (routes, connections, times,
  accessibility) and regional passenger, connectivity, cargo and distribution.
- **Hard deadline: Sunday 18 Oct, 09:00 (America/Lima)** via `andes project submit`. When the
  organizers open judging they snapshot the submission; later changes don't reach the jury.
- The jury opens the deployed URL from the organizers' machine and reviews this GitHub repo.
  What scores: the full flow works live from the public URL, real users outside the team
  with evidence in logs or data, and readable code.

## Priorities

Time beats polish. In order:

1. A deployed, public, working end-to-end flow. It must work in a private window, without a
   logged-in session, pending permissions or local files. localhost, mockups and videos
   don't count.
2. Real usage evidence (logs, data, waitlist).
3. Code quality the jury can read.

Ship the smallest thing that demos the core flow, then iterate. No speculative abstractions,
no features nobody asked for, no future-proofing. If a request is needlessly complex, say so
and offer the minimal variant.

## Engineering rules

- **Fail loud.** One correct path. No silent fallbacks, no defaults that hide misconfiguration
  (`process.env.X ?? throw`, not `|| "default"`). Validate at system edges only.
- **Surgical changes.** Touch only what the task needs and match the existing style. No
  drive-by refactors or reformatting.
- **Comments say why, never what.** No dates or ticket IDs in source; that context goes in
  commit bodies.
- **Dependencies:** don't add one if under ~50 lines of direct code would do.
- **Tooling:** `pnpm` for JS/TS and `uv` for Python, never npm, yarn or raw pip. If the repo
  gets a `Dockerfile` or `compose.yaml`, run commands inside the container.
- **Language:** all code, identifiers, comments, docstrings, log messages and commits are in
  English, always, even when the user writes in Spanish. Spanish is only for human-facing docs
  (GUIDE.md, README, pitch, `andes project` updates and description) and end-user UI copy.

## Architecture and code quality

The jury reviews this repo, so its structure is part of the score. Keep it simple, but keep it
clean.

- **Repo structure:** organize code by feature or domain (e.g. `routes/`, `stops/`, `trips/`),
  not by file type. Inside each one, keep these apart:
  - **domain:** pure logic, no I/O;
  - **application:** use cases that orchestrate the domain;
  - **infrastructure:** HTTP handlers, DB, external APIs, LLM calls.

  Shared config, env loading and logging live in one place each.
- **Dependencies point inward.** Domain code never imports frameworks, SDKs or the DB client.
  Infrastructure depends on the domain, never the reverse.
- **SOLID, applied pragmatically:**
  - **Single responsibility:** one reason to change per module or function. No god files.
  - **Open/closed:** add a new data source or provider by adding a module, not by editing
    `if` chains spread across the code.
  - **Liskov:** every implementation of an interface honors its contract and raises the same
    error types.
  - **Interface segregation:** small interfaces that expose only what the caller uses.
  - **Dependency inversion:** inject dependencies through constructors or function parameters,
    with no hidden globals or singletons, so tests can swap them.
- **Patterns only where they earn their place:**
  - **Adapter:** one per external data source or API (GTFS, transit APIs, maps, WhatsApp/Zavu,
    LLM providers), behind a domain-level interface.
  - **Repository:** for persistence, so use cases never build queries.
  - **Strategy:** only once there are two or more real interchangeable algorithms (e.g. route
    ranking).
  - **Factory or composition root:** a single place that wires concrete implementations.

  No pattern for a single implementation with no external boundary. Three similar lines beat
  a premature abstraction.
- **Typed boundaries:** validate input at the edges (request schemas, env, external responses)
  with typed models, and pass typed objects inside, not raw dicts or `any`.
- **Errors:** domain-specific error types, mapped to HTTP status codes in one place. Never
  swallow exceptions.
- **Tests:** cover the domain and use-case logic with fast unit tests that use fake adapters.
  Write integration tests only for the critical demo flow.
- **README:** keep a short Spanish run section: requirements, env vars (names only), how to
  run, how to deploy and the live URL.

## Ask vs. decide

Ask one concrete question only when the ambiguity affects the product's core flow, the data
model or anything irreversible (deletes, deploys, renames of public resources). For internal
details, pick the simplest option, state the assumption in one line and keep going.

## Bitácora

[BITACORA.md](BITACORA.md) is the project log. Keeping it current is part of every task, not
an afterthought.

- **When:** append an entry as each step lands:
  - a code change worth noting;
  - a decision and its alternatives;
  - a test or experiment and its result, including failures;
  - a blocker;
  - a deploy;
  - an `andes project` submission or update.

  Don't log every trivial commit.
- **Format:** newest first, under the day's `## YYYY-MM-DD` heading:
  `### HH:MM · <Tipo> · <title>`, using Lima time and one of Cambio, Decisión, Prueba,
  Bloqueo, Deploy or Entrega. The body says what, why and evidence (commit SHA, command and
  its real output, URL). Write it in Spanish.
- **Facts only:** record what actually ran and what it returned. A failed test is logged as
  failed. Never log secrets, credit codes or personal data.
- Commit the entry together with the change it describes. It is the raw material for
  `andes project update` posts and for the pitch.

## Git

- Work in a worktree (`.claude/worktrees/<slug>`, ignored by git), never in the main checkout.
  Branches use `feat/`, `fix/`, `chore/` or `docs/` plus a slug.
- **Commit and push straight to `main` without asking.** This repo is the exception to "only
  commit when asked". One logical change per commit. From a worktree branch:
  `git fetch origin && git rebase origin/main && git push origin HEAD:main`, so `main` only
  moves fast-forward.
- **Open a PR only when parallel sessions** work on the repo at the same time. Each one works
  on its own branch, and the PR is how its work joins `main`.
- Commit format: `<gitmoji> <type>[(scope)]: <subject>`, English, imperative, ≤72 chars. Add a
  body (3–5 lines) only when the why isn't obvious.
  Common gitmoji: ✨ feat · 🐛 fix · ♻️ refactor · 🔧 config · 📝 docs · 🚀 deploy · 🙈 gitignore
  · ➕ add dependency · 🔥 remove.
- No attribution anywhere: no `Co-Authored-By` trailers, no "Generated with" footers.
- Never force-push and never rewrite `main`'s history.

## Secrets: this repo is public

- Never commit API keys, tokens, `.env` files, sponsor credit codes, Wi-Fi passwords or
  personal user data. Use `.env` (ignored) and commit a `.env.example` with names only.
- Read config from env vars and fail at startup if a required one is missing.
- The same applies to `andes project update` and the project description: they're shown to
  mentors, the jury and the public gallery.

## Hack the Andes CLI (`andes`)

- Use `--output json` and put it before the subcommand: `andes --output json project submit …`.
  Treat the server response as the source of truth.
- `andes project update --message "…"` posts to the shared log. Post after a key decision, a
  user test, a working demo or a blocker. Say what changed, why and what's next, using only
  verifiable facts. Don't narrate every commit.
- `andes project submit` takes `--deployment-url`, `--presentation-url`,
  `--github-url https://github.com/cuisangelo/Kekero` and `--description` or `--file`. Omitted
  fields keep their saved values. Submit early, then correct.
- Show the user the exact payload and get an OK before the first `project submit` or any
  change to a submitted field. Routine `project update` posts and read-only commands need no OK.
- Never run `andes team leave`: the team is a single person and leaving dissolves it.

## Done means verified

A claim is earned by running the source of truth, not by reading code.

- **"It works":** open the deployed URL in a clean session or `curl` the endpoint and check the
  response. A local test run is not enough.
- **"It's deployed":** check the platform's deploy status and then hit the live URL. A
  successful build doesn't mean the endpoint is live.
- **"It's submitted":** `andes --output json project` shows the saved fields.
- **"My commit landed":** `git ls-remote origin <branch>` or
  `git merge-base --is-ancestor <sha> origin/main`.

Report outcomes faithfully. If something failed or was skipped, say so with the output.
