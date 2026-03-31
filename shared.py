from typing import Literal
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass

QUADLET_EXTENSIONS = {
    ".container",
    ".network",
    ".volume",
    ".pod"
}

@dataclass
class QuadletContext:
    path: Path
    systemd_dir: Path
    quadlet_files_all: list[Path]
    pod_names: set[str]
    container_names: set[str]
    secret_names: set[str]
    volume_names: set[str]
    network_names: set[str]

def require_root() -> None:
    if os.geteuid() != 0:
        print("Please run script as superuser.\nExiting ...")
        exit(1)

def load_quadlet_context(path: str | Path) -> QuadletContext:
    path = Path(path)
    quadlet_dir = path / "quadlet"
    files = [p for p in quadlet_dir.iterdir() if p.is_file() and p.suffix in QUADLET_EXTENSIONS]
    return QuadletContext(
        path              = path,
        systemd_dir       = Path("/etc/containers/systemd"),
        quadlet_files_all = files,
        pod_names         = {n for f in files if f.suffix == '.pod'       for n in parse_quadlet(f, "PodName=")},
        container_names   = {n for f in files if f.suffix == '.container' for n in parse_quadlet(f, "ContainerName=")},
        secret_names      = {s.split(",")[0] for f in files if f.suffix == '.container' for s in parse_quadlet(f, "Secret=")},
        volume_names      = {n for f in files if f.suffix == '.volume'    for n in parse_quadlet(f, "VolumeName=")},
        network_names     = {n for f in files if f.suffix == '.network'   for n in parse_quadlet(f, "NetworkName=")},
    )

def parse_quadlet(path: str, starts_with: str) -> list[str]:
    result = set()
    with open(path) as content:
        for line in content:
            if line.startswith(starts_with) and "=" in line:
                value = line.split("=",1)[1].split("#")[0].strip() # Get Value (behind =) without trailing comments (#)
                result.add(value)
    return list(result)

def systemctl(action: Literal["start","stop","is-active","daemon-reload"], service_name: str | None = None) -> bool:
    cmd = ["sudo","systemctl",action]
    if service_name is not None:
        cmd.append(service_name)

    proc = subprocess.run(
        cmd,
        capture_output=True
    )
    return proc.returncode == 0

def is_service_running(service_name: str):
    return systemctl("is-active", service_name)

def create_symboliclink(src: Path, dst: Path) -> bool:
    proc = subprocess.run(
        ["sudo", "ln", "-s", str(src), str(dst)],
        capture_output=True
    )
    return proc.returncode == 0

def remove_symboliclink(path: Path) -> bool:
    proc = subprocess.run(
        ["sudo", "unlink", str(path)],
        capture_output=True
    )
    return proc.returncode == 0

def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() == "y"

def link_quadlet_file(src: Path, dst: Path) -> None:
    if dst.is_symlink() and dst.resolve() == src.resolve():
        print(f"  └─ ✓ Already linked '{src} → {dst}'")
        return
    if dst.exists():
        print(f"\n  └─ '{dst}' exists and is not a symlink or points elsewhere.")
        if not confirm("     Override? (May cause other containers to break)"):
            print("  └─ Skipped.")
            return
        remove_symboliclink(dst)
    create_symboliclink(src,dst)
    print(f"  └─ ✓ Linked '{src} → {dst}'")

def unlink_quadlet_file(dst: Path) -> None:
    if not dst.exists() and not dst.is_symlink():
        print(f"  └─ ✓ Quadlet not found. '{dst}'")
        return
    if not dst.is_symlink():
        print(f"\n  └─ '{dst}' exists but is not a symlink.")
        if not confirm("     Delete anyway? (May cause other containers to break)"):
            print("  └─ Skipped.")
            return
    remove_symboliclink(dst)
    print(f"  └─ ✓ Unlinked '{dst}'")

def stop_services(ctx: "QuadletContext") -> None:
    print("► Checking for running services...")
    for pod in ctx.pod_names:
        service_name = f"{pod}-pod"
        if is_service_running(service_name):
            print(f"  └─ Stopping '{service_name}'...")
            systemctl("stop", service_name)
    for container in ctx.container_names:
        if is_service_running(container):
            print(f"  └─ Stopping '{container}'...")
            systemctl("stop", container)
    for network in ctx.network_names:
        service_name = f"{network}-network"
        if is_service_running(service_name):
            print(f"  └─ Stopping '{service_name}'...")
            systemctl("stop", service_name)

def podman_secret_create(secret_name: str, secret_value: str) -> bool:
    proc = subprocess.run(
        ["sudo","podman", "secret", "create", secret_name, "-"],
        input=secret_value,
        capture_output=True,
        text=True
    )
    return proc.returncode == 0

def podman_exists(resource: Literal["container", "network", "volume", "pod", "secret"], name: str) -> bool:
    return subprocess.run(
        ["sudo", "podman", resource, "exists", name],
        capture_output=True
    ).returncode == 0

def podman_remove(resource: Literal["container", "network", "volume", "pod", "secret"], name: str) -> bool:
    return subprocess.run(
        ["sudo", "podman", resource, "rm", name],
        capture_output=True
    ).returncode == 0

