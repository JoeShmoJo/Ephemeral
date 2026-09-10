const L = require('./lib.js');
const { d, C, PAGE_W, code, paste, callout, grid, P, B, N, H1, H1c, H2, H3, SP, toRuns } = L;
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, TableOfContents,
  Footer, PageNumber, BorderStyle, LevelFormat,
} = d;
const fs = require('fs');

const body = [];
const A = (...x) => body.push(...x);

/* ============================ COVER ============================ */
A(
  new Paragraph({ spacing: { before: 1200, after: 0 }, children: [
    new TextRun({ text: 'Pull Requests', size: 72, bold: true, color: C.h1, font: 'Segoe UI' })]}),
  new Paragraph({ spacing: { before: 0, after: 120 }, children: [
    new TextRun({ text: 'in VS Code', size: 72, bold: true, color: C.h2, font: 'Segoe UI' })]}),
  new Paragraph({ spacing: { before: 0, after: 600 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: '0969DA', space: 8 } },
    children: [new TextRun({ text: 'Branch, propose, review, merge — without leaving the editor. With the PowerShell equivalent of every step.', size: 24, color: '424A53', font: 'Segoe UI' })]}),
);

A(H1c('How to use this sheet'));
A(P('This covers the **GitHub Pull Requests** extension for VS Code. Menu paths are written with ▸, so **Ctrl+Shift+P ▸ Create Pull Request** means "open the Command Palette and run that command".'));
A(P('Every step also has its **PowerShell equivalent** in a grey box — the extension is a front end for the same Git commands, and knowing both means you are never stuck when a button does not appear.'));
A(P('Open the **Navigation Pane** (View ▸ Navigation Pane, or *Ctrl+F*) to jump between sections.'));
A(callout('note', 'VS Code and the extension change their layout every few releases. **The Command Palette is the part that does not move** — press `Ctrl+Shift+P`, type *pull request*, and every command this sheet mentions is in that list.'));

/* ============================ TOC ============================ */
A(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: toRuns('Contents') }));
A(new TableOfContents('Contents', { hyperlink: true, headingStyleRange: '1-3' }));
A(new Paragraph({ spacing: { before: 200 }, children: [new TextRun({
  text: 'If this list is blank or out of date: click it, then press F9 to rebuild it.', italics: true, size: 18, color: C.cmt })]}));

/* ============================ WHY ============================ */
A(H1('What a pull request is'));
A(P('A pull request is a **proposal**: *"here are commits on a branch — please look at them, then put them into main."* It is not a Git feature; it is a GitHub feature wrapped around two branches. The PR is a page that shows the difference between your branch and `main`, gathers comments and test results, and ends with a merge button.'));

A(H2('The shape of it'));
A(P('branch  →  commit  →  push  →  **open PR**  →  review  →  **merge**  →  delete branch'));
A(P('Nothing is added to `main` until the merge. Until then the branch is a sandbox: push broken code to it as often as you like.'));

A(H2('Why bother when you are the only developer'));
A(B('**You review your own diff.** Reading every changed line in one screen catches the debug print you left in, the file you did not mean to commit, the password in a config.'));
A(B('**`main` stays releasable.** If a branch turns out badly you close the PR and delete it. Nothing to undo.'));
A(B('**Tests run before the merge, not after.** GitHub Actions report on the PR, so a red check stops a bad merge.'));
A(B('**The reasoning is written down.** In six months the PR description explains why, which the code never does.'));
A(B('**It is the habit every team expects.** Practising alone costs nothing.'));
A(callout('tip', 'Working solo, keep branches small and short-lived — one change, one PR, merged the same day. A branch that lives for three weeks turns into a merge conflict.'));

/* ============================ SETUP ============================ */
A(H1('Setup, once'));

A(H2('Install the extension'));
A(N('**Ctrl+Shift+X** opens Extensions.'));
A(N('Search for **GitHub Pull Requests**, published by GitHub.'));
A(N('Install. A **GitHub icon** appears in the Activity Bar down the left edge.'));

A(H2('Sign in'));
A(P('Click the GitHub icon, then **Sign in**. A browser window opens; approve, and VS Code takes over. If nothing happens, use the **Accounts** icon at the bottom of the Activity Bar ▸ *Sign in with GitHub*.'));
A(callout('note', 'This sign-in is separate from the credential Git uses to push. It is normal to authorise GitHub twice on a new machine — once for the extension, once on your first `git push`.'));

A(H2('Check the repository is connected'));
A(P('The extension only appears when the folder you have open is a Git repository with a GitHub remote:'));
A(code(['git remote -v']));
A(P('No output means there is no remote yet — see the Git cheat sheet for `git remote add origin`.'));

A(H2('Two settings worth changing'));
A(grid([4000, 6080], [
  ['Setting', 'Why'],
  ['Git: Autofetch', 'VS Code notices when GitHub has moved ahead, so the branch you are working from is not silently stale. **Ctrl+,** then search *autofetch*.'],
  ['GitHub Pull Requests: Default Merge Method', 'Set it to *squash* if you want each PR to land on `main` as one tidy commit. Search *default merge method*.'],
]));

/* ============================ TOUR ============================ */
A(H1('Where everything lives'));
A(grid([3000, 7080], [
  ['Where', 'What it is for'],
  ['GitHub icon (Activity Bar)', 'The **Pull Requests** and **Issues** lists. Your PRs, PRs assigned to you, all open PRs. This is the home base.'],
  ['Source Control (Ctrl+Shift+G)', 'Stage, commit, push. The **Create Pull Request** button appears here after you push a branch.'],
  ['Branch name (bottom-left)', 'Click it to switch or create a branch. Fastest branch switcher in the app.'],
  ['Command Palette (Ctrl+Shift+P)', 'Every command by name. Type *pull request* or *git* to browse.'],
  ['PR description tab', 'Opens when you click a PR: description, checks, reviewers, comment box, and the merge button.'],
  ['Changes in Pull Request', 'Appears while you have a PR checked out. The file-by-file diff you review from.'],
]));

/* ============================ CREATE ============================ */
A(H1('Make a change and open a PR'));
A(P('The whole loop, start to finish. This is the section to keep open the first few times.'));

A(H2('1 — Start a branch'));
A(P('Click the **branch name in the bottom-left corner** ▸ *Create new branch…* ▸ type a name ▸ Enter. Name it after the change: `fix-login-crash`, `add-export-button`.'));
A(P('In PowerShell:'));
A(code(['git switch -c fix-login-crash']));
A(callout('warning', 'Start the branch **before** you make the change if you can. If you have already edited files, do not worry — uncommitted edits follow you onto the new branch.'));

A(H2('2 — Make the change and commit'));
A(P('Edit as usual. Then **Ctrl+Shift+G**, type a message in the box, and press **Ctrl+Enter** to commit. VS Code stages everything for you if nothing is staged.'));
A(code(['git add .', 'git commit -m "fix the crash when the login form is empty"']));

A(H2('3 — Publish the branch'));
A(P('The blue button in Source Control now reads **Publish Branch**. Click it. That creates the branch on GitHub, which is what makes a PR possible.'));
A(code(['git push -u origin fix-login-crash']));

A(H2('4 — Open the pull request'));
A(P('VS Code offers a **Create Pull Request** button as soon as the branch is published. Or: **Ctrl+Shift+P ▸ GitHub Pull Requests: Create Pull Request**.'));
A(P('The panel that opens asks for four things:'));
A(grid([2500, 7580], [
  ['Field', 'What to put'],
  ['Base', 'The branch you want to merge **into** — almost always `main`.'],
  ['Merge (or Branch)', 'The branch the change is **on** — the one you just published.'],
  ['Title', 'Same style as a commit message: *fix crash when the login form is empty*.'],
  ['Description', 'Why, not what. The diff already shows what. Note anything you are unsure about.'],
]));
A(P('Click **Create**. VS Code opens the PR page in a tab, and you are now "in review mode" on that PR.'));
A(callout('tip', 'Not finished yet? Use the arrow next to Create and choose **Create as Draft**. A draft PR runs the tests but cannot be merged until you press *Ready for review* — ideal for pushing work in progress from one machine to another.'));

A(H2('5 — Read your own diff'));
A(P('In the GitHub view, expand your PR ▸ **Files Changed** (or the *Changes in Pull Request* section). Click each file; VS Code opens a red/green diff. Read every line before merging your own work — this is the entire point of the exercise.'));

A(H2('6 — Merge'));
A(P('On the PR tab, scroll to the bottom and pick a merge method, then confirm. Tick **Delete branch** so the branch does not pile up.'));
A(grid([2500, 7580], [
  ['Method', 'What lands on main'],
  ['Create a merge commit', 'Every commit from the branch, plus a merge commit. Full history, messier graph.'],
  ['Squash and merge', 'One commit containing the whole change. Tidy `main`; the good default working solo.'],
  ['Rebase and merge', 'Each commit replayed onto `main` with no merge commit. Linear history, no record of the branch.'],
]));

A(H2('7 — Get back to main'));
A(P('The merge happened on GitHub, so your PC does not know about it yet:'));
A(paste(['git switch main', 'git pull']));
A(P('In VS Code: click the branch name ▸ `main`, then the **sync** button (⟳) in the status bar. If you deleted the branch on GitHub, clean up the local copy too:'));
A(code(['git branch -d fix-login-crash']));

/* ============================ REVIEW ============================ */
A(H1('Reviewing a pull request'));
A(P('Reviewing your own PR is worth doing properly. Reviewing someone else\'s uses exactly the same tools.'));

A(H2('Look without changing anything'));
A(P('Click a PR in the GitHub view. The **description tab** opens with the conversation, the checks, and the file list. Clicking a file opens a read-only diff. This does not touch your working folder.'));

A(H2('Check the branch out to run it'));
A(P('To actually run the code, check the PR out: on the PR tab press **Checkout**, or **Ctrl+Shift+P ▸ GitHub Pull Requests: Checkout Pull Request**. VS Code switches your working folder to that branch.'));
A(P('When you are done, press **Exit Review Mode** in the Pull Requests view — it puts you back on the branch you came from.'));
A(code(['git switch fix-login-crash   # the same thing, by hand', 'git switch main              # and back']));
A(callout('warning', 'Commit or stash your own work before checking out someone else\'s PR. VS Code will refuse the switch if uncommitted changes are in the way.'));

A(H2('Comment on a specific line'));
A(N('Open the file diff from the PR.'));
A(N('Hover over the line number. A **+** appears — click it.'));
A(N('Type the comment.'));
A(N('**Add Comment** posts it immediately. **Start Review** holds it back so several comments post together as one review.'));

A(H2('Finish the review'));
A(P('Once you have a review pending, use **Submit Review** on the PR tab and pick one:'));
A(grid([2800, 7280], [
  ['Verdict', 'Means'],
  ['Comment', 'Notes, no judgement. Does not block or unblock the merge.'],
  ['Approve', 'Good to merge. **GitHub will not let you approve your own PR** — merge it directly instead.'],
  ['Request changes', 'Blocks the merge until the reviewer approves a later version.'],
]));

A(H2('Answer comments and push a fix'));
A(P('Reply in the thread on the PR tab, then **Resolve conversation** when it is dealt with. To change the code, just commit and push to the same branch:'));
A(paste(['git add .', 'git commit -m "address review comments"', 'git push']));
A(P('The PR updates itself. There is no "new PR" step — a pull request tracks the branch, so every push to that branch appears in it automatically.'));

/* ============================ CHECKS ============================ */
A(H1('Checks, conflicts, and staying current'));

A(H2('Reading the checks'));
A(P('If the repository runs GitHub Actions, results appear on the PR tab as it goes.'));
A(grid([2400, 7680], [
  ['Symbol', 'Meaning'],
  ['Yellow dot', 'Still running. The merge button waits.'],
  ['Green tick', 'Passed. Safe to merge.'],
  ['Red cross', 'Failed. Click **Details** to open the log on GitHub — the failing step is expanded for you.'],
]));
A(P('Fix it the same way as any other change: commit to the branch, push, and the checks run again.'));

A(H2('"This branch is out of date with main"'));
A(P('Someone (or you, from another machine) merged something else first. Bring `main` into your branch:'));
A(paste(['git switch fix-login-crash', 'git fetch origin', 'git merge origin/main']));
A(P('If it merges cleanly, `git push` and the warning clears. In VS Code the same thing is **Ctrl+Shift+P ▸ Git: Merge Branch… ▸ origin/main**.'));

A(H2('A conflict inside a PR'));
A(P('GitHub will say the branch has conflicts and refuse to merge. Resolve them **on your PC**, not on the website:'));
A(N('Run the merge above. VS Code lists the conflicted files in Source Control under *Merge Changes*.'));
A(N('Open each one. VS Code shows **Accept Current Change / Accept Incoming Change / Accept Both** buttons above the conflict — or click *Resolve in Merge Editor* for a three-pane view.'));
A(N('"Current" is your branch. "Incoming" is `main`.'));
A(N('Stage each resolved file, commit, push.'));
A(code(['git add .', 'git commit -m "merge main into fix-login-crash"', 'git push']));
A(callout('tip', 'Merge `main` into a long-running branch every day or two. Small conflicts resolved early beat one enormous conflict at merge time.'));

/* ============================ EXTRAS ============================ */
A(H1('Things worth knowing'));

A(H2('Link a PR to an issue'));
A(P('Put a closing keyword in the PR description and GitHub closes the issue when the PR merges:'));
A(code(['Closes #14', 'Fixes #14', 'Resolves #14']));
A(P('Typing `#` in the description box brings up a searchable list of issues.'));

A(H2('Draft pull requests'));
A(P('A draft says "not ready, do not merge". Checks still run. Turn a normal PR into a draft, or a draft into a real one, with the button on the PR tab.'));

A(H2('Create issues without leaving the editor'));
A(P('Select a line of code ▸ right-click ▸ **Create Issue From Selection**. The issue links back to the exact line. A `TODO` comment can be turned into an issue the same way.'));

A(H2('Protect main so the habit sticks'));
A(P('On GitHub: repository ▸ **Settings ▸ Branches ▸ Add rule** ▸ branch name `main` ▸ tick *Require a pull request before merging*. Now a direct push to `main` is rejected and you have to use a PR — worth it once the habit is worth keeping.'));

A(H2('The PowerShell equivalent, if you ever want it'));
A(P('GitHub\'s own CLI does PRs from the terminal. Useful when VS Code is not open:'));
A(code([
  'winget install --id GitHub.cli -e',
  'gh auth login',
  'gh pr create --fill',
  'gh pr status',
  'gh pr checks',
  'gh pr merge --squash --delete-branch',
]));

/* ============================ PALETTE ============================ */
A(H1('Command Palette reference'));
A(P('Press **Ctrl+Shift+P** and start typing. These are the commands worth knowing by name.'));
A(grid([4600, 5480], [
  ['Type this', 'Does what'],
  ['Create Pull Request', 'Opens the create-PR panel for the current branch'],
  ['Checkout Pull Request', 'Switches your working folder to a PR\'s branch'],
  ['Exit Review Mode', 'Leaves a checked-out PR and returns to your branch'],
  ['Open Pull Request on GitHub', 'Opens the PR in a browser'],
  ['Refresh Pull Requests View', 'When the list is showing something stale'],
  ['Git: Create Branch', 'New branch from where you are'],
  ['Git: Checkout to', 'Switch branches'],
  ['Git: Publish Branch', 'Push a new local branch to GitHub'],
  ['Git: Sync', 'Pull then push, in one action'],
  ['Git: Merge Branch', 'Merge another branch into this one'],
  ['Git: Undo Last Commit', 'Puts the last commit\'s changes back as edits'],
  ['Git: Stash', 'Park uncommitted changes'],
]));

A(H2('Keyboard shortcuts'));
A(grid([2600, 7480], [
  ['Keys', 'Opens'],
  ['Ctrl+Shift+P', 'Command Palette — everything'],
  ['Ctrl+Shift+G', 'Source Control: stage, commit, push'],
  ['Ctrl+Enter', 'Commit, when the message box has focus'],
  ['Ctrl+Shift+X', 'Extensions'],
  ['Ctrl+,', 'Settings'],
  ['Ctrl+`', 'The terminal'],
]));

/* ============================ TROUBLE ============================ */
A(H1('When it will not behave'));
A(grid([3900, 6180], [
  ['Symptom', 'Fix'],
  ['No **Create Pull Request** button', 'The branch is not published yet. Push it: `git push -u origin BRANCHNAME`. Also check you are not sitting on `main` — you cannot open a PR from `main` into `main`.'],
  ['The GitHub view is empty or says sign in', 'Accounts icon ▸ sign out of GitHub ▸ sign in again. If it loops, close VS Code, reopen, retry.'],
  ['GitHub view does not appear at all', 'The open folder is not a Git repository with a GitHub remote. Check `git remote -v`, and make sure you opened the project folder itself, not its parent.'],
  ['I committed to `main` by mistake', 'Move the commits onto a branch — see below.'],
  ['Checkout is refused', 'Uncommitted changes are in the way. Commit them, or `git stash`, then retry.'],
  ['PR shows commits I did not expect', 'The base is wrong, or your branch started from an old `main`. Merge `origin/main` in and check the base branch on the PR tab.'],
  ['Merge button is greyed out', 'A check is still running, a review requested changes, or there is a conflict. The PR tab says which.'],
  ['Pushed but the PR did not update', 'You pushed to a different branch than the PR tracks. `git status` names the current branch; compare it with the PR\'s.'],
]));

A(H2('Moving accidental commits off main'));
A(P('You committed straight to `main` and now want them in a PR instead. Nothing is lost — the commits just need a branch of their own.'));
A(paste([
  'git switch -c fix-login-crash',
  'git switch main',
  'git reset --hard origin/main',
  'git switch fix-login-crash',
  'git push -u origin fix-login-crash',
]));
A(callout('danger', 'That `git reset --hard` throws away anything on `main` that is not on GitHub — which is exactly what you want here, **because the first line already copied those commits onto the new branch**. Run `git log --oneline -5` on the new branch first and confirm your commits are there.'));

/* ============================ SUMMARY ============================ */
A(H1('One-page summary'));

A(H2('Every change, start to finish'));
A(paste([
  'git switch -c short-name-for-the-change',
  '# ... edit files ...',
  'git add .',
  'git commit -m "what this change does"',
  'git push -u origin short-name-for-the-change',
]));
A(P('Then **Ctrl+Shift+P ▸ Create Pull Request** ▸ read the diff ▸ merge ▸ tick *Delete branch*.'));

A(H2('Afterwards'));
A(paste(['git switch main', 'git pull']));

A(H2('Answering review comments'));
A(paste(['git add .', 'git commit -m "address review comments"', 'git push']));

A(H2('Branch out of date'));
A(paste(['git fetch origin', 'git merge origin/main', 'git push']));

A(H2('The four buttons that matter'));
A(grid([2800, 7280], [
  ['Button', 'When'],
  ['Publish Branch', 'After the first commit on a new branch'],
  ['Create Pull Request', 'Once the branch is on GitHub'],
  ['Checkout', 'To run or edit a PR\'s code locally'],
  ['Merge / Squash and merge', 'Checks green, diff read, done'],
]));

/* ============================ DOCUMENT ============================ */
const spaced = [];
for (let i = 0; i < body.length; i++) {
  spaced.push(body[i]);
  if (body[i] instanceof d.Table && body[i + 1] instanceof d.Table) spaced.push(SP(0));
}

const doc = new Document({
  creator: 'Pull Request Cheat Sheet',
  title: 'Pull Requests in VS Code',
  description: 'Managing GitHub pull requests from VS Code, with PowerShell equivalents',
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
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: 'D0D7DE', space: 6 } },
        children: [
          new TextRun({ text: 'Pull Requests in VS Code', size: 16, color: '8C959F' }),
          new TextRun({ text: '\t\t', size: 16 }),
          new TextRun({ children: ['Page ', PageNumber.CURRENT, ' of ', PageNumber.TOTAL_PAGES], size: 16, color: '8C959F' }),
        ] })] }),
    },
    children: spaced,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = process.argv[2] || 'PR-Cheat-Sheet.docx';
  fs.writeFileSync(out, buf);
  console.log('wrote', out, buf.length, 'bytes');
});
