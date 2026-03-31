from shared import require_root, load_quadlet_context, systemctl

def podfather_stop(path: str) -> None:
    require_root()
    ctx = load_quadlet_context(path)
    print("► Stopping services...")
    for pod_name in ctx.pod_names:
        service_name = f"{pod_name}-pod"
        print(f"  └─ Stopping '{service_name}'...")
        systemctl("stop", service_name)
