from typing import Literal
import subprocess
import json


def podman_exists(resource: Literal["container", "network", "volume", "pod", "secret"], name: str) -> bool:
    return subprocess.run(
        ["sudo", "podman", resource, "exists", name],
        capture_output=True
    ).returncode == 0

def podman_remove(resource: Literal["container", "network", "volume", "pod", "secret"], name: str) -> bool:
    return subprocess.run(
        ["sudo", "podman", resource, "rm", name],
        capture_output=True
    ).returncode == 0

def podman_secret_create(secret_name: str, secret_value: str) -> bool:
    proc = subprocess.run(
        ["sudo", "podman", "secret", "create", secret_name, "-"],
        input=secret_value,
        capture_output=True,
        text=True
    )
    return proc.returncode == 0

def podman_secret_extract(secret_name: str) -> str:
    if not podman_exists("secret", secret_name):
        print(f"ERROR: Secret does not exist: '{secret_name}'")
        return None

    proc = subprocess.run(
        ["sudo", "podman", "secret", "inspect", "--showsecret", secret_name],
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        print(f"ERROR: Failed to extract secret '{secret_name}'")
        return None

    json_data = json.loads(proc.stdout)
    secret_value = json_data[0]["SecretData"]

    if not secret_value:
        print(f"ERROR: Failed to extract secret '{secret_name}'")
        return None
    return secret_value
