"""Temporary target module while the legacy tests of ``tests/test_project_init.py`` are refactored.

This module serves only as the mirror target of
``tests/unit/devcapsule/legacy_refactoring/test_project_init.py`` under *Unit Tests*
rule 1 of ``WORKFLOW-LOCAL.md``. It holds no code. The tests mirrored here are
the ones marked expected to fail on 2026-11-04 with the reason
``TODO: fix the wrong approach to testing``; each is rewritten against its
real unit as the maintenance workstream refactors it, and this module is
deleted when the last one leaves.
"""

__all__: list[str] = []
