import unittest

from src.field_service import WorkOrderPhoto, photo_follow_up


class RecordingClient:
    def __init__(self):
        self.calls = []

    def upload_photo(self, photo, filename):
        self.calls.append(("upload", filename))
        return "uploaded-image"

    def remove_background(self, image):
        self.calls.append(("background", image))
        return "cutout-image"

    def signed_cutout(self, bucket, key):
        self.calls.append(("presign", bucket, key))
        return "https://download.example/cutout"


class FieldServiceDecisionTest(unittest.TestCase):
    def test_dispatched_photo_becomes_follow_up_ready(self):
        client = RecordingClient()
        photo = WorkOrderPhoto("WO-7", "tech-2", "door.jpg", b"bytes", True)

        result = photo_follow_up(photo, client, "field-service")

        self.assertEqual(result["status"], "follow_up_ready")
        self.assertEqual(result["work_order_id"], "WO-7")
        self.assertEqual(result["download_url"], "https://download.example/cutout")
        self.assertEqual(client.calls[-1], ("presign", "field-service", "work-orders/WO-7/tech-2.png"))


if __name__ == "__main__":
    unittest.main()
