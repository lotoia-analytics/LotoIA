from __future__ import annotations

from lotoia.governance import build_scientific_nuclei_registry

_REGISTRY = build_scientific_nuclei_registry()

PAGES = list(_REGISTRY.page_ids)
LABELS = dict(_REGISTRY.page_labels)
PAGE_AUDIT_MATRIX = dict(_REGISTRY.page_audit_matrix)
PAGE_GROUPS = {
    mode: [section.as_dict() for section in sections]
    for mode, sections in _REGISTRY.mode_sections.items()
}

