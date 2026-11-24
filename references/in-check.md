# What keeps Claude in check: settings and hooks

Checked against the Claude Code docs on 2026-11-23 (Claude Code 2.1.331). Key names and hook events change. If
something here fails, or the installed version is much newer, read the page named in each section at
`https://code.claude.com/docs/en/<page>.md` before you write the file.

Contents: [Why this job is different](#why-this-job-is-different) · [Settings files](#settings-files) ·
[Permissions](#permissions) · [Sandbox](#sandbox) · [Hooks](#hooks) · [The three hooks worth having](#the-three-hooks-worth-having) ·
[Test every hook](#test-every-hook) · [Model and effort](#model-and-effort)

## Why this job is different

CLAUDE.md, rules and skills are read by the model, and the model may decide a line does not apply. Settings and hooks
are executed by Claude Code itself. The docs' rule: "If something has to happen every time, make it a hook, a deny
rule, or a managed setting." And the reverse: a hook is for a rule with zero exceptions. A preference with exceptions
("prefer named exports") stays in CLAUDE.md. A harness with forty enforced rules has mostly enforced preferences.

So the question for every rule the user cares about is: what happens the one time in fifty that Claude skips it? If
the answer is "someone is charged twice" or "the secrets file is read", enforce it here. If the answer is "the code
is a little less tidy", leave it as a line.

## Settings files

Docs pages: `settings`, `settings-reference`.

| File | Who it is for | In git |
|---|---|---|
| `.claude/settings.json` | everyone on the project | yes |
| `.claude/settings.local.json` | this person, this project | no (gitignore it) |
| `~/.claude/settings.json` | this person, every project | no |

- Strict JSON. A comment or a trailing comma breaks the file, and a broken file is skipped whole, silently dropping
  every rule and hook in it. Validate after every edit.
- Lists from all files are merged, never replaced. Precedence for single values: local, then project, then user.
- MCP servers do not go here. They live in `.mcp.json` (see `can-do.md`).
- Edit an existing file key by key. Never overwrite it: it may hold approvals and hooks the user depends on.
- First line worth adding: `"$schema": "https://json.schemastore.org/claude-code-settings.json"` for editor checks.
- Some cloud sessions do not apply a repository's `.claude/settings.json`. If the user works in Claude Code on the
  web, say so in the report and keep the must-hold rules in a place that travels (a check in CI, a git hook).

## Permissions

Docs pages: `permissions`, `permission-modes`.

```json
{
  "permissions": {
    "allow": ["Bash(npm run test *)", "Bash(npm run lint)"],
    "ask":   ["Bash(git push *)"],
    "deny":  ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]
  }
}
```

**Order.** Deny is checked first, then ask, then allow. The first match wins and a more specific rule does not beat a
broader one. A deny rule holds in every permission mode.

**What each list is for**

- `deny`: things that must not happen. Reading secrets, editing generated or vendored files, a destructive command.
- `ask`: things a person should see first. Pushing, deploying, sending, anything outside the machine.
- `allow`: the safe commands the task runs constantly (the test, lint, typecheck and build commands), so nobody is
  prompted for them. New terminal sessions start in auto mode, where a classifier already approves routine work, so
  a long allow list buys little. Keep it to what the task's loop needs.

**Rule syntax**

| Rule | Matches |
|---|---|
| `Bash(npm run *)` | commands starting `npm run `. The space before `*` matters: `Bash(ls *)` does not match `lsof`. |
| `Read(./.env)`, `Read(./secrets/**)` | paths relative to the working directory. A bare name such as `Read(.env)` matches at any depth. |
| `Edit(/migrations/**)` | a single leading slash anchors at the project root (the settings file's project), not the disk root. `//` is the disk root, `~/` is home. |
| `WebFetch(domain:example.com)` | one host |
| `mcp__github__*` | every tool of one MCP server |
| `Agent(name)`, `Skill(name)` | one subagent, one skill |

Three traps:

- **Path rules only work on `Read` and `Edit`.** `Write(...)`, `Grep(...)` and `Glob(...)` path rules are accepted
  and match nothing. `Edit(...)` covers every editing tool, and a `Read` deny also blocks edits to that path.
- **Bash rules match the text of the command.** The docs say a Bash rule "isn't a security boundary around the
  program": `Bash(curl *)` does not stop `/usr/bin/curl` or `sh -c 'curl ...'`. A `Read` deny does not stop a script
  that opens the file. For a boundary that holds, use the sandbox or a hook.
- **`"defaultMode": "auto"` or `"bypassPermissions"` in a project file is ignored.** Those belong in the user's own
  settings. Never set bypass mode for a user; the docs keep it for disposable containers.

**Trust.** A project's `allow` rules take effect only after the user has accepted the workspace trust dialog for
the folder; `deny` and `ask` rules apply at once. If an allow rule seems ignored, that is the first thing to check.

**Find what to deny from the project, not from a list.** Look for: files holding secrets (`.env*`, key files,
credentials), generated or vendored folders Claude should not edit by hand (`dist/`, lockfiles, generated clients),
folders where a mistake is expensive (migrations, infrastructure), and commands that reach outside the machine
(deploy, publish, push to a protected branch, production database tools). Each rule gets a reason in the harness map.

Replace a wildcard allow such as `Bash(*)` or `Edit(*)` with the commands the task really needs. Say what was removed.

## Sandbox

Docs page: `sandboxing`. An operating-system boundary around shell commands and everything they start. It is what
makes a deny hold against a script. Off by default.

```json
{ "sandbox": { "enabled": true, "network": { "allowedDomains": ["registry.npmjs.org", "github.com"] } } }
```

- Works on macOS, Linux and WSL2. On native Windows commands run unsandboxed.
- It covers shell commands only. The Read, Edit and WebFetch tools are still governed by permission rules, so use
  both.
- Writes are limited to the working directory by default; network goes through an allow list that starts empty, so
  list the hosts the task's commands need (package registry, git host) or installs will fail.

**Earns its place when** the task has real blast radius (infrastructure, production data, money), Claude will run
unattended, or the project pulls in code or content nobody has read. **Skip when** it is ordinary work on a personal
project, watched; mention it as available and move on.

## Hooks

Docs pages: `hooks-guide` (start here), `hooks` (reference). A hook runs a command of yours at a fixed point in
Claude's loop. Hooks live in a settings file under `hooks`; there is no separate hooks file.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "f=$(jq -r '.tool_input.file_path') && npx prettier --write --ignore-unknown \"$f\"" }]
      }
    ]
  }
}
```

Three levels: the event, a matcher group, then the handlers. The events that matter for a harness:

| Event | Fires | Exit code 2 does | Matcher is |
|---|---|---|---|
| `PreToolUse` | before a tool call | blocks the call; stderr is shown to Claude | tool name: `Bash`, `Edit`, `Write`, `Read`, `mcp__server__.*` |
| `PostToolUse` | after a tool call succeeds | cannot undo it; stderr is shown to Claude | tool name |
| `Stop` | when Claude tries to end its turn | sends Claude back to work with stderr as the reason | none |
| `SubagentStop` | when a subagent finishes | same, for the subagent | agent type |
| `UserPromptSubmit` | when the user sends a prompt | blocks the prompt | none |
| `SessionStart` | start, resume, after `/clear`, after compaction | nothing | `startup`, `resume`, `clear`, `compact` |

There are 33 events in all; the `hooks` page lists the rest.

**Exit codes.** `0` is success. `2` blocks (on events that can block) and sends stderr to Claude. Any other code,
including `1`, is a non-blocking error and the action goes ahead. A hook that enforces something exits `2`.

**Input.** The hook gets JSON on stdin: `tool_name`, `tool_input` (for file tools, `tool_input.file_path` is
absolute; for Bash, `tool_input.command`), `cwd`, `hook_event_name`. `${CLAUDE_PROJECT_DIR}` is the project root.

**Useful handler fields**

| Field | Use |
|---|---|
| `if` | one permission rule that narrows the hook, such as `"Bash(git commit *)"` or `"Edit(*.py)"`. Tool events only. |
| `timeout` | seconds. Set it for anything that could hang. |
| `onFailure: "block"` | block the action when the hook itself crashes or times out. Without it a broken hook lets everything through. |
| `async: true` | run in the background. It cannot block. |

Handler `type` can also be `prompt` or `agent` (a model decides), `http`, or `mcp_tool`. A model-decided hook is not
deterministic, so it does not count as enforcement.

**Matchers** are case-sensitive: `Bash`, not `bash`. `Edit|Write` is an exact list. `mcp__github` alone matches
nothing; write `mcp__github__.*`.

**Reading the JSON without assuming `jq`.** The docs' examples use `jq`, which many machines lack. Check what the
machine has (`command -v jq node python3`) and use that:

```bash
# jq
f=$(jq -r '.tool_input.file_path')
# node
f=$(node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s).tool_input.file_path||""))')
# python
f=$(python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
```

On Windows a hook command runs in Git Bash, or in PowerShell when Git Bash is not installed, where shell syntax such
as `1>&2 || exit 2` does not work. Check which the user has before writing the command, and set `"shell"` (`"bash"` or
`"powershell"`) on the handler when it matters. A hook script file must be executable (`chmod +x`), or it fails
without blocking anything.

**A hook runs with the user's full permissions, on every matching event, without asking.** Keep each one short, fast
and readable, and show the user every hook you add.

## The three hooks worth having

Most harnesses need at most these. Add one only when the project has the thing it runs.

**1. The check at Stop.** Claude cannot end its turn until the check passes. This is the docs' own pattern:

```json
{ "hooks": { "Stop": [ { "hooks": [
  { "type": "command", "command": "npm run typecheck 1>&2 || exit 2", "timeout": 120 }
] } ] } }
```

Output goes to stderr so Claude sees why it was sent back. After eight blocked stops in a row with no tool call
between them, Claude Code ends the turn anyway.

Before wiring it:
- **Run the command now. It must pass.** A check that already fails traps every session, this one included, and
  pushes Claude to "fix" things nobody asked about. If it fails today, report that, and either fix it with the
  user's OK or leave the hook out and list it as the first thing to turn on once the check is green.
- **Keep it fast.** It runs every time Claude stops, even after a question. Typecheck, lint or a quick test subset
  belong here; a ten-minute suite belongs in CLAUDE.md as the command to run before calling work done.
- When the check is slow or flaky, use the softer levels: the command in CLAUDE.md, or `/goal <condition>` for one
  long run.
- **When the check fails today**, a softer hook still closes the loop: run it after each edit instead of at Stop.
  `PostToolUse` cannot block, so nothing is trapped, and with exit code 2 its output is shown to Claude:
  ```json
  { "hooks": { "PostToolUse": [ { "matcher": "Edit|Write", "hooks": [
    { "type": "command", "if": "Edit(src/**)", "command": "make test 1>&2 || exit 2", "timeout": 120 }
  ] } ] } }
  ```
  Claude sees the failing test after every change to the source, including the failure that was already there, so
  say in CLAUDE.md which failures are known. Move the check to `Stop` once it is green.

**2. Format or lint after an edit.** `PostToolUse` with matcher `Edit|Write`, running the project's own formatter on
the edited file (the example above). Only when the project already has a formatter configured. It replaces a
"remember to format" line that Claude would follow most of the time.

**3. A guard before a dangerous action.** `PreToolUse` that exits 2. Try a permission `deny` rule first: it is one
line and needs no script. Use a hook when the condition is something a rule cannot express, such as "no commit while
tests fail" or "no edit to a migration that has already run":

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [
  { "type": "command", "if": "Bash(git commit *)", "command": "npm test 1>&2 || exit 2", "onFailure": "block" }
] } ] } }
```

A fourth, when sessions are long: `SessionStart` with matcher `compact`, whose command prints the few lines that
must survive compaction (the current task, the progress file's path). Plain output from this event is added to
Claude's context.

## Test every hook

A hook that was never fired is a guess. For each one:

1. Pipe it a sample event and read the exit code:
   ```bash
   echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$PWD"'/src/x.ts"}}' | <the hook command>; echo "exit $?"
   ```
2. For a blocker, show it blocking: feed it the case it exists for and confirm exit 2 and a message on stderr. Then
   feed it a harmless case and confirm exit 0.
3. For the Stop check, run the command once passing and once failing (break something small, run, restore).
4. `/hooks` lists what Claude Code loaded. `claude --debug` logs each hook run.

## Model and effort

Docs page: `model-config`. Usually nothing to set: the defaults suit most work. Worth knowing:

- `"model"` in `.claude/settings.json` sets the project default; `/model` and `/effort` change it for a session.
- A subagent or skill can name its own `model` and `effort`. A cheaper model on a narrow, mechanical subagent
  (running tests, searching) saves money; a reviewer should not be weaker than the author.
- `opusplan` plans on Opus and executes on Sonnet.
