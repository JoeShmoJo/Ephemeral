const L = require('./lib.js');
const { d, C, PAGE_W, code, paste, callout, grid, P, B, N, H1, H1c, H2, H3, SP, toRuns, MONO } = L;
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, TableOfContents,
  PageOrientation, LevelFormat, Header, Footer, PageNumber, BorderStyle, convertInchesToTwip,
} = d;
const fs = require('fs');

const body = [];
const A = (...x) => body.push(...x);

/* ============================ COVER ============================ */
A(
  new Paragraph({ spacing: { before: 1200, after: 0 }, children: [
    new TextRun({ text: 'Git + GitHub', size: 72, bold: true, color: C.h1, font: 'Segoe UI' })]}),
  new Paragraph({ spacing: { before: 0, after: 120 }, children: [
    new TextRun({ text: 'PowerShell Cheat Sheet', size: 72, bold: true, color: C.h2, font: 'Segoe UI' })]}),
  new Paragraph({ spacing: { before: 0, after: 600 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: '0969DA', space: 8 } },
    children: [new TextRun({ text: 'Everything for a solo project on Windows — create, save, sync, and un-break a repository.', size: 24, color: '424A53', font: 'Segoe UI' })]}),
);

A(H1c('How to use this sheet'));
A(P('Every command below is meant to be **pasted into PowerShell** while you are sitting inside your project folder. Blue-tinted blocks are complete, copy-the-whole-thing snippets. Grey blocks are single commands, explained one at a time.'));
A(P('Open the **Navigation Pane** (View ▸ Navigation Pane, or *Ctrl+F*) to jump between sections. Every heading in this document appears there.'));

A(H2('Colour key'));
A(grid([1900, 3300, 4880], [
  ['Colour', 'Means', 'Example'],
  ['Red', 'The program you are running', 'git'],
  ['Purple', 'The git sub-command (the verb)', 'git status'],
  ['Blue', 'A switch / option', 'git log --oneline'],
  ['Dark blue', 'Text, paths, and URLs', 'git commit -m "my message"'],
  ['Orange', 'YOU MUST REPLACE THIS', 'git remote add origin https://github.com/USERNAME/REPOSITORY.git'],
  ['Green', 'Branch and remote names', 'git push -u origin main'],
], { mono: [2] }));

A(SP(160));
A(callout('tip', 'The single most useful command in Git is `git status`. When you are unsure of anything — before or after — run it. It tells you what branch you are on, what has changed, and usually what to type next.'));

/* ============================ TOC ============================ */
A(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: toRuns('Contents') }));
A(new TableOfContents('Contents', { hyperlink: true, headingStyleRange: '1-3' }));
A(new Paragraph({ spacing: { before: 200 }, children: [new TextRun({
  text: 'If this list is blank or out of date: click it, then press F9 to rebuild it.', italics: true, size: 18, color: C.cmt })]}));

/* ============================ QUICK START ============================ */
A(H1('Quick start: the one-liners'));
A(P('These are the blocks you will use 95% of the time. Each one is self-contained — paste the whole thing.'));

A(H2('Save my work and upload it'));
A(P('The everyday loop. Change the message in quotes to describe what you actually did.'));
A(paste(['git add . && git commit -m "describe what I changed" && git push']));
A(callout('note', 'The `&&` chain needs **PowerShell 7+**. Check with `$PSVersionTable.PSVersion`. On Windows PowerShell 5.1, replace every `&&` with `;` — but note that `;` runs the next command even if the previous one failed.'));

A(H2('Get the latest version from GitHub'));
A(paste(['git pull']));
A(P('If you have local edits in progress, commit them first (block above), then pull.'));

A(H2('What is going on right now?'));
A(paste(['git status && git log --oneline -10']));

A(H2('Brand-new repository, start to finish'));
A(P('Run this **inside your project folder**, after creating an empty repository on GitHub. Replace the URL.'));
A(paste([
  'git init',
  'git add .',
  'git commit -m "initial commit"',
  'git branch -M main',
  'git remote add origin https://github.com/USERNAME/REPOSITORY.git',
  'git push -u origin main',
]));

A(H2('Throw away everything I did locally and match GitHub'));
A(callout('danger', 'This **permanently discards** your uncommitted work. Run `git status` first and be sure.'));
A(paste(['git restore . && git pull']));

A(H2('Copy an existing GitHub repository onto this PC'));
A(paste([
  'cd C:\\Projects\\A_REPOSITORIES',
  'git clone https://github.com/USERNAME/REPOSITORY.git',
  'cd REPOSITORY',
]));

/* ============================ ONE-TIME SETUP ============================ */
A(H1('One-time setup'));
A(P('Do this once per computer. You never have to think about it again.'));

A(H2('Check that Git is installed'));
A(code(['git --version']));
A(P('No version number? Install it, then **close and reopen PowerShell** so the new PATH is picked up:'));
A(code(['winget install --id Git.Git -e']));

A(H2('Tell Git who you are'));
A(P('Every commit is stamped with this. Use the same email as your GitHub account.'));
A(paste([
  'git config --global user.name "Your Name"',
  'git config --global user.email "you@example.com"',
]));

A(H2('Sensible defaults worth setting'));
A(paste([
  'git config --global init.defaultBranch main',
  'git config --global pull.rebase false',
  'git config --global core.autocrlf true',
  'git config --global credential.helper manager',
]));
A(grid([2600, 7480], [
  ['Setting', 'Why'],
  ['init.defaultBranch main', 'New repositories start on `main`, matching GitHub — no more `git branch -M main`.'],
  ['pull.rebase false', '`git pull` merges instead of rebasing. Simpler and safer when you are working alone.'],
  ['core.autocrlf true', 'Handles Windows vs. Unix line endings so files do not show up as "entirely changed".'],
  ['credential.helper manager', 'Windows remembers your GitHub sign-in instead of asking every push.'],
], { mono: [0] }));

A(H2('Signing in to GitHub'));
A(P('The first `git push` opens a browser window — sign in there and Windows stores the credential. **Your account password will not work at the PowerShell prompt**; GitHub stopped accepting it. If you are ever asked for a password in the terminal, paste a *Personal Access Token* instead (GitHub ▸ Settings ▸ Developer settings ▸ Tokens).'));

A(H2('See what is configured'));
A(code(['git config --global --list']));

/* ============================ NEW REPO ============================ */
A(H1('Create a new repository'));
A(H2('Before you start'));
A(B('You already have a project folder on your PC.'));
A(B('You created an **empty** repository on GitHub.'));
A(B('Do **not** tick "Add a README", ".gitignore", or "license" when creating it — those create commits that your local repository does not have, and your first push will be rejected.'));
A(callout('tip', 'If you already ticked one of those boxes, do not start over. Just run `git pull origin main --allow-unrelated-histories` before your first push.'));

A(H2('Step by step'));
A(H3('1. Open PowerShell in the project folder'));
A(code(['cd C:\\Projects\\A_REPOSITORIES\\Ephemeral']));
A(callout('tip', 'Faster: in File Explorer, open the folder, then Shift+right-click in the empty space ▸ **Open PowerShell window here**. Or type `cd ` (with the space) and drag the folder onto the window.'));

A(H3('2. Initialise the local repository'));
A(code(['git init']));
A(P('This creates a hidden `.git` folder. That folder *is* your repository — the history lives there, not on GitHub.'));

A(H3('3. Stage all files'));
A(code(['git add .']));
A(P('The `.` means "everything in this folder and below". Staging is you saying *these are the changes I want in my next snapshot*.'));

A(H3('4. Make the first commit'));
A(code(['git commit -m "initial commit"']));

A(H3('5. Name the branch main'));
A(code(['git branch -M main']));
A(P('GitHub expects `main`. Older Git versions default to `master`; `-M` renames it either way.'));

A(H3('6. Point the local repository at GitHub'));
A(code(['git remote add origin https://github.com/USERNAME/REPOSITORY.git']));
A(P('`origin` is just a nickname for the GitHub URL. Example:'));
A(code(['git remote add origin https://github.com/JoeShmoJo/Ephemeral.git']));

A(H3('7. Push'));
A(code(['git push -u origin main']));
A(P('`-u` links your local `main` to GitHub\'s `main`, so from now on plain `git push` and `git pull` know where to go.'));

A(H2('Short version'));
A(paste([
  'git init',
  'git add .',
  'git commit -m "initial commit"',
  'git branch -M main',
  'git remote add origin https://github.com/USERNAME/REPOSITORY.git',
  'git push -u origin main',
]));
A(P('**Memory aid:**  init → add → commit → branch → remote → push'));

A(H2('Fixing a wrong remote URL'));
A(P('Typo in the URL, or you pointed it at the wrong repository:'));
A(code([
  'git remote -v',
  'git remote set-url origin https://github.com/USERNAME/REPOSITORY.git',
]));

/* ============================ EVERYDAY ============================ */
A(H1('The everyday workflow'));
A(P('Once the repository exists, this is the entire job.'));

A(H2('The three-command loop'));
A(code([
  'git status                              # what changed?',
  'git add .                               # stage all of it',
  'git commit -m "describe what I changed" # snapshot it locally',
  'git push                                # send it to GitHub',
]));
A(P('**Memory aid:**  add → commit → push'));
A(paste(['git add . && git commit -m "describe what I changed" && git push']));

A(H2('Staging only some files'));
A(P('When you changed five things but only want to commit two of them:'));
A(code([
  'git add notes.md src\\main.py',
  'git commit -m "update notes and main script"',
]));

A(H2('Writing a commit message worth reading'));
A(P('Finish the sentence *"If applied, this commit will…"*. Present tense, under ~60 characters, says **what and why** — not "update files".'));
A(grid([5040, 5040], [
  ['Good', 'Not so good'],
  ['add retry logic to the download step', 'fixes'],
  ['fix crash when the input file is empty', 'update'],
  ['rewrite README install instructions', 'stuff'],
  ['remove unused test fixtures', 'asdf'],
]));

A(H2('Commit often, push whenever'));
A(P('A commit is a local save point and costs nothing — make them small and frequent. A push is a backup to GitHub. There is no penalty for pushing ten times a day.'));

/* ============================ SYNC ============================ */
A(H1('Updating from GitHub, and conflicts'));
A(P('These five situations cover essentially every sync problem you will hit working solo across two machines.'));

A(H2('Situation 1 — Normal update'));
A(P('You changed files locally and want them on GitHub.'));
A(code(['git status', 'git add .', 'git commit -m "describe what I changed"', 'git push']));
A(paste(['git add . && git commit -m "describe what I changed" && git push']));

A(H2('Situation 2 — Push rejected because GitHub has changes'));
A(P('If GitHub has commits your PC does not have (you edited on the website, or from another machine), `git push` is rejected. The message says *"Updates were rejected because the remote contains work that you do not have locally."*'));
A(P('Bring the GitHub changes down first, then push:'));
A(code(['git pull', 'git push']));
A(paste(['git pull && git push']));
A(callout('note', 'This is not an error you caused. It is Git protecting the commits that are already on GitHub.'));

A(H2('Situation 3 — The pull produced a merge conflict'));
A(P('Git could not decide which version of a line to keep, so it is asking you. Nothing is broken and nothing is lost.'));
A(N('See which files are affected:'));
A(code(['git status']));
A(N('Open each conflicted file. You will see markers like this:'));
A(code([
  '<<<<<<< HEAD',
  'your local version of the line',
  '=======',
  'the version that came from GitHub',
  '>>>>>>> origin/main',
]));
A(N('Edit the file so it reads exactly the way you want it — keep one side, keep both, or rewrite it entirely.'));
A(N('**Delete all three marker lines** (`<<<<<<<`, `=======`, `>>>>>>>`), then save.'));
A(N('Stage, commit, push:'));
A(code(['git add .', 'git commit -m "resolve merge conflict"', 'git push']));
A(callout('tip', 'To find every leftover marker before you commit: `git diff --check`, or search the folder for `<<<<<<<`.'));
A(P('**Abort and pretend it never happened:**'));
A(code(['git merge --abort']));
A(P('That returns you to exactly where you were before the pull.'));
A(P('**Memory aid:**  pull → resolve → add → commit → push'));

A(H2('Situation 4 — Discard my local changes, take GitHub\'s version'));
A(callout('danger', '`git restore .` throws away uncommitted edits to tracked files. They are not recoverable. Run `git status` first and read the list.'));
A(code(['git status', 'git restore .', 'git pull']));
A(paste(['git restore . && git pull']));

A(H2('Situation 5 — Also delete untracked files'));
A(P('`git restore .` does not touch files Git has never seen. To remove those as well:'));
A(P('**Always preview first.** `-n` means "dry run — show me, do not delete":'));
A(code(['git clean -fdn']));
A(P('Read that list carefully. If it is correct:'));
A(code(['git clean -fd', 'git pull']));
A(callout('danger', '`git clean -fd` permanently deletes untracked files and folders. There is no undo, and they never go to the Recycle Bin.'));

A(H2('Not ready to commit, but need to pull'));
A(P('Park your changes, pull, then bring them back:'));
A(paste(['git stash', 'git pull', 'git stash pop']));
A(P('`git stash list` shows what is parked; `git stash drop` throws the top one away.'));

/* ============================ UNDO ============================ */
A(H1('Undo: the safety net'));
A(P('Almost everything in Git is reversible **once it has been committed**. That is the real reason to commit often.'));

A(grid([4400, 5680], [
  ['I want to…', 'Command'],
  ['Undo edits to one file (not yet committed)', 'git restore path\\to\\file'],
  ['Undo all uncommitted edits', 'git restore .'],
  ['Unstage a file, keep the edits', 'git restore --staged path\\to\\file'],
  ['Fix the last commit message', 'git commit --amend -m "better message"'],
  ['Add a forgotten file to the last commit', 'git add forgotten.txt && git commit --amend --no-edit'],
  ['Undo the last commit, keep the changes', 'git reset --soft HEAD~1'],
  ['Undo the last commit and its changes', 'git reset --hard HEAD~1'],
  ['Get one file back as GitHub has it', 'git checkout origin/main -- path\\to\\file'],
  ['Reverse an old commit safely', 'git revert COMMITHASH'],
  ['See everything I have done recently', 'git reflog'],
], { mono: [1] }));

A(SP(140));
A(callout('warning', 'Never `--amend` or `reset` a commit you have **already pushed** — it rewrites history that GitHub already has, and the next push will be rejected. To undo something already on GitHub, use `git revert`, which makes a new commit that cancels the old one.'));

A(H2('When you have really made a mess'));
A(P('`git reflog` lists every position `HEAD` has been in, including commits you thought you destroyed. Find the line you want, note its short hash, and go back to it:'));
A(code([
  'git reflog',
  'git reset --hard a1b2c3d   # the hash from the reflog line you want',
]));

/* ============================ BRANCHES ============================ */
A(H1('Branches (optional, but useful)'));
A(P('A branch is a parallel line of work. Try something risky on a branch and `main` stays untouched. Working alone, you can ignore branches entirely — but they are the cheapest safety net there is.'));

A(H2('Create one and switch to it'));
A(code(['git switch -c experiment']));
A(P('Then work, add, commit, push as normal. The first push needs the `-u`:'));
A(code(['git push -u origin experiment']));

A(H2('Move between branches'));
A(code(['git branch          # list branches, * marks the current one', 'git switch main', 'git switch experiment']));

A(H2('Merge the work back into main'));
A(paste(['git switch main', 'git pull', 'git merge experiment', 'git push']));

A(H2('Delete a branch you are finished with'));
A(code(['git branch -d experiment              # local', 'git push origin --delete experiment    # on GitHub']));

/* ============================ IGNORE ============================ */
A(H1('.gitignore essentials'));
A(P('A `.gitignore` file lists things Git should never track: secrets, build output, huge data files, editor cruft. It lives in the top folder of the repository and **should be committed**.'));

A(H2('Create a starter .gitignore'));
A(P('Paste this whole block — it writes the file for you:'));
A(paste([
  '@"',
  '# Windows',
  'Thumbs.db',
  'desktop.ini',
  '',
  '# Editors',
  '.vscode/',
  '.idea/',
  '',
  '# Python',
  '__pycache__/',
  '*.pyc',
  '.venv/',
  '',
  '# Node',
  'node_modules/',
  '',
  '# Secrets - never commit these',
  '.env',
  '*.key',
  '',
  '# Big / generated stuff',
  'out/',
  '*.log',
  '"@ | Set-Content -Encoding utf8 .gitignore',
]));
A(callout('note', 'That `@" … "@` is a PowerShell here-string. The closing `"@` **must be at the very start of its own line** or PowerShell will complain.'));

A(H2('I already committed something that should be ignored'));
A(P('Adding it to `.gitignore` is not enough — Git keeps tracking files it already knows about. Untrack it, keeping the file on disk:'));
A(code([
  'git rm --cached secrets.env',
  'git commit -m "stop tracking secrets.env"',
  'git push',
]));
A(callout('warning', 'The file is removed from *future* commits, but it is still in the history, and if the repository is public, treat any leaked password or key as compromised — rotate it.'));

A(H2('Check whether a file is ignored'));
A(code(['git check-ignore -v path\\to\\file']));

/* ============================ POWERSHELL ============================ */
A(H1('PowerShell notes and gotchas'));

A(H2('Paths with spaces need quotes'));
A(code(['cd "C:\\Users\\Me\\OneDrive\\My Projects\\Ephemeral"']));

A(H2('Chaining commands'));
A(grid([2200, 7880], [
  ['Operator', 'Behaviour'],
  ['&&', 'Run the next command **only if** the previous one succeeded. PowerShell 7+ only.'],
  [';', 'Run the next command **regardless** of whether the previous one failed. Works everywhere.'],
], { mono: [0] }));
A(P('Check your version with `$PSVersionTable.PSVersion`. If it starts with 5, use `;` — or install PowerShell 7 with `winget install --id Microsoft.PowerShell -e`.'));

A(H2('Quoting commit messages'));
A(P('Single quotes are safest in PowerShell, because double quotes let `$` expand into variables:'));
A(code([
  "git commit -m 'fix the $HOME lookup'   # literal text, safe",
  'git commit -m "fix the $HOME lookup"   # PowerShell replaces $HOME first',
]));

A(H2('OneDrive and cloud-synced folders'));
A(callout('warning', 'Keeping a Git repository inside OneDrive, Dropbox, or Google Drive causes real corruption — two sync engines fight over the same `.git` folder. Keep repositories somewhere local, such as `C:\\Projects`, and let GitHub be your backup.'));

A(H2('The editor opened and I cannot get out'));
A(P('If you run `git commit` without `-m`, Git opens an editor. If that editor is Vim: press `Esc`, type `:wq`, press `Enter`. To avoid it entirely, always pass `-m`, or set a friendlier editor:'));
A(code(['git config --global core.editor "code --wait"   # VS Code']));

A(H2('A long output opened a pager'));
A(P('When `git log` fills the screen with a `:` prompt, press `q` to quit. To stop that happening:'));
A(code(['git --no-pager log --oneline -20']));

/* ============================ DANGER ============================ */
A(H1('The danger zone'));
A(P('Four commands can destroy work. Everything else in Git is recoverable.'));
A(grid([3000, 7080], [
  ['Command', 'What it can cost you'],
  ['git push --force', 'Overwrites commits on GitHub. Other copies of the repository — including your other PC — break. Never use it as a routine fix for a rejected push; `git pull` is the answer there.'],
  ['git reset --hard', 'Deletes uncommitted work with no prompt. `git reflog` can rescue *committed* work, not uncommitted work.'],
  ['git clean -fd', 'Deletes untracked files and folders. No Recycle Bin. Always run `git clean -fdn` first.'],
  ['git restore .', 'Discards every uncommitted edit to tracked files.'],
], { mono: [0] }));
A(SP(140));
A(callout('danger', 'Before anything on that list, run `git status` and read it. If you are not sure, commit first — a commit you do not want costs nothing, and it makes the change undoable.'));

/* ============================ TROUBLESHOOT ============================ */
A(H1('Troubleshooting common messages'));
A(grid([3900, 6180], [
  ['Message', 'What to do'],
  ['Updates were rejected because the remote contains work that you do not have locally', 'GitHub is ahead of you. `git pull`, resolve anything it asks about, then `git push`.'],
  ['fatal: not a git repository', 'You are in the wrong folder, or never ran `git init`. Check with `git status` and `cd` to the project folder.'],
  ['fatal: remote origin already exists', 'The remote is already set. Point it somewhere else with `git remote set-url origin URL`.'],
  ['src refspec main does not match any', 'You have not committed anything yet. Run `git add .` then `git commit -m "initial commit"`.'],
  ['Please tell me who you are', 'Set `user.name` and `user.email` — see One-time setup.'],
  ['Support for password authentication was removed', 'Use the browser sign-in window, or a Personal Access Token instead of your password.'],
  ['Your local changes would be overwritten by merge', 'Commit them, or `git stash`, then pull, then `git stash pop`.'],
  ['nothing to commit, working tree clean', 'Not an error. Nothing has changed since your last commit.'],
  ['detached HEAD', 'You are looking at an old commit, not a branch. `git switch main` returns you to normal.'],
  ['error: pathspec ... did not match any file', 'A typo in a filename or branch name. `git status` and `git branch` show the real names.'],
]));

/* ============================ INDEX ============================ */
A(H1('Command index'));
A(grid([3900, 6180], [
  ['Command', 'Does what'],
  ['git status', 'What has changed, what branch you are on, what to do next'],
  ['git add .', 'Stage every change in this folder and below'],
  ['git add FILE', 'Stage one file'],
  ['git commit -m "msg"', 'Snapshot the staged changes locally'],
  ['git push', 'Send commits to GitHub'],
  ['git pull', 'Bring GitHub commits down and merge them'],
  ['git clone URL', 'Copy a GitHub repository onto this PC'],
  ['git init', 'Turn the current folder into a repository'],
  ['git remote -v', 'Show which GitHub repository this is linked to'],
  ['git remote set-url origin URL', 'Repoint it at a different repository'],
  ['git log --oneline -10', 'Last ten commits, one line each'],
  ['git log --oneline --graph --all', 'Visual history including branches'],
  ['git diff', 'Exactly what you changed but have not staged'],
  ['git diff --staged', 'What you have staged but not committed'],
  ['git show COMMITHASH', 'Everything a specific commit changed'],
  ['git branch', 'List branches'],
  ['git switch -c NAME', 'Create a branch and move to it'],
  ['git switch main', 'Move back to main'],
  ['git merge NAME', 'Merge a branch into the current one'],
  ['git stash', 'Park uncommitted changes'],
  ['git stash pop', 'Bring parked changes back'],
  ['git restore FILE', 'Undo uncommitted edits to a file'],
  ['git restore --staged FILE', 'Unstage a file, keep the edits'],
  ['git revert COMMITHASH', 'Make a new commit that undoes an old one'],
  ['git reflog', 'Every recent position of HEAD — the rescue tool'],
  ['git rm --cached FILE', 'Stop tracking a file, keep it on disk'],
  ['git check-ignore -v FILE', 'Explain why a file is being ignored'],
  ['git config --global --list', 'Show your global settings'],
], { mono: [0] }));

/* ============================ CARD ============================ */
A(H1('One-page summary'));
A(P('Print this page and stick it next to the monitor.'));

A(H2('Normal day'));
A(paste(['git add . && git commit -m "what I changed" && git push']));
A(H2('GitHub changed too'));
A(paste(['git pull', '# fix conflicts if it asks', 'git add . && git commit -m "resolve merge conflict" && git push']));
A(H2('Bin my local changes'));
A(paste(['git restore . && git pull']));
A(H2('Bin local changes and untracked files'));
A(paste(['git clean -fdn        # PREVIEW - read the list', 'git restore . && git clean -fd && git pull']));
A(H2('New repository'));
A(paste([
  'git init && git add . && git commit -m "initial commit" && git branch -M main',
  'git remote add origin https://github.com/USERNAME/REPOSITORY.git',
  'git push -u origin main',
]));
A(H2('When lost'));
A(paste(['git status']));

/* --- separate adjacent tables so Word does not merge them into one --- */
const spaced = [];
for (let i = 0; i < body.length; i++) {
  spaced.push(body[i]);
  if (body[i] instanceof d.Table && body[i + 1] instanceof d.Table) spaced.push(SP(0));
}

/* ============================ DOCUMENT ============================ */
const doc = new Document({
  creator: 'Git Cheat Sheet',
  title: 'Git + GitHub PowerShell Cheat Sheet',
  description: 'Practical Git reference for Windows PowerShell',
  features: { updateFields: true },
  styles: {
    default: {
      document:  { run: { font: 'Segoe UI', size: 21, color: '1F2328' }, paragraph: { spacing: { line: 276, before: 80, after: 80 } } },
      heading1:  { run: { font: 'Segoe UI', size: 34, bold: true, color: C.h1 },
                   paragraph: { spacing: { before: 320, after: 160 },
                     border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: 'B6D9F5', space: 6 } } } },
      heading2:  { run: { font: 'Segoe UI', size: 26, bold: true, color: C.h2 }, paragraph: { spacing: { before: 280, after: 100 } } },
      heading3:  { run: { font: 'Segoe UI', size: 22, bold: true, color: C.h3 }, paragraph: { spacing: { before: 200, after: 80 } } },
    },
    paragraphStyles: [
      { id: 'TOC1', name: 'toc 1', basedOn: 'Normal', quickFormat: true, run: { bold: true, size: 21 }, paragraph: { spacing: { before: 120, after: 40 } } },
      { id: 'TOC2', name: 'toc 2', basedOn: 'Normal', quickFormat: true, run: { size: 20 }, paragraph: { indent: { left: 300 }, spacing: { before: 20, after: 20 } } },
      { id: 'TOC3', name: 'toc 3', basedOn: 'Normal', quickFormat: true, run: { size: 19, color: '57606A' }, paragraph: { indent: { left: 600 }, spacing: { before: 20, after: 20 } } },
    ],
  },
  numbering: {
    config: [{
      reference: 'steps',
      levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.START,
        style: { paragraph: { indent: { left: 420, hanging: 260 } } } }],
    }],
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } },
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: 'D0D7DE', space: 6 } },
        children: [
          new TextRun({ text: 'Git + GitHub PowerShell Cheat Sheet', size: 16, color: '8C959F' }),
          new TextRun({ text: '\t\t', size: 16 }),
          new TextRun({ children: ['Page ', PageNumber.CURRENT, ' of ', PageNumber.TOTAL_PAGES], size: 16, color: '8C959F' }),
        ] })] }),
    },
    children: spaced,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = process.argv[2] || 'Git-Cheat-Sheet.docx';
  fs.writeFileSync(out, buf);
  console.log('wrote', out, buf.length, 'bytes');
});
