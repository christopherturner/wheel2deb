# Multi-Arch Docker Packaging

Build Debian packages (`.deb`) for target architectures (e.g. `arm64`, `amd64`, `armhf`, `i386`) and distributions (`debian:trixie`, `debian:bookworm`, `ubuntu:jammy`, `ubuntu:noble`, etc.) directly via `wheel2deb fetch`.

## Prerequisites

1. **Docker** installed and running.
2. **QEMU / binfmt emulation** for cross-architecture builds:
   ```bash
   docker run --privileged --rm tonistiigi/binfmt --install all
   ```

## Usage

```bash
wheel2deb fetch [OPTIONS] [PACKAGES...]
```

### Options

| Flag | Long Option | Default | Description |
|---|---|---|---|
| `-d` | `--distro` | `debian` | Distribution (`debian`, `ubuntu`) |
| `-r` | `--release` | `trixie` | Release codename (`trixie`, `bookworm`, `jammy`, `noble`, etc.) |
| `-a` | `--arch` | `amd64` | Target architecture (`amd64`, `arm64`, `armhf`, `i386`) |
| `-f` | `--requirements` | *None* | Path to `requirements.txt` file |
| `-o` | `--output-dir` | `output` | Base output directory |
| `-p` | `--apt-pkgs` | *None* | Extra build headers (e.g. `"libssl-dev libxml2-dev"`) |
| | `--build / --no-build` | `True` | Automatically convert and build final `.deb` packages |
| `-w` | `--workers` | `4` | Max workers for package building |
| | `--force` | `False` | Force build even if `.deb` exists |

### Examples

#### 1. From a `requirements.txt` file for Debian Trixie on ARM64:
```bash
wheel2deb fetch -d debian -r trixie -a arm64 -f requirements.txt
```

#### 2. Popular packages (data science / web) for Ubuntu Jammy on AMD64:
```bash
wheel2deb fetch -d ubuntu -r jammy -a amd64 pydantic uvicorn
```

#### 3. Packages with native C/C++ extensions (e.g. NumPy, PyYAML):
```bash
wheel2deb fetch -d debian -r bookworm -a arm64 numpy pyyaml
```

#### 4. Packages requiring extra C development headers:
```bash
wheel2deb fetch -d debian -r trixie -a arm64 \
  -p "libssl-dev libxml2-dev libxslt1-dev" \
  Scrapy
```

#### 5. Download and build wheels only (skip generating `.deb`):
```bash
wheel2deb fetch --no-build -d debian -r bookworm -a armhf requests
```

## Output Structure

Build artifacts are organized under `--output-dir`:

```
output/<distro>_<release>_<arch>/
├── wheels/   # Raw .whl files compiled/downloaded inside the target container
└── debs/     # Final .deb packages and Debian source package directories
```
