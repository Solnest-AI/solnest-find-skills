If the user said "set this up", follow SETUP below.

# Find Skills (Solnest AI)

This repo installs the `find-skills` skill. When the user asks "is there a skill for X" or "how do I do X", the skill has you search the open skills library (https://skills.sh) with the `npx skills` command, check how popular and trusted each match is, show the best ones, and install the one the user picks.

What is in here:
- `skill/find-skills/`: the skill (`SKILL.md`, `LICENSE`, `scripts/`). It installs to `~/.claude/skills/find-skills`.
- `install.sh`: the installer. `VERSION` and `CHANGELOG.md`: what release this is.

The skill text is Vercel's open-source `find-skills` skill (MIT license, kept in `skill/find-skills/LICENSE`). Solnest AI added the setup and the automatic updates.

## Your own changes (read first, every time)

Before anything else, read `~/.solnest/find-skills/my-instructions.md` if it exists and
follow it. It holds this user's own changes to how this tool works, and it wins over the
defaults in this file.

When the user asks to change how this tool works for them (wording, tone, topics, steps,
defaults, what to include or leave out), write the change into that file in plain words,
create it if needed, and read it back to them. **Never edit this tool's own files for
that.** This tool updates itself automatically and replaces its own files, so a change
made there is lost on the next update. That one file is where their changes live. An
update never touches it, and it never touches a file they added to the skill folder or any
skill they installed with this tool.

## Rules for you (Claude) during setup

- You run every command yourself with your Bash tool. The user never opens a terminal. On Windows, Claude Code runs Bash commands in Git Bash, where these commands (including `~`) work.
- One step per message. Do not report success until you have seen real output.
- This tool needs no accounts and no keys. Never ask for one.
- Installing a skill that this tool finds is always the user's choice. Show what you found, ask, and install only after a plain yes.

## SETUP

### Step 1: Look for a copy that is already there

Run:

```bash
D="$HOME/.claude/skills/find-skills"; if [ -L "$D" ]; then echo "LINK"; elif [ -f "$D/VERSION" ]; then echo "SOLNEST COPY $(cat "$D/VERSION")"; elif [ -e "$D" ]; then echo "OTHER COPY"; else echo "NOTHING THERE"; fi
```

- `NOTHING THERE` or `SOLNEST COPY`: go to Step 2.
- `LINK` or `OTHER COPY`: the user already has find-skills from somewhere else, usually the original installed with `npx skills add`. Tell them: "You already have find-skills. I can swap it for the Solnest copy. It is the same skill, plus it keeps itself up to date. OK to swap?" Only after a plain yes, run:

  ```bash
  npx -y skills remove find-skills -g -y
  ```

  Then run the check above again. If it still says `LINK` or `OTHER COPY`, stop and tell the user what is in that folder. Do not delete it yourself. If they say no, stop here: the copy they have already works.

### Step 2: Install

Tell the user in one line: "Installing the find-skills skill. About a minute, nothing for you to do." Then run one of these:

- You are reading this from the GitHub page (no local copy of this repo):

  ```bash
  bash -o pipefail -c "curl -fsSL https://raw.githubusercontent.com/Solnest-AI/solnest-find-skills/main/install.sh | bash"
  ```

- You already have this repo as a folder on this computer: `bash "<this folder>/install.sh"`

The installer copies the skill to `~/.claude/skills/find-skills`, finds Python 3.9 or newer (or installs one for this user, no admin rights needed), writes a small launcher (`bin/py`) so the updater always uses that Python, proves the updater starts, and checks that Node.js is on this computer. Running it again is safe: it leaves every file the user added alone.

### Step 3: Read the checklist it printed

- Every line starts with `[ok]`: go on to Step 4.
- `[!!] Node.js   not found`: the skill searches with `npx`, which comes with Node.js. Install it, then run Step 2 again:
  - Mac with Homebrew (`command -v brew` prints a path): `brew install node`
  - Windows: `winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements`
  - Anything else, or if the line above fails: send the user to https://nodejs.org to download and run the LTS installer with the default choices.
  
  After Node.js is installed, the user may need to close and reopen Claude Code once so it is found. Then run Step 2 again.
- `STOP: ... is a link`, `... a git checkout` or `... holds a different skill`: something else lives at `~/.claude/skills/find-skills`. Nothing was changed. Go back to Step 1. Do not delete it yourself.
- `ERROR: could not download`: usually the network. Run Step 2 once more.
- `ERROR: no working Python`: send the user to https://www.python.org/downloads/ (on Windows they must tick "Add python.exe to PATH"). When they say it is installed, run Step 2 again.
- `[!!] updater`: run Step 2 once more. If it repeats, send the full output to hello@solnestai.com.

### Step 4: Real test (read-only)

Run one real search. It only reads the public skills library. It installs nothing.

```bash
npx -y skills find "pdf" </dev/null
```

Expect a list of skills, each with an install count and a `https://skills.sh/...` link. The first run can take up to a minute while `npx` fetches the search tool. If it fails with a network error, run it once more.

Show the user the top three results in plain words. Do not install any of them.

### Step 5: Turn on automatic updates (required, silent)

Run this exactly:

```bash
SKILL="$HOME/.claude/skills/find-skills"; "$SKILL/bin/py" "$SKILL/scripts/solnest_autoupdate.py" register --name find-skills --folder "$SKILL" --update '{python} scripts/update.py' --after 'grep -q "^name: find-skills" SKILL.md && {python} scripts/update.py --help' --undo '{python} scripts/update.py --undo'
```

From now on the skill keeps itself on the latest release with no one asking: once a day, in the background when Claude Code starts, it installs the newest published release and checks that the skill is still in one piece. It never touches a file the user added or a skill they installed, and if a new release fails that check it puts the old version back by itself. Relay the one line it prints. Nothing else to tell them.

### Step 6: Tell the user what worked

Short checklist: skill installed (path), Node.js found, the test search returned N results, automatic updates on. Then: "Any time you wonder if Claude can do something, just ask: is there a skill for that? Try it now: find a skill for making PDFs."

The skill loads by itself the next time they open Claude Code. In this chat, if they ask for a skill right away, read `~/.claude/skills/find-skills/SKILL.md` and follow it from the top.

## Update

Updates install themselves (Step 5). Files the user added and skills they installed are never touched. Changes the user asked for live in `~/.solnest/find-skills/my-instructions.md`, outside the skill folder, so they survive every update.

Only when the user asks to update now:

```bash
SKILL="$HOME/.claude/skills/find-skills"; "$SKILL/bin/py" "$SKILL/scripts/update.py" && grep -q "^name: find-skills" "$SKILL/SKILL.md" && echo "[ok] skill in place"
```

Then run the Step 5 line once more, so a newer auto-updater is picked up. To go back one version: `"$HOME/.claude/skills/find-skills/bin/py" "$HOME/.claude/skills/find-skills/scripts/update.py" --undo`. If `scripts/update.py` is missing (a copy that did not come from this repo), run SETUP from Step 1.

"Is it updating itself?": `~/.claude/skills/find-skills/bin/py ~/.solnest/autoupdate.py status`. Use `pause` in place of `status` to stop all automatic updates, and `resume` to turn them back on.

If `status` shows the last check failed, offer to update now with the line above.

This only updates the find-skills skill itself. Skills the user installed with it are updated by their own tool: `npx -y skills update`, and only when the user asks.

## Repair

Run Step 2 again, then Step 5.

## Uninstall

```bash
~/.claude/skills/find-skills/bin/py ~/.solnest/autoupdate.py remove --name find-skills
```

Then, after a plain yes from the user, delete the folder `~/.claude/skills/find-skills`. Skills they installed with it stay.
