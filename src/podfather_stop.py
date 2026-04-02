from shared import require_root, load_quadlet_context, systemctl, BOLD, YELLOW, RESET

def podfather_stop(path: str) -> None:
    require_root()
    ctx = load_quadlet_context(path)
    print(f"{BOLD}► Stopping services...{RESET}")
    for pod_name in ctx.pod_names:
        service_name = f"{pod_name}-pod"
        print(f"  └─ {YELLOW}Stopping '{service_name}'...{RESET}")
        systemctl("stop", service_name)
