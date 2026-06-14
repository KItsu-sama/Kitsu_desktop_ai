"""
application/modules/reflex_compiler.py

Compiles human-editable reflex_groups.yaml into an optimised runtime
structure that the reflex handler can query without touching YAML at
request time.

Call once at startup:

    from application.modules.reflex_compiler import compile_groups, load_runtime
    compile_groups()                   # reads YAML, writes runtime JSON
    groups = load_runtime()            # returns compiled dict, ready to use

Runtime schema (per group):

    {
      "group":     str,
      "priority":  int,
      "tags":      list[str],
      "tool":      str | None,
      "fingerprints": list[int],          # simhash of each trigger phrase
      "trigger_texts": list[str],         # raw triggers (for trigram/token scoring)
      "responses": list[{"text": str, "weight": int}],
      "total_weight": int                 # sum of weights (for O(1) sampling)
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml  # PyYAML — already a common dep; add to requirements if absent

from shared.utils.simhashh import simhash as compute_simhash

log = logging.getLogger("reflex.compiler")

# ── Paths (override via env if needed) ───────────────────────────────────────

AUTHORING_PATH = Path("data/reflex_groups.yaml")
RUNTIME_PATH   = Path("data/reflex_runtime.json")


# ── Compiler ─────────────────────────────────────────────────────────────────

def compile_groups(
    src: Path = AUTHORING_PATH,
    dst: Path = RUNTIME_PATH,
) -> list[dict[str, Any]]:
    """
    Read *src* (YAML), compute simhash fingerprints for every trigger phrase,
    write compiled runtime dict to *dst* (JSON), return compiled list.

    Safe to call on every startup — fast even for hundreds of groups because
    simhash is O(tokens).
    """
    raw: list[dict] = yaml.safe_load(src.read_text(encoding="utf-8")) or []

    compiled: list[dict[str, Any]] = []

    for entry in raw:
        group_id   = entry.get("group", "unnamed")
        priority   = int(entry.get("priority", 5))
        tags       = entry.get("tags", [])
        tool       = entry.get("tool")           # None if absent
        triggers   = entry.get("triggers", [])
        responses  = entry.get("responses", [])

        # Validate
        if not triggers:
            log.warning("group %r has no triggers — skipping", group_id)
            continue
        if not responses:
            log.warning("group %r has no responses — skipping", group_id)
            continue

        # Pre-compute fingerprints for every trigger phrase
        fingerprints = [compute_simhash(t) for t in triggers]

        # Normalise weights (default 1 if missing)
        norm_responses = []
        total_weight   = 0
        for r in responses:
            w = int(r.get("weight", 1))
            norm_responses.append({"text": str(r.get("text", "")), "weight": w})
            total_weight += w

        compiled.append({
            "group":         group_id,
            "priority":      priority,
            "tags":          tags,
            "tool":          tool,
            "fingerprints":  fingerprints,
            "trigger_texts": triggers,           # kept for hybrid scoring
            "responses":     norm_responses,
            "total_weight":  total_weight,
        })

    # Sort by priority descending so the runtime can iterate in order
    compiled.sort(key=lambda g: g["priority"], reverse=True)

    # Persist — atomic write
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(compiled, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(dst)

    log.info(
        "reflex compiler: %d groups compiled → %s",
        len(compiled),
        dst,
    )
    return compiled


def load_runtime(path: Path = RUNTIME_PATH) -> list[dict[str, Any]]:
    """
    Load the pre-compiled runtime JSON.  Falls back to recompiling if the
    file is missing so startup is always safe.
    """
    if not path.exists():
        log.warning("runtime file missing — recompiling from YAML")
        return compile_groups()

    data = json.loads(path.read_text(encoding="utf-8"))

    # Restore integer fingerprints after JSON load
    for group in data:
        group["fingerprints"] = [
            int(fp) for fp in group.get("fingerprints", [])
        ]
    log.info("reflex compiler: loaded %d groups from %s", len(data), path)
    return data