from pathlib import Path
import getpass
import os
import yaml
import subprocess
from shared import \
    load_quadlet_context,\
    stop_services,\
    link_quadlet_file, \
    podman_exists, \
    podman_secret_create, \
    systemctl

def podfather_build(path: str) -> None:

    if os.geteuid() != 0:
        print("Please run script as superuser.\nExiting ...")
        exit(1)

    path = Path(path)
    ctx = load_quadlet_context(path)

    stop_services(ctx)

    podfather_yml_path = path / "podfather.yml"

    def load_config(config_path: str ) -> dict:
        with open(config_path) as f:
            return yaml.safe_load(f)

    config = load_config(podfather_yml_path)

    print("► Applying permissions...")
    for entry in config.get("permissions", []):
        raw_path = podfather_yml_path.parent / entry["path"]
        # Expand globs (e.g. *.sql); fall back to the plain path if no matches
        resolved_paths = list(raw_path.parent.glob(raw_path.name)) or [raw_path.resolve()]
        recursive = entry.get("recursive", False)
        r_flag = ["-R"] if recursive else []

        for path in resolved_paths:
            if "chmod" in entry:
                subprocess.run(["sudo", "chmod"] + r_flag + [entry["chmod"], str(path)], capture_output=True)

            if "owner" in entry or "group" in entry:
                owner_group = f"{entry.get('owner', '')}:{entry.get('group', '')}"
                subprocess.run(["sudo", "chown"] + r_flag + [owner_group, str(path)], capture_output=True)

            print(f"  └─ ✓ {path}")

    print("► Checking external files...")
    for file in config.get("external_files", []):
        path = (podfather_yml_path.parent / file["path"]).resolve()
        if path.exists():
            print(f"  └─ ✓ External file exists: '{path}'")
        else:
            print(f"  └─ ✘ External file missing:'{path}'\n     {file['description']}")

    # Check if secret exsits, create and ask for value if not
    print("► Checking Podman secrets...")
    for secret_name in ctx.secret_names:
        if podman_exists("secret",secret_name):
            print(f"  └─ Secret '{secret_name}' exists ✓")
        else:
            print(f"  └─ Secret '{secret_name}' is missing...")
            new_secret = getpass.getpass(f"     \n{secret_name}     \nEnter value for secret:")
            podman_secret_create(secret_name,new_secret)

    # Linking Quadletfiles to system /etc/containers/systemd
    print("► Linking Quadlet files...")
    for src in ctx.quadlet_files_all:
        dst = ctx.systemd_dir / src.name
        link_quadlet_file(src,dst)

    # Linking resource dir to system /etc/containers/systemd
    print("► Linking resource dir...")
    link_quadlet_file(ctx.path / "resource", ctx.systemd_dir / "resource")

    print("► Reloading systemd daemon...")
    if systemctl("daemon-reload"):
        print(f"  └─ ✓ systemctl daemon-reload was successfull")
    else:
        print(f"  └─ ✘ systemctl daemon-reload failed")

