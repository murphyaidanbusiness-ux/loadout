---
name: loadout
description: Fit Claude Code's harness to a project and the task in front of it. Audits the eight pieces a harness is made of (CLAUDE.md, rules, skills, commands, subagents, MCP servers, settings, hooks), builds the check that lets Claude prove its own work, adds only the pieces this task needs, cuts what is bloated or stale, and tests every piece it touches. Use whenever someone asks to set up, optimize, tune, audit or fix their Claude Code setup, says "set up Claude Code for this project", "improve my CLAUDE.md", "what hooks, skills or subagents should I have", "Claude keeps ignoring my rules", "Claude says it's done when it isn't", "Claude keeps forgetting where we were", "get Claude ready for this task", or mentions harness engineering or a loadout for Claude, even if they never say "harness". Works for code and for work with no code (writing, research, operations).
---

# Loadout

Same model, better loadout. The harness is everything around the model: what Claude knows, what Claude can do, and
what keeps it in check. This skill fits that to one project and one task. It is built on four ideas.

- **The loop comes first.** The piece that moves results most is a check Claude can run that comes back pass or
  fail. With one, Claude finds its own mistakes. Without one, the user is the test suite. Everything else is second.
- **A piece earns its place or it is left out.** There are eight pieces. Consider all eight, every time, and give
  each one a verdict for this task: build, tune, keep, cut or skip, with the reason. A harness that has all eight
  because there are eight is worse than one with three that the task uses. Studies bear this out: context files
  written by a model did not raise success and cost about 20% more, and long or self-written skills scored at or
  below having none (`references/evidence.md`).
- **Write what Claude cannot find. Enforce what cannot have exceptions.** CLAUDE.md, rules and skills are read by
  the model, and the model may decide a line does not apply. Settings and hooks are executed by Claude Code. So
  instructions carry only what reading the project would not reveal, and a rule that must hold every time becomes a
  deny rule or a hook.
- **Tested or it doesn't count.** A hook that was never fired and a command that was never run are guesses. Every
  piece this skill touches is exercised before it is reported.

| Job | Pieces | Who acts on it |
|---|---|---|
| What Claude knows | CLAUDE.md, rules, skills | the model reads it |
| What Claude can do | commands, subagents, MCP servers | the model uses it |
| What keeps it in check | settings (permissions, sandbox), hooks | Claude Code enforces it |

## Ground rules

- **Read first, change after the go.** Steps 1 to 4 change nothing. Building starts when the user approves the
  plan. If they already said to go ahead, or nobody is there to answer, build, and list every assumption you made.
- **Never replace what exists.** Read every existing piece in full before touching it. Edit settings key by key.
  A line that names something specific to this project (a person, an incident, a quirk of the code) is hard-won:
  keep it, word for word if in doubt. Tell the user exactly what you cut and why.
- **Build the harness, not the task.** Do not write the feature, fix the bug or draft the piece the harness is
  for, however ready you are to. The exception is a check the loop needs (one test of the path the task touches),
  and that goes in the plan first.
- **The harness lives in harness files.** Leave the user's own documents as they are (their spec, their style
  guide, their notes, their source). Point to them from CLAUDE.md or a skill; do not add to them unless asked.
- **Nothing invented.** A command goes in the harness only after you ran it and saw what it does. A fact goes in
  only if the user said it, the project shows it, or you hit it yourself. No summaries of the codebase: Claude can
  read the code, and a written summary goes stale.
- **Stay inside the project.** Do not edit the user's own `~/.claude` files, install plugins, connect services,
  commit, or push without asking. Never set bypass-permissions mode. Never print a secret.
- **Use the file tools, and respect a refusal.** Create and change harness files with Write and Edit, never with
  shell redirection, so the user sees each change as a diff. Claude Code protects the `.claude/` folder: a write
  there asks the user first, or goes to auto mode's classifier, which may refuse a change that widens Claude's own
  permissions. Tell the user in the plan to expect the prompt (they can allow edits to this project's `.claude`
  folder for the session). If a write is refused, stop and report what you would have written. This skill changes
  Claude's own controls, so the user's say over those changes is the point.
- **Check current facts.** The reference files carry the date they were checked against the docs. Claude Code
  changes weekly. If a field or command fails, read the docs page the reference names before trying a variant.

## How to run

`/loadout <what the user is trying to do>` runs the whole thing. Narrower forms: **audit** (steps 1 to 4, report
only), **fix <what went wrong>** and **prune** (both under [After the build](#after-the-build)). With no task given,
ask for one: a harness fitted to nothing is a template.

### 1. Understand the task

From the user's words and the project, pin down four things:

1. **The work.** What they will be doing here for the next days or weeks, concretely.
2. **What has gone wrong.** Any failure they name ("it marked people paid when they weren't", "it forgets where we
   were", "it makes up statistics") is the harness's first job. Each named failure must map to a piece by step 3.
3. **What done looks like**, and how anyone checks it today.
4. **How it runs.** Watched or unattended. Alone or a team. On their machine or in the cloud.

Read the project before asking anything. Then ask only what it cannot tell you, in one message, each question with
the assumption you will make if there is no answer. Usually that is: how they know work is right today, what Claude
has got wrong here before, and whether anything must never happen.

### 2. Take stock

Run the bundled check from the project root. It reads only:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/loadout_check.py" .
```

(`scripts/loadout_check.py` is in this skill's folder; use `python` or `py -3` where `python3` is missing.) It lists
the eight pieces, the checks the project can already run, and concrete faults: settings that are not valid JSON,
misspelled fields that are silently ignored, hooks pointing at missing scripts, commands in CLAUDE.md that do not
exist. Without Python, do the same by hand: look for `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/rules/`,
`.claude/skills/`, `.claude/commands/`, `.claude/agents/`, `.mcp.json`, `.claude/settings.json` and
`.claude/settings.local.json`.

Then:
- Read every existing piece in full. The script counts; only reading tells you what a file is worth.
- **Run the project's checks now** (test, typecheck, lint, build) and record which pass, which fail and how long
  each takes. This is the baseline. A check that already fails changes what you may wire up in step 5.
- Note the Claude Code version (`claude --version`) and what the machine has (`git`, `node`, `python3`, `jq`).

### 3. Decide

Open `references/tasks.md`, find the recipe closest to the task, and read only that part.

**First the loop.** Name the check that tells Claude this task's work is right, and pick how strictly it is held:

| Level | What it is | Use when |
|---|---|---|
| 1 | The exact command in CLAUDE.md, with "run it before saying the work is done" | always, when a check exists |
| 2 | A `verify` skill holding the recipe; Claude Code runs it before each commit | the check has several steps or needs setup |
| 3 | A `Stop` hook: Claude cannot end its turn until the check passes | the check is fast, passes today, and "done" has been wrong before |
| 4 | A reviewer subagent that can read but not edit | nothing can check the work automatically (writing, design, judgment) |

If the project has no check at all, building one is the plan's first line: a test of the path the task touches, a
script that compares output with a known answer, a screenshot next to a reference, or a written checklist plus a
reviewer.

**Then each piece.** Give all eight a verdict. Route each thing the task needs to the right piece:

| What the task needs | Piece |
|---|---|
| A fact or command Claude needs every session and could not find | CLAUDE.md |
| Conventions for one area of the project | a rule scoped with `paths` |
| A multi-step procedure, or reference needed only sometimes | a skill |
| A prompt the user keeps retyping | a command (a skill run by name) |
| A second opinion from something that did not do the work, or a noisy job kept out of the way | one subagent |
| A system outside the project that no command-line tool reaches | an MCP server |
| Something that must never happen | a `deny` permission rule; a hook if a rule cannot express it |
| Something that must happen every time | a hook |
| Something a person should see first | an `ask` permission rule |
| Work that survives between sessions | a progress file the user can read, named in CLAUDE.md |

Defaults that keep a harness honest:
- Skip is a valid verdict and needs a reason ("no outside system involved", "one person, no repeated procedure
  yet"), plus the event that would change it.
- Subagents: none, or one reviewer. MCP: only where no command-line tool does the job. Skills: one to three, short.
- Enforce only what has zero exceptions. A preference stays a line in CLAUDE.md.
- Check what is built in before building (`references/can-do.md` lists it): `/verify`, `/goal`, `/code-review`,
  `/batch` and others already exist.
- An existing harness is usually improved by cutting. Look for what to remove before what to add.

### 4. Show the plan

One short message, then stop for the go (unless already given):

- the task as you understand it, in a sentence, and the assumptions you made
- the loop: the check, the level, and whether it passes today
- the eight pieces, one line each: verdict and reason
- what will be cut from existing files, and what in them stays untouched
- what only the user can do (install a tool, set a secret, approve a server)

### 5. Build

Work in this order:

1. **The loop.** Get the check running and passing, or record why it cannot yet.
2. **What Claude knows** (`references/knows.md`): CLAUDE.md, then rules, then skills.
3. **What Claude can do** (`references/can-do.md`): commands, subagents, MCP servers.
4. **What keeps it in check** (`references/in-check.md`): permissions, sandbox, hooks.

**Read the reference for a job before you write any piece in it, even a small one.** What you remember about
Claude Code's formats is older than the product, and a wrong field fails silently: Claude Code ignores what it does
not recognise and reports nothing. These are the mistakes memory makes most:

- Path rules in permissions work only as `Read(...)` and `Edit(...)`. `Write(...)`, `Grep(...)` and `Glob(...)`
  path rules are accepted and match nothing. Deny is checked first, then ask, then allow.
- A hook blocks with exit code 2. Exit code 1 lets the action through.
- Hooks live inside a settings file. MCP servers live in `.mcp.json`, and an entry with a `url` needs a `type`.
- A settings file is strict JSON. One comment or trailing comma and the whole file is skipped.
- `"defaultMode": "auto"` in a project file is ignored. A project's `allow` rules wait for the user to trust the
  folder; `deny` and `ask` do not.
- A rule's only frontmatter field is `paths`. Subagent fields are camelCase (`disallowedTools`); skill fields are
  hyphenated (`allowed-tools`). Custom commands are skills now, and `/agents` no longer opens an editor.
- A wildcard allow such as `Bash(*)` approves every command. Replace it with the commands the task runs.

While building:
- One file at a time, each with the Write or Edit tool. A single shell command that writes the whole harness
  hides every change from the user and skips the protections on `.claude/`.
- If the project is under git, git is the backup: leave the changes uncommitted so the user can review them with
  `git diff`. Otherwise copy every file you are about to change into `.claude/loadout-backup/` first.
- Keep everything short. The limit is not a line count; it is whether each line would be missed.
- Wire a blocking check only if it passes today. A `Stop` hook on a failing check traps every session, this one
  included, and pushes Claude to "fix" things nobody asked about. If the baseline fails, report it, leave the
  blocking hook out, and list "turn on the Stop check once it is green" for the user. When the failure the user
  named is broken checks or false "done", wire the softer version meanwhile: the same check after each edit, which
  shows Claude the output without holding the turn (`references/in-check.md`).
- Write hooks for the shell and tools this machine has. Many machines have no `jq`.
- Anything that sends, publishes, deploys or deletes is something the user starts, never Claude on its own.
- Mark anything you wrote from inference (a skill's steps, a rule) for the user to read once. Instructions a model
  wrote for itself, unreviewed, measurably hurt.

### 6. Prove it

Do each of these and keep the output for the report:

1. Run the check script again. No errors. Go through every warning: fix it, or name it in the report with the
   reason it stays.
2. Run the loop's check once and show the result.
3. Fire every hook you wrote: pipe it a sample event, show it passing a harmless case, and for a blocker show it
   blocking the case it exists for (exit code 2, with a message). `references/in-check.md` has the commands.
4. Test a deny rule with a harmless stand-in, never the real secret: create a dummy file the rule covers, try to
   read it, confirm the refusal, delete it. Permission and hook changes apply to the running session.
5. Run each new command or skill once on a small real case. Ask a new subagent one real question.
6. If `claude` is on the path and the user is fine with a short extra run, confirm a fresh session picks the
   harness up: `claude -p "What command checks work in this project? Answer with the command only."`

If a piece cannot be tested here, say so in the report. Do not describe it as working.

### 7. Write the map and report

Write `.claude/HARNESS.md` from `assets/loadout-map.md`. It is not loaded into sessions, so it costs nothing. It
records the task, the loop, each of the eight with its reason and the condition for removing it, what was cut,
what was tested and how, and what is waiting on the user. It is what makes the next `/loadout fix` or
`/loadout prune` possible, and it is how a teammate learns why a hook exists.

Then tell the user, briefly: what the loop is and that it ran, what was built, cut and skipped, what you could not
test, and what needs them. Say plainly what this is and is not: it does not make the model smarter, it gives Claude
a way to check its work and removes ways to go wrong. Suggest they run one small real task in a fresh session and
bring back whatever goes wrong.

## After the build

A harness is finished by use. The working definition of harness engineering is this habit: when the agent makes a
mistake, change the harness so it cannot make that mistake again.

**`/loadout fix <what went wrong>`.** Find which kind of failure it was, then make the smallest change:

| What happened | Change |
|---|---|
| Claude did not know something | one line in CLAUDE.md, a scoped rule or a skill. Only what it could not have found. |
| Claude knew and did it anyway | If it can never be allowed: a deny rule or a hook. Otherwise look for the cause: a contradicting line, a file too long to hold attention, a rule with no reason. More capitals is never the fix. |
| Claude said it was done and it was not | strengthen the loop one level, or fix a check that passes when it should fail |
| Claude could not reach or do something | a command-line tool first, an MCP server second, or a permission |
| Claude lost its place | a progress file, and a line in CLAUDE.md to read it first |
| The same prompt typed again and again | a command |

Add a rule after a mistake has happened twice or cost something real, not on the first slip. Test the change, then
record it in the map with the date and the failure it answers.

**`/loadout prune`.** Run it when a new model ships, when the harness feels heavy, or when the map is a couple of
months old. Every piece encodes a guess about what the model cannot do, and those guesses go stale.
`references/evidence.md` lists what has already been retired (emphasis in capitals, "keep going" lines,
architecture descriptions, subagents used to save context). For each piece in the map, check its removal
condition and whether the failure it answered still happens. Remove one piece at a time and watch a real task
before removing the next. Suggest `/context all` and `/usage` to the user to see what each piece costs, and
`/doctor` for a second opinion on the install.

## What this skill won't do

- Promise better results. It reports what was built, what was tested and what was only reasoned about.
- Install a piece because a complete harness "should" have it.
- Write down facts it did not check, or describe a codebase back to the model that can read it.
- Change the user's global configuration, install plugins, connect services or loosen permissions without asking.
