# Changelog

## 1.0.0

First release as its own GitHub repo.
- Install by pasting the repo link into Claude Code and saying "set this up".
- The skill installs to `~/.claude/skills/find-skills`. Setup checks for Node.js (the skill needs it to search) and finds Python (or installs it) for the updater.
- Updates install themselves once a day, in the background, from published releases only. If a new release does not start, the old one is put back by itself.
- An update never touches a file you added or a skill you installed. Changes you ask for are kept in `~/.solnest/find-skills/my-instructions.md`.
- The skill text is Vercel's open-source `find-skills` (MIT license, kept in the skill folder).
