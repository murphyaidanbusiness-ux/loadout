# What Claude knows: CLAUDE.md, rules, skills

Checked against the Claude Code docs on 2026-11-23 (Claude Code 2.1.331). Field names and paths change. If something
here fails, or the installed version is much newer, read the page named in each section at
`https://code.claude.com/docs/en/<page>.md` before you write the file.

Contents: [The one test](#the-one-test) · [CLAUDE.md](#claudemd) · [Rules](#rules) · [Skills](#skills) ·
[Which of the three](#which-of-the-three) · [Check it loaded](#check-it-loaded)

## The one test

Everything in this job is read by the model and can be ignored by it. So each line has to earn the tokens it costs in
every session. The docs give the test, and it applies to all three pieces:

1. Could Claude find this by reading the project?
2. Would it actually go and look?

If both are yes, leave the line out. What passes the test: exact commands, places where the project is misleading,
decisions that live in nobody's files, and anything the user has had to correct twice.

## CLAUDE.md

Docs page: `memory`. Loaded in full at the start of every session and re-read from disk after compaction (the
project-root file only).

**Where**

| File | Who it is for |
|---|---|
| `./CLAUDE.md` or `./.claude/CLAUDE.md` | the project, shared through git |
| `./CLAUDE.local.md` | this person, this project; add it to `.gitignore` |
| `~/.claude/CLAUDE.md` | this person, every project |
| `<subdir>/CLAUDE.md` | loads only once Claude reads or edits a file in that folder |

Files from the working directory upward are all joined together; none overrides another. When two lines disagree,
Claude may follow either, so a contradiction is a defect to remove, not a precedence question.

**Size.** The docs' target is under 200 lines per file: "Longer files consume more context and reduce adherence." Treat
that as a ceiling. Most good ones are far shorter. `@path` imports (up to four hops deep) keep a file tidy but save no
context: an imported file loads with the file that imports it.

**What goes in**

- The exact commands: test, one test file, typecheck, lint, run, build. Commands you ran and saw work.
- What "done" means here and the check that proves it (the feedback loop from the main workflow).
- Where the code or the folder is misleading, and why.
- Decisions and constraints that are not written anywhere in the project, each with its reason.
- Pointers to files Claude should read for a kind of work ("before touching payments, read `docs/billing.md`").

**What stays out**

- A description of the architecture or a directory tree. Claude reads the project itself.
- Generic advice ("write clean code", "follow best practices", a persona line). It changes nothing and costs tokens
  every turn.
- Emphasis. The docs say piling on IMPORTANT and capitals "mostly makes Claude over-apply the rule".
- Step-by-step procedures (a skill) and rules for one area of the project (a path-scoped rule).
- Anything that must hold with no exceptions. That is a deny rule or a hook: see `in-check.md`.

**How to write a line.** Say what to do, concretely enough to check, and give the reason when it is not obvious. A rule
with its reason gets applied to cases the rule did not name; a bare "never" gets applied too widely or dropped.

```markdown
# Commands
- Test: `npm test`. One file: `npm test -- path/to/file.test.ts`
- Typecheck: `npm run typecheck`. Run it before saying a change is done.

# Conventions
- Money is integer cents everywhere. Floats caused a rounding bug in invoices.

# Gotchas
- `lib/supabase.ts` exports an admin client that skips row-level security. Server code only.
```

**An existing file.** Never replace it wholesale. Read every line and sort it: keep (passes the test), move (to a rule,
a skill, a hook or a deny rule), fix (wrong or stale, such as a test command that does not exist), cut (generic,
duplicated, contradicted). Hard-won facts are the lines that name something specific about this project: a person, an
incident, a quirk. Keep every one of them, word for word if in doubt. Tell the user what was cut and why.

**AGENTS.md.** Claude Code reads `AGENTS.md` only when no `CLAUDE.md` or `CLAUDE.local.md` exists at or above the
working directory. If the project has both, or other tools use `AGENTS.md`, make `CLAUDE.md` a short file whose first
line is `@AGENTS.md`, followed by anything Claude-specific, so there is one source of truth.

**Auto memory** is separate: Claude's own notes in `~/.claude/projects/<project>/memory/`, on by default, local to the
machine. Do not build on it for anything a teammate or a cloud session must see.

## Rules

Docs page: `memory`, section on `.claude/rules/`. A rule is a markdown file of instructions for one topic.

- Location: `.claude/rules/*.md` (subfolders allowed) or `~/.claude/rules/`.
- The only frontmatter Claude Code reads is `paths`. Any other field is ignored without an error.
- No `paths`: the rule loads at launch, exactly like more CLAUDE.md. With `paths`: it loads when Claude reads, writes
  or edits a file that matches.

```markdown
---
paths:
  - "app/api/**/*.ts"
  - "lib/stripe.ts"
---
# Payment code
- Mark an order paid only inside the verified webhook handler. A redirect to the success page proves nothing.
```

Patterns are relative to the folder that holds `.claude`. `**/*.ts` matches at any depth, `src/**/*` everything under
`src/`, `/*.md` only the top level. Braces work (`*.{ts,tsx}`). A stray `[` makes the pattern match nothing.

**Earns its place when** the project has an area with its own conventions (payments, migrations, a design system, the
tests) and those lines would be noise for everything else. That is the whole value: the lines cost nothing until
Claude touches the area.

**Skip when** the project is small enough that all its conventions fit in a short CLAUDE.md, or the "rule" would have
no `paths`. An unscoped rule is only a second CLAUDE.md.

**Gotcha.** A path-scoped rule is not re-injected after compaction until Claude touches a matching file again. A line
that must always be in view belongs in the root CLAUDE.md.

## Skills

Docs page: `skills`. A skill is a folder with a `SKILL.md`: instructions Claude loads on demand, plus any files and
scripts that go with them. Custom commands have been merged into skills: see `can-do.md` for the command side.

- Location: `.claude/skills/<name>/SKILL.md` (project, shared through git) or `~/.claude/skills/<name>/SKILL.md`
  (personal, every project). Cloud sessions do not read the personal folder.
- Only the name and description sit in context until the skill is used. Then the whole body enters the conversation
  and stays. Keep the body under 500 lines and move detail into files the body points to.

```markdown
---
name: draft-issue
description: Draft this week's newsletter issue from the notes in sources/. Use when asked to write, draft or start an issue.
---
1. Read `voice.md` and the two most recent files in `issues/`.
2. ...
```

Frontmatter that matters when building a harness (all optional; unknown fields are ignored silently):

| Field | Use |
|---|---|
| `description` | What it does and when to use it. Claude decides from this alone. Lead with the use case and the words a user would say. Cut off at 1,536 characters. |
| `disable-model-invocation: true` | Only the user can run it. Use for anything with side effects (deploy, send, publish, delete). Also removes the description from context. |
| `user-invocable: false` | Only Claude can run it; hidden from the `/` menu. |
| `allowed-tools` | Tools that need no permission prompt during the turn that invokes the skill, such as `Bash(npm test *)`. It does not restrict tools. |
| `argument-hint`, `arguments` | What to type after the name. `$ARGUMENTS`, `$0`, `$1` in the body are replaced. |
| `paths` | Globs. The skill is offered only when matching files are in play. |
| `context: fork`, `agent` | Run the skill in a subagent (see `can-do.md`). The body must then be a complete task. |
| `model`, `effort` | Override for the turn. |

A line starting with `` !`command` `` in the body runs before Claude sees the skill and is replaced by its output
(for example `` !`git diff --stat` ``). If the command fails, the whole skill aborts, so append `|| true` when a
non-zero exit is normal.

**Earns its place when** the user repeats a multi-step procedure, pastes the same playbook, or there is reference
material Claude needs only sometimes (an API's quirks, a style guide, a release checklist).

**Skip when** the content is a fact Claude needs in every session (CLAUDE.md), or a one-off. A skill nobody invokes
still costs its description in every session.

**Writing one.** The CLAUDE.md test applies: only what Claude cannot work out alone. Write the description for
matching, the body as standing instructions with reasons, and put the most important lines first (after compaction
only the first 5,000 tokens of each skill come back). Bundle a script when the same code would otherwise be rewritten
every run. If the skill ends in "check your work", say what the check is.

**Sharing.** If the skill may be uploaded to claude.ai or packaged, use only `name`, `description`, `license`,
`compatibility`, `metadata` and `allowed-tools` in the frontmatter. Any other key fails the upload with a hard error.

## Which of the three

| The thing you want Claude to know | Put it in |
|---|---|
| A fact or convention for every session | CLAUDE.md |
| A personal preference for this project | CLAUDE.local.md |
| Conventions for one area of the project | a rule with `paths` |
| A procedure with steps, or reference needed sometimes | a skill |
| A prompt the user keeps retyping | a user-invocable skill |
| Something that must happen every time, no exceptions | not here: a hook or a deny rule |
| A tone, length or format for every reply | an output style (`/output-style`), not CLAUDE.md |

## Check it loaded

- `/context all` lists the memory files, rules and skills in the session and what each costs.
- `/memory` shows which CLAUDE.md files are loaded. `/skills` lists skills. `/doctor` flags oversized or stale
  instruction files.
- From a script: `claude -p "What is the test command for this project? Answer with the command only."` in the project
  folder. If the answer is not the one in CLAUDE.md, the file is not loading or the line is not clear.
- A rule with `paths`: ask Claude to read a matching file, then ask what it knows about that area.
- A skill that does not trigger: check the description holds the words the user would say, then run it by name.
