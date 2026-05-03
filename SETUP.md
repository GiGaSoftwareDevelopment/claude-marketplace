# Setting up your computer to use plugins from this marketplace

A walkthrough for first-time users — no developer experience assumed. You'll spend a few minutes in your computer's command-line app (Terminal on Mac, PowerShell on Windows), then everything else happens inside Claude.

If you've already done a developer setup before — git, GitHub access, an SSH key — skim Steps 1–4 and pick up at [Step 5 (Clone the notes repo)](#step-5--download-the-notes-repo).

## What you'll be doing, big picture

1. Make sure your computer has the small set of developer tools needed.
2. Tell your computer who you are (so changes you save are signed with your name).
3. Set up a security key so GitHub can recognize your computer.
4. Download a copy of the notes repo someone has invited you to.
5. Install the plugin inside your Claude client (Cowork or Claude Code).
6. Tell the plugin where your local copy of the notes repo lives.
7. Try saving a session.

It's mostly copy-paste-and-press-Return. The whole thing takes about 20 minutes the first time, less if you already have a developer setup.

---

## Before you start

You need:

- A Mac (macOS) or Windows PC.
- A **GitHub account**. Sign up at [github.com](https://github.com) if you don't have one.
- An **invite to a notes repo** — the person who's setting you up will add you as a GitHub collaborator. Check your email for a GitHub invite and accept it before continuing.
- A **Claude plan**: Pro, Max, Team, Enterprise, or Console. The free Claude.ai plan does not support plugins.
- A **Claude client installed** — either:
  - **Claude Cowork** (recommended for non-developers) — download from [claude.ai/download](https://claude.ai/download).
  - **Claude Code** (for engineers comfortable with a terminal CLI) — install instructions in [Step 6 → For Claude Code users](#step-6b--for-claude-code-users).

---

## Step 1 — Open your shell

This is where you'll paste the commands in Steps 2–5.

**Mac:** Press **Cmd+Space**, type **Terminal**, press **Return**. A window with a blinking cursor appears.

**Windows:** Click the **Start** menu, type **PowerShell**, press **Enter**. (Use plain PowerShell, not "Windows PowerShell ISE.")

Whenever a step shows you a command, click into the window, paste with **Cmd+V** (Mac) or **Ctrl+V** (Windows), and press **Return** / **Enter** to run it. Read what's printed afterward — if something fails, the error message is the most useful thing to share with whoever's helping you.

---

## Step 2 — Install developer tools

These give you `git` (for downloading and updating the notes repo) and supporting tools.

### macOS

In Terminal, run:

```
xcode-select --install
```

If a small window pops up, click **Install** and wait — a few minutes. If it instead says *"command line tools are already installed"*, you're set.

Verify:

```
git --version
```

You should see a version number. If it says "command not found," re-run the install.

### Windows

Download and install **Git for Windows** from [git-scm.com/download/win](https://git-scm.com/download/win). Accept the default options when the installer prompts you.

Git for Windows gives you `git`, `ssh-keygen`, and a Bash-like shell.

After install, **close and reopen** PowerShell, then verify:

```powershell
git --version
```

You should see a version number.

---

## Step 3 — Tell your computer who you are

This step is identical on Mac and Windows. Replace the values in quotes with your real name and the email associated with your GitHub account:

```
git config --global user.name "Your Name Here"
```

```
git config --global user.email "youremail@example.com"
```

Verify:

```
git config --global user.name
```

Should print the name you just set. If it's empty or wrong, run the first command again.

---

## Step 4 — Set up a GitHub SSH key

GitHub needs to recognize your machine when you download the notes repo or push changes. The cleanest way is an **SSH key**.

### Generate the key (Mac and Windows)

In your shell, run:

```
ssh-keygen -t ed25519 -C "youremail@example.com"
```

It will ask:

- *"Enter file in which to save the key"* — press **Return** to accept the default.
- *"Enter passphrase"* — press **Return** twice to skip (recommended for simplicity), or set one if you prefer extra security.

### Copy the public key

**Mac:**

```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

That silently copies your public key to the clipboard.

**Windows (PowerShell):**

```powershell
Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard
```

Same effect — public key copied.

### Add the key to GitHub

In your browser, go to [github.com/settings/ssh/new](https://github.com/settings/ssh/new):

- **Title:** anything that helps you remember which computer (e.g., *"My MacBook"* or *"Work PC"*)
- **Key:** paste with **Cmd+V** / **Ctrl+V**
- Click **Add SSH key**

### Verify

Back in your shell:

```
ssh -T git@github.com
```

It will warn about a fingerprint the first time — type **yes** and press Return. Then you should see:

> Hi `<your-github-username>`! You've successfully authenticated, but GitHub does not provide shell access.

That's success. (The "no shell access" line sounds scary but is normal.)

If you instead see *"Permission denied (publickey)"*, the key didn't get added correctly. Re-do this step.

---

## Step 5 — Download the notes repo

The person who set you up will tell you the repo address — it looks like `git@github.com:<owner>/<reponame>.git`. We recommend cloning into a `Dev` folder in your home directory:

**Mac (Terminal):**

```bash
mkdir -p ~/Dev && cd ~/Dev
git clone git@github.com:<owner>/<reponame>.git
```

**Windows (PowerShell):**

```powershell
New-Item -ItemType Directory -Force -Path ~/Dev | Out-Null
cd ~/Dev
git clone git@github.com:<owner>/<reponame>.git
```

You'll now have a folder at `~/Dev/<reponame>`. **Remember this path** — you'll give it to Claude in Step 7.

If you get a permission error, you probably haven't accepted the GitHub collaborator invite yet (check your email).

---

## Step 6 — Install the plugin

Pick the section for whichever Claude client you're using.

### Step 6a — For Cowork users (recommended for non-developers)

#### Download the plugin

Click this link to download `scribe-v0.1.1.zip` directly:

**[Download scribe v0.1.1](https://github.com/GiGaSoftwareDevelopment/claude-marketplace/releases/download/v0.1.1/scribe-v0.1.1.zip)**

It saves to your Downloads folder.

To browse all versions or grab an older one, see [all releases](https://github.com/GiGaSoftwareDevelopment/claude-marketplace/releases).

#### Open Cowork's plugin manager

In the Cowork app, find the **Customize** panel — usually accessed from a sidebar or menu in the chat view.

![Select the Customize entry](docs/cowork-install/1-select-customize.png)

#### Add a personal plugin

In Customize, click the **+** next to **Personal plugins** to open the add-plugin menu.

![Click + next to Personal plugins](docs/cowork-install/2-click-plus-to-add-personal-plugin.png)

#### Choose "Upload plugin"

From the menu, choose **Upload plugin** (the option for installing a custom plugin from a file).

![Select Upload plugin](docs/cowork-install/3-select-upload-plugin.png)

#### Browse for the zip

In the dialog that appears, click **Browse files** to open the file picker.

![Click Browse files](docs/cowork-install/4-select-browse-files.png)

You can also drag the zip from Finder / Explorer directly into the dialog's drop zone — same result.

![Drag the plugin into the modal](docs/cowork-install/5-drag-plugin-to-modal.png)

Pick the `scribe-vX.Y.Z.zip` you downloaded a minute ago.

#### Confirm MCP server registration

Cowork will ask you to confirm registering the plugin's MCP server. Click **Continue**.

![Click Continue for MCP servers](docs/cowork-install/6-click-continue-for-mcp-servers.png)

The MCP server is what lets the plugin write notes to your repo and run git on your behalf — it's required for scribe to do anything useful. It runs as you, on your computer.

#### Confirm the install

You should now see scribe under **Personal plugins** with version, source, and the **Skills** tab populated with `/session-summary`.

![Scribe installed and ready](docs/cowork-install/7-install-result.png)

#### Restart Cowork

**Quit Cowork completely** (Cmd+Q on Mac, or Cowork → Quit Cowork in the menu bar) and reopen it. This is required so Cowork loads the new MCP server into a fresh session.

Now skip to [Step 7 — Configure scribe](#step-7--configure-scribe).

### Step 6b — For Claude Code users

If you don't already have Claude Code installed, install it now.

#### Install Claude Code

**macOS** (in Terminal):

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Or via Homebrew:

```bash
brew install claude-code
```

**Windows** (in PowerShell):

```powershell
irm https://claude.ai/install.ps1 | iex
```

Verify:

```
claude doctor
```

The first time you run `claude` (no arguments) it opens your browser to log in.

#### Install scribe

In Terminal, run `claude` to start a session. Send these slash commands one at a time:

```
/plugin marketplace add GiGaSoftwareDevelopment/claude-marketplace
```

```
/plugin install scribe@gigasoftware-marketplace
```

After both succeed, **exit Claude Code** (Ctrl+C twice or `/quit`) and start it again with `claude` so the plugin loads into a fresh session.

---

## Step 7 — Configure scribe

In a fresh chat (Cowork or Claude Code), tell Claude:

> Configure scribe to save my notes to ~/Dev/&lt;your-repo-name&gt;

(Replace `<your-repo-name>` with whatever you cloned in Step 5.)

The `~` part expands automatically to your home folder, so this command works on any Mac or Windows machine without typing your full path. If you cloned the repo somewhere else, give the full path instead.

Claude will set things up and confirm. It figures out your user-folder name automatically from the git identity you set in Step 3.

Then verify everything works end-to-end:

> Verify my scribe install.

Claude runs a series of checks. Everything should come back green or with a single yellow `notes_user_dir_exists` warning (that one's expected — the folder is created on your first save). If anything's red, the message tells you what to fix — most commonly it points back to one of Steps 2, 3, or 4.

---

## Step 8 — Save your first session

You're done with setup. Have a short conversation with Claude — talk through whatever's on your mind for the day. Then send:

```
/session-summary
```

Or just say it conversationally:

> Save this to scribe.

Claude writes a markdown file into the repo, commits it, and pushes it to GitHub. You can verify by going to the repo on github.com — your new file will be there in your personal user-folder (e.g. `<your-username-slug>/communications/...`).

---

## What to do if something goes wrong

- **A command says "command not found".** Re-run Step 2 (developer tools).
- **GitHub says "Permission denied (publickey)".** Re-do Step 4 (SSH key).
- **`/session-summary` doesn't seem to do anything.** You probably forgot to fully restart Cowork (or Claude Code) after installing the plugin in Step 6. Quit completely, reopen, try again.
- **Cowork shows scribe but no skills under it.** You're on an outdated zip — download the latest release from Step 6a and re-upload, then quit and reopen.
- **Claude says push failed.** You probably haven't accepted the GitHub collaborator invite yet, or your access is read-only. Check with the person who set you up.
- **`claude doctor` reports red items** (Code path only). Follow the specific suggestion it prints. Common fixes: restart your shell, log in to a paid plan, install Git for Windows.
- **Anything else.** Copy what's on your screen and send it to whoever's helping you. The actual error message is the fastest way to fix it.

---

## What this guide covered

| You did | So that |
|---|---|
| Installed developer tools (Xcode CLT or Git for Windows) | Your computer has `git` and friends |
| Set git identity | Notes get attributed to you |
| Created and registered an SSH key | GitHub recognizes your computer |
| Cloned the notes repo | You have a local copy on disk |
| Installed scribe (via Cowork upload or Code marketplace) | The plugin's commands are available in chat |
| Pointed scribe at your repo | Saves know where to write |

Once this is done, the only thing you need day-to-day is opening Cowork (or running `claude`), having a conversation, and saying *"save this to scribe"* (or running `/session-summary`) at the end. Everything else is automatic.
