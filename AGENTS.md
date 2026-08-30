# Skill Authoring Rules for Agents

Guidelines for AI agents creating or editing skills in this repository:

1. **Routing Relies on Frontmatter**:
   - `description` in YAML frontmatter is the **only** text the agent reads before activating the skill. Write it in 3rd person and explicitly state *what* it does and *exact conditions/keywords* that trigger it.
   - Keep `name` lowercase and hyphenated, matching the parent directory name.

2. **Cross-Workspace Script Execution**:
   - Because user sessions run from arbitrary project roots, reference scripts inside `SKILL.md` using `~/.gemini/skills/<skill_name>/scripts/<script_name>` or relative markdown links `[script](./scripts/foo.sh)`.
   - Never assume the user's CWD is the skill directory.

3. **Progressive Disclosure & Token Economy**:
   - Keep `SKILL.md` concise (< 150 lines). Move heavy documentation, schema dumps, or extensive cheat sheets into a `references/` subfolder and link to them with markdown links.
   - Do not duplicate general coding advice; focus strictly on domain-specific procedures, tools, and runbooks.
