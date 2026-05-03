# Setup guide for software engineers

For engineers who'll **consume** the notes captured by stakeholders — read other people's session summaries, search across the corpus, build tooling on top, contribute notes during feature work, or maintain the plugin itself.

If you're a stakeholder primarily *creating* notes (product owners, subject-matter experts, documentarians), use [SETUP-END-USER.md](SETUP-END-USER.md) instead — it covers the Claude Cowork install path with screenshots and a guided walkthrough.

---

## Prereqs

Standard developer-machine baseline. If any of these aren't true on your machine, knock them out first.

| Requirement | Verify |
|---|---|
| `git` on PATH | `git --version` |
| Python 3.10+ on PATH | `python3 --version` |
| `git config --global user.name` and `user.email` set | `git config --global user.name` |
| GitHub SSH key registered with your account | `ssh -T git@github.com` (look for *"Hi `<username>`!"*) |
| Collaborator access on the team's notes repo | Check your email for the GitHub invite and accept it |
| **Claude plan**: Pro, Max, Team, Enterprise, or Console | (free Claude.ai plan does not include Claude Code) |

---

## 1. Install Claude Code

**macOS:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
# or: brew install claude-code
```

**Windows (PowerShell):**

```powershell
irm https://claude.ai/install.ps1 | iex
```

Verify:

```
claude doctor
```

The first time you run `claude` it'll open your browser to authenticate.

Full reference: [docs.claude.com/en/docs/claude-code/setup](https://docs.claude.com/en/docs/claude-code/setup).

---

## 2. Clone the team's notes repo

```bash
mkdir -p ~/Dev && cd ~/Dev
git clone git@github.com:<owner>/<reponame>.git
```

Whoever invited you has the exact URL. The recommended convention is `~/Dev/<reponame>` — the configure step in §4 assumes that location.

---

## 3. Install scribe via the marketplace

In a Claude Code session (`claude`):

```
/plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace
```

```
/plugin install scribe@gigasoftware-marketplace
```

Exit Claude Code (`/quit`) and start it again — the plugin's MCP server and `session-summary` skill load on session boot.

The first time scribe's MCP launches, it sets up its own Python venv at `~/.claude/plugins/.../scribe/.venv/` and `pip install`s the `mcp` package. ~10 seconds, one-time, requires `python3` on PATH (see prereqs).

---

## 4. Configure scribe

In a fresh Claude Code session, ask Claude (with `~/Dev/<reponame>` substituted to your actual clone path):

> Configure scribe to save my notes to ~/Dev/&lt;reponame&gt;

Claude calls `add_repo`. Tilde expansion happens server-side, so the same prompt works on any machine.

Verify:

> Verify my scribe install.

Calls `verify_credentials`. Twelve checks across repo state, Python runtime, network, and push permission. All-green is the target; the only acceptable warn at this point is `notes_user_dir_exists` (your subfolder doesn't exist until first save).

---

## 5. Save your first session

```
/session-summary
```

— or just *"save this to scribe"* in chat. Calls `save_session`, writes the note to `<your-userslug>/communications/...` (or wherever Claude picks based on conversation context), copies any attached media, updates daily rollup + INDEX, runs `git pull --rebase --autostash`, commits, pushes.

Verify the push landed by visiting the notes repo on github.com.

---

## Multi-repo

scribe supports multiple notes repos out of the box. Tools available to Claude:

- `add_repo(name, path, user?)` — register another repo. Becomes current if no current was set.
- `list_repos()` — show configured repos and the current default.
- `switch_repo(name)` — change current default.
- `remove_repo(name)` — unregister (does not touch files on disk).
- All of `save_session`, `repo_info`, `verify_credentials` accept an optional `repo` kwarg to override the current default for a single call.

Conversationally:

> Add another scribe repo at ~/Dev/personal-notes called personal
> Switch scribe to personal-notes for now
> Save this to scribe under personal-notes

Per-machine config lives at `~/.config/scribe/config.json`.

---

## Plugin source and tests

- Source: [`scribe/`](scribe/) — server, launcher, skill, tests.
- Run the test suite: `cd scribe && python3 -m unittest test_server -v` (37 offline tests, no `mcp` package required for tests; stubs the SDK).
- For the full plugin manifest reference, see Anthropic's [plugins reference](https://code.claude.com/docs/en/plugins-reference).

---

## Cutting a release

If you maintain this plugin and need to ship a new version, follow [RELEASE.md](RELEASE.md). It's structured as an AI-runnable playbook — open this repo in a Claude Code session and ask *"cut release v0.X.Y"*; Claude reads RELEASE.md and walks the four version-update locations + the GitHub release flow.

---

## Troubleshooting

- **`claude doctor` reports red items** — install Git for Windows, restart shell, ensure paid plan, etc. Doctor's output is specific.
- **Plugin install succeeded but `/session-summary` doesn't appear** — restart Claude Code (`/quit`, then `claude`). Plugin tools load on session boot only.
- **Push fails** — not a collaborator on the notes repo, or SSH key isn't registered with the GitHub account that has access.
- **`mcp_package_importable: fail` in verify** — the MCP venv didn't bootstrap. Ensure `python3 --version` returns 3.10+, then restart Claude Code so the launcher retries.

---

## For end users

If your role is primarily *creating* notes (you talk through your work in Claude and want it captured for the team), see [SETUP-END-USER.md](SETUP-END-USER.md) — that walks through the Claude Cowork install path with screenshots and is structured so a Claude Cowork session can guide you through it interactively.
