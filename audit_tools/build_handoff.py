"""Generate an offline source inventory; syntax indexing is NOT a human code review.

Only approved first-party folders are scanned. Secret files, dependencies, caches,
generated output and the two specifically excluded legacy utilities are not opened.
The generated HTML is the only deliverable; helpers make its coverage reproducible.
"""

import ast
import hashlib
import html
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "WearHowZ_Project_Audit_Handoff.html"
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "htmlcov", "__pycache__", ".pytest_cache", ".ruff_cache", "test-results", "playwright-report"}
GENERATED = {"package-lock.json", "coverage.xml", ".coverage", "openapi.json", "verification.json", "dependency-audit.json"}
TEXT = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".css", ".html", ".md", ".json", ".toml", ".ini", ".yml", ".yaml", ".txt", ".mako"}


def purpose(rel):
    if "/tests/" in rel or ".test." in rel or ".spec." in rel:
        return "Test/fixture: verification intent, not proof of a passing current run."
    if "/alembic/versions/" in rel:
        return "Database migration: upgrade/downgrade and historical schema evolution; never edit an applied migration."
    if "/api/v1/" in rel:
        return "HTTP boundary: dependencies and validated payloads delegate to service/repository operations."
    if "/services/" in rel:
        return "Business operations: coordinates authorization, repositories, transaction effects and integrations."
    if "/repositories/" in rel:
        return "Persistence access: queries and row locking, usually inside the caller's transaction."
    if "/models/" in rel:
        return "SQLAlchemy persistence mapping: tables, fields, relationships and constraints."
    if "/schemas/" in rel:
        return "Pydantic input/output validation and serialization contract."
    if "/tasks/" in rel:
        return "Background worker function or scheduler registration; inspect retries and transaction boundaries."
    if "/integrations/" in rel:
        return "External provider adapter; local syntax/tests do not establish live acceptance."
    if "/core/" in rel:
        return "Shared runtime infrastructure or policy: verify callers and startup validation."
    if "/docs/" in rel or rel.endswith(".md"):
        return "Documentation/historical evidence; reconcile claims with source and verification dates."
    if rel.endswith(".tsx"):
        return "React UI/component: renders state and coordinates hooks, forms and API reads/writes."
    if rel.endswith(".ts") and "/src/" in rel:
        return "Frontend types, parsing, validation or state helpers; imports identify consumers."
    if rel.endswith(".css"):
        return "Presentation rules: layout, typography, responsive states and accessibility styling."
    return "Entry point, configuration, asset or tooling; inspect explicit settings and callers."


def python_index(text):
    tree = ast.parse(text)
    symbols = []
    def visit(node, owner=""):
        for child in ast.iter_child_nodes(node):
            nested = isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            name = f"{owner}.{child.name}" if owner and nested else child.name if nested else owner
            if nested:
                calls = sorted({ast.unparse(n.func) for n in ast.walk(child) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))})
                symbols.append({"name": name, "kind": type(child).__name__, "start": child.lineno,
                    "end": child.end_lineno, "doc": ast.get_docstring(child) or "", "calls": calls[:50]})
            visit(child, name)
    visit(tree)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append((node.module or "") + ": " + ", ".join(n.name for n in node.names))
        elif isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
    return {"symbols": symbols, "imports": sorted(set(imports)), "hooks": [], "parse_errors": []}


def main():
    records, excluded, ts_paths = [], [], []
    for folder in ("drip-backend", "drip-frontend", ".github"):
        # Prune before descent; never enumerate dependency/secret directory contents.
        import os
        for directory, dirs, files in os.walk(ROOT / folder):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                file = Path(directory) / name
                rel = file.relative_to(ROOT).as_posix()
                secret = (name.startswith(".env") and name != ".env.example") or file.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
                if secret:
                    excluded.append({"path": rel, "reason": "Secret/configuration value file: not opened or hashed"})
                    continue
                if name in {"fix_migration.py", "seed_users.py"}:
                    excluded.append({"path": rel, "reason": "AGENTS.md specifically excludes this legacy utility unless named"})
                    continue
                if name in GENERATED or file.suffix in {".xml", ".lock"} or "/docs/audit/" in rel and file.suffix == ".json":
                    excluded.append({"path": rel, "reason": "Generated or historical machine output: not a first-party source review"})
                    continue
                if file.suffix.lower() not in TEXT and name not in {"Dockerfile", "Dockerfile.worker", "Makefile", ".gitignore", ".dockerignore", ".env.example"}:
                    excluded.append({"path": rel, "reason": "Binary/asset or unsupported text type; visual/content verification pending"})
                    continue
                raw = file.read_bytes()
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    excluded.append({"path": rel, "reason": "Non-UTF-8 source: manual decoding review needed"})
                    continue
                record = {"path": rel, "lines": len(text.splitlines()), "sha256": hashlib.sha256(raw).hexdigest(), "purpose": purpose(rel), "symbols": [], "imports": [], "hooks": [], "parse_errors": []}
                if file.suffix == ".py":
                    try:
                        record.update(python_index(text))
                    except SyntaxError as exc:
                        record["parse_errors"] = [f"Line {exc.lineno}: {exc.msg}"]
                elif file.suffix in {".ts", ".tsx", ".js", ".mjs", ".cjs"}:
                    ts_paths.append(rel)
                records.append(record)
    if ts_paths:
        proc = subprocess.run(["node", str(ROOT / "audit_tools/index_typescript.cjs")], input=json.dumps(ts_paths), text=True, capture_output=True, check=True, encoding="utf-8")
        indexed = json.loads(proc.stdout)
        for record in records:
            record.update(indexed.get(record["path"], {}))
    records.sort(key=lambda r: r["path"])
    narrative = json.loads((ROOT / "audit_tools/review_notes.json").read_text(encoding="utf-8"))
    reviewed = narrative["reviewed_files"]
    for record in records:
        record["review"] = reviewed.get(record["path"], "Mechanically indexed only; semantic line-by-line review remains open.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all", "--", "drip-backend", "drip-frontend", ".github"], cwd=ROOT, text=True)
    summary = {"files": len(records), "lines": sum(r["lines"] for r in records), "symbols": sum(len(r["symbols"]) for r in records), "files_with_review_notes_including_partial": len(reviewed), "files_read_in_full_this_pass": sum(v.startswith("Read in full") or v.startswith("Read in two contiguous") for v in reviewed.values()), "parse_errors": sum(bool(r["parse_errors"]) for r in records), "groups": dict(Counter(r["path"].split('/')[0] for r in records)), "commit": commit}
    esc = html.escape
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WearHowZ — Project Audit &amp; Handoff</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#203b32;background:#f5f1e7;margin:0}main{max-width:1100px;margin:auto;padding:32px}h1,h2,h3{line-height:1.2}h1{font:46px Georgia,serif}section,details{background:#fffdf7;border:1px solid #d4d1c4;padding:18px;margin:18px 0}summary{cursor:pointer;font-weight:650;overflow-wrap:anywhere}a{color:#164e72}code,pre{font:13px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#eee;padding:14px}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #ddd;padding:8px;vertical-align:top;overflow-wrap:anywhere}.warn{border-left:6px solid #a64526}.pill{background:#e1eadf;padding:4px 8px}input{width:95%;padding:12px;font:inherit}.small{font-size:13px;color:#52645d}.symbol{border-top:1px solid #ddd;padding:8px 0}@media print{details{break-inside:avoid}input{display:none}}@media(max-width:600px){main{padding:15px}h1{font-size:32px}table{font-size:13px}}</style></head><body><main>', '<h1>WearHowZ<br>Project audit &amp; new-chat handoff</h1>', '<p>Snapshot: 5 November 2026 · Asia/Karachi · local working tree, including uncommitted files.</p>', '<section class="warn"><h2>Review status: in progress</h2><p>This is an evidence-backed handoff and complete mechanical source inventory, <strong>not a completed A–Z semantic/line-by-line audit</strong>. Indexing every definition does not prove its purpose or correctness. Use the coverage ledger below; do not convert an indexed item into “reviewed” without reading its body and connections.</p></section>', '<nav><a href="#start">Start here</a> · <a href="#findings">Findings</a> · <a href="#architecture">Architecture</a> · <a href="#coverage">Coverage ledger</a> · <a href="#excluded">Exclusions</a></nav>']
    parts += ['<section id="start"><h2>New-chat starting instructions</h2><pre>' + esc(narrative["start_prompt"]) + '</pre><p>Repository HEAD: <code>' + commit + '</code>. HEAD alone does not contain the uncommitted implementation described here. The new chat needs access to this working copy.</p></section>']
    for section in narrative["sections"]:
        parts.append('<section id="' + esc(section['id']) + '"><h2>' + esc(section['title']) + '</h2>' + section['html'] + '</section>')
    parts.append('<section><h2>Snapshot totals</h2><pre>' + esc(json.dumps(summary, indent=2)) + '</pre><p>Each symbol range is inclusive. Python calls are syntactic candidates, including nested definitions, not a resolved call graph. TypeScript declarations use its compiler parser; anonymous callbacks and every JSX expression are not individually explained. Docstrings quote source intent, not independently verified behavior.</p><details><summary>Uncommitted paths at snapshot</summary><pre>' + esc(status) + '</pre></details></section>')
    parts.append('<section id="coverage"><h2>File and definition coverage ledger</h2><label for="filter">Filter by path, symbol, import or review note</label><input id="filter" placeholder="For example: payment_service or useAccountWrite"><p id="visible"></p></section>')
    for r in records:
        parts.append('<details class="file"><summary>' + esc(r['path']) + ' · ' + str(r['lines']) + ' lines · ' + str(len(r['symbols'])) + ' definitions</summary><p><strong>Review:</strong> ' + esc(r['review']) + '</p><p>' + esc(r['purpose']) + '</p><p class="small">SHA-256: ' + r['sha256'] + '</p>')
        if r['parse_errors']:
            parts.append('<p class="warn">Parser diagnostics: ' + esc('; '.join(r['parse_errors'])) + '</p>')
        if r['imports']:
            parts.append('<details><summary>Imports / direct dependencies</summary><pre>' + esc('\n'.join(r['imports'])) + '</pre></details>')
        if r['hooks']:
            parts.append('<p>Hook calls: ' + esc(', '.join(r['hooks'])) + '</p>')
        for symbol in r['symbols']:
            parts.append('<div class="symbol"><strong>' + esc(symbol['name']) + '</strong> <span class="small">' + esc(symbol['kind']) + ' · lines ' + str(symbol['start']) + '–' + str(symbol['end']) + '</span>')
            if symbol['doc']:
                parts.append('<p class="small">Source docstring: ' + esc(symbol['doc']) + '</p>')
            if symbol['calls']:
                parts.append('<p class="small">Syntactic calls: ' + esc(', '.join(symbol['calls'])) + '</p>')
            parts.append('</div>')
        parts.append('</details>')
    parts.append('<section id="excluded"><h2>Explicit exclusions</h2><p>Dependency directories, .git internals, environments, caches and generated output directories were pruned before descent. No secret files were opened or hashed. Binary assets need a separate visual review. Lockfiles are not third-party source, but remain an explicit dependency-reproducibility review gap in this pass.</p><ul>')
    parts += ['<li><code>' + esc(r['path']) + '</code>: ' + esc(r['reason']) + '</li>' for r in excluded]
    parts += ['</ul></section><script>const files=[...document.querySelectorAll("details.file")];const filter=document.getElementById("filter");function update(){const q=filter.value.toLowerCase();let n=0;for(const f of files){f.hidden=!f.textContent.toLowerCase().includes(q);if(!f.hidden)n++}document.getElementById("visible").textContent=n+" files shown"}filter.addEventListener("input",update);update();</script></main></body></html>']
    document = '\n'.join(parts).replace("Snapshot: 5 November 2026", "Snapshot: 6 November 2026")
    document = document.replace('</style>', '*{box-sizing:border-box}body{overflow-wrap:anywhere}table{table-layout:fixed}input{width:100%}</style>')
    document = document.replace('<a href="#findings">Findings</a>', '<a href="#latest-findings">New findings</a> · <a href="#findings">Earlier findings</a>')
    OUT.write_text(document, encoding="utf-8")
    print(json.dumps({**summary, "output": str(OUT), "bytes": OUT.stat().st_size}))


if __name__ == "__main__":
    main()
