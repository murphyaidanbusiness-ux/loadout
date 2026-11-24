# Fitting the harness to the task

Eleven kinds of work and what a harness for each looks like. Find the one or two closest to the user's task and read
only those. A task can combine two (a new app over many sessions with an interface is 4 plus 1). When nothing fits,
use [the five questions](#when-nothing-fits).

Every recipe starts with **the loop**: what Claude runs to find out whether its work is right. That is the piece to
get working first. The rest is listed by job, with what to leave out, because the common failure is a harness with
every piece and no loop.

Contents: [1 Interface work](#1-interface-work) · [2 Backend, data and payments](#2-backend-data-and-payments) ·
[3 Fixing bugs](#3-fixing-bugs) · [4 A new build over many sessions](#4-a-new-build-over-many-sessions) ·
[5 One change across many files](#5-one-change-across-many-files) · [6 Data analysis and experiments](#6-data-analysis-and-experiments) ·
[7 Infrastructure and production](#7-infrastructure-and-production) · [8 Mobile apps](#8-mobile-apps) ·
[9 Writing, research and operations](#9-writing-research-and-operations) · [10 A large or unfamiliar codebase](#10-a-large-or-unfamiliar-codebase) ·
[11 Running unattended](#11-running-unattended) · [When nothing fits](#when-nothing-fits)

## 1 Interface work

**The loop.** Claude has to see what it built. Run the app, open the page, take a screenshot, compare it with the
reference, fix, repeat. Types and unit tests pass on interfaces that look wrong.
- A browser Claude can drive: Claude in Chrome (`claude --chrome`) on the user's machine, or a Playwright MCP server
  in `.mcp.json`. One is enough.
- What "right" means, written down: the reference (a mockup file, a URL, an existing screen to match) and a short
  checklist (spacing, states, mobile width, console free of errors). A screenshot with nothing to compare it to
  proves nothing.

**Knows.** CLAUDE.md: how to start the dev server and on which port, where the design reference and tokens live,
how to run one component's test. A rule scoped to the components folder if the project has a design system with its
own conventions.
**Can do.** `/verify` builds and runs the app; if launching takes more than one command, `/run-skill-generator`
records the recipe. A read-only reviewer subagent that is handed the reference and the screenshot, when the look
matters: the builder should not grade its own design.
**In check.** Format after edit, if a formatter is configured. Typecheck at Stop.
**Skip.** A database server, extra subagents, component-library documentation Claude can read from `node_modules`.
**The usual mistake.** The browser tool is wired up and nothing says what the page should look like.

## 2 Backend, data and payments

**The loop.** A test that exercises the real path, plus one real request against the service running locally.
- The command for one test file belongs in CLAUDE.md, with the environment it needs ("integration tests need
  `DATABASE_URL`; see `.env.example`").
- For anything a third party calls back (payments, webhooks), the loop must include a real event in test mode, fired
  by the provider's own CLI (Stripe: `stripe listen` and `stripe trigger`). A redirect to a success page is not
  proof that money moved.
- No tests yet? Then the first piece of the harness is one honest end-to-end test of the path the task touches.
  Write it before the feature, with the user's OK.

**Knows.** CLAUDE.md: the commands, and the rules that cost money when broken, each with its reason (who may mark an
order paid, where the server-only client may be used). A rule scoped to the API or payment folders for conventions
that only matter there. A skill for running a migration, user-invoked only.
**Can do.** The provider's CLI before any MCP server. A database server only against a development database, and
only if looking up the schema is slowing the work.
**In check.** Deny reading `.env*` and secrets folders. Ask before push and before any deploy or migration command
against a real environment. A guard on migrations that have already run, if the project has them. Typecheck or the
fast tests at Stop.
**Skip.** A subagent per layer. Broad allow lists.
**The usual mistake.** Pointing a tool at production data, or a harness whose only check is "it compiles".

## 3 Fixing bugs

**The loop.** A failing test or a command that reproduces the bug, written first, then turned green. The docs'
rewrite of "fix the login bug" is "write a failing test that reproduces it, then fix it".

**Knows.** Very little. The test command and how to run one test. Facts about the code that the tests do not show
(a format quirk, a function another system depends on), each with its reason.
**Can do.** A `fix-bug` command that carries the reproduce-first steps, if bug fixing is most of what the user does
here. A code intelligence plugin for a typed language.
**In check.** The test suite at Stop, once the suite is green. A deny or a guard on editing the tests is too blunt
(new tests must be written); the line "fix the code, not the test, and say so if a test is wrong" belongs in
CLAUDE.md with its reason.
**Skip.** Almost everything else. Bug fixing needs a short, accurate CLAUDE.md and a loop. This is the task where an
existing harness most often needs cutting, not adding.
**The usual mistake.** A long CLAUDE.md of general advice, a wrong test command, and rules that contradict each
other, so the real ones get lost.

## 4 A new build over many sessions

**The loop.** A feature list that is the definition of done, and a way to test each feature the way a user would.
This is Anthropic's own pattern for long builds:
- **A feature list as a JSON file**, every feature starting as not passing, with one field that flips when the
  feature has been checked end to end. JSON, because the model is less likely to rewrite it than a markdown list.
  Claude may change that one field and nothing else: never delete or reword a feature to make the list look done.
- **A progress file** Claude appends to at the end of every session and reads at the start of the next: what was
  done, what is half-done, what to do next.
- **A start script** that installs what is needed and launches the app, so a new session is running in one command.
- **Git as the checkpoint**: a commit per finished feature, so a bad session can be thrown away.
- **A browser check** (see recipe 1). It cannot run before there is an app, but decide it now: name the tool that
  will open the app, write each feature's check as steps a user would take in it, and list "turn the browser check
  on" in the harness map for the first session that has a screen. Without one, Claude tends to mark features done
  on the strength of unit tests.

**Knows.** CLAUDE.md, short: read the progress file and the feature list first, work on the next unfinished feature,
check it for real before flipping its field, commit, update the progress file. The spec stays in its own file.
**Can do.** Commands that fit how the user works: one to start a session, one to wrap up. `/goal` with the feature
list as its condition for a long run, with a turn limit.
**In check.** Permissions for the stack's commands. A Stop check once there is a build or test command to run; there
is none on day one, so list it in the harness map as the thing to turn on.
**Leave to the user.** The stack and other decisions the spec leaves open belong to the build, not the harness.
Record them as open questions for the first session; if a check needs a decision now, propose it and wait.
**Skip.** Agent teams, a reviewer per feature, anything that assumes code that does not exist yet. Older advice to
limit Claude to one feature per session was for earlier models; keep the list and the checks, and let it go further
when the checks pass.
**The usual mistake.** No record between sessions, and "done" meaning "written".

## 5 One change across many files

**The loop.** A judge that exists before the first file is touched: a command that passes on correct files and
fails on a deliberately broken one. Parallel work multiplies a wrong rule across every file, so prove the judge
catches a mistake, then try the change on three files before all of them.

**Knows.** The rulebook for the change (old pattern, new pattern, the cases that are different) as a skill. A
checklist file on disk listing every unit of work and its state, so the job can resume.
**Can do.** `/batch <instruction>` splits the work into units and runs each in its own git worktree. For hundreds of
files, a script that loops `claude -p` over the checklist with a turn limit.
**In check.** The judge at Stop or as the `/goal` condition. Permissions limited to the files in scope.
**Skip.** Hand-built orchestration when `/batch` fits.
**The usual mistake.** No judge, so nobody finds out the rule was wrong until every file has it.

## 6 Data analysis and experiments

**The loop.** A script that runs start to finish from a clean state and checks a known answer: a row count, a total
that must reconcile, a metric on a small fixed sample with a fixed seed. "The chart looks plausible" is not a check.

**Knows.** CLAUDE.md: how to set up the environment, where the data is and which copy is the source of truth, how to
run the pipeline on a small sample, what must never be overwritten. A rule scoped to notebooks if they have
conventions.
**Can do.** A database or warehouse server when the data lives there, read-only credentials. A command for "run on
the sample and report the checks".
**In check.** Deny edits to raw data. Deny reads of data that is private or too large to be useful in a
conversation; point Claude at a summary or a sample instead. A spending cap on anything that launches compute.
**Skip.** Web-app machinery.
**The usual mistake.** Results nobody can reproduce, and a long run that spends money with no cap.

## 7 Infrastructure and production

**The loop.** The tool's own dry run, read by Claude and by a person: a plan, a diff, a `--dry-run`. Claude prepares
the change and proves what it would do. A person applies it.

**Knows.** CLAUDE.md: which environment is which, the dry-run command for each tool, who approves what.
**Can do.** The tools' own CLIs. Credentials that can read and plan and cannot apply are the real boundary; say so
to the user, because no setting inside Claude Code replaces it.
**In check.** This is the task where enforcement earns its place. Deny the commands that change real systems
(apply, destroy, delete, force-push) and test that each deny fires. Turn the sandbox on with a network allow list.
Ask before push. Remember that a Bash deny matches the command's text, not the program, so the credentials and the
sandbox are what hold.
**Skip.** Trusting a line in CLAUDE.md that says "never apply".
**The usual mistake.** A prompt where a permission should be.

## 8 Mobile apps

**The loop.** Build, run in a simulator or emulator, look at the screen, read the build errors, fix. Claude needs
the exact build and test commands for one scheme or variant, and a way to capture the screen.

**Knows.** CLAUDE.md: the scheme or module, the simulator or device name, the build, test and run commands that
work from a terminal.
**Can do.** A simulator or emulator tool Claude can drive, if the user has one set up; otherwise the platform's
command-line build and screenshot tools.
**In check.** Deny hand edits to generated project files that tools manage. Build at Stop if it is fast enough.
**Skip.** Anything the platform's own tooling already does.
**The usual mistake.** No build loop, so Claude writes screens it has never seen.

## 9 Writing, research and operations

Claude Code works in any folder, and none of this needs code. There are no tests, so the harness has to supply them.

**The loop.** A written standard the work is checked against, by something other than the writer:
- **A checklist** the piece must pass: length, structure, what every piece of this kind includes.
- **A source check**: every number, quote and factual claim has a link or a file it came from, and the source was
  opened. A claim with no source is cut or marked. This is the check for "it keeps making things up".
- **A voice or style check** against real examples of the user's own work, not adjectives about it.
- **A reviewer subagent** with read-only tools that gets the draft and the standard and reports only what fails.

**Knows.** CLAUDE.md, short: who the reader is, how the work flows through the folders, where the standard and the
examples live. The voice lives in its own file with examples; CLAUDE.md points to it. A skill for each deliverable
the user makes repeatedly (the weekly issue, the report, the reply).
**Can do.** A command that starts the recurring job. Connectors only for systems the work needs (the inbox, the
calendar, the document store). Anything that sends or publishes is user-invoked only.
**In check.** Ask before anything leaves the machine. Protect finished work from being overwritten if the user
keeps an archive.
**Skip.** Test runners, linters, formatters, code review, database servers. Say plainly that they were skipped and
why.
**The usual mistake.** CLAUDE.md as a brand bible: long, general, and unread.

## 10 A large or unfamiliar codebase

**The loop.** Whatever the area being changed already has: its tests, its build. The harness work here is mostly
about what Claude reads.

**Knows.** A short root CLAUDE.md for what is true everywhere, and a CLAUDE.md in each package or subsystem the
user works in, which loads only when Claude works there. Rules with `paths` for conventions that cut across
folders. Start sessions in the subdirectory being worked on.
**Can do.** A code intelligence plugin for the language. The built-in Explore subagent for wide searches.
**In check.** Deny reads of generated, built and vendored folders so searches stay clean. `claudeMdExcludes` for
packages the user never touches.
**Skip.** One enormous root CLAUDE.md that describes every package.
**The usual mistake.** Describing the architecture in CLAUDE.md. Claude can read the code; write down only what
the code does not show.

## 11 Running unattended

**The loop.** The same check as the attended version of the task, made strict, because nobody is there to notice.

Answer the docs' five questions in the harness map: what done looks like, how it checks itself, what it may touch,
what stops it, where the result goes and who signs off.

**Knows.** A prompt that stands alone: a scheduled run starts with no conversation.
**Can do.** `claude -p` with `--max-turns` and `--max-budget-usd`; `/goal` with a turn limit; `/loop` inside an open
session; `/schedule` for cloud tasks.
**In check.** `--permission-mode dontAsk` with an explicit `--allowedTools` list, so anything unplanned is refused
instead of waiting. The sandbox. One branch it may push to, protected by a rule on the git host. Results as a pull
request or a report a person approves.
**Skip.** Bypass mode outside a disposable container.
**The usual mistake.** No cap and no review of the first few runs.

## When nothing fits

Ask the five questions of the task, in this order, and build only what the answers call for:

1. **How will Claude know the work is right?** Build that first.
2. **What does Claude need to know that it cannot find by reading the project?** That is CLAUDE.md, a rule or a skill.
3. **What does the user do over and over?** That is a command.
4. **What must never happen, with no exceptions?** That is a deny rule or a hook. If the list is long, most of it
   is preference.
5. **What outside system does the work need to reach?** A CLI first, an MCP server second.
