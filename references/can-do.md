# What Claude can do: commands, subagents, MCP servers

Checked against the Claude Code docs on 2026-11-23 (Claude Code 2.1.331). Field names and commands change. If
something here fails, or the installed version is much newer, read the page named in each section at
`https://code.claude.com/docs/en/<page>.md` before you write the file.

Contents: [Use what is built in first](#use-what-is-built-in-first) · [Commands](#commands) · [Subagents](#subagents) ·
[MCP servers](#mcp-servers) · [Plugins](#plugins) · [Running without a person](#running-without-a-person) ·
[Check it works](#check-it-works)

## Use what is built in first

Claude Code already ships much of what people build by hand. Before adding a piece, check that one of these does
not cover it. They cost nothing to keep and they stay current.

| Need | Built in |
|---|---|
| Build and run the app, then look at the result | `/verify`. `/run-skill-generator` records how to launch the app as a project skill. |
| Keep working until a condition holds | `/goal <condition>` (a small model checks after every turn) |
| A review by something that did not write the code | `/code-review` (fresh subagent), `/security-review` |
| Split one change across many files in parallel | `/batch <instruction>` (5 to 30 units, each in its own worktree) |
| Search a large codebase without flooding the conversation | the Explore subagent, used automatically |
| Audit the install, extensions and CLAUDE.md | `/doctor`, `/doctor prompt-audit` |
| Fewer permission prompts for safe commands | `/fewer-permission-prompts` |
| Repeat a prompt on a timer | `/loop 15m <prompt>`; `/schedule` for cloud tasks |
| See what is loaded and what it costs | `/context all`, `/usage` |

Tell the user about the ones that fit their task. A harness that names the right built-in beats one that rebuilds
it.

## Commands

Docs page: `skills`. Custom commands have been merged into skills. A file in `.claude/commands/` still works, but
the docs say to use a skill for anything new. So a "command" is a skill the user runs by name.

Make one when the user keeps typing the same prompt to start a piece of work. It is the cheapest piece of a harness
and usually the most used.

```markdown
---
name: fix-bug
description: Fix a bug the reproduce-first way. Use when asked to fix a bug or a failing test.
argument-hint: [what is wrong]
---
Bug: $ARGUMENTS

1. Write a failing test that reproduces it. Run it and show that it fails for the right reason.
2. Fix the cause. Leave the test as written.
3. Run the whole suite. Show the output.
```

- `$ARGUMENTS` is what the user typed after the name. Without the placeholder, the arguments are appended.
- Anything with side effects outside the project (deploy, publish, send, delete) gets
  `disable-model-invocation: true`, so only the user can start it.
- **A project skill named `verify` is special.** When one exists at session start, Claude Code's commit instructions
  tell Claude to run it before each commit (v2.1.286 or later), and `/verify` runs it. That makes
  `.claude/skills/verify/SKILL.md` the natural home for "how to check work in this project". If the user later runs
  `/verify` or `/run-skill-generator`, Claude Code may write or update that file itself.

## Subagents

Docs page: `sub-agents`. A subagent is a separate Claude with its own context window, its own system prompt and,
if you choose, fewer tools. It gets the task message and the project's CLAUDE.md. It does not get the conversation.

**What they are good for** (the docs' list):

- work that can run in parallel
- keeping long output (a full test run, a wide search) out of the main conversation
- a reviewer that has not seen how the work was done
- a task that should have fewer tools than the main session, such as a reviewer that can read but not edit

**What they are not good for.** The docs retired two habits: using subagents "to protect your context window" (it
rarely runs out now) and delegating "for a better answer". By default a subagent is the same model on the same task:
"You get parallelism or a fresh pair of eyes out of it, but not a smarter answer." Each one spends its own tokens
and first has to rediscover context the main session already had.

So most harnesses need zero or one custom subagent, and the one is usually an independent checker.

```markdown
---
name: reviewer
description: Reviews changed files against the spec they were built from. Use after implementing a feature, before saying it is done.
tools: Read, Grep, Glob
---
You are reviewing work you did not do. Compare the changed files against the spec you are given.
Check that every requirement is met and each listed edge case is covered.
Report only gaps that affect correctness. Skip style.
```

- Location: `.claude/agents/<name>.md` (project) or `~/.claude/agents/` (personal). Only `name` and `description`
  are required. Unknown fields are ignored without an error, so a misspelled field silently does nothing.
- Fields that matter here (exact spelling): `tools` (allow list; omit to inherit all), `disallowedTools`, `model`
  (`haiku`, `sonnet`, `opus`, `inherit` or a full id), `skills` (skills preloaded in full), `maxTurns`, `memory`
  (`project` gives it its own notes folder in `.claude/agent-memory/<name>/`), `isolation: worktree`,
  `permissionMode`, `effort`.
- `tools: Read, Grep, Glob` is enforced by Claude Code, not requested in the prompt. That is what makes a reviewer
  safe to trust with the question "is this right?".
- Claude delegates from the `description`. Say when to use it. To force it, name it: "use the reviewer subagent".
- Tell a reviewer what to skip. A reviewer asked to find problems always finds something, and fixing every finding
  adds layers nobody needed.
- A reviewer should not be a weaker model than the author. Set `model: haiku` only for simple mechanical jobs
  (collecting files, running a command and summarising).
- `/agents` no longer opens an editor. Write the file, or ask Claude to.

**Earns its place when** the task has no automatic check and needs a second look (writing, design, research,
anything judged by reading), when a noisy job repeats (run the whole suite and report only failures), or when work
splits into independent parts. **Skip when** the work is small, sequential or already covered by a built-in.

Agent teams and dynamic workflows (many agents under a script) exist and cost far more tokens. Leave them out
unless the user's task is one the docs name for them: a codebase-wide audit, a migration across hundreds of files.

## MCP servers

Docs pages: `mcp-quickstart`, `mcp`. An MCP server gives Claude tools and data from outside the project: a browser,
a database, an issue tracker, a design file.

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "docs": {
      "type": "http",
      "url": "https://example.com/mcp",
      "headers": { "Authorization": "Bearer ${DOCS_API_KEY}" }
    }
  }
}
```

- The project file is `.mcp.json` at the project root (not inside `.claude/`), key `mcpServers`. It is shared
  through git. `claude mcp add --scope project ...` writes it; `--scope user` keeps a server personal.
- Every entry with a `url` needs a `type` (`http` for remote servers; `sse` is deprecated). Without it the entry is
  skipped.
- Secrets never go in the file. Use `${VAR}` or `${VAR:-default}`, which expand in `command`, `args`, `env`, `url`
  and `headers`.
- The user approves project servers the first time. In `claude -p` and cloud sessions they load with no prompt.

**Cost.** Tool definitions are loaded on demand (tool search is on by default), so an idle server costs its name
and instructions, not its whole tool list. The real costs are trust and noise: the docs warn that "servers that
fetch external content can expose you to prompt injection risk", and every connected server is one more thing
Claude might reach for.

**Earns its place when** the task's check or its data lives somewhere Claude cannot reach from the shell: a browser
for interface work, a database for schema questions (a development database, never production), a design tool, a
tracker. **Skip when** a command-line tool already does it. The docs prefer the CLI: `gh`, `aws`, `psql`, `stripe`
and the like need no server, and Claude already knows them.

Remove or disable servers the project does not use. Ask before removing one: it may serve another project.

For interface work on the user's own machine, Claude in Chrome (`claude --chrome`, or `/chrome`) is the built-in
alternative to a browser server. It needs the Chrome extension and does not work in WSL.

## Plugins

Docs page: `plugins/install`. A plugin bundles skills, subagents, hooks and MCP servers for reuse across projects.
For a harness, two kinds matter:

- **Code intelligence** for typed languages: `/plugin install typescript-lsp@claude-plugins-official` (also
  `pyright-lsp`, `gopls-lsp`, `rust-analyzer-lsp` and others). Claude then sees type errors after every edit and can
  jump to definitions. The language server binary must be installed separately, and it does not run in cloud
  sessions. This is a feedback loop that costs almost nothing: suggest it for any typed codebase.
- A plugin the team already uses. Record it in `.claude/settings.json` under `enabledPlugins` so everyone gets it.

Installing a plugin is the user's action: name it, say why, and let them run the command. Plugins run code with the
user's privileges.

## Running without a person

Docs pages: `headless`, `goal`, `scheduled-tasks`. When the task will run unattended (overnight, on a schedule, in
CI), the docs give five questions to settle first. Put the answers in the harness map:

1. Does it know what done looks like? A goal condition, a spec file, a failing test to turn green.
2. Can it check its own work? The check command, a `Stop` hook, a review step.
3. What may it touch? Permission rules, the sandbox, a worktree, the one branch it may push to.
4. What stops it? `--max-turns`, `--max-budget-usd`.
5. Where does the result go, and who signs off? A pull request or a summary, then a person.

```bash
claude -p "<the task>" --permission-mode dontAsk --allowedTools "Read,Edit,Bash(npm test *)" \
  --max-turns 30 --max-budget-usd 5 --output-format json
```

- `claude -p` starts in manual permission mode, so an unattended run must say what is allowed. `dontAsk` denies
  anything not pre-approved.
- Without `--bare`, a `-p` run executes the project's hooks and connects its MCP servers with no trust prompt.
  `--bare` skips hooks, skills, MCP and CLAUDE.md, and needs an API key.
- `/goal` needs a condition Claude's own output can prove ("the test command prints 0 failures"), and a bound
  ("or stop after 20 turns").

## Check it works

- A command: run it by name with a real argument.
- A subagent: ask Claude to use it by name on a small real case; confirm it returns what its description promises,
  and that a read-only one cannot edit. `claude plugin validate .claude/agents` checks the files parse.
- An MCP server: `claude mcp list` shows whether it connected. Inside a session, `/mcp`. Then make one real call.
- A skill folder: `claude plugin validate .claude/skills`.
