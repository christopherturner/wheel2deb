import re
from pathlib import Path
from threading import Event, Thread
from time import sleep
from typing import List

from wheel2deb import logger as logging
from wheel2deb.logger import TASK
from wheel2deb.utils import shell

logger = logging.getLogger(__name__)


def parse_debian_control(cwd: Path):
    """
    Extract fields from debian/control
    :param cwd: Path to debian source package
    :return: Dict object with fields as keys
    """

    field_re = re.compile(r"^([\w-]+)\s*:\s*(.+)")

    content = (cwd / "debian" / "control").read_text()
    control = {}
    for line in content.split("\n"):
        m = field_re.search(line)
        if m:
            g = m.groups()
            control[g[0]] = g[1]

    for k in ("Build-Depends", "Depends"):
        if k in control:
            m = re.findall(r"([^=\s,()]+)\s?(?:\([^)]+\))?", control[k])
            control[k] = m

    return control


def build_package(cwd: Path) -> int:
    """Run dpkg-buildpackage in specified path."""
    args = ["dpkg-buildpackage", "-us", "-uc"]
    arch = parse_debian_control(cwd)["Architecture"]
    if arch != "all":
        args += ["--host-arch", arch]

    stdout, returncode = shell(args, cwd=cwd)
    logger.debug(stdout)
    if returncode:
        logger.error(f'failed to build package in "{cwd}" ☹')

    return returncode


def build_packages(paths: List[Path], threads: int, force_build: bool) -> None:
    """
    Run several instances of dpkg-buildpackage in parallel.
    :param paths: List of paths where dpkg-buildpackage will be called
    :param threads: Number of threads to run in parallel
    """

    paths = [p for p in paths if not Path(str(p) + ".deb").is_file() or force_build]
    logger.log(TASK, f"Building {len(paths)} source packages...")

    workers = []
    for i in range(threads):
        event = Event()
        event.set()
        workers.append({"done": event, "path": None, "error": None})

    def build(done, path, error_holder):
        try:
            logger.info(f"building {path}")
            rc = build_package(path)
            if rc:
                error_holder["msg"] = f"build failed with code {rc}"
        except Exception as e:
            error_holder["msg"] = f"build raised: {e}"
        finally:
            done.set()

    while False in [w["done"].is_set() for w in workers] or paths:
        for w in workers:
            if w["done"].is_set() and paths:
                w["done"].clear()
                w["error"] = {"msg": None}
                w["path"] = paths.pop()
                Thread(target=build, args=(w["done"], w["path"], w["error"])).start()
        sleep(1)

    # check for errors after all builds complete
    for w in workers:
        if w["error"] and w["error"]["msg"]:
            logger.error(w["error"]["msg"])


def build_all_packages(output_directory: Path, workers: int, force_build: bool) -> None:
    """
    Build debian source packages in parallel.
    :param output_directory: path where to search for source packages
    :param workers: Number of threads to run in parallel
    :param force_build: Build packages even if .deb already exists
    """

    if output_directory.exists() is False:
        logger.error(f"Directory {output_directory} does not exist")
        return

    if output_directory.is_dir() is False:
        logger.error(f"{output_directory} is not a directory")
        return

    paths = []
    for pkg_dir in output_directory.iterdir():
        if pkg_dir.is_dir() and (pkg_dir / "debian/control").is_file():
            paths.append(pkg_dir)

    build_packages(paths, workers, force_build)
