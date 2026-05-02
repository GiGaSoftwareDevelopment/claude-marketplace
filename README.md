# claude-marketplace

GigaSoftware's plugin marketplace for [Claude Cowork](https://claude.ai) and [Claude Code](https://docs.claude.com/en/docs/claude-code).

## Plugins

| Plugin | What it does |
|---|---|
| [`scribe`](scribe/) | Capture Claude sessions — summaries, attached images, audio, video, PDFs — into a git-versioned notes repo. Multi-repo, multi-user. |

More plugins to follow.

## Install (one-time, per machine)

In a Cowork or Claude Code session, run:

```
/plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace
```

Then install whichever plugin(s) you want:

```
/plugin install scribe@claude-marketplace
```

After installing, restart your Claude session so the plugin's tools and skills load. You only need to add the marketplace once per machine; updates land via `/plugin marketplace update`.

## Per-plugin docs

Each plugin's directory has its own `README.md` with usage, configuration, and any required prerequisites. Start there.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
