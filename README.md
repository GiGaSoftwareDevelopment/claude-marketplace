# claude-marketplace

GigaSoftware's plugin marketplace for [Claude Cowork](https://claude.ai) and [Claude Code](https://docs.claude.com/en/docs/claude-code).

## Plugins

| Plugin | What it does |
|---|---|
| [`scribe`](scribe/) | Capture Claude sessions — summaries, attached images, audio, video, PDFs — into a git-versioned notes repo. Multi-repo, multi-user. |

More plugins to follow.

---

## Install in Claude Cowork — for end users, stakeholders, and note-takers

If your role is to **create** the notes — product owners, stakeholders, subject-matter experts, documentarians, anyone primarily *talking through* their work in Claude and capturing it for the team — install via Claude Cowork. Cowork is the desktop chat app and is the right surface for conversation-first note capture.

> **First time installing a Claude plugin on this computer?** Follow **[SETUP.md](SETUP.md)** end-to-end — a non-developer walkthrough covering developer tools, GitHub access, downloading the plugin, and uploading it into Cowork. Includes screenshots for every step.

If your machine is already set up and you've installed plugins from this marketplace before, the short version:

1. Download the latest plugin zip from [Releases](https://github.com/GiGaSoftwareDevelopment/claude-marketplace/releases) (the [SETUP.md install step](SETUP.md#step-6a--for-cowork-users-recommended-for-non-developers) has the direct link for the current version).
2. In Cowork: **Customize → Personal plugins → +  → Upload plugin**, drop the zip in.
3. Quit and reopen Cowork.
4. In a new chat, configure the plugin against your local notes repo (e.g., *"Configure scribe to save my notes to ~/Dev/&lt;your-repo&gt;"*).

---

## Install in Claude Code — for the software development team

If your role is to **consume** the notes — engineers reading other stakeholders' captures, searching across the repo, processing notes as training data, building tools on top of the corpus, or contributing notes during feature work — install via Claude Code. Code is the CLI client and is the right surface for repo-aware engineering work.

If you don't have Claude Code installed yet, the [SETUP.md install step](SETUP.md#step-6b--for-claude-code-users) has the canonical install commands for Mac and Windows. Otherwise:

1. In a Claude Code session, run:
   ```
   /plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace
   ```
   ```
   /plugin install scribe@gigasoftware-marketplace
   ```
2. Exit and relaunch Claude Code (`/quit` then `claude`) so the plugin loads.
3. Configure the plugin against your local notes repo (e.g., *"Configure scribe to save my notes to ~/Dev/&lt;your-repo&gt;"*).

Updates land later via `/plugin marketplace update`.

---

Each plugin's directory has its own `README.md` with usage details and configuration options. Start there once installed.

For maintainers cutting new releases of plugins in this marketplace, see [RELEASE.md](RELEASE.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).
