from shared import \
    load_quadlet_context, \
    require_root, \
    confirm, \
    stop_services, \
    podman_exists, \
    podman_remove, \
    unlink_quadlet_file, \
    systemctl

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

    # Remove Podman secrets
    if keep_secrets:
        print("► Skipping Podman secrets (--keep-secrets)")
    else:
        print("► Removing Podman secrets...")
        for secret in ctx.secret_names:
            if podman_exists("secret",secret):
                podman_remove("secret",secret)
                print(f"  └─ ✓ Secret removed: '{secret}'")
            else:
                print(f"  └─ ✓ Secret not found: '{secret}' ")

    # Removing Podman Containers
    print("► Removing Podman containers...")
    for container in ctx.container_names:
        if podman_exists("container",container):
            podman_remove("container",container)
            print(f"  └─ ✓ Container removed: '{container}'")
        else:
            print(f"  └─ ✓ Container not found: '{container}'")

    # Removing Podman Pods
    print("► Removing Podman Pods...")
    for pod in ctx.pod_names:
        if podman_exists("pod",pod):
            podman_remove("pod",pod)
            print(f"  └─ ✓ Pod removed: '{pod}'")
        else:
            print(f"  └─ ✓ Pod not found: '{pod}'")

    # Removing Podman Volumes
    if keep_volumes:
        print("► Skipping Podman volumes (--keep-volumes)")
    else:
        print("► Removing Podman Volumes...")
        for volume in ctx.volume_names:
            if podman_exists("volume",volume):
                podman_remove("volume",volume)
                print(f"  └─ ✓ Volume removed: '{volume}'")
            else:
                print(f"  └─ ✓ Volume not found: '{volume}'")

    # Removing Podman Networks
    if keep_networks:
        print("► Skipping Podman networks (--keep-networks)")
    else:
        print("► Removing Podman Networks...")
        for network in ctx.network_names:
            if podman_exists("network",network):
                podman_remove("network",network)
                print(f"  └─ ✓ Network removed: '{network}'")
            else:
                print(f"  └─ ✓ Network not found: '{network}'")

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