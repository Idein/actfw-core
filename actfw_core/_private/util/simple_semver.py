import re

from ...compat.dataclasses import dataclass


# Simplified SemVer
@dataclass(frozen=True, eq=True, order=True)
class SimpleSemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, s: str) -> "SimpleSemVer":
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", s)
        if m is None:
            raise ValueError(f"invalid `SimpleSemVer`: {s}")
        (major, minor, patch) = m.group(1, 2, 3)
        return cls(int(major), int(minor), int(patch))

    def to_str(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
