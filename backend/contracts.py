"""contracts/*.json 로더. enum·스키마는 여기서만 읽고 코드에 하드코딩하지 않는다 (CONTRACT §0-3)."""
import json, pathlib, functools

ROOT = pathlib.Path(__file__).resolve().parent.parent / "contracts"


@functools.lru_cache
def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def enums() -> dict:
    return load("enums.json")


def schema(kind: str) -> dict:
    return load(f"{kind}.schema.json")


def check_schema(obj, sch) -> list[str]:
    """최소 JSON 스키마 검사(type/enum/required/min/max/items/pattern). 실패 사유 목록을 돌려준다."""
    import re
    fails = []
    t = sch.get("type")
    if t == "object":
        if not isinstance(obj, dict):
            return ["not an object"]
        for k in sch.get("required", []):
            if k not in obj:
                fails.append(f"missing {k}")
        props = sch.get("properties", {})
        if not sch.get("additionalProperties", True):
            fails += [f"extra field {k}" for k in obj if k not in props]
        for k, v in obj.items():
            if k in props:
                fails += [f"{k}: {f}" for f in check_schema(v, props[k])]
        return fails
    if t == "array":
        if not isinstance(obj, list):
            return ["not an array"]
        if "minItems" in sch and len(obj) < sch["minItems"]:
            fails.append("too few items")
        if "maxItems" in sch and len(obj) > sch["maxItems"]:
            fails.append("too many items")
        if sch.get("uniqueItems") and len(set(map(str, obj))) != len(obj):
            fails.append("duplicate items")
        for i, v in enumerate(obj):
            fails += [f"[{i}] {f}" for f in check_schema(v, sch.get("items", {}))]
        return fails
    if "enum" in sch and obj not in sch["enum"]:
        return [f"{obj!r} not in enum"]
    if t == "integer" and not (isinstance(obj, int) and not isinstance(obj, bool)):
        return ["not an integer"]
    if t == "number" and not isinstance(obj, (int, float)):
        return ["not a number"]
    if t == "boolean" and not isinstance(obj, bool):
        return ["not a boolean"]
    if t == "string":
        if not isinstance(obj, str):
            return ["not a string"]
        if "pattern" in sch and not re.fullmatch(sch["pattern"], obj):
            return [f"{obj!r} bad format"]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in sch and obj < sch["minimum"]:
            fails.append("below minimum")
        if "maximum" in sch and obj > sch["maximum"]:
            fails.append("above maximum")
    return fails
