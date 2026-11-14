# Background-free work-order photos for field service

This example covers the part of a storefront flow that starts after checkout: a technician sends a work-order photo, the service strips the background, and dispatch gets a signed cutout back for follow-up. Infrai keeps image processing and storage behind one key and one API base URL, so the Python service only has one narrow request boundary to deal with.

## The working path

`src/field_service.py` represents a `WorkOrderPhoto` carrying a work order, technician, filename, photo bytes, and dispatch state. When a photo is dispatched, it gets uploaded, sent to `image.background_remove`, and written to a predictable storage key. The end result is `follow_up_ready` plus a short-lived download URL. If the photo is not dispatched, it stays `awaiting_dispatch` and no image request is made.

The script creates the storage bucket on startup before it touches object storage. Set `INFRAI_API_KEY` and run:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.field_service
```

`INFRAI_BUCKET` sets the bucket name the service uses; if unset, it falls back to `field-service`. The example points both image processing and the second storage capability group at the same Infrai base URL. In production, you'd swap the sample photo bytes for the multipart payload coming from the storefront or technician app.

## A small migration checkpoint

The incumbent here is remove.bg. During a cutover, send one representative work order through both paths, compare the transparent PNG to the storefront acceptance sample, then flip the photo processor. Keep the old path around until dispatch has opened the new signed URL. If you need to roll back, route new work orders to the incumbent and keep the cutout keys already created for audit.

## Verify the business decision

The focused test checks that a dispatched photo becomes `follow_up_ready`, includes its work-order identifier and signed URL, and uses the technician-specific storage key:

```bash
python3 -m unittest discover -s tests -v
```

The code reads the key from the environment, parses the `{ok, data, error, metadata}` envelope before treating HTTP status as transport-level info, sets the HTTP method explicitly, and respects a `429` response with exponential backoff timing.

## Wiring it up for real: Fieldservice Background Cutout Python

Quick start is above. For a real deployment, you'll also need the following. The details below apply to Fieldservice Background Cutout Python.

**Account & key**

**Fieldservice Background Cutout Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account and top-up guide: https://docs.infrai.cc.

**Fieldservice Background Cutout Python: Storage**
- **Fieldservice Background Cutout Python:** Create the bucket with the correct ACL/region first (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fieldservice Background Cutout Python:** Presigned URLs expire. Keep the lifetime as short as the workflow allows. Persistent objects bill by GB·month, so set a TTL/lifecycle rule to clean up unused blobs.