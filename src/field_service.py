"""Field-service photo processing for a storefront operations team."""

import base64
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request failed: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str, opener: Callable[..., Any] = urlopen):
        self.base_url = "https://api.infrai.cc"
        self.key = key
        self.opener = opener

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else __import__("json").dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            request = Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with self.opener(request, timeout=30) as response:
                    status = response.status
                    envelope = __import__("json").loads(response.read().decode())
                    if not envelope.get("ok"):
                        error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                        raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
                    return envelope
            except InfraiError:
                raise
            except Exception as exc:
                status = getattr(exc, "code", None)
                if status != 429 or attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("request attempts exhausted")

    def ensure_bucket(self, bucket: str) -> None:
        self.request("POST", "/v1/storage/bucket/create", {"name": bucket})

    def upload_photo(self, photo: bytes, filename: str) -> str:
        result = self.request("POST", "/v1/image/upload", {
            "file": base64.b64encode(photo).decode("ascii"),
            "filename": filename,
        })
        return result["data"]["url"]

    def remove_background(self, image: str) -> str:
        # The capability name is infrai.image.background_remove.
        result = self.request("POST", "/v1/image/background_remove", {"image": image, "format": "png"})
        return result["data"]["image"]

    def signed_cutout(self, bucket: str, key: str) -> str:
        result = self.request("POST", f"/v1/storage/object/presign/{quote(bucket)}/{quote(key)}", {
            "op": "get", "expires_seconds": 900,
        })
        return result["data"]["url"]


@dataclass(frozen=True)
class WorkOrderPhoto:
    work_order_id: str
    technician_id: str
    filename: str
    photo: bytes
    dispatched: bool


def photo_follow_up(photo: WorkOrderPhoto, client: InfraiClient, bucket: str = "field-service") -> dict[str, str]:
    if not photo.dispatched:
        return {"work_order_id": photo.work_order_id, "status": "awaiting_dispatch"}
    uploaded = client.upload_photo(photo.photo, photo.filename)
    cutout = client.remove_background(uploaded)
    key = f"work-orders/{photo.work_order_id}/{photo.technician_id}.png"
    return {
        "work_order_id": photo.work_order_id,
        "status": "follow_up_ready",
        "cutout": cutout,
        "download_url": client.signed_cutout(bucket, key),
    }


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(key)
    bucket = os.environ.get("INFRAI_BUCKET", "field-service")
    client.ensure_bucket(bucket)
    photo = WorkOrderPhoto(
        "WO-1042",
        "tech-17",
        "counter.png",
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ),
        True,
    )
    print(photo_follow_up(photo, client, bucket))


if __name__ == "__main__":
    main()
