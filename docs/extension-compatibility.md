# Extension context compatibility

## Scope

CLM contributes its protocol and steering through the native
`live_context_management` prompt section when Pi exposes mutable sections. Older hosts
retain the existing string-return fallback. Restored context views exclude Pi-owned
system messages so checkpoint validation uses the same conversation space as the
`context` hook.

A whole `systemPrompt` return is an intentional replacement on modern Pi, not an
additive contribution. CLM does not clear another extension's override, rewrite its
handlers, or relax checkpoint digests to mask a mismatch.

## Companion extensions

- `@henryqw/pi-add-dir@3.1.1` already uses the native `pi_add_dir` section. It accepts
  the older `add-dir:state` directory entries. No source patch is required for the
  prompt-composition issue. Its commands are `/dir-add`, `/dir-ls` and `/dir-reload`;
  `add_directory` is model-only, while file search has structured codemode results.
- The open-codebase-index fix belongs in that project's
  `src/adapters/shared/extension-core.ts`: contribute workflow guidance through
  `codebase_index_guidance` and retain its older-host fallback. Build its checkout
  before testing or loading `dist/pi-extension.js`.
- The older unscoped `pi-add-dir@1.3.1` and index `0.36.3` release can still freeze
  later instructions. Updating only CLM is not a complete rollout. Do not load an npm
  release and its local checkout together.

Companion patch artifacts are intentionally not maintained in this repository; each
project should carry its own source change and tests.

## Reproducible wire check

See `docs/development.md` and `scripts/check-extension-context.py`. Select the Pi
executable explicitly: pnpm normally prepends the locally pinned Pi to PATH. The check
reports the actual runtime and uses isolated configuration, a local Responses endpoint,
and scripted answers instead of paid model calls.

Repeatable `--extension` options test every load order. `--without-clm` supplies a native
Pi baseline; `--require-guidance` asserts additional companion instruction markers.
The default checks preserve structured/append guidance, the CLM protocol and CLM tools.
Marker presence is a deterministic fixture assertion, not a semantic completeness claim.

## Validation and remaining limits

The CLM regressions are tested against pinned Pi 0.85.0; real request construction was
also checked on Pi 1.0.3 and 1.1.0. With the Henry fork and rebuilt index checkout, all
24 load orders / 72 HTTP requests retained the five expected instruction markers.
A separate real RPC fixture covered model-issued mirror compression, `/clm-compact`,
native compaction, clone isolation, fork inheritance, tree restoration and parent-session
restoration. Native summarizers intentionally use their own instructions rather than
the ordinary agent prompt. These controls test lifecycle/request integrity, not model
summary quality or arbitrary third-party behavior.

- A varying `context` transform before CLM can still invalidate its exact-prefix
  checkpoint, even when only an injected timestamp changes. Prefer CLM before those
  transforms; do not ignore unmatched source prefixes.
- Continuity ordering (upstream issue #1 / PR #7) is separate and is not changed by this
  patch. The reviewed PR keeps managed continuity leading in CLM mode; it does not
  guarantee every provider cache continuation.
- Prompt-only usage accounting (PR #8) is a separate budgeting correction. Existing
  contributor PRs are not duplicated or bundled into this compatibility change.
- Clean reload/resume controls and the snapshot fix do not establish the cause of every
  reset reported in issue #9.
- The index checkout's full suite was not entirely green: watcher assertions also failed
  on untouched HEAD, and a setup timeout passed in isolation. Successful adapter/wire
  checks are not a waiver of the companion project's full validation gate.
