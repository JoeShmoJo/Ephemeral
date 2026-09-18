# How work gets done in this repository

Drop this file at the root of a repository as `CLAUDE.md`. Claude Code reads it
automatically in every session. It also reads fine as plain documentation, so it
works as `CONTRIBUTING.md` if a human needs it instead.

---

## The rule that matters

**Nothing goes onto `main` except through a pull request.**

No direct commits to `main`, no exceptions for "small" changes. If a change is
worth making, it is worth a branch and a diff I can read afterwards.

**Open the PR and merge it. Do not wait for me.** I read the diff after the
fact, from the PR, which is why the PR still has to exist and its description
still has to be honest. Do not ask "shall I merge?" — the answer is yes.

---

## For Claude, or any agent working in this repository

### The loop

1. **Branch first.** Name it after the change: `fix-login-crash`,
   `add-export-button`. Never start work on `main`.
2. **Commit** in logical pieces, present tense, saying what and why:
   `fix crash when the login form is empty`.
3. **Push** the branch: `git push -u origin <branch-name>`.
4. **Open a pull request** against `main`. Fill in the description properly —
   see below.
5. **Merge it yourself**, squash, and say what landed and what to look at.
   Squash-merging deletes the branch, so start the next change from a fresh
   `main` (`git fetch --prune`, then branch again) rather than reusing the old
   branch — its commits are dead history once squashed, and pushing them back
   only causes conflicts.

### Never, without asking me first

- Push or commit **directly** to `main` — it goes through a PR, always
- `git push --force`, or rewrite history that is already pushed
  (force-pushing your own branch to drop dead squash-merged commits is fine)
- Delete a branch I have not merged
- `git reset --hard` or `git clean -fd` on work I have not committed
- Anything outward-facing: creating repositories, changing settings, adding
  collaborators, posting comments on other people's issues or PRs

### Pull request descriptions

Write them for me reading the PR cold in a week.

- **Why, not what.** The diff already shows what changed.
- **Say what you were unsure about.** If a decision could reasonably have gone
  the other way, say which way you went and why. It is merged by the time I
  read it, so an open question is a thing for me to change next — not a gate.
  Flag anything you could not test, and anything I should smoke-test myself.
- **Warn me when the diff will not render.** Binary files, `.docx`, images, and
  anything converted between encodings show up as "file not displayed". Say so
  and describe what changed, or I will think something is broken.
- Keep it short. Three headings is plenty.

### If I ask for changes

Commit and push to the **same branch**. The PR updates itself — never open a
second PR for review feedback. Reply in the thread, and resolve it once the
change is pushed.

---

## My environment

Assume all of this unless I say otherwise.

| | |
|---|---|
| OS | Windows |
| Editor | VS Code, with the **GitHub Pull Requests** extension |
| Shell | **Windows PowerShell 5.1** — the one that ships with Windows |

### PowerShell 5.1 rules

These are not style preferences. Snippets that break them fail on my machine.

- **No `&&`.** PowerShell 5.1 rejects it: *"the token '&&' is not a valid
  statement separator in this version"*. Use `;` to chain, or
  `if ($?) { ... }` when a step must not run after a failure.
  ```powershell
  git add . ; if ($?) { git commit -m "message" } ; if ($?) { git push }
  ```
- **Write files as UTF-8, explicitly.** `>` and `Set-Content` default to UTF-16
  in 5.1, and Git treats a UTF-16 file as **binary** — no diff, no review.
  ```powershell
  Set-Content -Encoding utf8 -Path notes.md -Value "# Notes"
  ```
- **Quote paths with spaces**: `cd "C:\Users\Me\My Projects\Thing"`
- Single-quote anything containing `$`, or PowerShell will expand it.

---

## Attribution — read this once

An agent working here has no GitHub identity of its own. It acts through **my**
GitHub authorization, so every push, pull request, and comment shows up under my
account. The commit author field and a `Co-Authored-By` trailer are the only
record of who actually wrote it.

That is the real reason for the PR rule: my name is on everything, so I read the
diff before it lands.

---

## For me — the VS Code side

**Start a change**
Branch name, bottom-left corner → *Create new branch…*

**Commit**
`Ctrl+Shift+G`, type the message, `Ctrl+Enter`

**Publish**
The blue **Publish Branch** button in Source Control

**Open the PR**
`Ctrl+Shift+P` → *Create Pull Request*

**Review it**
GitHub icon in the Activity Bar → the PR → **Files Changed** → click each file.
Hover a line number → **+** to comment.

**Merge**
Claude merges. If you are merging one yourself: bottom of the PR tab, squash
and merge, and tick **Delete branch**.

**Afterwards — the step that is easy to forget**
`Ctrl+Shift+P` → **Exit Review Mode**, then:
```powershell
git switch main ; git pull ; git fetch --prune
```
Merging on GitHub does not move your local `main`, and does not take VS Code out
of review mode. If the PR panel still shows the merged PR, this is why.

---

## About this repository

<!-- Replace this section when you paste the file into a new repo. -->

- **What it is:** _one line_
- **How to run it:** _command_
- **How to test it:** _command_
- **Anything unusual:** _generated files, big binaries, things not to edit by hand_
