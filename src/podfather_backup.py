import sys
import os
import subprocess
import json
import base64
import hashlib
import uuid
import tarfile
import tempfile
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from pathlib import Path
from shared import \
    load_quadlet_context,\
    require_root, \
    confirm, \
    BOLD, GREEN, RED, YELLOW, RESET
from podman import podman_exists, podman_secret_create, podman_remove, podman_secret_extract

# ── Crypto ────────────────────────────────────────────────────────────────────
def get_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt(text: str, password: str) -> str:
    salt = os.urandom(16)
    token = Fernet(get_key(password, salt)).encrypt(text.encode())
    return base64.urlsafe_b64encode(salt + token).decode()

def decrypt(encrypted: str, password: str) -> str:
    raw = base64.urlsafe_b64decode(encrypted.encode())
    salt, token = raw[:16], raw[16:]
    return Fernet(get_key(password, salt)).decrypt(token).decode()

def encrypt_file(src: Path, dst: Path, password: str) -> None:
    raw = src.read_bytes()
    salt = os.urandom(16)
    token = Fernet(get_key(password, salt)).encrypt(raw)
    dst.write_bytes(base64.urlsafe_b64encode(salt + token))

def decrypt_file(src: Path, dst: Path, password: str) -> None:
    raw = base64.urlsafe_b64decode(src.read_bytes())
    salt, token = raw[:16], raw[16:]
    dst.write_bytes(Fernet(get_key(password, salt)).decrypt(token))

# ── File utilities ────────────────────────────────────────────────────────────
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# ── Archive utilities ─────────────────────────────────────────────────────────
def tar_folder(folder: str, output: str):
    with tarfile.open(output, "w:gz") as tar:
        tar.add(folder, arcname=".")

def untar(path: str, output: str):
    with tarfile.open(path, "r:gz") as tar:
        tar.extractall(output, filter="data")

# ── Public API ────────────────────────────────────────────────────────────────
def podfather_backup_create(path: Path, file: Path, encryption_password: str) -> None:
    require_root()
    path = Path(path)
    file = Path(file)

    if file.is_dir() or file.suffix.lower() != ".tar":
        print("Invalid Backup destination file. Must be a .tar file")
        return

    if file.exists():
        if not confirm(f"Backup file '{file}' already exists. Overwrite?"):
            print("Aborted.")
            return
        file.unlink()
    
    ctx = load_quadlet_context(path)
    backup_data = {
        "files": [],
        "podman_secrets": [],
        "decryption_test": ""
    }

    print(f"{BOLD}► Creating backup '{file}'...{RESET}")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        print(f"{BOLD}► Backing up Podman secrets...{RESET}")
        for secret_name in ctx.secret_names:
            secret_value = podman_secret_extract(secret_name)
            if secret_value is None:
                print(f"  └─ {RED}✘{RESET} Skipping secret '{secret_name}': could not extract")
                continue
            data = {
                "name": secret_name,
                "value": encrypt(secret_value, encryption_password)
            }
            backup_data["podman_secrets"].append(data)
            print(f"  └─ {GREEN}✓{RESET} '{secret_name}'")

        print(f"{BOLD}► Backing up external files...{RESET}")
        for f in ctx.external_files:
            abs_path = (ctx.path / f["path"]).resolve()
            data = {
                "path": f["path"],
                "checksum": sha256(abs_path),
                "filename": str(uuid.uuid4())
            }
            encrypt_file(abs_path,tmp_dir / data["filename"],encryption_password)
            backup_data["files"].append(data)
            print(f"  └─ {GREEN}✓{RESET} '{abs_path}'")
        
        backup_data["decryption_test"] = (encrypt("SUCCESS",encryption_password))
        
        with open(tmp_dir / "decryption_test",mode="w") as f:
            f.write(backup_data["decryption_test"])
        with open(tmp_dir / "secrets.json",mode="w") as f:
            json.dump(backup_data["podman_secrets"], f)
        with open(tmp_dir / "files.json",mode="w") as f:
            json.dump(backup_data["files"], f)
        
        tar_folder(tmp_dir,file)
    print(f"  └─ {GREEN}✓{RESET} Backup created: '{file}'")

def podfather_backup_restore(path: Path, file: Path, decryption_password: str) -> None:
    require_root()
    path = Path(path)
    file = Path(file)

    if not file.exists():
        print(f"ERROR: backup file '{file}' not found")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        untar(file,tmp_dir)

        with open(tmp_dir / "decryption_test", mode="r") as f:
            try:
                test_result = decrypt(f.read(), decryption_password)
            except InvalidToken:
                print(f"{RED}✘{RESET} Wrong decryption password or corrupted backup.")
                return
            if test_result != "SUCCESS":
                print(f"{RED}✘{RESET} Decryption test failed. Wrong password or corrupted backup.")
                return
            print(f"{BOLD}► Decryption test passed {GREEN}✓{RESET}")

        print(f"{BOLD}► Restoring Podman secrets...{RESET}")
        with open(tmp_dir / "secrets.json", mode="r") as content:
            podman_secrets = json.load(content)
        with open(tmp_dir / "files.json", mode="r") as content:
            files = json.load(content)

        for secret in podman_secrets:
            decrypted_value = decrypt(secret["value"], decryption_password)
            if podman_exists("secret",secret["name"]):
                podman_remove("secret",secret["name"])
            if podman_secret_create(secret['name'], decrypted_value):
                print(f"  └─ {GREEN}✓{RESET} Restored secret: '{secret['name']}'")
            else:
                print(f"  └─ {RED}✘{RESET} Failed to restore secret: '{secret['name']}'")
        
        print(f"{BOLD}► Restoring external files...{RESET}")
        for f in files:
            tmp_file = tmp_dir / f["filename"]
            dst_file = (path / f["path"]).resolve()

            if not dst_file.parent.exists():
                print(f"  └─ {RED}✘{RESET} Cannot restore '{dst_file.name}': parent folder missing: '{dst_file.parent}'")
                continue

            decrypt_file(tmp_file, dst_file, decryption_password)
            if f["checksum"] == sha256(dst_file):
                print(f"  └─ {GREEN}✓{RESET} Restored file: '{dst_file}'")
            else:
                print(f"  └─ {RED}✘{RESET} Checksum mismatch: '{dst_file}'")
