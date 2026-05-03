# RELEASE.md — Release playbook for scribe (and future plugins)

This file is a playbook for **Claude** to follow when the user asks to cut a new release. Read this end-to-end before doing anything; verify each step before moving to the next.

Trigger phrases that should cause you to follow this playbook:
*"release scribe"*, *"cut a release"*, *"release vX.Y.Z"*, *"ship a new version"*, *"publish scribe"*, or any close variation. The user may include the target version in their prompt (*"cut release v0.2.0"*); if not, ask them what semver bump they want and infer.

## How to use this file

You will be doing two things in tandem:

1. **Updating version strings in source** — every place in the repo that names a version. There are four such places (see *Version locations* below). Miss any one and the release ships inconsistent metadata.
2. **Creating the GitHub release artifact** — building the versioned zip and attaching it to a tag.

Most steps run on the user's host (Terminal). A few you can do directly via bash and file tools because they only touch the mounted repo. Follow the *who runs this* note on each step.

---

## Inputs you need from the user

Before doing anything, confirm:

- **Target version** (e.g., `0.1.2`, `0.2.0`, `1.0.0`). Strip any leading `v` — it's added back where needed (tag, filename, URL).
- **Release notes** (one to four bullet points describing what's new). If the user didn't provide them, scan recent git history (`git log <previous-tag>..HEAD --oneline`) and propose a draft for them to approve.

If either is missing, ask once. Don't proceed until both are nailed down.

---

## Version locations (the four places to update)

A release with target version `X.Y.Z` requires updating **all four** of these. Miss any and verification will fail.

| # | File | Field | Example value |
|---|---|---|---|
| 1 | `scribe/.claude-plugin/plugin.json` | `"version"` | `"0.1.2"` |
| 2 | `scribe/pyproject.toml` | `version` | `"0.1.2"` |
| 3 | `SETUP-END-USER.md` (download link text) | the version inside the markdown link text | `Download scribe v0.1.2` |
| 4 | `SETUP-END-USER.md` (download link URL) | the version appears **twice** in this URL — once as the tag, once in the filename | `releases/download/v0.1.2/scribe-v0.1.2.zip` |

`SETUP-DEV-TEAM.md` does **not** carry a version-pinned download link — engineers install via `/plugin marketplace add` + `/plugin install` slash commands, which resolve to the latest release automatically. No edit needed there.

`README.md` and `SETUP.md` are version-agnostic routers; they don't reference specific versions either.

Use grep to confirm before and after — search for the *previous* version, replace, then verify zero residual matches:

```
grep -rEn "0\.1\.1|v0\.1\.1|scribe-v0\.1\.1\.zip" --include="*.md" --include="*.toml" --include="*.json" .
```

Should return zero hits after the update (other than `RELEASE.md` itself if examples there reference the old version).

---

## Step 1 — Confirm clean state

You can run these via bash directly (they only read the mounted repo).

```bash
git status --short
git rev-parse --abbrev-ref HEAD       # should be "main"
git log --oneline -10                 # eyeball recent commits
```

Expected:
- `git status` is clean (no uncommitted changes), or all uncommitted changes are intentionally part of the release.
- On `main`, not a feature branch.
- Recent commits look like the work you're shipping.

If anything's off, surface it to the user and stop — don't release from a half-finished tree.

---

## Step 2 — Update the four version strings

Use the file tools (Edit) to bump each location. Read the file first if you haven't recently. After all four edits:

```bash
grep -rEn "<previous-version-without-v>|v<previous-version>|scribe-v<previous-version>\.zip" --include="*.md" --include="*.toml" --include="*.json" .
```

Should be empty. If anything matches, you missed a location — fix it before continuing.

---

## Step 3 — Run the test suite

```bash
cd scribe && python3 -m unittest test_server -v 2>&1 | tail -10
```

All tests must pass. Failures here block the release — do not continue. Surface the failures to the user.

---

## Step 4 — Build the versioned zip

The user must run this in their Terminal — the sandbox can't reach `~/Downloads`. Hand them this command (substitute the version you just bumped):

> ```bash
> cd /Users/<user>/Dev/claude-marketplace/scribe
> zip -r ~/Downloads/scribe-vX.Y.Z.zip . \
>   -x ".venv/*" -x "__pycache__/*" -x "*.egg-info/*" -x "*.pyc" \
>   -x ".pytest_cache/*" -x ".DS_Store"
> ```

Substitute `X.Y.Z` with the real numbers. Verify with the user that the file landed at `~/Downloads/scribe-vX.Y.Z.zip` before continuing.

You can verify the zip's plugin.json carries the right version with:

```bash
unzip -p ~/Downloads/scribe-vX.Y.Z.zip .claude-plugin/plugin.json
```

— but this also needs to run on the user's host, not the sandbox. Ask them to paste the output back if you want to confirm.

---

## Step 5 — Commit, tag, push

User runs from their Terminal:

> ```bash
> cd /Users/<user>/Dev/claude-marketplace
> git add scribe/.claude-plugin/plugin.json scribe/pyproject.toml SETUP-END-USER.md
> git commit -m "scribe vX.Y.Z: <one-line summary of the release>"
> git push
>
> git tag vX.Y.Z
> git push origin vX.Y.Z
> ```

Substitute `X.Y.Z` and the summary line. Commit message format is *"scribe vX.Y.Z: <what changed>"* — keeps the git log readable and matches the release notes.

---

## Step 6 — Create the GitHub release

User runs (substitute version + paste the release notes you drafted earlier):

> ```bash
> gh release create vX.Y.Z ~/Downloads/scribe-vX.Y.Z.zip \
>   --title "scribe vX.Y.Z" \
>   --notes "## What's new
>
> - <bullet 1>
> - <bullet 2>
>
> ## Install
>
> **Cowork users** — download \`scribe-vX.Y.Z.zip\` below and follow [SETUP-END-USER.md](https://github.com/GiGaSoftwareDevelopment/claude-marketplace/blob/main/SETUP-END-USER.md).
>
> **Claude Code users** — \`/plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace\` then \`/plugin install scribe@gigasoftware-marketplace\`."
> ```

Tell the user to verify the release appears at `https://github.com/GiGaSoftwareDevelopment/claude-marketplace/releases/tag/vX.Y.Z` and that `scribe-vX.Y.Z.zip` is listed under Assets.

---

## Step 7 — Verify the SETUP-END-USER.md link resolves

After the release is published, the URL in SETUP-END-USER.md needs to actually serve the zip. Have the user open this in a browser:

```
https://github.com/GiGaSoftwareDevelopment/claude-marketplace/releases/download/vX.Y.Z/scribe-vX.Y.Z.zip
```

It should download immediately. If it 404s, the asset wasn't attached correctly — re-check Step 6.

---

## Step 8 — (Optional) Re-test the install path end-to-end

In a fresh Cowork or Claude Code session, walk through the relevant setup guide (SETUP-END-USER.md for the Cowork upload path, SETUP-DEV-TEAM.md for the Code marketplace path), install the new build, and run `verify_credentials`. This catches release-time regressions before users hit them.

If anything fails:
- Fix the issue.
- Bump to the next patch version.
- Re-run this whole playbook from Step 1.

---

## What to do when things go wrong

- **Tests fail in Step 3.** Stop. Surface the failure to the user. Don't release a broken plugin.
- **Grep in Step 2 still finds the old version after your edits.** You missed a location. Use the table at the top of this file to identify which one.
- **`gh release create` fails with "release already exists".** The tag is taken — either bump to the next patch, or `gh release delete vX.Y.Z` first if it's a botched earlier attempt and you genuinely want to overwrite (rare, prefer bumping).
- **The download URL 404s in Step 7 even though the release page exists.** The asset filename in the URL doesn't match what was uploaded. Check `gh release view vX.Y.Z` and confirm the asset is named exactly `scribe-vX.Y.Z.zip` (no `.zip.zip`, no version mismatch).
- **User doesn't have `gh` installed.** Install with `brew install gh` then `gh auth login`. Or perform Step 6 via the GitHub web UI: Releases → Draft a new release → tag `vX.Y.Z` → upload the zip → publish.

---

## Conventions

- **Versioning is semver** (MAJOR.MINOR.PATCH). Plugin behavior changes that break existing configs → bump MAJOR. New tools or notable features → MINOR. Bug fixes and doc-only changes → PATCH.
- **No skipped versions.** If `v0.1.1` is current, the next release is `v0.1.2` or `v0.2.0`, never `v0.1.5`.
- **One commit per release.** Bundle the version bumps + any release-time fixes into a single commit so the tag points at a clean shippable state.
- **Tags are lowercase-v-prefixed**: `v0.1.1`, not `0.1.1` or `V0.1.1`. The GitHub release URL pattern depends on this exact format.
- **Asset filename pattern**: `scribe-vX.Y.Z.zip`. Don't drop the `v`, don't drop the version, don't add suffixes like `-final` or `-rc1`.

---

## Quick reference card

For a v0.1.1 → v0.1.2 release:

1. **You** (Claude): bump `0.1.1` to `0.1.2` in the four files (table above), grep-verify, run tests.
2. **User** (Terminal): build zip, commit, tag, push, `gh release create`.
3. **Both**: verify download link works.

That's the whole loop.
