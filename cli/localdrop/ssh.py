import subprocess
import signal
import os
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class SSHManager:
    def __init__(self, assigned_port: int, local_port: int, local_url: Optional[str], ssh_key_path: Path, server_host: str):
        self.assigned_port = assigned_port
        self.local_port = local_port
        self.local_url = local_url
        self.ssh_key_path = ssh_key_path
        self.server_host = server_host
        self.process: Optional[subprocess.Popen] = None
        self._ensure_ssh_key()

    def _ensure_ssh_key(self):
        if not self.ssh_key_path.exists():
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            self.ssh_key_path.parent.mkdir(parents=True, exist_ok=True)
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.ssh_key_path, "wb") as f:
                f.write(private_pem)
            os.chmod(self.ssh_key_path, 0o600)
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
            pub_path = self.ssh_key_path.with_suffix(".pub")
            with open(pub_path, "wb") as f:
                f.write(public_pem)
            
            return public_pem.decode()
        else:
            pub_path = self.ssh_key_path.with_suffix(".pub")
            if pub_path.exists():
                with open(pub_path) as f:
                    return f.read()
        return None

    def build_command(self) -> list[str]:
        target = "localhost"
        if self.local_url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(self.local_url)
                target = parsed.netloc.split(":")[0]
            except Exception:
                pass

        return [
            "ssh",
            "-R", f"{self.assigned_port}:{target}:{self.local_port}",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ExitOnForwardFailure=yes",
            "-i", str(self.ssh_key_path),
            "-p", "22",
            "-N",
            f"tunnel@{self.server_host}",
        ]

    def start(self):
        cmd = self.build_command()
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        return self.process

    def stop(self):
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.process = None

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None
