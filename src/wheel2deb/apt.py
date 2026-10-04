import re
from functools import lru_cache
from typing import Optional

import attr

from wheel2deb import logger as logging
from wheel2deb.utils import shell

# https://www.debian.org/doc/debian-policy/ch-controlfields.html#version
PACKAGE_VER_RE = re.compile(
    r"^(?:(?P<epoch>\d+):)?"
    r"(?P<version>(?:[\w\.~\-]+(?=-(?P<revision>[^-]+$)))|[\w\.~\-]+)"
)

APT_CACHE_MADISON_RE = re.compile(r"[^|]+\|([^|]+)\|[^|]+")

logger = logging.getLogger(__name__)

_cache = None


@attr.s(frozen=True)
class Package:
    # package name
    name: str = attr.ib()
    # upstream version
    version: str = attr.ib()
    # debian revision
    revision: str = attr.ib()
    epoch: str = attr.ib()

    @classmethod
    def factory(cls, name, pkg_version):
        m = PACKAGE_VER_RE.match(pkg_version)
        if not m:
            raise ValueError(f"Invalid package version: {pkg_version}")
        return cls(name, **m.groupdict())

    def __str__(self):
        # show only package name and upstream version
        return "{}=={}".format(self.name, self.version)


@lru_cache
def search_package(name, arch) -> Optional[Package]:
    name = name + ":" + arch if arch else name
    output, rc = shell(["apt-cache", "madison", name])
    if rc:
        logger.debug(f"apt-cache madison failed for {name}: {output}")
        return None
    match = APT_CACHE_MADISON_RE.match(output)
    return Package.factory(name, match.group(1).strip()) if match is not None else None


def search_packages(names, arch):
    if not names:
        return

    logger.debug(f"searching {' '.join(names)} in apt cache...")

    for name in names:
        yield search_package(name, arch)
