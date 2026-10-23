# AI Skills (`ai-skills`)

Central, cross-platform skills repository for Google Antigravity (`agy`).

## Setup (macOS / Linux)

```bash
mkdir -p ~/.gemini && ln -sfn ~/Code/ai-skills ~/.gemini/skills
```

`agy` resolves `~/.gemini/skills` transparently. Any subfolder containing `SKILL.md` becomes immediately available across all workspaces.

## Skills Catalog

- **[`macos-reminders`](./macos-reminders/SKILL.md)** (*macOS*): Apple Reminders automation via EventKit Swift CLI (`remindctl`) & AppleScript fallback.
- **[`moonshine-game-streaming`](./moonshine-game-streaming/SKILL.md)** (*Linux / RTX 4060*): Administration, monitoring, configuration, and troubleshooting for Moonshine headless GameStream server on `odyseusz` (Ubuntu 26.04 Wayland, HDR, 4K).
- **[`macos-disk-triage`](./macos-disk-triage/SKILL.md)** (*macOS / Apple Silicon*): Diagnose and safely reclaim disk space on the 245 GB dev MacBook. Checks known runaway writers (Gemini telemetry leak, ~39 GB/hour) before analysing, carries a forensic baseline, and lists the destructive traps to avoid.
- **[`r-data-analysis`](./r-data-analysis/SKILL.md)** (*Universal*): Interactive data analysis, GLMM/survival modeling, SQLite querying, and `.Rmd` workflows via persistent `r-btw` MCP session.
- **[`grounded-theory`](./grounded-theory/SKILL.md)** (*Universal*): Investigative sensemaking and Grounded Theory (Glaser & Strauss) — anomaly detection, *in-vivo* language coding, contradiction mapping, open/axial/selective coding, and iterative hypothesis testing via the Constant Comparative Method.
- **[`zambrow`](./zambrow/README.md)** (*macOS / Universal*): Local assistant for Zambrów — municipal news, events calendar, ads, company directory, and Kino MOK cinema showtimes with automated Filmweb/IMDb ratings. Includes local PC CLI integration (`zambrow_tool.py`) and a Google Agent Skills package for Gemini Web GUI (`web/zambrow.zip`).

## Non-Obvious Behaviors

- **Progressive Disclosure & Description Limits**: `agy` only injects frontmatter `name` (max 64 chars) and `description` into context upfront. The `description` field has a **strict 1,024-character hard limit** (recommended: 100–150 words / ~400–700 chars); exceeding it causes runtime loading failure. The full `SKILL.md` body loads on-demand only when activated.
- **Helper Scripts**: Place binaries and helpers in `<skill>/scripts/`. In `SKILL.md`, reference them via `~/.gemini/skills/<skill>/scripts/...` to ensure execution regardless of workspace CWD.
- **Gemini Web GUI Maintenance**: Skills intended for the Gemini Web interface (`gemini.google.com`) or mobile/desktop Gemini apps **do not sync automatically** with this git repository. Any updates to web skills (e.g. `zambrow/web`) must be manually re-packaged and uploaded via **gemini.google.com -> Customize -> Skills -> Upload**. Note that web skills **do not support `references/` directories**; they must be 100% self-contained within `SKILL.md`.
