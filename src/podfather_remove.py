from shared import \
    load_quadlet_context, \
    require_root, \
    confirm, \
    stop_services, \
    unlink_quadlet_file, \
    systemctl, \
    BOLD, GREEN, RED, YELLOW, RESET
from podman import podman_exists, podman_remove
import sys

def _remove_resources(kind: str, names: set) -> None:
    print(f"{BOLD}► Removing Podman {kind}s...{RESET}")
    for name in names:
        if podman_exists(kind, name):
            podman_remove(kind, name)
            print(f"  └─ {GREEN}✓{RESET} {kind.capitalize()} removed: '{name}'")
        else:
            print(f"  └─ {GREEN}✓{RESET} {kind.capitalize()} not found: '{name}'")

def _print_removal_warning(ctx, keep_secrets: bool, keep_volumes: bool, keep_networks: bool) -> None:
    will_delete = [
        f"  • All containers and the pod",
        f"  • All systemd service files",
    ]
    if not keep_volumes:
        will_delete.append("  • All volumes and their data")
    if not keep_networks:
        will_delete.append("  • All networks")
    if not keep_secrets:
        will_delete.append("  • All secrets")

    kept = []
    if keep_volumes:
        kept.append("volumes")
    if keep_networks:
        kept.append("networks")
    if keep_secrets:
        kept.append("secrets")

    print(f"{YELLOW}{BOLD}⚠️  WARNING: This will remove '{ctx.path.name}' resources!{RESET}")
    print()
    print(f"{YELLOW}The following will be permanently deleted:")
    for item in will_delete:
        print(item)
    if kept:
        print(f"\nThe following will be kept: {', '.join(kept)}")
    print(f"{RESET}")

def podfather_remove(path: str, keep_secrets: bool = False, keep_volumes: bool = False, keep_networks: bool = False, skip_confirm: bool = False) -> None:

    require_root()

    ctx = load_quadlet_context(path)

    if not skip_confirm:
        _print_removal_warning(ctx, keep_secrets, keep_volumes, keep_networks)
        if not confirm("Are you sure you want to continue?"):
            print(f"{YELLOW}Aborted.{RESET}")
            sys.exit(0)

    stop_services(ctx)

    if keep_secrets:
        print(f"{YELLOW}► Skipping Podman secrets (--keep-secrets){RESET}")
    else:
        _remove_resources("secret", ctx.secret_names)

    _remove_resources("container", ctx.container_names)
    _remove_resources("pod",       ctx.pod_names)

    if keep_volumes:
        print(f"{YELLOW}► Skipping Podman volumes (--keep-volumes){RESET}")
    else:
        _remove_resources("volume", ctx.volume_names)

    if keep_networks:
        print(f"{YELLOW}► Skipping Podman networks (--keep-networks){RESET}")
    else:
        _remove_resources("network", ctx.network_names)

    # Unlinking Quadletfiles from system /etc/containers/systemd
    print(f"{BOLD}► Un-Linking Quadlet files...{RESET}")
    for src in ctx.quadlet_files_all:
        dst = ctx.systemd_dir / src.name
        unlink_quadlet_file(dst)

    # Unlinking resource dir from system /etc/containers/systemd
    print(f"{BOLD}► Un-Linking resource dir...{RESET}")
    unlink_quadlet_file(ctx.systemd_dir / "resource")

    print(f"{BOLD}► Reloading systemd daemon...{RESET}")
    if systemctl("daemon-reload"):
        print(f"  └─ {GREEN}✓{RESET} systemctl daemon-reload was successfull")
    else:
        print(f"  └─ {RED}✘{RESET} systemctl daemon-reload failed")