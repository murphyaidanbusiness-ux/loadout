# The evidence behind this skill

What has been measured about each part of a harness, what has not, and where each claim comes from. Read this when
you need to explain a choice to the user, when the user asks "does this actually help?", or when you are tempted to
add a piece because it seems thorough. Every source was opened on 2026-11-23.

Strength: **study** = a controlled study (most are 2026 preprints, not yet peer reviewed). **vendor** = a company
reporting its own numbers. **practice** = guidance with no measurement behind it.

## What moves results

| Finding | Number | Source | Strength |
|---|---|---|---|
| A check the agent must pass before it finishes | A finish-time check added alone: 69.7% to 71.9% of tasks. In a second test it was one of the changes behind 52.8% to 66.5%. | AHE, arXiv 2604.25850 (Terminal-Bench 2); LangChain, Feb 2026 | study; vendor |
| A separate grader instead of self-grading | "improved task success by up to 10 points", most on the hardest problems | Anthropic, "How the Claude Code team thinks about verification", Nov 2026 | vendor |
| Facts the model does not have | A docs index for APIs newer than the model's training: 53% to 100% pass rate | Vercel, Jan 2026 (model and test count not published) | vendor |
| A short memory of lessons from real failures | Added alone: 69.7% to 75.3%, the largest single gain in that study | AHE, arXiv 2604.25850 | study |
| A few focused skills written by people | 33.9% to 50.5% across 87 tasks. Coding tasks alone: +11.6 points | SkillsBench, arXiv 2602.12670 | study |
| Loading tools on demand | Tool choice accuracy 49% to 74% on one model | Anthropic, "Advanced tool use", Nov 2025 | vendor |

## What does not help, or hurts

| Finding | Number | Source | Strength |
|---|---|---|---|
| A context file written by the model | Success -0.5 and -2 points (not significant), cost +20% and +23%. The authors "suggest omitting LLM-generated context files". | ETH Zurich, arXiv 2602.11988 | study |
| A context file written by a person | +2.4 points, not statistically significant, cost up to +19%. Claude Code was the one agent that did not gain. | same | study |
| An overview of the repository | Did not reduce the steps the agent took to find the right file | same | study |
| Skills the model wrote for itself, unreviewed | 8.1 to 11.5 points below having no skills at all | SkillsBench | study |
| Long, comprehensive skills | +0.7 points, against +19 for compact ones. Four or more skills gained about half as much as one to three. | SkillsBench | study |
| A skill that holds knowledge the agent always needs | The skill was never invoked in 56% of cases, so it scored the same as nothing | Vercel | vendor |
| Instructions alone, with no tools or checks behind them | A 79-line system prompt added alone: 69.7% to 67.4% | AHE | study |
| Telling the agent to use subagents | Cost up 1.5 to 2.9 times. On one set of long tasks Claude Code fell from 71.67% to 50%. | DeLM, arXiv 2606.10662 (10 tasks per benchmark; the authors propose a rival system) | study, small |
| An MCP server where a command-line tool exists | Command-line-only setups were 5 to 28 times cheaper on the same task | arXiv 2608.08654 (one task) | study, small |

Read the two tables together. Files of prose do little by themselves; checks, tools and enforcement do more, and
prose helps when it carries something the model could not have known. That is why this skill builds the loop first,
writes only what Claude cannot find, keeps skills few and short, and asks the user for the facts only they have.

## What nobody has measured

No study found measures hooks, permission rules, the sandbox, commands or plan mode against task success. The case
for them is safety and logic: a deny rule is the difference between a rule that is followed most of the time and one
that cannot be broken. Say so when asked. Do not tell a user that a deny rule or a hook "makes Claude better". It
makes a specific bad outcome impossible.

Also unsettled:
- How long a context file can be. ETH found no link between length and success. The reason to stay short is cost,
  staleness and the reader's attention. The docs' 200-line target is guidance.
- How many instructions a model can follow. A 2025 study put the practical limit near 150 to 200; a 2026 re-run
  puts it near 2,000 on newer models. Do not quote either as a law.
- The model matters more than the harness on most benchmarks. A harness decides how close a model gets to its
  ceiling. It does not raise the ceiling.

## What goes stale

Anthropic's harness team: "every component in a harness encodes an assumption about what the model can't do on its
own, and those assumptions are worth stress testing". When a new model lands they re-examine the harness,
"stripping away pieces that are no longer load-bearing". Things they have dropped as models improved:

| Dropped | Why |
|---|---|
| Emphasis (IMPORTANT, capitals) on lines Claude kept missing | Current models over-apply an emphasised rule. Make it a hook or shorten the file. |
| "Keep going", "don't be lazy", "be thorough", "think hard" | They cause over-work; effort is a setting. A check to pass is the fix. |
| Subagents to save context, or to get a better answer | Context rarely runs out now; a subagent is the same model on the same task. |
| A description of the architecture in CLAUDE.md | Claude reads the project. |
| Forced context resets, one-feature-per-session limits | Newer models hold a long task without them. |
| Rigid rules for how to use memory | They made stronger models worse. Say what the memory is for. |

The prune step in the main workflow applies this list. Remove one piece at a time and watch a real task, because
after a large cut it is hard to tell which piece was doing the work.

## Sources

- Claude Code docs, best practices and reference pages: `https://code.claude.com/docs/en/best-practices.md`,
  `memory.md`, `skills.md`, `sub-agents.md`, `hooks.md`, `permissions.md`, `settings.md`, `mcp.md`
- Anthropic, "Harness design for long-running application development", 24 Mar 2026:
  `https://www.anthropic.com/engineering/harness-design-long-running-apps`
- Anthropic, "Effective harnesses for long-running agents", 26 Nov 2025:
  `https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents`
- Anthropic, "How the Claude Code team thinks about verification", 16 Nov 2026:
  `https://claude.dev/blog/how-the-claude-code-team-thinks-about-verification/`
- Anthropic, "Effective context engineering for AI agents", 29 Sep 2025:
  `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`
- Anthropic, "Advanced tool use", 24 Nov 2025: `https://www.anthropic.com/engineering/advanced-tool-use`
- Gloaguen et al. (ETH Zurich), "Evaluating AGENTS.md", arXiv 2602.11988 (v3)
- SkillsBench, arXiv 2602.12670 (v4)
- Lin et al., AHE, arXiv 2604.25850
- Mao et al., DeLM, arXiv 2606.10662
- MCP and command-line cost comparison, arXiv 2608.08654
- Galster et al., "Harness Engineering for Agentic AI Coding Tools", arXiv 2602.14690 (the eight mechanisms; 2,853
  repositories; context files in 90.6% of them, no other mechanism above 20% for Claude Code)
- Vercel, "AGENTS.md outperforms skills in our agent evals", 27 Jan 2026
- LangChain, "Improving Deep Agents with harness engineering", 17 Feb 2026
- Mitchell Hashimoto, "My AI adoption journey", 5 Feb 2026 (the working definition: every time the agent makes a
  mistake, engineer a fix so it never makes that mistake again)
