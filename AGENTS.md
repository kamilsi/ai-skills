# Skill Authoring Rules for Agents

Guidelines for AI agents creating or editing skills in this repository:

1. **Frontmatter Constraints & Routing (Agent Skills Specification)**:
   - **`name`** (required): Maximum **64 characters**, lowercase alphanumeric and hyphens only (`^[a-z0-9-]+$`). Must match the parent directory name.
   - **`description`** (required): Strict hard limit: **max 1,024 characters**. Exceeding 1,024 characters causes runtime errors or silent dropping of the skill during YAML parsing.
   - **Optimal description length**: ~100–150 words (400–700 characters). Write in 3rd person, clearly state *what* it does and *exact conditions/keywords* that trigger it. Avoid bloated keyword dumping; keep triggers focused and natural.
   - The frontmatter `description` is the **only** text the agent reads before activating the skill (it is injected into the model's system prompt at startup).

2. **Cross-Workspace Script Execution**:
   - Because user sessions run from arbitrary project roots, reference scripts inside `SKILL.md` using `~/.gemini/skills/<skill_name>/scripts/<script_name>` or relative markdown links `[script](./scripts/foo.sh)`.
   - Never assume the user's CWD is the skill directory.

3. **Progressive Disclosure & Token Economy (CLI / IDE Skills)**:
   - Keep `SKILL.md` concise (< 150–500 lines). Move heavy documentation, schema dumps, or extensive cheat sheets into a `references/` subfolder and link to them with markdown links.
   - Do not duplicate general coding advice; focus strictly on domain-specific procedures, tools, and runbooks.

4. **Web Skills (Gemini Web UI / Mobile / Gems)**:
   - Skills packaged for the Gemini Web UI (`web/` or standalone web gems) **do NOT support `references/` or auxiliary directories** — the browser runtime cannot read external files or navigate subdirectories.
   - Web skills must be **100% self-contained within `SKILL.md`**. All relevant category mappings, URLs, and institutions must be written directly into `SKILL.md`.
   - Never bundle a `references/` directory into web skill ZIP packages (`.zip` must contain only `SKILL.md`).
