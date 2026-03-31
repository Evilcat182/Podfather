from shared import require_root, load_quadlet_context, systemctl

def podfather_start(path: str) -> None:
    require_root()
    ctx = load_quadlet_context(path)
    print("► Starting services...")
    for pod_name in ctx.pod_names:
        service_name = f"{pod_name}-pod"
        print(f"  └─ Starting '{service_name}'...")
        systemctl("start", service_name)

