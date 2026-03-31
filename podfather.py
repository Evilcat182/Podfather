import argparse, sys
from pathlib import Path
from shared import *
from podfather_build import podfather_build
from podfather_remove import podfather_remove

class AppError(Exception):
    pass

systemd_dir = Path("/etc/containers/systemd")

def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if getattr(args, 'path', None) is None:
        args.cmd_parser.print_help()
        return 1

    try:
        path = resolve_path(args.path)
        validate_quadlet_dir(path)
    except AppError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    dispatch = {
        'build':  lambda: podfather_build(path),
        'start':  lambda: start(path),
        'stop':   lambda: stop(path),
        'remove': lambda: podfather_remove(path),
    }
    dispatch[args.command]()
    return 0

def start(path):
    print(f"executing start function on {path}")

def stop(path):
    print(f"executing stop function on {path}")

def resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise AppError(f"Path '{raw}' does not exist (resolved to '{path}')")
    if not path.is_dir():
        raise AppError(f"Path '{raw}' is not a directory (resolved to '{path}')")
    return path

def validate_quadlet_dir(path: Path) -> None:
    quadlet_dir = path / 'quadlet'
    if not quadlet_dir.is_dir():
        raise AppError(f"No 'quadlet' folder found in '{path}'")
    if not any(quadlet_dir.glob('*.container')):
        raise AppError(f"No .container file found in '{quadlet_dir}'")

def build_parser() -> argparse.ArgumentParser:
    FMT = argparse.RawDescriptionHelpFormatter
    PATH_ARG = dict(nargs='?', metavar='PATH',
                    help='Path to the project directory containing quadlet/')
    
    parser = argparse.ArgumentParser(
        prog='podfather', formatter_class=FMT,
        description='Manage Quadlet containers.',
        epilog=(
            'Commands:\n'
            '  build     Build a Quadlet container\n'
            '  start     Start a Quadlet container\n'
            '  stop      Stop a Quadlet container\n'
            '  remove    Remove a Quadlet container\n'
            '\n'
            "Run 'podfather COMMAND --help' for command-specific help."
        ),
    )
    sub = parser.add_subparsers(dest='command')

    build_p = sub.add_parser('build', formatter_class=FMT,
        help='Build a Quadlet container',
        description='Build a Quadlet container from a project directory.',
        epilog='Examples:\n  podfather build .\n  podfather build --start /path/to/project\n  podfather build --secret DB_PASS=hunter2 --start .\n  podfather build --secret DB_PASS=hunter2 --secret API_KEY=abc .')
    build_p.set_defaults(cmd_parser=build_p)
    build_p.add_argument('path', **PATH_ARG)
    build_p.add_argument('--start', action='store_true', help='Automatically start the service after build')
    build_p.add_argument('--secret', dest='secrets', action='append', metavar='NAME=VALUE', help='Create a Podman secret (can be repeated)')

    start_p = sub.add_parser('start', formatter_class=FMT,
        help='Start a Quadlet container',
        description='Start a Quadlet container from a project directory.',
        epilog='Examples:\n  podfather start .\n  podfather start /path/to/project')
    start_p.set_defaults(cmd_parser=start_p)
    start_p.add_argument('path', **PATH_ARG)

    stop_p = sub.add_parser('stop', formatter_class=FMT,
        help='Stop a Quadlet container',
        description='Stop a running Quadlet container.',
        epilog='Examples:\n  podfather stop .\n  podfather stop /path/to/project')
    stop_p.set_defaults(cmd_parser=stop_p)
    stop_p.add_argument('path', **PATH_ARG)

    remove_p = sub.add_parser('remove', formatter_class=FMT,
        help='Remove a Quadlet container',
        description='Remove a Quadlet container and its associated resources.',
        epilog='Examples:\n  podfather remove .\n  podfather remove --confirm /path/to/project\n  podfather remove --confirm --keep-secrets .')
    remove_p.set_defaults(cmd_parser=remove_p)
    remove_p.add_argument('path', **PATH_ARG)
    remove_p.add_argument('--confirm', action='store_true', help='Confirm removal without prompting')
    remove_p.add_argument('--keep-secrets', action='store_true', help='Keep secrets when removing')

    return parser

if __name__ == '__main__':
    exitcode = main()
    # Skip sys.exit if is executed in vscode terminal
    if not hasattr(sys,'ps1'):
        sys.exit(exitcode)
