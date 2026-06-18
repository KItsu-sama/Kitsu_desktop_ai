"""Site customization for runtime compatibility.

This project may run on Python versions where enum.StrEnum is missing
(e.g., Python < 3.11). Some dependencies import StrEnum from stdlib:

    from enum import StrEnum

To prevent hard startup failure, we provide a compatible fallback.
"""

from __future__ import annotations

import enum


if not hasattr(enum, "StrEnum"):
    class StrEnum(str, enum.Enum):
        """Fallback replacement for enum.StrEnum (Python < 3.11).

        Behaves like a str-based Enum.
        """

        def __str__(self) -> str:  # pragma: no cover
            return str(self.value)

    enum.StrEnum = StrEnum  # type: ignore[attr-defined]

