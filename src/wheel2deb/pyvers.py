import re

import attr


@attr.s(frozen=True)
class Version:
    major: int = attr.ib(converter=int)
    minor: int = attr.ib(converter=int, default=0)
    micro: int = attr.ib(converter=int, default=0)

    @classmethod
    def from_str(cls, version_str):
        m = re.match(r"(\d)(?:\.(\d+))?(?:\.(\d+))?", version_str)
        if not m:
            raise ValueError(f"Invalid version string: {version_str}")
        v = [int(i) if i else 0 for i in m.groups()]
        return cls(v[0], v[1], v[2])

    def inc(self):
        return Version(self.major, self.minor + 1, 0)

    def __str__(self):
        return (
            str(self.major)
            + "."
            + str(self.minor)
            + (("." + str(self.micro)) if self.micro else "")
        )


@attr.s(frozen=True)
class VersionRange:
    min: Version | None = attr.ib(default=None)
    max: Version | None = attr.ib(default=None)

    @max.validator  # type: ignore[misc]
    def _check_max(self, attribute, value):
        """Enforce max > min. Interval must be open"""
        if value and self.min and value <= self.min:
            raise ValueError("min must be strictly smaller than max")

    def __contains__(self, item):
        if self.min and self.max:
            return self.min <= item < self.max
        elif self.min:
            return self.min <= item
        elif self.max:
            return item < self.max
        else:
            return True
