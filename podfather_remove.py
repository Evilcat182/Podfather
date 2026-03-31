from shared import \
    load_quadlet_context, \
    require_root, \
    confirm, \
    stop_services, \
    podman_exists, \
    podman_remove, \
    unlink_quadlet_file, \
    systemctl, \
    BOLD, GREEN, RED, YELLOW, RESET

def _remove_resources(kind: str, names: set) -> None:
    print(f"{BOLD}► Removing Podman {kind}s...{RESET}")
    for name in names:
        if podman_exists(kind, name):
            podman_remove(kind, name)
            print(f"  └─ {GREEN}✓{RESET} {kind.capitalize()} removed: '{name}'")
        else:
            print(f"  └─ {GREEN}✓{RESET} {kind.capitalize()} not found: '{name}'")

def podfather_remove(path: str, keep_secrets: bool = False, keep_volumes: bool = False, keep_networks: bool = False) -> None:

    require_root()

    ctx = load_quadlet_context(path)

    print(f"{YELLOW}{BOLD}⚠️  WARNING: This will remove ALL '{ctx.path.name}' data!{RESET}")
    print()
    print(f"{YELLOW}The following will be permanently deleted:")
    print("  • All containers and the pod")
    print("  • All volumes and their data")
    print("  • All networks")
    print("  • All secrets")
    print(f"  • All systemd service files{RESET}")
    print()
    if not confirm("Are you sure you want to continue?"):
        print(f"{YELLOW}Aborted.{RESET}")
        exit(0)

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