from shared import \
    load_quadlet_context, \
    require_root, \
    confirm, \
    stop_services, \
    podman_exists, \
    podman_remove, \
    unlink_quadlet_file, \
    systemctl

def _remove_resources(kind: str, names: set) -> None:
    print(f"\u25ba Removing Podman {kind}s...")
    for name in names:
        if podman_exists(kind, name):
            podman_remove(kind, name)
            print(f"  \u2514\u2500 \u2713 {kind.capitalize()} removed: '{name}'")
        else:
            print(f"  \u2514\u2500 \u2713 {kind.capitalize()} not found: '{name}'")

def podfather_remove(path: str, keep_secrets: bool = False, keep_volumes: bool = False, keep_networks: bool = False) -> None:

    require_root()

    ctx = load_quadlet_context(path)

    print(f"⚠️  WARNING: This will remove ALL '{ctx.path.name}' data!")
    print()
    print("The following will be permanently deleted:")
    print("  • All containers and the pod")
    print("  • All volumes and their data")
    print("  • All networks")
    print("  • All secrets")
    print("  • All systemd service files")
    print()
    if not confirm("Are you sure you want to continue?"):
        print("Aborted.")
        exit(0)

    stop_services(ctx)

    if keep_secrets:
        print("► Skipping Podman secrets (--keep-secrets)")
    else:
        _remove_resources("secret", ctx.secret_names)

    _remove_resources("container", ctx.container_names)
    _remove_resources("pod",       ctx.pod_names)

    if keep_volumes:
        print("► Skipping Podman volumes (--keep-volumes)")
    else:
        _remove_resources("volume", ctx.volume_names)

    if keep_networks:
        print("► Skipping Podman networks (--keep-networks)")
    else:
        _remove_resources("network", ctx.network_names)

    # Unlinking Quadletfiles from system /etc/containers/systemd
    print("► Un-Linking Quadlet files...")
    for src in ctx.quadlet_files_all:
        dst = ctx.systemd_dir / src.name
        unlink_quadlet_file(dst)

    # Unlinking resource dir from system /etc/containers/systemd
    print("► Un-Linking resource dir...")
    unlink_quadlet_file(ctx.systemd_dir / "resource")

    print("► Reloading systemd daemon...")
    if systemctl("daemon-reload"):
        print(f"  └─ ✓ systemctl daemon-reload was successfull")
    else:
        print(f"  └─ ✘ systemctl daemon-reload failed")