"""File storage behind a tiny interface, so hosted and self-hosted can differ.

Only a local-disk backend ships today. For hosted deployments on Cloud Run, point
STORAGE_LOCAL_DIR at a mounted volume or add an S3-compatible backend here
(Supabase Storage and Cloudflare R2 both speak S3).
"""

import uuid
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Storage(Protocol):
    def put(self, org_id: uuid.UUID, name: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("Invalid storage key")
        return p

    def put(self, org_id: uuid.UUID, name: str, data: bytes) -> str:
        suffix = Path(name).suffix.lower()[:8]
        key = f"{org_id}/{uuid.uuid4().hex}{suffix}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


def get_storage() -> Storage:
    return LocalStorage(get_settings().storage_local_dir)
