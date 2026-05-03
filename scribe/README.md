# scribe

A Claude plugin that captures sessions — conversation, decisions, attached images / audio / video / PDFs — into a git-versioned notes repo. Works in **Claude Cowork** and **Claude Code**.

Designed for shared collaborative notes repos: each user gets their own per-stakeholder subdirectory (`<repo>/<userslug>/...`), so a single private repo can collect notes from multiple people without their content colliding. Per-user directories sit alongside cross-cutting team folders (PRDs, ideation, conventions) that everyone contributes to.

## Install

> **First-time setup?** If your Mac doesn't have developer tools, GitHub access, or a local clone of the notes repo yet, follow [`../SETUP.md`](../SETUP.md) — a step-by-step walkthrough for non-developers. The instructions below assume those prereqs are done.

In a Cowork or Claude Code session:

```
/plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace
/plugin install scribe@gigasoftware-marketplace
```

Fully quit and relaunch your Claude client so the plugin's tools and skill load. The first time scribe's MCP runs, it sets up its own local Python venv (about 10 seconds, one-time, requires `python3` on PATH).

## First-time configuration

Scribe doesn't know where to write your notes until you tell it. From a Claude session, ask Claude something like:

> Configure scribe to save notes to my repo at /Users/me/Dev/team-notes.

Claude will use the `add_repo` tool to register the repo. It derives your user slug from `git config user.name` (override-able) and uses the directory's basename as the short repo identifier (override-able). The first repo you add becomes the active default.

If anything looks off, ask:

> Verify my scribe install.

Claude runs `verify_credentials` and reports the status of each check — git identity, push permission, Python runtime, etc. — with remediation hints for anything that's not green.

## Usage

Run the skill from any Claude session:

```
/session-summary
```

(Qualified form: `/scribe:session-summary` — useful if you have multiple plugins defining a `session-summary` command.)

Or just talk to Claude in conversation:

> Save this session to scribe.
> Capture this for the team.
> Summarize what we did and save it under the dossier folder for 123 Main St.

Claude will pick the right destination folder (based on your repo's existing layout and the conversation context), copy any attached files into a `media/` folder beside the note, append a one-line entry to a daily rollup, update the repo's `INDEX.md`, and commit + push automatically.

## Multiple notes repos

You can register more than one repo with scribe:

> Add my personal-notes repo at /Users/me/Dev/personal as well.

Switch defaults:

> Switch scribe to my personal-notes repo for now.

Or override per save:

> Save this to scribe under personal-notes.

Tools available to Claude: `add_repo`, `list_repos`, `switch_repo`, `remove_repo`, plus the core `save_session`, `repo_info`, and `verify_credentials`.

## Verify the install works

Ask Claude:

> Verify my scribe install.

Claude will run `verify_credentials`, which checks: git identity, origin reachability, push permission (via `git push --dry-run` against the live remote), Python runtime, and your user-slug consistency. Any `fail` or `warn` items come with remediation hints.

## How notes are laid out

For a user `alexsmith` with a repo at `/Users/me/Dev/team-notes`, after a few `/session-summary` invocations the layout looks like:

```
team-notes/
├── alexsmith/
│   ├── INDEX.md                              # running, reverse-chronological index
│   ├── communications/
│   │   └── 2026-05-02-rollup.md             # one-line per save, that day's chronological log
│   ├── clients/
│   │   └── jane-doe/
│   │       ├── 2026-05-02-offer-accepted.md
│   │       └── media/
│   │           └── 2026-05-02-offer-accepted-inspection.jpg
│   ├── workflows/
│   └── shared/                               # cross-cutting, optionally
└── morgangarcia/                             # another user's namespace
    └── ...
```

The exact subfolder names within each user's namespace are flexible — scribe doesn't impose a fixed structure. Claude picks folders based on context and any conventions documented in the consumer repo's own `CLAUDE.md`.

## Note format

Each saved note follows this frontmatter shape:

```markdown
---
date: YYYY-MM-DD
participants: [<you>, <others>]
transaction: <optional context — property address, project name, deal id>
tags: [<freeform>]
media: [media/<file1>, media/<file2>]   # omitted if no attachments
---

## Summary
## Decisions
## Next Steps
## Source Material
```

Empty sections may be omitted. Scribe never invents content — sections that weren't covered in the session are dropped.

## Configuration file

Scribe stores per-machine config at `~/.config/scribe/config.json` (or `$XDG_CONFIG_HOME/scribe/config.json` if set):

```json
{
  "version": 1,
  "current": "team-notes",
  "repos": {
    "team-notes": {
      "path": "/Users/me/Dev/team-notes",
      "user": "alexsmith",
      "added_at": "2026-05-02T..."
    }
  }
}
```

You can edit this file directly or use the MCP tools.

## Requirements

- macOS or Linux
- `python3` 3.10+ on PATH (ships with macOS Command Line Tools: `xcode-select --install`)
- `git` on PATH
- For each notes repo: write access to `origin` (SSH key with GitHub, or HTTPS credentials cached)

## Development

Source layout:

```
scribe/
├── .claude-plugin/plugin.json   # manifest (declares the MCP server)
├── launcher.sh                  # bootstraps the venv, runs server.py
├── server.py                    # the MCP server
├── pyproject.toml
├── test_server.py               # 37 offline tests, no network or mcp dep needed
├── skills/session-summary/SKILL.md
└── README.md
```

Run the tests:

```bash
cd scribe
python3 -m unittest test_server -v
```

The suite stubs `mcp.server.fastmcp` so you don't need the real `mcp` package installed to validate logic. Each test sets up an isolated git repo + scribe config in tmp.

## License

Apache-2.0. See [`../LICENSE`](../LICENSE).
