# AI Skills (`ai-skills`)

Central, cross-platform skills repository for Google Antigravity (`agy`).

## Setup (macOS / Linux)

```bash
mkdir -p ~/.gemini && ln -sfn ~/Code/ai-skills ~/.gemini/skills
```

`agy` resolves `~/.gemini/skills` transparently. Any subfolder containing `SKILL.md` becomes immediately available across all workspaces.

## Skills Catalog

- **[`macos-reminders`](./macos-reminders/SKILL.md)** (*macOS*): Apple Reminders automation via EventKit Swift CLI (`remindctl`) & AppleScript fallback.
- **[`r-data-analysis`](./r-data-analysis/SKILL.md)** (*Universal*): Interactive data analysis, GLMM/survival modeling, SQLite querying, and `.Rmd` workflows via persistent `r-btw` MCP session.

## Non-Obvious Behaviors

- **Progressive Disclosure**: `agy` only injects frontmatter `name` and `description` into context upfront. The full `SKILL.md` body loads on-demand only when activated.
- **Helper Scripts**: Place binaries and helpers in `<skill>/scripts/`. In `SKILL.md`, reference them via `~/.gemini/skills/<skill>/scripts/...` to ensure execution regardless of workspace CWD.
