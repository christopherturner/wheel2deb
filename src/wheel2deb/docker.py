import hashlib
import subprocess
from pathlib import Path
from typing import List, Optional

from wheel2deb import logger as logging

logger = logging.getLogger(__name__)


def fetch_wheels_in_docker(
    output_directory: Path,
    packages: Optional[List[str]] = None,
    requirements: Optional[Path] = None,
    distro: str = "debian",
    release: str = "trixie",
    arch: str = "amd64",
    apt_pkgs: Optional[str] = None,
) -> Optional[Path]:
    target_dir = output_directory / f"{distro}_{release}_{arch}"
    wheels_dir = target_dir / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)

    mounts = ["-v", f"{wheels_dir.resolve()}:/wheels"]
    # Map debian/user arch to docker platform
    arch_to_platform = {
        "x86": "linux/386",
        "i386": "linux/386",
        "i686": "linux/386",
        "amd64": "linux/amd64",
        "x86_64": "linux/amd64",
        "arm64": "linux/arm64",
        "aarch64": "linux/arm64",
        "armhf": "linux/arm/v7",
        "armv7l": "linux/arm/v7",
    }
    platform = arch_to_platform.get(arch.lower(), f"linux/{arch}")
    extra_apt = f" {apt_pkgs}" if apt_pkgs else ""

    cache_key = hashlib.sha256(
        f"{distro}:{release}:{arch}:{extra_apt}".encode()
    ).hexdigest()[:8]
    image_tag = f"wheel2deb-{distro}-{release}-{arch}:{cache_key}"

    dockerfile = f"""FROM {distro}:{release}
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-wheel python3-dev build-essential{extra_apt}
"""
    logger.task(f"Ensuring build environment image {image_tag} ({platform})...")
    res = subprocess.run(
        ["docker", "build", "--platform", platform, "-t", image_tag, "-"],
        input=dockerfile.encode(),
    )
    if res.returncode != 0:
        logger.error(f"Failed to prepare Docker build environment image {image_tag}")
        return None

    # Determine targets to fetch
    req_mounts = list(mounts)
    targets_to_fetch: List[tuple[str, List[str]]] = []

    if requirements:
        req_mounts += ["-v", f"{requirements.resolve()}:/tmp/requirements.txt:ro"]
        # Try full requirements file first, fallback to individual lines if it fails
        targets_to_fetch.append((str(requirements), ["-r", "/tmp/requirements.txt"]))

    if packages:
        # Fetch packages one by one so one invalid package doesn't abort the entire batch
        for pkg in packages:
            targets_to_fetch.append((pkg, [pkg]))

    failures = []
    logger.task(f"Fetching wheels in {image_tag}...")

    for display_name, pip_args in targets_to_fetch:
        cmd = [
            "docker",
            "run",
            "--rm",
            "--platform",
            platform,
            *req_mounts,
            image_tag,
            "pip3",
            "wheel",
            "--wheel-dir=/wheels",
            *pip_args,
        ]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            logger.error(f"Failed to fetch wheel for '{display_name}'")
            failures.append(display_name)

    if failures:
        logger.warning(
            f"The following package(s) could not be fetched: {', '.join(failures)}"
        )

    # Return wheels_dir if at least one wheel exists
    found_wheels = list(wheels_dir.glob("*.whl"))
    if not found_wheels:
        logger.error("No wheels were downloaded or built.")
        return None

    return wheels_dir
