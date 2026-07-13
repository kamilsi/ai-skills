---
name: r-data-analysis
description: General key workflows and best practices for R-based statistical analysis, package installation, time-series, survival models, and report proofreading.
---

# R-Based Data Analysis with MCP: Key Workflows

This skill provides general, highly efficient workflows for pair-programming and executing R-based data analyses on the system.

## 1. Incremental R Execution (via r-btw)
* **Execution**: Use the `r-btw` MCP tools (like `btw_tool_run_r`) to execute R code incrementally.
* **Code Size**: Write short, idiomatic R snippets (preferably under 50 lines) focused on a single logical step.
* **Outputs**: Prefer returning structured summaries (e.g., using `head()`, `str()`, or `summary()`) rather than raw printed tables to avoid context pollution.
* **Tidyverse**: Use `dplyr`, `tidyr`, `ggplot2`, and the wider tidyverse ecosystem for clean data manipulations.
* **Serialization of S7 & Condition Objects**: In newer versions of `btw` and `ellmer` (e.g., `btw` >= 1.3.0 and `mcptools` >= 1.0.0), returning mixed outputs (like plots, warnings, or messages) can cause JSON serialization errors: `No method asJSON S3 class: S7_object` or `No method asJSON S3 class: condition`.
  * If this occurs, register S4 methods for `jsonlite:::asJSON` at the beginning of the R code block to translate these classes into serializable lists:
    ```R
    tryCatch({
      methods::setOldClass("S7_object")
      methods::setOldClass("condition")
    }, error = function(e) NULL)
    methods::setMethod(jsonlite:::asJSON, "S7_object", function(x, ...) jsonlite:::asJSON(S7::props(x), ...))
    methods::setMethod(jsonlite:::asJSON, "condition", function(x, ...) jsonlite:::asJSON(conditionMessage(x), ...))
    ```

## 2. Package Installation Workflow
If a package is missing or needs an update:
1. **Identify the R Library Path**: Check `.libPaths()` to see where libraries are being loaded.
2. **Primary - pak**: Install standard packages via the terminal using the `pak` package manager:
   ```bash
   Rscript -e "pak::pkg_install('package_name')"
   ```
3. **Fallback - install.packages**: If `pak` fails to uncompress or build (e.g., due to local cache corruption or network issues with remote repositories), run a standard `install.packages()` targeting CRAN and Posit's R-universe:
   ```bash
   Rscript -e "install.packages('package_name', repos = c('https://posit-dev.r-universe.dev', 'https://cloud.r-project.org'))"
   ```


## 3. Data Preprocessing & Session Reconstruction
* **Event Sessionization**: To group sequential log events into distinct activity sessions:
  * Sort records chronologically per entity identifier.
  * Compute time diffs between consecutive observations.
  * Segment into distinct sessions using a threshold gap (e.g., if the time gap between events exceeds a specific limit).
* **Feature Categorization**: Group raw categorical variables into meaningful ordinal or speed/intensity classes to analyze heterogeneity and mixing penalties in linear regressions.

## 4. Advanced Modeling Workflows

### Time-Series Forecasting (TSLM)
* Use `tsibble` and `fable` to fit daily/hourly time-series linear regressions.
* **Important**: In `fable`, fit separate models individually rather than putting different response variables in a single `model()` call:
  ```R
  fit_metric_a <- daily_ts %>% model(TSLM(metric_a ~ factor_1 + factor_2))
  fit_metric_b <- daily_ts %>% model(TSLM(metric_b ~ factor_1 + factor_2))
  ```

### Binary Logistic Regression
* Model operational outcomes or activity status (active vs. suspended) as a binary outcome using `glm(..., family = binomial)`.
* Compute 50% probability threshold boundaries for key numerical predictors using:
  ```R
  threshold <- -coefs[1] / coefs[2]
  ```

### Survival Analysis (Maneuver loops vs. Real-Time)
* Use the `survival` and `survminer` packages.
* Fit Kaplan-Meier curves using `survfit(Surv(time, status) ~ group, data)` to compare persistence times or repetition frequencies.
* Run Log-Rank tests using `survdiff(Surv(time, status) ~ group, data)`.
* Run Cox Proportional Hazards regression to evaluate relative risks of session termination:
  ```R
  coxph(Surv(time, status) ~ covariates, data)
  ```

## 5. Report Compilation & Native HTML Rendering
When rendering `.Rmd` reports to read in the browser without external system packages like Pandoc:
1. **Compile to Markdown**: Use `knitr::knit()` via Rscript. This processes R code and outputs standard markdown text and tables without Pandoc dependencies:
   ```bash
   Rscript -e "knitr::knit('Report.Rmd', 'Report.md')"
   ```
2. **Render Markdown to HTML**: Use the C++-based R `markdown` package, which generates HTML files natively without external dependencies:
   ```bash
   Rscript -e "markdown::markdownToHTML('Report.md', 'Report.html')"
   ```

## 6. Proofreading Compiled Reports
Proofreading the raw `.Rmd` file is prone to errors since R code chunks are not yet evaluated. Always compile to Markdown (`.md`) to proofread the output before sharing it or converting it to HTML:
1. **Verify Code Execution**: Check the compiled `.md` file to ensure R code chunks executed successfully and did not output hidden warnings, warnings masked as output, or silent compilation failures.
2. **Inspect Formatted Outputs**: Review the generated tables, printed tibble structures, and metrics to ensure alignment.
3. **Verify inline variables**: Check that inline R expressions (e.g., `` `r round(var, 2)` ``) rendered with actual calculated values rather than NA or errors.
4. **Locate plot outputs**: Verify that figures and charts are correctly generated and referenced in the markdown text.
5. **Avoid Hardcoded Metrics**: Always use inline R expressions (e.g., `` `r round(coef(model)[2], 2)` ``) for reporting coefficients, statistics, and conversions in text descriptions or policy recommendations. Hardcoding numbers leads to maintenance issues and inconsistencies if model formulas or source datasets are updated.

## 7. Project Bootstrapping & Context Configuration
When starting to work on a new R project or codebase, follow these bootstrapping steps:
1. **Initialize Project Context**: Call `btw::use_btw_md(scope = "project")` to generate a `btw.md` file in the project root. This file controls which tools are exposed and defines specific coding styles (e.g., using `<-` for assignment, `|>` for pipes, and preference for tidyverse packages).
2. **Expose Custom Tools**: You can edit `btw.md` to add or remove exposed tool categories (e.g., `files`, `git`, `docs`, `session`, `web`).
3. **Resolve Package Dependencies**: Check the project's dependencies and install any missing packages using `pak` (or `install.packages()` fallback) immediately.
4. **Boot Up Session Adapters**: Run the S4 serialization registration script at the beginning of the first R evaluation chunk to ensure any plot outputs or system warnings do not break JSON communication with the MCP server.

