"""TK-001: validate contracts/openapi.yaml and generate typed clients.

Outputs (committed, CI checks they are in sync via `make gen-client`):
  apps/web/src/api-types.ts      TypeScript interfaces + string-union enums
  apps/api/src/api/schemas.py    Pydantic v2 models for the VPS API
  apps/worker/src/worker/schemas.py  Pydantic v2 models for the worker

Validation: every endpoint from PRD 4.7 exists, every operation has an
operationId and responses, and every local $ref resolves.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "contracts", "openapi.yaml")

try:
    import yaml
except ImportError:  # bootstrap for machines without pyyaml (e.g. bare CI)
    print("[gen-client] pyyaml missing, installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyyaml"],
                   check=True)
    import yaml

# (method, path) pairs required by PRD 4.7. Fails the run when one is missing.
EXPECTED_OPS = [
    ("get", "/healthz"),
    ("get", "/auth/google/login"),
    ("get", "/auth/google/callback"),
    ("post", "/auth/logout"),
    ("get", "/api/me"),
    ("delete", "/api/me"),
    ("post", "/api/consents"),
    ("delete", "/api/consents"),
    ("post", "/api/uploads"),
    ("post", "/api/uploads/{id}/parts"),
    ("get", "/api/uploads/{id}"),
    ("post", "/api/uploads/{id}/complete"),
    ("get", "/api/jobs"),
    ("get", "/api/jobs/{id}"),
    ("delete", "/api/jobs/{id}"),
    ("get", "/api/jobs/{id}/transcript"),
    ("patch", "/api/jobs/{id}/segments/{n}"),
    ("patch", "/api/jobs/{id}/speakers/{sid}"),
    ("get", "/api/jobs/{id}/audio-url"),
    ("get", "/api/jobs/{id}/export"),
    ("post", "/worker/v1/jobs/claim"),
    ("post", "/worker/v1/jobs/{id}/heartbeat"),
    ("post", "/worker/v1/jobs/{id}/result"),
    ("post", "/worker/v1/jobs/{id}/fail"),
    ("post", "/worker/v1/ping"),
]

REF_PREFIX = "#/components/schemas/"


def load_spec():
    with open(SPEC, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate(spec):
    errors = []
    paths = spec.get("paths", {})
    for method, path in EXPECTED_OPS:
        op = (paths.get(path) or {}).get(method)
        if not op:
            errors.append(f"missing {method.upper()} {path}")
            continue
        if not op.get("operationId"):
            errors.append(f"{method.upper()} {path}: no operationId")
        if not op.get("responses"):
            errors.append(f"{method.upper()} {path}: no responses")

    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    def check_ref(node, where):
        if isinstance(node, dict):
            ref = node.get("$ref", "")
            if ref.startswith(REF_PREFIX) and ref[len(REF_PREFIX):] not in schemas:
                errors.append(f"{where}: dangling $ref {ref}")
            for v in node.values():
                check_ref(v, where)
        elif isinstance(node, list):
            for v in node:
                check_ref(v, where)

    for path, item in paths.items():
        check_ref(item, path)
    check_ref(schemas, "components.schemas")
    return errors, schemas


# --- type mapping -----------------------------------------------------------

def deref(node, schemas):
    while isinstance(node, dict) and set(node) == {"$ref"}:
        node = schemas[node["$ref"][len(REF_PREFIX):]]
    return node


def is_nullable(node):
    if not isinstance(node, dict):
        return False, node
    for key in ("anyOf", "oneOf"):
        opts = node.get(key)
        if isinstance(opts, list) and len(opts) == 2:
            null = [o for o in opts if o == {"type": "null"} or o.get("type") == "null"]
            other = [o for o in opts if o not in null]
            if len(null) == 1 and len(other) == 1:
                return True, other[0]
    return False, node


def ref_name(node):
    if isinstance(node, dict) and set(node) == {"$ref"}:
        return node["$ref"][len(REF_PREFIX):]
    return None


def ts_type(node, schemas):
    nullable, node = is_nullable(node)
    name = ref_name(node)
    if name:
        base = name
    elif node.get("enum"):
        base = " | ".join(f'"{v}"' for v in node["enum"])
        base = f"({base})"
    else:
        t = node.get("type", "object")
        if t == "string":
            base = "string"
        elif t == "integer":
            base = "number"
        elif t == "number":
            base = "number"
        elif t == "boolean":
            base = "boolean"
        elif t == "array":
            base = f"{ts_type(node.get('items', {}), schemas)}[]"
        else:
            base = "Record<string, unknown>"
    return f"({base} | null)" if nullable else base


def py_type(node, schemas):
    nullable, node = is_nullable(node)
    name = ref_name(node)
    if name:
        base = name
    elif node.get("enum"):
        base = "str"
    else:
        t = node.get("type", "object")
        fmt = node.get("format")
        if t == "string":
            base = "str"
        elif t == "integer":
            base = "int"
        elif t == "number":
            base = "float"
        elif t == "boolean":
            base = "bool"
        elif t == "array":
            base = f"list[{py_type(node.get('items', {}), schemas)}]"
        elif fmt == "binary":
            base = "bytes"
        else:
            base = "dict"
    return f"({base} | None)" if nullable else base


def schema_refs(node, schemas):
    """Names this schema depends on (via $ref anywhere inside)."""
    found = set()

    def walk(n):
        if isinstance(n, dict):
            r = ref_name(n)
            if r:
                found.add(r)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(node)
    found.discard(node.get("__self__", ""))
    return {r for r in found if r in schemas}


def topo_order(schemas):
    """Order schemas so dependencies come first (cycles keep spec order)."""
    names = list(schemas)
    deps = {n: schema_refs(schemas[n], schemas) - {n} for n in names}
    ordered, done = [], set()
    while len(ordered) < len(names):
        progressed = False
        for n in names:
            if n in done:
                continue
            if deps[n] <= done:
                ordered.append(n)
                done.add(n)
                progressed = True
        if not progressed:  # cycle: keep spec order for the rest
            for n in names:
                if n not in done:
                    ordered.append(n)
                    done.add(n)
            break
    return ordered


def describe(raw, schemas):
    """Description on the property itself, else on its $ref target."""
    if isinstance(raw, dict) and raw.get("description"):
        return raw["description"]
    target = deref(raw, schemas)
    if isinstance(target, dict):
        return target.get("description", "")
    return ""


def ts_enum_values(values):
    return " | ".join(f'"{v}"' for v in values)


def py_member(value):
    name = "".join(c if (c.isalnum() or c == "_") else "_" for c in str(value)).upper()
    if name and name[0].isdigit():
        name = "V_" + name
    return name or "UNKNOWN"


# --- emitters ---------------------------------------------------------------

def emit_ts(schemas):
    out = ["// GENERATED by `make gen-client` from contracts/openapi.yaml.",
           "// Jangan sunting manual. (TK-001)",
           ""]
    for name, raw in schemas.items():
        node = deref(raw, schemas)
        if node.get("enum") and node.get("type", "string") == "string":
            out.append(f"export type {name} = {ts_enum_values(node['enum'])};")
            vals = ", ".join(f'"{v}"' for v in node["enum"])
            out.append(f"export const {name}Values: {name}[] = [{vals}];")
            out.append("")
        elif node.get("type") == "object" or "properties" in node:
            required = set(node.get("required", []))
            out.append(f"export interface {name} {{")
            for prop, sub in (node.get("properties") or {}).items():
                mark = "" if prop in required else "?"
                desc = describe(sub, schemas)
                if desc:
                    out.append(f"  /** {desc} */")
                out.append(f"  {prop}{mark}: {ts_type(sub, schemas)};")
            out.append("}")
            out.append("")
        elif node.get("allOf"):
            base = ref_name(node["allOf"][0])
            out.append(f"export type {name} = {base};")
            out.append("")
    return "\n".join(out)


def emit_py(schemas, package):
    out = [f'"""{package} models GENERATED by `make gen-client` (TK-001)."""',
           "",
           "from enum import Enum",
           "",
           "from pydantic import BaseModel, Field",
           "",
           ""]
    for name in topo_order(schemas):
        raw = schemas[name]
        node = deref(raw, schemas)
        if node.get("enum") and node.get("type", "string") == "string":
            out.append(f"class {name}(str, Enum):")
            for v in node["enum"]:
                out.append(f'    {py_member(v)} = "{v}"')
            out.append("")
            out.append("")
        elif node.get("type") == "object" or "properties" in node:
            required = set(node.get("required", []))
            out.append(f"class {name}(BaseModel):")
            props = node.get("properties") or {}
            if not props:
                out.append("    pass")
            for prop, sub in props.items():
                typ = py_type(sub, schemas)
                desc = describe(sub, schemas).replace('"', "'")
                if prop in required:
                    field = f'Field(description="{desc}")' if desc else None
                    out.append(f"    {prop}: {typ}" + (f" = {field}" if field else ""))
                else:
                    field = f'Field(default=None, description="{desc}")' if desc else "None"
                    out.append(f"    {prop}: {typ} = {field}")
            out.append("")
            out.append("")
        elif node.get("allOf"):
            base = ref_name(node["allOf"][0])
            out.append(f"class {name}({base}):")
            out.append("    pass")
            out.append("")
            out.append("")
    return "\n".join(out)


TARGETS = [
    ("apps/web/src/api-types.ts", emit_ts, None),
    ("apps/api/src/api/schemas.py", emit_py, "api"),
    ("apps/worker/src/worker/schemas.py", emit_py, "worker"),
]


def main():
    spec = load_spec()
    errors, schemas = validate(spec)
    if errors:
        print("[gen-client] contract INVALID:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"[gen-client] contract ok "
          f"({len(EXPECTED_OPS)} ops, {len(schemas)} schemas)")
    for rel, emitter, package in TARGETS:
        dest = os.path.join(ROOT, *rel.split("/"))
        body = emitter(schemas) if package is None else emitter(schemas, package)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        print(f"[gen-client] wrote {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
