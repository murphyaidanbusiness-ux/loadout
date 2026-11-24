#!/usr/bin/env python3
"""Inventory and check a project's Claude Code harness.

Usage:  python3 harness_check.py [project_dir] [--json] [--no-user]

Reads only. Prints a table of the eight pieces (CLAUDE.md, rules, skills, commands, subagents,
MCP servers, settings, hooks), the checks the project can run, and a list of findings:

  ERROR  the piece is broken and Claude Code will skip or misread it
  WARN   it loads, but it probably does not do what its author meant
  INFO   worth knowing

Exit code 1 when there is at least one ERROR, so it can be used as a check itself.
Standard library only. Facts checked against the Claude Code docs on 2026-11-23.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HOOK_EVENTS = {
    "SessionStart", "Setup", "UserPromptSubmit", "UserPromptExpansion", "PreToolUse", "PermissionRequest",
    "PermissionDenied", "PostToolUse", "PostToolUseFailure", "PostToolBatch", "Notification", "MessageDisplay",
    "SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted", "Stop", "StopFailure", "TeammateIdle",
    "InstructionsLoaded", "ConfigChange", "CwdChanged", "DirectoryAdded", "FileChanged", "WorktreeCreate",
    "WorktreeRemove", "PreCompact", "PostCompact", "PreModelSwitch", "PostModelSwitch", "Elicitation",
    "ElicitationResult", "SessionEnd",
}
HOOK_TYPES = {"command", "http", "mcp_tool", "prompt", "agent"}
SKILL_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
    "user-invocable", "allowed-tools", "disallowed-tools", "model", "effort", "context", "agent", "background",
    "hooks", "paths", "shell", "metadata", "license", "compatibility",
}
AGENT_FIELDS = {
    "name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns",
    "autoCompactWindow", "skills", "mcpServers", "hooks", "memory", "background", "omitClaudeMd", "effort",
    "isolation", "color", "initialPrompt", "experimental",
}
TOOL_NAMES = {"Bash", "PowerShell", "Edit", "Write", "Read", "Glob", "Grep", "Agent", "Workflow", "WebFetch",
              "WebSearch", "AskUserQuestion", "ExitPlanMode", "NotebookEdit", "Skill", "Monitor"}
SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", ".venv", "venv", "__pycache__", "target",
             ".turbo", ".cache", "vendor", ".pytest_cache", ".mypy_cache", "coverage"}
EMPHASIS = re.compile(r"\b(IMPORTANT|CRITICAL|NEVER|ALWAYS|MUST|YOU MUST|DO NOT)\b")

findings = []


def add(level, piece, where, msg):
    findings.append({"level": level, "piece": piece, "where": where, "msg": msg})


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def rel(root, path):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def list_files(root):
    """Project files, relative, forward slashes. Uses git when it can so ignored files stay out."""
    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard"],
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return [p for p in out.stdout.splitlines() if p]
    except (OSError, subprocess.SubprocessError):
        pass
    files = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            files.append(os.path.relpath(os.path.join(base, n), root).replace(os.sep, "/"))
        if len(files) > 50000:
            break
    return files


def frontmatter(text):
    """Return (fields, body, problem). A small YAML reader: top-level keys, scalars and simple lists."""
    if text is None:
        return {}, "", "unreadable"
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, "no frontmatter (the first line must be ---)"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, "frontmatter never closes (no second --- line)"
    fields, key = {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            if val in ("", "|", ">", "|-", ">-"):
                fields[key] = []
            else:
                fields[key] = val.strip("\"'")
        elif key is not None:
            item = raw.strip()
            if item.startswith("- "):
                item = item[2:].strip().strip("\"'")
            if isinstance(fields.get(key), list):
                fields[key].append(item)
            else:
                fields[key] = str(fields.get(key, "")) + " " + item
        else:
            return fields, "\n".join(lines[end + 1:]), "frontmatter line not understood: " + raw.strip()[:60]
    return fields, "\n".join(lines[end + 1:]), None


def expand_braces(pattern):
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    out = []
    for alt in m.group(1).split(","):
        out.extend(expand_braces(pattern[:m.start()] + alt + pattern[m.end():]))
    return out


def glob_regex(pattern):
    """Gitignore-style glob to a regex over relative paths."""
    anchored = pattern.startswith("/")
    p = pattern.lstrip("/")
    if p.startswith("./"):
        p = p[2:]
    out, i = "", 0
    while i < len(p):
        c = p[i]
        if p[i:i + 3] == "**/":
            out += "(?:.*/)?"
            i += 3
        elif p[i:i + 2] == "**":
            out += ".*"
            i += 2
        elif c == "*":
            out += "[^/]*"
            i += 1
        elif c == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(c)
            i += 1
    if not anchored and "/" not in p:
        out = "(?:.*/)?" + out
    return re.compile("^" + out + "$")


def glob_matches(pattern, files):
    try:
        regs = [glob_regex(p) for p in expand_braces(pattern)]
    except re.error:
        return 0
    return sum(1 for f in files if any(r.match(f) for r in regs))


# ---------------------------------------------------------------- checks the project can run

def find_checks(root):
    checks = []
    pkg = read(os.path.join(root, "package.json"))
    scripts = {}
    if pkg:
        try:
            scripts = json.loads(pkg).get("scripts", {}) or {}
        except ValueError:
            add("WARN", "loop", "package.json", "not valid JSON, so its scripts could not be read")
        runner = "pnpm" if os.path.exists(os.path.join(root, "pnpm-lock.yaml")) else \
                 "yarn" if os.path.exists(os.path.join(root, "yarn.lock")) else \
                 "bun" if os.path.exists(os.path.join(root, "bun.lockb")) or os.path.exists(os.path.join(root, "bun.lock")) else "npm"
        for name in scripts:
            if re.search(r"^(test|lint|typecheck|type-check|check|build|e2e|format)(:|$)", name):
                checks.append({"kind": name.split(":")[0], "command": f"{runner} run {name}", "source": "package.json"})
        if os.path.exists(os.path.join(root, "tsconfig.json")) and not any(c["kind"].startswith("type") for c in checks):
            checks.append({"kind": "typecheck", "command": "npx tsc --noEmit", "source": "tsconfig.json (no script for it)"})
    mk = read(os.path.join(root, "Makefile"))
    targets = set()
    if mk:
        targets = set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:", mk, re.M))
        for t in sorted(targets):
            if t in ("test", "lint", "check", "typecheck", "build", "fmt", "format", "e2e"):
                checks.append({"kind": t, "command": f"make {t}", "source": "Makefile"})
    pyproj = read(os.path.join(root, "pyproject.toml")) or ""
    is_py = bool(pyproj) or os.path.exists(os.path.join(root, "setup.py")) or os.path.exists(os.path.join(root, "requirements.txt"))
    if is_py and not any(c["kind"] == "test" for c in checks):
        if "pytest" in pyproj or os.path.isdir(os.path.join(root, "tests")) or os.path.exists(os.path.join(root, "pytest.ini")):
            checks.append({"kind": "test", "command": "python -m pytest -q", "source": "pyproject.toml / tests/"})
    if "[tool.ruff" in pyproj and not any(c["kind"] == "lint" for c in checks):
        checks.append({"kind": "lint", "command": "ruff check .", "source": "pyproject.toml"})
    if os.path.exists(os.path.join(root, "Cargo.toml")):
        checks += [{"kind": "test", "command": "cargo test", "source": "Cargo.toml"},
                   {"kind": "lint", "command": "cargo clippy", "source": "Cargo.toml"}]
    if os.path.exists(os.path.join(root, "go.mod")):
        checks += [{"kind": "test", "command": "go test ./...", "source": "go.mod"},
                   {"kind": "lint", "command": "go vet ./...", "source": "go.mod"}]
    return checks, scripts, targets, is_py


# ---------------------------------------------------------------- the eight pieces

def check_instruction_file(root, path, scripts, targets, is_py, has_pkg):
    text = read(path)
    if text is None:
        return 0
    name = rel(root, path)
    lines = text.split("\n")
    n = len(lines)
    if n > 200:
        add("WARN", "CLAUDE.md", name, f"{n} lines. The docs' target is under 200: longer files cost context every "
            "session and are followed less. Cut what Claude can find by reading the project.")
    shouty = sum(1 for ln in lines if EMPHASIS.search(ln))
    if shouty > 5:
        add("WARN", "CLAUDE.md", name, f"{shouty} lines lean on capitals (NEVER, ALWAYS, IMPORTANT...). Emphasis makes "
            "Claude over-apply a rule. Say it plainly with the reason, or enforce it with a hook or deny rule.")
    if re.search(r"[├└]──", text):
        add("WARN", "CLAUDE.md", name, "contains a directory tree. Claude reads the project itself; keep only "
            "what the layout hides.")
    in_fence = False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        bare = re.sub(r"`[^`]*`", "", ln)
        for imp in re.findall(r"(?:^|\s)@([~./\w][\w./~-]*)", bare):
            imp = imp.rstrip(".,;:")  # sentence punctuation after the path
            if "/" not in imp and "." not in imp:
                continue  # an @mention, not a path
            target = os.path.expanduser(imp) if imp.startswith("~") else os.path.join(os.path.dirname(path), imp)
            if not os.path.exists(target):
                add("WARN", "CLAUDE.md", name, f"imports @{imp}, which does not exist")
    # commands that cannot run in this project
    for cmd in set(re.findall(r"`([^`\n]{3,80})`", text)):
        m = re.match(r"^(npm|pnpm|yarn|bun)\s+(?:run\s+)?([\w:-]+)", cmd)
        if m:
            if not has_pkg:
                add("WARN", "CLAUDE.md", name, f"names the command `{cmd}`, but the project has no package.json")
            elif m.group(2) not in scripts and m.group(2) not in ("install", "i", "ci", "run", "exec", "add", "dlx", "x", "init", "create", "start", "test"):
                add("WARN", "CLAUDE.md", name, f"names the command `{cmd}`, but package.json has no \"{m.group(2)}\" script")
            elif m.group(2) == "test" and "test" not in scripts:
                add("WARN", "CLAUDE.md", name, f"names the command `{cmd}`, but package.json has no \"test\" script")
        m = re.match(r"^make\s+([\w.-]+)", cmd)
        if m and targets is not None and m.group(1) not in targets:
            add("WARN", "CLAUDE.md", name, f"names the command `{cmd}`, but the Makefile has no \"{m.group(1)}\" target"
                if targets else f"names the command `{cmd}`, but the project has no Makefile")
        if re.match(r"^(pytest|python -m pytest)\b", cmd) and not is_py:
            add("WARN", "CLAUDE.md", name, f"names the command `{cmd}`, but this does not look like a Python project")
    return n


def check_claude_md(root, files, scripts, targets, is_py):
    has_pkg = os.path.exists(os.path.join(root, "package.json"))
    found = []
    for cand in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
        p = os.path.join(root, cand)
        if os.path.isfile(p):
            n = check_instruction_file(root, p, scripts, targets, is_py, has_pkg)
            found.append(f"{cand} ({n} lines)")
    nested = [f for f in files if f.endswith("/CLAUDE.md") and not f.startswith(".claude/")]
    for f in nested[:20]:
        check_instruction_file(root, os.path.join(root, f), scripts, targets, is_py, has_pkg)
    if nested:
        found.append(f"{len(nested)} in subfolders")
    agents_md = os.path.isfile(os.path.join(root, "AGENTS.md"))
    main = read(os.path.join(root, "CLAUDE.md")) or read(os.path.join(root, ".claude/CLAUDE.md")) or ""
    has_main = any(c.startswith(("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")) for c in found)
    if agents_md and has_main and "@AGENTS.md" not in main:
        add("WARN", "CLAUDE.md", "AGENTS.md", "exists but is not read: Claude Code reads AGENTS.md only when there is "
            "no CLAUDE.md. Put `@AGENTS.md` at the top of CLAUDE.md to share one file.")
    elif agents_md and not has_main:
        found.append("AGENTS.md (read in place of CLAUDE.md)")
    return found


def check_rules(root, files):
    rules = [f for f in files if f.startswith(".claude/rules/") and f.endswith(".md")]
    scoped = 0
    for f in rules:
        fields, _, problem = frontmatter(read(os.path.join(root, f)))
        if problem and not problem.startswith("no frontmatter"):
            add("WARN", "rules", f, problem + ". The rule loads unscoped, in every session.")
        for k in fields:
            if k != "paths":
                add("WARN", "rules", f, f"frontmatter field `{k}` is ignored. `paths` is the only field a rule reads.")
        paths = fields.get("paths")
        if not paths:
            add("INFO", "rules", f, "has no `paths`, so it loads in every session like more CLAUDE.md")
            continue
        scoped += 1
        if isinstance(paths, str):
            paths = [p.strip().strip("\"'") for p in paths.strip("[]").split(",") if p.strip()]
        for p in paths:
            if p.count("[") != p.count("]"):
                add("ERROR", "rules", f, f"path pattern `{p}` has an unclosed [ and matches nothing")
            elif glob_matches(p, files) == 0:
                add("WARN", "rules", f, f"path pattern `{p}` matches no file in the project, so the rule never loads")
    return rules, scoped


def check_skills(root, files):
    skills = sorted({f.split("/")[2] for f in files if re.match(r"^\.claude/skills/[^/]+/SKILL\.md$", f)}
                    - {"loadout", "harness"})  # this skill itself, when installed per project
    for f in files:
        if re.match(r"^\.claude/skills/[^/]+\.md$", f) and not f.endswith("README.md"):
            add("ERROR", "skills", f, "a skill must be a folder: .claude/skills/<name>/SKILL.md. This file is not loaded.")
    for s in skills:
        f = f".claude/skills/{s}/SKILL.md"
        text = read(os.path.join(root, f))
        fields, body, problem = frontmatter(text)
        if problem:
            add("WARN" if problem.startswith("no frontmatter") else "ERROR", "skills", f, problem)
        for k in fields:
            if k not in SKILL_FIELDS:
                add("WARN", "skills", f, f"frontmatter field `{k}` is not a skill field and is ignored")
        desc = fields.get("description")
        if isinstance(desc, list):
            desc = " ".join(desc)
        if not desc:
            add("WARN", "skills", f, "no description. Claude decides when to use a skill from its description alone.")
        else:
            wtu = fields.get("when_to_use") or ""
            if isinstance(wtu, list):
                wtu = " ".join(wtu)
            if len(desc) + len(wtu) > 1536:
                add("WARN", "skills", f, f"description is {len(desc) + len(wtu)} characters; the listing cuts it at 1,536")
        if body.count("\n") > 500:
            add("WARN", "skills", f, f"body is {body.count(chr(10))} lines. Keep SKILL.md under 500 and move detail into files it points to.")
    return skills


def check_commands(root, files):
    cmds = [f for f in files if f.startswith(".claude/commands/") and f.endswith(".md")]
    if cmds:
        add("INFO", "commands", ".claude/commands/", f"{len(cmds)} command file(s) in the older format. They still work; "
            "the docs say to use a skill for anything new.")
    return cmds


def check_agents(root, files):
    agents = [f for f in files if f.startswith(".claude/agents/") and f.endswith(".md")]
    for f in agents:
        fields, _, problem = frontmatter(read(os.path.join(root, f)))
        if problem:
            add("ERROR", "subagents", f, problem + ". The file is skipped.")
            continue
        for req in ("name", "description"):
            if not fields.get(req):
                add("ERROR", "subagents", f, f"missing `{req}`. A subagent needs both name and description or it is skipped.")
        for k in fields:
            if k not in AGENT_FIELDS:
                hint = ""
                low = {a.lower().replace("-", "").replace("_", ""): a for a in AGENT_FIELDS}
                guess = low.get(k.lower().replace("-", "").replace("_", ""))
                if guess:
                    hint = f" Did you mean `{guess}`?"
                elif k == "allowed-tools":
                    hint = " Did you mean `tools`?"
                add("WARN", "subagents", f, f"frontmatter field `{k}` is not a subagent field and is silently ignored.{hint}")
    return agents


def check_mcp(root):
    servers = []
    if os.path.exists(os.path.join(root, ".claude", "mcp.json")):
        add("WARN", "MCP", ".claude/mcp.json", "is not read. Project servers go in .mcp.json at the project root.")
    path = os.path.join(root, ".mcp.json")
    text = read(path)
    if text is None:
        return servers
    try:
        data = json.loads(text)
    except ValueError as e:
        add("ERROR", "MCP", ".mcp.json", f"not valid JSON ({e}). No project server loads.")
        return servers
    block = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(block, dict):
        add("ERROR", "MCP", ".mcp.json", "has no `mcpServers` object, so it defines no servers")
        return servers
    for name, cfg in block.items():
        servers.append(name)
        if not isinstance(cfg, dict):
            add("ERROR", "MCP", ".mcp.json", f"server `{name}` is not an object")
            continue
        if "url" in cfg and "type" not in cfg:
            add("ERROR", "MCP", ".mcp.json", f"server `{name}` has a `url` but no `type` (use \"http\"). It is skipped.")
        if "url" not in cfg and "command" not in cfg:
            add("ERROR", "MCP", ".mcp.json", f"server `{name}` has neither `command` nor `url`")
        blob = json.dumps({k: cfg.get(k) for k in ("env", "headers", "args", "url")})
        for val in re.findall(r'"([^"]{20,})"', blob):
            if "${" in val:
                continue
            if re.search(r"(sk-|ghp_|xox[bp]-|Bearer [A-Za-z0-9._-]{16,}|://[^/\s:]+:[^@\s]+@)", val) or \
               re.fullmatch(r"[A-Za-z0-9_\-]{32,}", val):
                add("WARN", "MCP", ".mcp.json", f"server `{name}` seems to hold a secret in the file. Use ${{VAR}} "
                    "and keep the value in the environment.")
                break
    return servers


def rule_ok(rule):
    return bool(re.match(r"^(\*|mcp__[\w*.-]+|[A-Z][A-Za-z]*)(\(.*\))?$", rule))


def check_settings(root, files):
    info = {"files": [], "allow": 0, "ask": 0, "deny": 0, "hooks": [], "sandbox": False, "stop_hook": False}
    env_files = [f for f in os.listdir(root) if f.startswith(".env") and not f.endswith((".example", ".sample", ".template"))]
    deny_all = []
    have_jq = shutil.which("jq") is not None
    for fname in (".claude/settings.json", ".claude/settings.local.json"):
        path = os.path.join(root, fname)
        text = read(path)
        if text is None:
            continue
        info["files"].append(fname)
        try:
            data = json.loads(text)
        except ValueError as e:
            add("ERROR", "settings", fname, f"not valid JSON ({e}). Claude Code skips the whole file, so none of its "
                "rules or hooks apply. No comments, no trailing commas.")
            continue
        if not isinstance(data, dict):
            add("ERROR", "settings", fname, "must be a JSON object")
            continue
        if "mcpServers" in data:
            add("WARN", "settings", fname, "`mcpServers` here is not read. Servers go in .mcp.json.")
        perms = data.get("permissions") or {}
        if isinstance(perms, dict):
            for kind in ("allow", "ask", "deny"):
                rules = perms.get(kind) or []
                if not isinstance(rules, list):
                    add("ERROR", "settings", fname, f"permissions.{kind} must be a list")
                    continue
                info[kind] += len(rules)
                for r in rules:
                    if not isinstance(r, str) or not rule_ok(r):
                        add("ERROR", "settings", fname, f"permission rule {r!r} is not `Tool` or `Tool(specifier)`")
                        continue
                    m = re.match(r"^(Write|Grep|Glob|NotebookEdit|MultiEdit)\((.+)\)$", r)
                    if m and m.group(2) != "*":
                        swap = "Edit" if m.group(1) in ("Write", "NotebookEdit", "MultiEdit") else "Read"
                        add("WARN", "settings", fname, f"`{r}` matches nothing: path rules only work on Read and Edit. "
                            f"Use `{swap}({m.group(2)})`.")
                    if kind == "allow" and re.match(r"^(\*|Bash|Bash\(\*\)|Bash\(\*:\*\)|Edit|Edit\(\*\)|Write|Write\(\*\)|WebFetch|WebFetch\(\*\)|WebFetch\(domain:\*\))$", r):
                        add("WARN", "settings", fname, f"`{r}` in allow approves everything of that kind without asking. "
                            "Allow the commands the task needs instead.")
                    if kind == "deny":
                        deny_all.append(r)
            mode = perms.get("defaultMode")
            if mode in ("auto", "bypassPermissions"):
                add("WARN", "settings", fname, f"`defaultMode: {mode}` is ignored in a project file. It only works in "
                    "the user's own settings." + (" Bypass mode is for disposable containers." if mode == "bypassPermissions" else ""))
        sb = data.get("sandbox")
        if isinstance(sb, dict) and sb.get("enabled"):
            info["sandbox"] = True
        hooks = data.get("hooks")
        if hooks is None:
            continue
        if not isinstance(hooks, dict):
            add("ERROR", "hooks", fname, "`hooks` must be an object keyed by event name")
            continue
        for event, groups in hooks.items():
            if event not in HOOK_EVENTS:
                near = [e for e in HOOK_EVENTS if e.lower() == event.lower()]
                add("ERROR", "hooks", fname, f"`{event}` is not a hook event." + (f" Did you mean `{near[0]}`?" if near else ""))
                continue
            if not isinstance(groups, list):
                add("ERROR", "hooks", fname, f"`{event}` must be a list of matcher groups")
                continue
            for g in groups:
                if not isinstance(g, dict):
                    add("ERROR", "hooks", fname, f"`{event}`: each entry must be an object with a `hooks` list")
                    continue
                matcher = g.get("matcher")
                if isinstance(matcher, list):
                    add("ERROR", "hooks", fname, f"`{event}`: `matcher` must be a string such as \"Edit|Write\", not a list")
                elif isinstance(matcher, str) and event in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"):
                    for part in re.split(r"[|,]", matcher):
                        part = part.strip()
                        if part and re.fullmatch(r"[a-z]+", part) and part.capitalize() in TOOL_NAMES:
                            add("WARN", "hooks", fname, f"`{event}` matcher `{part}` never matches: tool names are "
                                f"case-sensitive (`{part.capitalize()}`)")
                        if re.fullmatch(r"mcp__[A-Za-z0-9_-]+", part):
                            add("WARN", "hooks", fname, f"`{event}` matcher `{part}` matches nothing. Use `{part}__.*`.")
                handlers = g.get("hooks")
                if not isinstance(handlers, list) or not handlers:
                    add("ERROR", "hooks", fname, f"`{event}`: a matcher group needs a non-empty `hooks` list of handlers")
                    continue
                for h in handlers:
                    if not isinstance(h, dict) or h.get("type") not in HOOK_TYPES:
                        add("ERROR", "hooks", fname, f"`{event}`: handler `type` must be one of {', '.join(sorted(HOOK_TYPES))}")
                        continue
                    label = f"{event}" + (f" [{matcher}]" if matcher else "")
                    if h["type"] == "command":
                        cmd = h.get("command")
                        if not isinstance(cmd, str) or not cmd.strip():
                            add("ERROR", "hooks", fname, f"`{event}`: a command handler needs a `command` string")
                            continue
                        info["hooks"].append(f"{label}: {cmd if len(cmd) < 70 else cmd[:67] + '...'}")
                        if event == "Stop":
                            info["stop_hook"] = True
                        # A placeholder, not the root itself: a root with a space ("C:\Users\First Last")
                        # would split the path at the space and report a hook that exists as missing.
                        expanded = cmd.replace("${CLAUDE_PROJECT_DIR}", "@ROOT@").replace("$CLAUDE_PROJECT_DIR", "@ROOT@")
                        expanded = expanded.replace('"', "").replace("'", "")
                        for script in re.findall(r"([^\s\"']*\.claude/hooks/[^\s\"']+|[^\s\"']+\.(?:sh|py|mjs|js|ps1))", expanded):
                            script = script.replace("@ROOT@", root)
                            sp = script if os.path.isabs(script) else os.path.join(root, script)
                            if not os.path.exists(sp):
                                add("ERROR", "hooks", fname, f"`{event}` runs {rel(root, sp)}, which does not exist")
                            elif sp.endswith(".sh") and os.name != "nt" and not os.access(sp, os.X_OK) and not re.search(r"\b(bash|sh)\s+[\"']?[^\s]*" + re.escape(os.path.basename(sp)), expanded):
                                add("ERROR", "hooks", fname, f"`{event}` runs {rel(root, sp)}, which is not executable (chmod +x)")
                        if re.search(r"\bjq\b", cmd) and not have_jq:
                            add("WARN", "hooks", fname, f"`{event}` uses jq, which is not installed on this machine, so the hook fails")
                        if event in ("PreToolUse", "Stop", "SubagentStop", "UserPromptSubmit") and re.search(r"exit 1\b", cmd):
                            add("WARN", "hooks", fname, f"`{event}` exits 1 on failure. Only exit code 2 blocks; 1 lets the action through.")
                    else:
                        info["hooks"].append(f"{label}: ({h['type']} hook)")
                        if event == "Stop":
                            info["stop_hook"] = True
    if env_files and not any(re.search(r"\.env", d) for d in deny_all):
        add("WARN", "settings", ".claude/settings.json", f"the project has {', '.join(sorted(env_files)[:3])} and no deny "
            "rule for it. Add `Read(./.env)` and `Read(./.env.*)` to permissions.deny so secrets stay out of the conversation.")
    return info


def user_level():
    home = os.path.expanduser("~/.claude")
    out = {}
    if not os.path.isdir(home):
        return out
    md = read(os.path.join(home, "CLAUDE.md"))
    if md is not None:
        out["CLAUDE.md"] = f"{md.count(chr(10)) + 1} lines"
        if md.count("\n") > 200:
            add("WARN", "CLAUDE.md", "~/.claude/CLAUDE.md", f"{md.count(chr(10)) + 1} lines, loaded into every project. The docs' target is under 200.")
    for sub, label in (("skills", "skills"), ("agents", "subagents"), ("rules", "rules"), ("commands", "commands")):
        d = os.path.join(home, sub)
        if os.path.isdir(d):
            n = len([x for x in os.listdir(d) if not x.startswith(".")])
            if n:
                out[label] = str(n)
    if os.path.isfile(os.path.join(home, "settings.json")):
        out["settings.json"] = "yes"
    return out


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return 0
    # The report uses UTF-8 characters; Windows consoles default to a legacy code page.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    root = os.path.abspath(args[0] if args else ".")
    as_json = "--json" in sys.argv
    if not os.path.isdir(root):
        print(f"not a folder: {root}", file=sys.stderr)
        return 2
    files = list_files(root)
    checks, scripts, targets, is_py = find_checks(root)
    claude_md = check_claude_md(root, files, scripts, targets if os.path.exists(os.path.join(root, "Makefile")) else set(), is_py)
    rules, scoped = check_rules(root, files)
    skills = check_skills(root, files)
    cmds = check_commands(root, files)
    agents = check_agents(root, files)
    servers = check_mcp(root)
    st = check_settings(root, files)
    user = {} if "--no-user" in sys.argv else user_level()

    md_text = " ".join(read(os.path.join(root, c)) or "" for c in ("CLAUDE.md", ".claude/CLAUDE.md"))
    named = [c for c in checks if c["command"] in md_text or c["command"].replace(" run ", " ") in md_text]
    has_verify = "verify" in skills
    if checks and not named and not st["stop_hook"] and not has_verify:
        add("WARN", "loop", "CLAUDE.md", "the project has checks Claude could run (" + ", ".join(sorted({c["command"] for c in checks})[:4]) +
            ") but nothing tells Claude to run them: no command in CLAUDE.md, no verify skill, no Stop hook.")
    if not checks:
        add("INFO", "loop", "project", "no test, lint, typecheck or build command found. Claude has nothing to run "
            "that comes back pass or fail; building one is the first job.")

    pieces = [
        ("CLAUDE.md", "knows", ", ".join(claude_md) if claude_md else ""),
        ("Rules", "knows", f"{len(rules)} ({scoped} path-scoped)" if rules else ""),
        ("Skills", "knows", f"{len(skills)}: {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}" if skills else ""),
        ("Commands", "can do", f"{len(cmds)} in .claude/commands/" + (f", plus {len(skills)} skills run by name" if skills else "") if cmds
            else (f"{len(skills)} skills run by name" if skills else "")),
        ("Subagents", "can do", f"{len(agents)}: " + ", ".join(os.path.basename(a)[:-3] for a in agents[:8]) if agents else ""),
        ("MCP servers", "can do", f"{len(servers)}: {', '.join(servers[:8])}" if servers else ""),
        ("Settings", "in check", (", ".join(st["files"]) + f" (allow {st['allow']}, ask {st['ask']}, deny {st['deny']}"
            + (", sandbox on" if st["sandbox"] else "") + ")") if st["files"] else ""),
        ("Hooks", "in check", f"{len(st['hooks'])}: " + "; ".join(st["hooks"][:4]) if st["hooks"] else ""),
    ]
    present = sum(1 for _, _, v in pieces if v)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: order[f["level"]])
    errors = sum(1 for f in findings if f["level"] == "ERROR")

    if as_json:
        print(json.dumps({"root": root, "pieces": [{"piece": p, "job": j, "found": v} for p, j, v in pieces],
                          "present": present, "checks": checks, "checks_named_in_claude_md": [c["command"] for c in named],
                          "stop_hook": st["stop_hook"], "verify_skill": has_verify,
                          "harness_map": os.path.exists(os.path.join(root, ".claude", "HARNESS.md")),
                          "user_level": user, "findings": findings}, indent=2))
        return 1 if errors else 0

    print(f"# Harness check: {root}\n")
    print(f"## The eight pieces ({present} of 8 present)\n")
    print("| Piece | Job | Found |")
    print("|---|---|---|")
    for p, j, v in pieces:
        print(f"| {p} | {j} | {v or 'none'} |")
    print("\n## The loop: what Claude can run to check its own work\n")
    if checks:
        for c in checks:
            mark = "named in CLAUDE.md" if c in named else "not named in CLAUDE.md"
            print(f"- `{c['command']}` ({c['kind']}, from {c['source']}; {mark})")
    else:
        print("- none found")
    print(f"- Stop hook: {'yes' if st['stop_hook'] else 'no'} · verify skill: {'yes' if has_verify else 'no'}"
          f" · harness map (.claude/HARNESS.md): {'yes' if os.path.exists(os.path.join(root, '.claude', 'HARNESS.md')) else 'no'}")
    if user:
        print("\n## Also loaded from the user's own ~/.claude (every project)\n")
        print("- " + ", ".join(f"{k}: {v}" for k, v in user.items()))
    print(f"\n## Findings ({errors} error(s), {sum(1 for f in findings if f['level'] == 'WARN')} warning(s))\n")
    if not findings:
        print("- none")
    for f in findings:
        print(f"- **{f['level']}** [{f['piece']}] `{f['where']}`: {f['msg']}")
    print("\nA count of pieces is not a score. A piece earns its place only if the task uses it.")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # output piped into head and the like
        sys.exit(0)
