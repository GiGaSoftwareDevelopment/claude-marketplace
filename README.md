# claude-marketplace

GigaSoftware's plugin marketplace for [Claude Cowork](https://claude.ai) and [Claude Code](https://docs.claude.com/en/docs/claude-code).

## Plugins

| Plugin | What it does |
|---|---|
| [`scribe`](scribe/) | Capture Claude sessions — summaries, attached images, audio, video, PDFs — into a git-versioned notes repo. Multi-repo, multi-user. |

More plugins to follow.

## Install

> **First time using a Claude plugin?** Read **[SETUP.md](SETUP.md)** first — it walks through everything from scratch (developer tools, GitHub access, cloning a repo, installing the plugin) for non-developers.

If you've installed Claude plugins before and your machine is already set up, the short version: in a Cowork or Claude Code chat, run

```
/plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace
```

then install whichever plugin you want:

```
/plugin install scribe@claude-marketplace
```

After installing, **fully quit and relaunch your Claude client** so the plugin's tools and skill load. Updates land via `/plugin marketplace update` later.

Each plugin's directory has its own `README.md` with usage and configuration. Start there once installed.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
