#!/usr/bin/env python3
"""CLI read-only — M-STAT-001 auditoria de remediação de diversidade pool 15D."""

from __future__ import annotations

import argparse
import json
import sys

from lotoia.statistics.diversity_remediation_audit import (
    MISSION_ID,
    audit_diversity_remediation_cycle,
    build_low_diversity_audit_pool,
    classify_remediation_root_cause,
)


def _default_history() -> list[object]:
    class _Draw:
        def __init__(self, numbers: list[int]) -> None:
            self.numbers = numbers

    return [_Draw(sorted(range(1, 16)))] + [
        _Draw(sorted({((offset * 3 + index * 2) % 25) + 1 for index in range(15)}))
        for offset in range(12)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M-STAT-001 — auditoria remediação diversidade")
    parser.add_argument("--requested-count", type=int, default=20)
    parser.add_argument("--pool-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=73)
    parser.add_argument(
        "--batch-label",
        default="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    )
    parser.add_argument("--json", action="store_true", help="Emitir JSON completo")
    args = parser.parse_args(argv)

    pool = build_low_diversity_audit_pool(
        pool_size=int(args.pool_size),
        requested_count=int(args.requested_count),
    )
    audit = audit_diversity_remediation_cycle(
        pool,
        game_size=15,
        requested_count=int(args.requested_count),
        batch_label=str(args.batch_label),
        history=_default_history(),
        seed=int(args.seed),
        baseline_pool=pool,
    )
    root_cause = classify_remediation_root_cause(audit)
    payload = {
        "mission_id": MISSION_ID,
        "audit": audit,
        "root_cause": root_cause,
        "functional_changes": False,
        "purge_executed": False,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    before = dict(audit.get("before") or {})
    after = dict(audit.get("after") or {})
    delta = dict(audit.get("delta") or {})
    top = dict(audit.get("top_slice") or {})
    rerank = dict((audit.get("corrective_actions") or {}).get("rerank_diversidade") or {})

    print(f"=== {MISSION_ID} — Auditoria remediação diversidade pool 15D ===")
    print(f"GP:{args.requested_count} 15D | pool={args.pool_size} | top_slice={args.requested_count * 3}")
    print()
    print("ANTES:")
    print(f"  diversity_score={before.get('diversity_score')} similarity={before.get('similarity_score')}")
    print(f"  max_overlap={before.get('max_overlap')} near_dup={before.get('near_duplicate_count')}")
    print(f"  candidate_pool_size={before.get('candidate_pool_size')}")
    print()
    print("DEPOIS:")
    print(f"  diversity_score={after.get('diversity_score')} similarity={after.get('similarity_score')}")
    print(f"  max_overlap={after.get('max_overlap')} near_dup={after.get('near_duplicate_count')}")
    print()
    print("DELTA:")
    print(f"  diversity_score={delta.get('diversity_score')}")
    print(f"  similarity_score={delta.get('similarity_score')}")
    print(f"  max_overlap={delta.get('max_overlap')}")
    print()
    print("TOP SLICE:")
    print(f"  top_slice_changed={top.get('top_slice_changed')}")
    print(f"  candidates_reordered={top.get('candidates_reordered')}")
    print(f"  candidates_replaced={top.get('candidates_replaced')}")
    print()
    print("RERANK:")
    print(f"  candidates_reordered={rerank.get('candidates_reordered')}")
    print(f"  candidates_replaced={rerank.get('candidates_replaced')}")
    print()
    print("AGENTE:", audit.get("agent_routing", {}).get("responsible_agent"))
    print("CAUSA RAIZ:", root_cause.get("primary_cause"))
    print("PRÓXIMA MISSÃO:", root_cause.get("recommended_next_mission"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
