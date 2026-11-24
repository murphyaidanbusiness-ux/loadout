# Loadout: test results (2026-11-23)

Tested headless (`claude -p`, auto mode, Claude Code 2.1.331) on
**Sonnet 5.5**, one run per configuration: the same prompt in the same sample project **with the skill** and
**without it**. Graded by a script for the mechanical checks and by a separate Sonnet grader for the rest, each
grader told to be even-handed. The four cases and their checks are the folders next to this file.

## The short version
- **Round 1: a tie.** 34 of 37 checks with the skill, 33 of 37 without. Plain Sonnet already cuts a bloated
  CLAUDE.md, fixes a wrong command and writes sensible permissions. The first checks measured mostly that.
- **Round 2: 44 of 46 with the skill, 37 of 46 without**, after the checklist was extended to what the skill is for
  and the skill was tightened. Where the two differ, every time: the skill's run **exercised what it built** (fired
  the hooks, ran the scripts, tried a deny rule on a dummy file), **enforced the failure the user named** with a hook
  instead of a line of text, and **left a record** of why each piece exists. Without the skill the run usually wrote
  good instructions and tested little or nothing.
- **It costs more.** 86 to 284 s and $0.32 to $0.61 a run with the skill; 35 to 122 s and $0.16 to $0.35 without.

## How far to trust this
- One run each, one model, four cases written by the same session that wrote the skill. A rerun could move any case
  by a check or two.
- Round 2 is not blind: the extra checks were written after seeing round 1, and the skill was tuned between rounds on
  these same cases. There is no held-out case. Read it as "the skill does what it was designed to do", not as a
  measured gain on new projects.
- Three baselines were carried from round 1 (same prompt, no skill). The Stripe baseline was rerun because its prompt
  changed (below).
- One baseline check was corrected upward after grading: it had failed on a false alarm in the skill's own check
  script (it read the full stop after `@voice.md.` as part of the file name). The script is fixed.
- Nothing here measures whether Claude then does the *task* better with the harness. That needs real use.

## Round 2, case by case
| Case | With skill | Without | What separated them |
|---|---|---|---|
| Next.js + Stripe: "set up my Claude Code before I add subscriptions; last time it marked people paid" | 11/11 | 9/11 | Skill: a guard hook fed 9 sample edits, a deny rule seen blocking, a reviewer run in a fresh session, the failing typecheck and hanging lint found and written down, a map. Baseline: one hook tested, the rest untested (it said so), no record. |
| Python repo, 164-line CLAUDE.md with `npm test` in it, allow-everything permissions, three unused MCP servers | 12/12 | 9/12 | Both cut the file (to 23 and 33 lines), fixed the command, kept all four hard-won facts. Skill also wired the tests to run after each edit (not a Stop hook: one test fails at baseline, and it said which), fired the hook both ways, wrote the map. Baseline: instruction only, no record, nothing run. |
| Newsletter folder, no code: "it keeps making up statistics" | 11/11 | 9/11 | Skill: a pass/fail script for a draft plus a read-only fact-checker, both run on real files (the script failed the draft with the invented 73%). Baseline: two prompt commands, never run. |
| New app over many weekends: "it forgets where we were and says things work when they don't" | 10/12 | 10/12 | Tie. Skill: a Stop hook that rejects "passes" without a test file and rejects a deleted or reworded feature, all fired; but the real browser check is only a to-do, and it picked a stack. Baseline: a better-defined browser check and a manual path for what Claude can't prove; but nothing enforces it, and it also picked a stack. |

## Round 1 (for the record)
| Case | With skill | Without |
|---|---|---|
| Stripe | 8/9 | 6/9 |
| Bloated setup | 9/10 | 9/10 |
| Newsletter | 8/9 | 9/9 |
| New build | 9/9 | 9/9 |

- The Stripe prompt ended "go ahead and build it". The baseline read "it" as the subscription feature and built the
  whole thing (21 files, webhook, migration, 26 tests). That reading was fair, so the prompt now says "make the
  changes to my setup ... don't build the subscriptions yet" and both configurations were rerun.
- The skill's run edited the newsletter owner's own `voice.md` (it added a pointer section). Counted as a failure.

## What changed in the skill between rounds
1. **Build the harness, not the task**, and leave the user's own documents alone (the `voice.md` edit).
2. **Use the Write and Edit tools**, never shell redirection, for harness files; respect a refused write to `.claude/`.
3. **Read the reference before writing a piece**, with the reason and a short list of what memory gets wrong. In
   round 1 Sonnet skipped the references on the small case and left `Edit(*)` and `Write(*)` in the allow list.
4. **A softer check when the baseline is red**: run the tests after each edit, which shows Claude the output without
   trapping the session, and move to a Stop hook once green.
5. After round 2, not retested: write each file one at a time (one run still wrote everything in a single shell
   command); leave the stack to the user; name the browser check on day one for a new build.

## Things the runs turned up that the skill now says
- Auto mode's classifier refused two baseline attempts to write an allow list into `.claude/settings.json`. The skill
  tells Claude to report a refusal, not work around it.
- A project's `allow` rules are ignored until the user accepts the folder's trust dialog; `deny` and `ask` apply at
  once. Every run hit this in headless mode.
- A check that fails before any work starts would trap a Stop hook. Two of four sample projects had one (a failing
  test; a typecheck that errors inside `node_modules`). The skill found both and kept them out of the blocking hook.

## What is not tested
- Interactive use: the plan step and waiting for the go (every test prompt said to go ahead).
- `/loadout fix`, `/loadout prune` and `/loadout audit`.
- Opus, Haiku, Fable; Windows; a machine without Python.
- Whether the description triggers the skill when it should not. It did trigger on both prompts that never said
  "harness" (the bloated setup and the newsletter), in both rounds.

## To rerun
From the skill folder, with Claude Code 2.1.269 or later: `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`.
These are real, billed model runs. The test prompts in the case folders use `/loadout`; rounds 1 and 2 were run when
the skill's command was still `/harness`, with otherwise identical prompts.
