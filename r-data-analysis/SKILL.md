---
name: r-data-analysis
description: >-
  Performs interactive statistical modeling, exploratory data analysis (EDA), database analytics,
  and R Markdown (.Rmd) workflows using the r-btw R MCP server (btw_tool_run_r). Activate this
  skill for ANY data analysis task, database telemetry queries, statistical comparisons, data
  visualization, survival analysis, GLMM/Cox modeling, or when working with R or .Rmd files.
  Leverages the persistent, live R session to perform fast, stateful, multi-step analysis and iterative debugging.
---

# Interactive R Data Analysis & Statistical Modeling Skill

Use this skill whenever you need to explore data, query SQLite databases, fit statistical models, perform survival or regression analysis, generate plots, or work with R Markdown (`.Rmd`) files.

---

## ⚡ The Power of the Stateful R MCP Session (`r-btw`)

Unlike one-off shell commands (`run_command` with `Rscript -e` or `python3`) where every invocation starts a cold process, re-parses libraries, and reloads data from disk, **the `r-btw` MCP server keeps the R session alive in memory across tool calls**.

### Why This Is Extremely Powerful:
1. **Persistent Memory State**: Once you load data frames, fit models (`fit_cox`, `fit_glmm`), or define helper functions in step 1, they remain in memory and ready for instant access in steps 2, 3, 4, etc.
2. **Effortless Multi-Step Exploration**: You can progressively drill down into data, test hypotheses, inspect residuals, and compare subsets without writing monolithic throwaway scripts.
3. **Interactive Debugging**: If a modeling function throws a convergence warning or index error, you can inspect the exact variables (`str()`, `summary()`, `head()`) in the live environment and fix it in the next call without starting over.
4. **Clean, Native Output**: Results are returned directly as structured R tibbles, data frames, numbers, and plots without bash quoting issues, subshell execution overhead, or permission prompts.

---

## Tool Overview (`r-btw` MCP Server)

Invoke these tools using `call_mcp_tool` with `ServerName: "r-btw"`:

| Tool Name | Purpose |
| :--- | :--- |
| **`btw_tool_run_r`** | Execute R code in the persistent session. Captures outputs, data frames, model summaries, and figures. |
| **`btw_tool_docs_help_page`** | Pull complete R function documentation, parameter specs, and examples on the fly. |
| **`btw_tool_docs_package_help_topics`** | List all available functions and help topics exported by an installed package. |
| **`btw_tool_docs_vignette`** | Read package tutorials and vignettes directly in markdown format. |
| **`btw_tool_env_describe_environment`** | List all loaded objects, variables, and models currently residing in the active R session. |
| **`btw_tool_env_describe_data_frame`** | Inspect column types, missing values, and summary stats for a specific data frame. |
| **`btw_tool_sessioninfo_package`** | Check package versions and dependencies. |
| **`list_r_sessions` / `select_r_session`** | View or switch between active R sessions. |

---

## 📚 On-Demand Documentation & Method Discovery

When exploring unfamiliar R packages or model objects:

1. **Pull Function Help & Signatures**:
   Use `btw_tool_docs_help_page` (e.g. `package_name: "survival"`, `topic: "coxph"`) to inspect argument signatures, defaults, and usage examples without guessing.
2. **Discover Available Methods for Any Model Class**:
   In `btw_tool_run_r`, query available S3/S4 methods for your fitted model:
   ```r
   # Find all generic methods implemented for a fitted model
   methods(class = class(fit_model))

   # Check function arguments directly
   args(predict.coxph)
   ```
3. **Browse Package Help Topics & Vignettes**:
   Use `btw_tool_docs_package_help_topics` to discover all available functions in a library.

---

## Standard Workflow

### Step 1: Connect and Load Data into Session State
Load your database or datasets once into session variables:
```r
library(DBI)
library(dplyr)
library(tidyr)

con <- dbConnect(RSQLite::SQLite(), "parkiza_stats.db")
scans <- dbGetQuery(con, "SELECT * FROM scans")
spots <- dbGetQuery(con, "SELECT * FROM spots")
sa <- dbGetQuery(con, "SELECT * FROM spot_availability")
dbDisconnect(con)
```

### Step 2: Interactive Data Transformation & EDA
Build derived features or pipelines. Because variables persist, subsequent calls can directly use `scans`, `spots`, and `sa`:
```r
df_all <- scans %>%
  crossing(spots) %>%
  left_join(sa, by = c("scan_id", "spot_id")) %>%
  mutate(
    is_occupied = 1 - is_free,
    weekday = weekdays(as.Date(target_date))
  )

# Return the object directly to display summary
head(df_all)
```

### Step 3: Statistical Modeling & Hypothesis Testing
Fit models (e.g., `survival::coxph`, `lme4::glmer`, `stats::lm`) and retain the model objects in session state:
```r
library(survival)
fit_cox <- coxph(Surv(time, status) ~ is_wider + zone + cluster(target_date), data = survival_data)
summary(fit_cox)
```

### Step 4: Multi-Step Diagnostics & Comparisons
In the next tool call, directly interrogate the fitted model without re-running Step 1 or 3:
```r
# Extract confidence intervals or compare odds ratios
round(exp(coef(fit_cox)), 3)
```

---

## 🚀 Pro-Tip: Running an Entire `.Rmd` in Memory (`knitr::purl`)

When working with an existing `.Rmd` report (like `parkiza_analysis.Rmd`), you can **ingest all code chunks directly into the live R session** in a single call:

```r
# Extract all Rmd chunks and evaluate them into global session memory
tmp_r <- tempfile(fileext = ".R")
knitr::purl("parkiza_analysis.Rmd", output = tmp_r, documentation = 0)
source(tmp_r, local = FALSE)
```

### Why This Unlocks Instant Analytics:
* **All Pipeline Variables Populated**: Every transformed tibble (`df_all`, `survival_data`), fitted model (`fit_cox`, `fit_glmm`), summary table (`spot_rank`, `runtime_df`), and threshold variable (`spot_7a14`, `median_occ`) becomes instantly accessible in memory.
* **Zero Boilerplate for Follow-up Questions**: When asked any analytical question (e.g., *"How many spots are freed up at 10 AM?"* or *"What are the GLMM coefficients?"*), the agent can query the in-memory objects directly in 1 second.
* **Interactive Chunk Prototyping**: Test and refine new modeling chunks on live data in `btw_tool_run_r` before editing `.Rmd`.

---

## Best Practices & Guidelines

1. **Work Incrementally**: Perform one clear analytical step per tool call.
2. **Implicit Returns**: Make the last expression in your R snippet the object you want returned (e.g. `tibble`, `summary_df`, `model_fit`). Avoid excessive `cat()` or `print()` calls unless needed for formatting.
3. **Keep Tool Calls Concise**: Leverage existing session objects rather than re-importing libraries or re-fetching raw data in every snippet.
4. **Render Rmd Reports Cleanly**: When compiling `.Rmd` files, use `rmarkdown::render()` or run the report compiler script, and use `btw_tool_run_r` to examine any underlying data shifts.

