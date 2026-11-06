# Project navigation

Preserve the more specific instructions in drip-backend/AGENTS.md.

## Graphify (optional navigation aid)

- Prefer a scoped Graphify query for architecture/navigation questions when
  graphify-out/graph.json exists and is current. Verify exact behavior against
  source and tests; graph extraction is not a completed semantic audit.
- Local tool installed for this workstation:
  `C:\Users\wasam\AppData\Local\WearHowZTools\graphify-0.9.103\Scripts\graphify.exe`.
  Other workstations should install `graphifyy==0.9.103` in an isolated environment.
- Query from the repository root: `graphify query "question" --budget 1200`.
  Use `graphify explain "symbol"` or `graphify path "A" "B"` for focused tracing.
  In PowerShell use `& 'full-path-to-graphify.exe'` if it is not on PATH.
- Build only with `graphify extract . --code-only --no-cluster --max-workers 1`,
  then `graphify cluster-only . --no-label --no-viz`. Preserve .graphifyignore.
  No semantic/cloud analysis, automatic hooks, global configuration changes,
  or scanning excluded files without explicit approval.
- Scope is backend/frontend first-party code, excluding documentation/media,
  secrets, dependencies, generated outputs and the two excluded legacy utilities.
- If unavailable or stale, say so and inspect scoped source. Do not let missing
  graph data block verification. Do not claim absence of a graph edge proves
  absence of a runtime relationship.
- Review graph.json and GRAPH_REPORT.md for sensitive content before committing.
  Never commit local caches or generated graph.html. Do not automatically commit.

The upstream Codex skill is not registered: its installer adds hooks beyond the
approved limited setup. These instructions provide project-local guidance only.
