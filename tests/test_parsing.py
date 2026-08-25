"""Tests for `birdnet_go.parsing` — the pure payload → field mapping.

Pinned to real shapes seen from a live BirdNET-Go instance (see the repo's
git history / handovers), not guessed schemas.
"""

from birdnet_go.parsing import (
    daily_to_fields,
    detection_to_fields,
    parse_sse_detection,
    summary_to_fields,
)

BASE_URL = "https://birdnet.example.com"

DAILY_PAYLOAD = [
    {"common_name": "wróbel", "scientific_name": "Passer domesticus", "count": 55},
    {
        "common_name": "kopciuszek",
        "scientific_name": "Phoenicurus ochruros",
        "count": 12,
        "thumbnail_url": "/media/thumb/kopciuszek.jpg",
    },
]

SUMMARY_PAYLOAD = [
    {"scientific_name": "Passer domesticus", "count": 55},
    {"scientific_name": "Phoenicurus ochruros", "count": 12},
    {"scientific_name": "Parus major", "count": 95},
]

DETECTION = {
    "id": 485170,
    "date": "2026-08-25",
    "time": "20:15:26",
    "timestamp": "2026-08-25T20:15:26+02:00",
    "speciesCode": "blared1",
    "scientificName": "Phoenicurus ochruros",
    "commonName": "kopciuszek",
    "confidence": 0.43,
}


class TestDailyToFields:
    def test_empty_payload_returns_zeroed_fields(self):
        fields = daily_to_fields([], BASE_URL)
        assert fields["detections_today"] == 0
        assert fields["species_today"] == 0
        assert fields["top_species"] is None
        assert fields["top_species_thumbnail"] is None

    def test_sums_detections_and_counts_species(self):
        fields = daily_to_fields(DAILY_PAYLOAD, BASE_URL)
        assert fields["detections_today"] == 55 + 12
        assert fields["species_today"] == 2

    def test_picks_highest_count_as_top_species(self):
        fields = daily_to_fields(DAILY_PAYLOAD, BASE_URL)
        assert fields["top_species"] == "wróbel"
        assert fields["top_species_scientific"] == "Passer domesticus"
        assert fields["top_species_count"] == 55

    def test_top_species_without_thumbnail_url_is_none(self):
        fields = daily_to_fields(DAILY_PAYLOAD, BASE_URL)
        assert fields["top_species_thumbnail"] is None

    def test_top_species_thumbnail_is_prefixed_with_base_url(self):
        payload = [
            {
                "common_name": "kopciuszek",
                "scientific_name": "Phoenicurus ochruros",
                "count": 12,
                "thumbnail_url": "/media/thumb/kopciuszek.jpg",
            }
        ]
        fields = daily_to_fields(payload, BASE_URL)
        assert (
            fields["top_species_thumbnail"] == f"{BASE_URL}/media/thumb/kopciuszek.jpg"
        )

    def test_missing_count_defaults_to_zero(self):
        fields = daily_to_fields(
            [{"common_name": "x", "scientific_name": "y"}], BASE_URL
        )
        assert fields["detections_today"] == 0


class TestSummaryToFields:
    def test_empty_payload_returns_zeroed_fields(self):
        fields = summary_to_fields([])
        assert fields == {"total_species": 0, "total_detections": 0}

    def test_counts_species_and_sums_detections(self):
        fields = summary_to_fields(SUMMARY_PAYLOAD)
        assert fields["total_species"] == 3
        assert fields["total_detections"] == 55 + 12 + 95


class TestDetectionToFields:
    def test_maps_basic_fields(self):
        fields = detection_to_fields(DETECTION, BASE_URL)
        assert fields["last_detection"] == "kopciuszek"
        assert fields["last_detection_scientific"] == "Phoenicurus ochruros"
        assert fields["last_detection_time"] == "2026-08-25T20:15:26+02:00"

    def test_confidence_is_rounded_to_percent(self):
        fields = detection_to_fields(DETECTION, BASE_URL)
        assert fields["last_detection_confidence"] == 43

    def test_confidence_none_stays_none(self):
        detection = {**DETECTION, "confidence": None}
        fields = detection_to_fields(detection, BASE_URL)
        assert fields["last_detection_confidence"] is None

    def test_image_url_is_percent_encoded(self):
        # Regression: a raw space in the scientific name produced an
        # invalid URL before this was fixed (see CHANGELOG 1.2.0).
        fields = detection_to_fields(DETECTION, BASE_URL)
        assert " " not in fields["last_detection_image"]
        assert fields["last_detection_image"] == (
            f"{BASE_URL}/api/v2/media/image/Phoenicurus%20ochruros"
        )

    def test_no_scientific_name_means_no_image_url(self):
        detection = {**DETECTION, "scientificName": None}
        fields = detection_to_fields(detection, BASE_URL)
        assert fields["last_detection_image"] is None


class TestParseSseDetection:
    def test_flat_detection_object(self):
        assert parse_sse_detection(DETECTION) == DETECTION

    def test_wrapped_in_detection_key(self):
        assert parse_sse_detection({"detection": DETECTION}) == DETECTION

    def test_list_wrapped_takes_first(self):
        assert parse_sse_detection([DETECTION]) == DETECTION

    def test_empty_list_is_not_a_detection(self):
        assert parse_sse_detection([]) is None

    def test_connection_confirmation_message_is_not_a_detection(self):
        # BirdNET-Go sends a non-detection message right after connecting.
        assert parse_sse_detection({"status": "connected"}) is None

    def test_non_dict_payload_is_not_a_detection(self):
        assert parse_sse_detection("not json") is None
        assert parse_sse_detection(None) is None
