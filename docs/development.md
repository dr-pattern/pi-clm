# Development

Node 22+ and pnpm through corepack. The Pi packages are peer dependencies, provided by
the Pi installation that loads the extension; the dev dependencies pin one version for
typechecking and tests.

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm check      # strict typecheck + tests
```

## Running a checkout in Pi

For one session:

```sh
pi -e /path/to/pi-clm/index.ts
```

Or install the checkout in place, so edits apply on the next `/reload`:

```sh
pi install /path/to/pi-clm
```

Do not load pi-clm together with the original live-context extension; they share
session entry types.

## Wire-level extension compatibility check

The default `check` runs against pinned Pi 0.85.0. The optional wire check reports its
selected runtime. Under pnpm, `pi` usually resolves to the locally pinned executable;
select an absolute executable path to test a separately installed Pi (such as 1.0.3):

```sh
corepack pnpm check:compatibility --pi /absolute/path/to/pi
# Explicitly use the pinned executable to verify the legacy fallback:
corepack pnpm check:compatibility --pi ./node_modules/.bin/pi
# Compare a native-Pi baseline with CLM omitted:
corepack pnpm check:compatibility --pi /absolute/path/to/pi --without-clm
```

This opt-in check needs Python 3.8+ (stdlib only) and the selected Pi executable. It runs
isolated CLI subprocesses with only this checkout and a minimal instruction injector,
tests both load orders over three user turns, and checks the final serialized HTTP
requests received by a local Responses fixture. No real model is called. Personal
configuration, session metadata and provider credentials are not inherited; fixtures and
captures are temporary. Other explicitly loaded extensions remain trusted executable
code and may have their own side effects.

Add other extension **entry-point files** to test every order with them as well:

```sh
corepack pnpm check:compatibility --extension /path/to/another-extension/index.ts
```

An extension that still returns a whole prompt for an additive contribution can make this
check fail even after pi-clm is fixed. See `docs/extension-compatibility.md` for the
integration boundary, companion-version requirements and validation limits. Each extension
must own its additive contribution; CLM does not patch installed packages automatically.

The check verifies the injector's structured/append guidance, CLM's protocol and CLM tool
declarations. Add `--require-guidance "unique instruction marker"` to assert a companion's
own guidance too. Matching is exact fixture-marker presence, not semantic equivalence.
It does not prove arbitrary extension semantics, checkpoint ownership,
WebSocket cache reuse or the cause of every reload reset. Native prompt sections and
conversation checkpoint validation are distinct compatibility boundaries.

## Releasing

1. Set `version` in `package.json` and merge to `main`.
2. Tag and push the tag:

   ```sh
   git tag v1.0.0 && git push origin v1.0.0
   ```

3. The `release` workflow runs the typecheck and tests, refuses a tag that does not match
   `package.json`, and publishes to npm. It needs the repository secret `NPM_TOKEN`, an
   npm token allowed to publish `@lolipopshock/pi-clm`.

Users then install with `pi install npm:@lolipopshock/pi-clm`; the tarball is the TypeScript sources
(Pi loads them directly), the bundled steering brief and the docs.
