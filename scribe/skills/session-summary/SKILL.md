---
name: session-summary
description: Capture the current Claude session — conversation, decisions, attached images / audio / video / PDFs — into a git-versioned notes repo. Calls the scribe MCP server to save a markdown note, copy media, append a daily rollup, update the repo's INDEX.md, and commit + push. Supports multiple notes repos per user. Trigger phrases include "save this to scribe", "summarize this session", "capture this for the team", "/session-summary", or any close variation.
---

# session-summary

A skill for capturing the current Claude session into a git repo via the **scribe** MCP server. The MCP runs as the user (host-side), so it has full filesystem and git credentials — works from Cowork (sandboxed) or Claude Code.

When invoked, follow this procedure.

## 1. Confirm scribe is reachable and configured

Call `mcp__scribe__list_repos`. Three possible states:

- **No repos configured** (empty `repos` map) → first-run flow. Go to step 2.
- **One or more repos configured, `current` is set** → ready. Go to step 3.
- **Configured but `current` is `null` or invalid** → ask the user which repo to use, then `mcp__scribe__switch_repo`. Then go to step 3.

If the call itself fails ("tool not found"), the scribe MCP isn't registered in this session — tell the user to install the plugin (`/plugin install scribe@gigasoftware-marketplace`) and restart their Claude session, then stop.

## 2. First-run flow (only if no repos are configured)

The user has scribe installed but hasn't pointed it at a notes repo yet. Ask them:

1. *"Where should I save your notes? Paste the absolute path to your cloned notes repo."* (Example: `/Users/larry/Dev/ground-zero`.) The path must be a git repo on this machine — not a URL. If they only have a URL, tell them to `git clone` it first and come back with the local path.

2. *"What short name should I use to refer to this repo?"* — used as the `name` for `add_repo` and as the identifier when they later have multiple. Suggest one based on the directory's basename. Lowercase, hyphens only. Example: `ground-zero`.

3. *"What user slug should your notes go under?"* — defaults to slugified `git config user.name`. Show the suggestion and let them confirm or override. The slug becomes a top-level subdirectory in the repo (`<repo>/<user>/...`).

Once you have all three, call `mcp__scribe__add_repo(name=..., path=..., user=...)`. It auto-sets `current` if there was no current. Confirm with one line: *"Configured `<name>` at `<path>`, notes will go under `<user>/`."*

Optionally offer: *"Want me to verify push access works? I'll run scribe's verify_credentials check."* — a good idea on first install.

## 3. Review the session

Look at what happened in this session:
- Conversation with the user (instructions, decisions, observations)
- Connector tool results (Gmail, Calendar, Drive, etc.)
- Any uploaded files: images, audio, video, PDFs, docs

## 4. Choose the destination folder

The scribe MCP scopes everything under `<user>/<folder>/...` automatically — pass `folder` *without* the user prefix.

The folder structure within the user's namespace is **consumer-defined**. The scribe plugin doesn't impose a specific layout. Look at:

- The repo's existing structure (run a quick `ls` via bash if needed) — match what's already there.
- The repo's `CLAUDE.md` if it has one — many notes repos document their conventions there.

Common patterns you'll see in notes repos that use scribe:

- `clients/<client-name>/` — per-client subfolders for client interactions
- `contacts/<category>/<name>/` — per-contact subfolders (vendors, partners, etc.)
- `workflows/` — process documentation, recurring patterns
- `communications/` — daily rollups (the MCP creates these automatically)
- `monday/`, `linear/`, etc. — per-tool capture
- `shared/` or `team/` — collaborative docs accessible to everyone in the repo
- `prds/`, `ideation/`, `conventions/` — cross-cutting team docs

If the user's intent is ambiguous between two folders, ask once. Otherwise pick one and proceed.

## 5. Identify attached media

For every uploaded image / audio / video / PDF / doc in this session, find its host-readable absolute path. Cowork uploads typically live at:

```
/Users/<user>/Library/Application Support/Claude/local-agent-mode-sessions/<...>/uploads/<filename>
```

Pass each as `{ "source_path": "<abs-path>", "descriptor": "<short-label>" }`. Do NOT transcribe audio or video unless the user explicitly asks — save the file and reference it in the note.

## 6. Build the note body

```markdown
## Summary
<what happened, in the user's voice where possible>

## Decisions
<what was decided and why>

## Next Steps
<who owes whom what, by when>

## Source Material
<links: connector references (Gmail thread id, Drive URL, calendar event), context links>
<relative links to any copied media, e.g. ![photo](media/2026-05-02-walkthrough-photo.jpg)>
```

Do NOT invent details. If a section wasn't covered in this session, leave it terse or omit it rather than guess.

## 7. Save via the MCP

Call `mcp__scribe__save_session` once with everything:

```json
{
  "folder": "clients/jane-doe",
  "slug": "offer-accepted",
  "frontmatter": {
    "date": "2026-05-02",
    "participants": ["<you>", "Jane Doe"],
    "transaction": "123 Main St",
    "tags": ["buyer", "offer"]
  },
  "body": "## Summary\n...\n",
  "media": [
    { "source_path": "/Users/.../uploads/inspection.jpg", "descriptor": "inspection-photo" }
  ],
  "repo": "ground-zero"
}
```

The `repo` field is optional — omit to use the current default. Pass it explicitly only when the user said *"save this to my X repo"* and X is one of their configured repos (verify against `list_repos` if unsure).

The MCP will:
1. Write `<user>/<folder>/<date>-<slug>.md`
2. Copy each media file into `<user>/<folder>/media/` with canonical names
3. Append to `<user>/communications/<date>-rollup.md`
4. Update `<user>/INDEX.md`
5. `git pull --rebase --autostash`, stage, commit, and push

## 8. Report back

Tell the user, in one or two lines:
- Relative path of the saved note
- Number of media files copied (if any)
- Whether commit + push succeeded (read `git.committed`, `git.pushed`, `git.error` from the response)

If `git.pulled` is `false` (rebase conflict), surface the error verbatim — do NOT auto-resolve.
If `git.pushed` is `false` but `git.committed` is `true`, tell the user the commit is local and push can be retried.

If multiple repos are configured, mention which repo the note went to.
