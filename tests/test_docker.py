from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from wheel2deb.cli import app
from wheel2deb.docker import fetch_wheels_in_docker

UBUNTU_RELEASES = ["resolute", "noble", "jammy", "focal"]
DEBIAN_RELEASES = ["forky", "trixie", "bookworm", "bullseye"]
TARGET_ARCHS = ["amd64", "arm64", "armhf", "i386"]

MATRIX = [("ubuntu", rel, arch) for rel in UBUNTU_RELEASES for arch in TARGET_ARCHS] + [
    ("debian", rel, arch) for rel in DEBIAN_RELEASES for arch in TARGET_ARCHS
]


@pytest.mark.parametrize("distro,release,arch", MATRIX)
def test_fetch_wheels_in_docker__generates_correct_platform_and_tag(
    tmp_path, distro, release, arch
):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Mock wheel output directory having a wheel so it succeeds
        expected_dir = tmp_path / f"{distro}_{release}_{arch}" / "wheels"
        expected_dir.mkdir(parents=True, exist_ok=True)
        (expected_dir / "test-1.0-py3-none-any.whl").touch()

        result = fetch_wheels_in_docker(
            output_directory=tmp_path,
            packages=["testpkg"],
            distro=distro,
            release=release,
            arch=arch,
        )

        assert result == expected_dir
        assert mock_run.call_count >= 2

        # Verify docker build call (build environment image)
        build_call = mock_run.call_args_list[0]
        build_cmd = build_call[0][0]
        assert build_cmd[0] == "docker"
        assert build_cmd[1] == "build"
        assert f"wheel2deb-{distro}-{release}-{arch}" in build_cmd[5]

        # Verify docker run call (pip wheel invocation)
        run_call = mock_run.call_args_list[1]
        run_cmd = run_call[0][0]
        assert run_cmd[0] == "docker"
        assert run_cmd[1] == "run"
        assert f"{expected_dir.resolve()}:/wheels" in run_cmd


@pytest.mark.parametrize(
    "distro,release,arch",
    [
        ("ubuntu", "jammy", "amd64"),
        ("debian", "bookworm", "arm64"),
        ("ubuntu", "noble", "armhf"),
        ("debian", "trixie", "i386"),
    ],
)
def test_cli_fetch__matrix_integration(tmp_path, distro, release, arch):
    runner = CliRunner()
    with patch("wheel2deb.cli.fetch_wheels_in_docker") as mock_fetch:
        mock_fetch.return_value = tmp_path / f"{distro}_{release}_{arch}" / "wheels"

        result = runner.invoke(
            app,
            [
                "fetch",
                "--no-build",
                "-d",
                distro,
                "-r",
                release,
                "-a",
                arch,
                "-o",
                str(tmp_path),
                "pydantic",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["distro"] == distro
        assert kwargs["release"] == release
        assert kwargs["arch"] == arch
        assert kwargs["packages"] == ["pydantic"]
