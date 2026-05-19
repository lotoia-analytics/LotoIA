"""Legacy validators adapter.

The official validators namespace is ``lotoia.ingestion.validators``.
This module intentionally exposes no public validators.
"""

from lotoia.ingestion import validators as _official_validators

__all__ = list(_official_validators.__all__)
