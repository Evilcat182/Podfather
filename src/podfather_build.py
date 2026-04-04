from pathlib import Path
import getpass
import subprocess
from shared import \
    load_quadlet_context,\
    require_root, \
    stop_services,\
    link_quadlet_file, \
    systemctl, \
    BOLD, GREEN, RED, YELLOW, RESET
from podman import podman_exists, podman_secret_create

def podfather_build(path: str) -> None:
    require_root()
    path = Path(path)

    ctx = load_quadlet_context(path)
    stop_services(ctx)

    print(f"{BOLD}► Applying permissions...{RESET}")
    for entry in ctx.permissions:
        raw_path = ctx.path / entry["path"]
        # Expand globs (e.g. *.sql); fall back to the plain path if no matches
        resolved_paths = list(raw_path.parent.glob(raw_path.name)) or [raw_path.resolve()]
        recursive = entry.get("recursive", False)
        r_flag = ["-R"] if recursive else []

        for p in resolved_paths:
            if "chmod" in entry:
                subprocess.run(["sudo", "chmod"] + r_flag + [entry["chmod"], str(p)], capture_output=True)

            if "owner" in entry or "group" in entry:
                owner_group = f"{entry.get('owner', '')}:{entry.get('group', '')}"
                subprocess.run(["sudo", "chown"] + r_flag + [owner_group, str(p)], capture_output=True)

            print(f"  └─ {GREEN}✓{RESET} {p}")

    print(f"{BOLD}► Checking external files...{RESET}")
    for file in ctx.external_files:
        path = (ctx.path / file["path"]).resolve()
        if path.exists():
            print(f"  └─ {GREEN}✓{RESET} External file exists: '{path}'")
        else:
            print(f"  └─ {RED}✘{RESET} External file missing:'{path}'\n     {file['description']}")

    # Check if secret exsits, create and ask for value if not
    print(f"{BOLD}► Checking Podman secrets...{RESET}")
    for secret_name in ctx.secret_names:
        if podman_exists("secret",secret_name):
            print(f"  └─ Secret '{secret_name}' exists {GREEN}✓{RESET}")
        else:
            print(f"  └─ {YELLOW}Secret '{secret_name}' is missing...{RESET}")
            new_secret = getpass.getpass(f"     \n{secret_name}     \nEnter value for secret:")
            podman_secret_create(secret_name,new_secret)

    # Linking Quadletfiles to system /etc/containers/systemd
    print(f"{BOLD}► Linking Quadlet files...{RESET}")
    for src in ctx.quadlet_files_all:
        dst = ctx.systemd_dir / src.name
        link_quadlet_file(src,dst)

    # Linking resource dir to system /etc/containers/systemd
    print(f"{BOLD}► Linking resource dir...{RESET}")
    link_quadlet_file(ctx.path / "resource", ctx.systemd_dir / "resource")

    print(f"{BOLD}► Reloading systemd daemon...{RESET}")
    if systemctl("daemon-reload"):
        print(f"  └─ {GREEN}✓{RESET} systemctl daemon-reload was successfull")
    else:
        print(f"  └─ {RED}✘{RESET} systemctl daemon-reload failed")

