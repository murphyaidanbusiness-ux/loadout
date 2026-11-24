# Harness map

What this project's Claude Code setup is for and why each piece is there. Claude does not load this file in a
session; it is for people, and for `/loadout fix` and `/loadout prune`.

Built <date> · Claude Code <version> · model <model> · by the loadout skill

## The task this is fitted to

<One or two sentences: the work, and the failures the user named.>

Assumptions made without an answer: <list, or "none">

## The loop

- **Check:** `<command, or the checklist and reviewer>`
- **Held by:** <a line in CLAUDE.md | the verify skill | a Stop hook | a reviewer subagent>
- **State on <date>:** <passes in N seconds | fails: what and why | does not exist yet: what turns it on>

## The eight pieces

| Piece | Verdict | What and where | Why, for this task | Remove or revisit when |
|---|---|---|---|---|
| CLAUDE.md | built / tuned / kept / cut / skipped | | | |
| Rules | | | | |
| Skills | | | | |
| Commands | | | | |
| Subagents | | | | |
| MCP servers | | | | |
| Settings | | | | |
| Hooks | | | | |

## Enforced, with no exceptions

| Rule | How it is enforced | The reason |
|---|---|---|
| | deny rule / ask rule / hook / sandbox | |

## What was cut

| Cut | From | Why |
|---|---|---|
| | | |

Kept word for word (hard-won, specific to this project): <list>

## What was tested

| Piece | Test | Result |
|---|---|---|
| | | |

Not tested here, and why: <list, or "nothing">

## Waiting on you

- [ ] <Read once: anything Claude wrote from inference (skill steps, rules)>
- [ ] <Installs, secrets, approvals>
- [ ] <Checks to turn on later, and the condition>

## Changes

| Date | What went wrong | What changed |
|---|---|---|
| | | |
