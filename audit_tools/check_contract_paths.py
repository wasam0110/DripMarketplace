"""Static path-shape audit, not runtime OpenAPI or semantic contract validation.

Reads route decorators and master include_router imports without importing the
application or settings. Dynamic expressions are explicitly unresolved; matching
path shapes do not prove correct payload, ownership, response or HTTP behavior.
"""

import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "drip-backend/app/api/v1"


def literal(node, default=None):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return default


def kw(call, name, default=None):
    return next((literal(item.value, default) for item in call.keywords if item.arg == name), default)


def backend_routes():
    tree = ast.parse((API / "router.py").read_text(encoding="utf-8-sig"))
    aliases, mounts, routes = {}, [], []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for item in node.names:
                aliases[item.asname or item.name] = node.module if item.name == "router" else f"{node.module}.{item.name}"
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "include_router":
                arg = call.args[0]
                alias = arg.value.id if isinstance(arg, ast.Attribute) else arg.id
                mounts.append((aliases[alias], kw(call, "prefix", "")))
    for module, mount in mounts:
        path = ROOT / "drip-backend" / (module.replace(".", "/") + ".py")
        module_tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        prefixes = {}
        for node in module_tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "APIRouter":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        prefixes[target.id] = kw(node.value, "prefix", "")
        for node in module_tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute) or not deco.args:
                    continue
                if not isinstance(deco.func.value, ast.Name) or deco.func.value.id not in prefixes:
                    continue
                method = deco.func.attr
                if method not in {"get", "post", "put", "patch", "delete", "head", "options", "api_route"}:
                    continue
                route_path = literal(deco.args[0])
                if not isinstance(route_path, str):
                    raise ValueError(f"Unresolved backend path: {path}:{deco.lineno}")
                for verb in kw(deco, "methods", ["GET"]) if method == "api_route" else [method.upper()]:
                    routes.append({"method": verb, "path": mount + prefixes[deco.func.value.id] + route_path,
                                   "file": path.relative_to(ROOT).as_posix(), "line": deco.lineno})
    return routes


def segments(path):
    return path.split("?", 1)[0].strip("/").split("/")


def compatible(front, back):
    a, b = segments(front), segments(back)
    return len(a) == len(b) and all(x == y or "{dynamic}" in x or re.fullmatch(r"\{[^}]+\}", y) for x, y in zip(a, b))


def main():
    routes = backend_routes()
    files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "drip-frontend/src").rglob("*")
                   if path.suffix in {".ts", ".tsx"} and ".test." not in path.name)
    proc = subprocess.run(["node", str(ROOT / "audit_tools/index_typescript.cjs")], input=json.dumps(files),
                          capture_output=True, text=True, encoding="utf-8", check=True)
    indexed = json.loads(proc.stdout)
    calls, unresolved = [], []
    for file, value in indexed.items():
        for call in value["requests"]:
            for path in call["paths"]:
                row = {"file": file, **call, "path": path}
                row.pop("paths")
                if not path.startswith("/") or "{dynamic}" in path.split("/", 2)[1]:
                    unresolved.append(row)
                    continue
                candidates = [route for route in routes if compatible(path, route["path"])]
                row["status"] = "shape_match" if any(call["method"] in {"?", route["method"]} for route in candidates) else "method_mismatch" if candidates else "path_mismatch"
                row["backend_candidates"] = candidates
                calls.append(row)
    output = {"limitations": "Static shape matching only; dynamic variable/helper calls and runtime API prefix are not resolved. No app/settings import or provider calls.",
              "routes": routes, "calls": calls, "unresolved": unresolved}
    (ROOT / "audit_tools/contract_inventory.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    mismatches = [{k: row[k] for k in ("file", "line", "method", "path", "status")} for row in calls if row["status"] != "shape_match"]
    print(json.dumps({"backend_method_paths": len(routes), "checked_call_variants": len(calls),
                      "unresolved_call_variants": len(unresolved), "mismatches": mismatches}, indent=2))


if __name__ == "__main__":
    main()
