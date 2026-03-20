import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TunnelConfig:
    server_url: str = "https://api.tunnel.dev"
    auth_token: Optional[str] = None
    ssh_key_path: str = "~/.tunnel/tunnel_ed25519"
    default_ttl: str = "2h"
    
    @property
    def ssh_key_path_expanded(self) -> Path:
        return Path(self.ssh_key_path).expanduser()


config_dir = Path("~/.tunnel").expanduser()
config_file = config_dir / "config.json"


def ensure_config_dir():
    config_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> TunnelConfig:
    ensure_config_dir()
    if config_file.exists():
        try:
            with open(config_file) as f:
                data = json.load(f)
                return TunnelConfig(**{k: v for k, v in data.items() if k in TunnelConfig.__annotations__})
        except (json.JSONDecodeError, TypeError):
            pass
    return TunnelConfig()


def save_config(cfg: TunnelConfig):
    ensure_config_dir()
    with open(config_file, "w") as f:
        json.dump(asdict(cfg), f, indent=2)


config = load_config()


def get_ssh_key_path() -> Path:
    key_path = config.ssh_key_path_expanded
    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
    return key_path


def set_auth_token(token: str):
    config.auth_token = token
    save_config(config)


def get_auth_token() -> Optional[str]:
    return config.auth_token


def set_server_url(url: str):
    config.server_url = url.rstrip("/")
    save_config(config)


def parse_ttl(ttl_str: str) -> int:
    ttl_str = ttl_str.lower().strip()
    if ttl_str == "forever" or ttl_str == "0":
        return 0
    if ttl_str.endswith("m"):
        return int(ttl_str[:-1]) * 60
    if ttl_str.endswith("h"):
        return int(ttl_str[:-1]) * 3600
    if ttl_str.endswith("d"):
        return int(ttl_str[:-1]) * 86400
    if ttl_str.isdigit():
        return int(ttl_str)
    raise ValueError(f"Invalid TTL format: {ttl_str}. Use format like '30m', '2h', '24h', or 'forever'")
