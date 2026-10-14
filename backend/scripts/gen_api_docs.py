"""Generate docs/API.md from the live OpenAPI spec (run with the API server up)."""
import collections
import json
import urllib.request

spec = json.load(urllib.request.urlopen("http://127.0.0.1:8000/openapi.json"))
groups: dict[str, list[tuple[str, str, str]]] = collections.OrderedDict()
total = 0
for path, ops in sorted(spec["paths"].items()):
    for method, op in ops.items():
        if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            continue
        total += 1
        tag = op.get("tags", ["misc"])[0]
        groups.setdefault(tag, []).append((method.upper(), path, op.get("summary", "") or ""))

lines = [
    "# Nimbus Ninjas — API Reference",
    "",
    "Generated from the live OpenAPI schema (`GET /openapi.json`, interactive docs at `/docs`).",
    f"Base URL: `http://localhost:8000/api/v1` — **{total} endpoints** across {len(groups)} tags.",
    "",
    "Authentication: `Authorization: Bearer <JWT>` (obtain via `POST /auth/login`).",
    "Role checks are enforced server-side per endpoint; unauthenticated requests return 401,",
    "missing permissions return 403.",
    "",
]
for tag, items in groups.items():
    lines.append(f"## {tag} ({len(items)})")
    lines.append("")
    lines.append("| Method | Path | Summary |")
    lines.append("|---|---|---|")
    for method, path, summary in sorted(items, key=lambda x: (x[1], x[0])):
        s = summary.replace("|", "\\|")
        lines.append(f"| {method} | `{path}` | {s} |")
    lines.append("")

out = "\n".join(lines) + "\n"
with open(r"C:\Users\bhanu\Desktop\AnaRisk\Anarisk\docs\API.md", "w", encoding="utf-8") as f:
    f.write(out)
print(f"OK: {total} endpoints, {len(groups)} tags -> docs/API.md")
