# claude-marketplace

GigaSoftware's plugin marketplace for [Claude Cowork](https://claude.ai) and [Claude Code](https://docs.claude.com/en/docs/claude-code).

## Plugins

| Plugin | What it does |
|---|---|
| [`scribe`](scribe/) | Capture Claude sessions — conversation summaries, decisions, attached spreadsheets, documents, images, audio, video, PDFs — into a git-versioned notes repo. Multi-repo, multi-user. |

More plugins to follow.

### About scribe

**`scribe` lets non-developer stakeholders — product owners, subject-matter experts, domain leads, customers, anyone whose context matters but who isn't writing code — turn their Claude conversations into shared, version-controlled team notes.**

After working through a problem with Claude (deciding something, walking a workflow, reviewing a contract, brainstorming a feature, debugging a process), the user runs `/session-summary` or just says *"save this to scribe"*. The plugin writes the conversation summary as a markdown file into a shared git repo, copies any attached files (Excel sheets, Word docs, photos, voice memos, screenshots, PDFs) alongside it, updates a daily rollup and an index, and pushes — all from inside the chat. The notes are now versioned, searchable, and diff-able alongside the rest of the team's work.

Two patterns this enables:

- **Stakeholder → engineering hand-off.** A product owner thinks through requirements out loud with Claude, attaches the relevant spec spreadsheet and a few mockup screenshots, and saves to scribe. The dev team picks up the note from the shared repo with the full context — what was decided, what was attached, why — without anyone needing to have been in the same meeting.
- **Stakeholder ↔ stakeholder collaboration.** Multiple contributors share one private repo, each with their own per-user folder for personal capture plus shared folders (PRDs, conventions, ideation) that everyone writes into. Notes accumulate over time into a durable knowledge base the whole team can browse.

Notes stay private by default — `scribe` writes to whatever git repo each user has it pointed at, so a private team repo on GitHub stays private. The plugin runs locally on each user's machine; nothing leaves their computer except the commits they push to their own repo.

## Get started

Pick the setup guide that matches your role:

### → [SETUP-END-USER.md](SETUP-END-USER.md)

For **end users, stakeholders, and note-takers** who'll *create* notes — product owners, subject-matter experts, documentarians. Uses Claude Cowork. Non-developer walkthrough with screenshots, designed to be opened directly inside a Cowork session and guided through interactively.

### → [SETUP-DEV-TEAM.md](SETUP-DEV-TEAM.md)

For **software engineers** who'll *consume* notes — reading captures, searching the corpus, building tooling, contributing during feature work, or maintaining the plugin. Uses Claude Code. Engineer-paced.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
