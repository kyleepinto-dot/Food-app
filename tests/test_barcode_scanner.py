import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import flet as ft
import cv2
import numpy as np

from pages.barcode_page import (
    CAMERA_LANDSCAPE_ASPECT_RATIO,
    CAMERA_PORTRAIT_ASPECT_RATIO,
    BarcodeScannerController,
    get_camera_preview_aspect_ratio,
    get_camera_preview_dimensions,
)


class _TestScannerController(BarcodeScannerController):
    def __init__(self, platform: str):
        self.page = cast(ft.Page, SimpleNamespace(platform=platform))

    def append_debug(self, step: str, message: str) -> None:
        pass


class BarcodeScannerImageTests(unittest.TestCase):
    @staticmethod
    def _live_stream_controller() -> BarcodeScannerController:
        controller = BarcodeScannerController.__new__(BarcodeScannerController)
        controller.running = True
        controller.streaming_supported = True
        controller.lookup_in_progress = False
        controller.active_lookup_token = None
        controller.last_failed_barcode = None
        controller.stream_frame_in_progress = False
        controller.camera_generation = 1
        controller.result_text = SimpleNamespace(value="Live barcode scanning is active")
        controller.page = cast(ft.Page, SimpleNamespace(update=Mock()))
        controller.append_debug = Mock()
        controller.decode_scan_window = AsyncMock(return_value=[])
        controller.handle_decoded_barcode = AsyncMock()
        return controller

    def test_live_stream_skips_processing_during_product_lookup(self):
        controller = self._live_stream_controller()
        controller.lookup_in_progress = True
        event = SimpleNamespace(bytes=b"encoded-frame")

        asyncio.run(controller.process_stream_frame(event))

        cast(AsyncMock, controller.decode_scan_window).assert_not_awaited()
        cast(AsyncMock, controller.handle_decoded_barcode).assert_not_awaited()

    def test_live_stream_allows_only_one_frame_decode_at_a_time(self):
        controller = self._live_stream_controller()
        controller.stream_frame_in_progress = True
        event = SimpleNamespace(bytes=b"encoded-frame")

        asyncio.run(controller.process_stream_frame(event))

        cast(AsyncMock, controller.decode_scan_window).assert_not_awaited()

    def test_live_stream_drops_result_if_lookup_starts_during_decode(self):
        controller = self._live_stream_controller()
        event = SimpleNamespace(bytes=b"encoded-frame")

        async def begin_lookup(_frame):
            controller.lookup_in_progress = True
            return [SimpleNamespace(data=b"0898999000022")]

        controller.decode_scan_window = AsyncMock(side_effect=begin_lookup)
        encoded_frame = np.full((20, 20, 3), 255, dtype=np.uint8)
        saved, encoded = cv2.imencode(".jpg", encoded_frame)
        self.assertTrue(saved)
        event.bytes = encoded.tobytes()

        asyncio.run(controller.process_stream_frame(event))

        cast(AsyncMock, controller.handle_decoded_barcode).assert_not_awaited()
        self.assertFalse(controller.stream_frame_in_progress)

    def test_live_stream_miss_does_not_overwrite_status_or_update_page(self):
        controller = self._live_stream_controller()
        encoded_frame = np.full((20, 20, 3), 255, dtype=np.uint8)
        saved, encoded = cv2.imencode(".jpg", encoded_frame)
        self.assertTrue(saved)

        asyncio.run(controller.process_stream_frame(SimpleNamespace(bytes=encoded.tobytes())))

        assert controller.result_text is not None
        self.assertEqual(controller.result_text.value, "Live barcode scanning is active")
        cast(Mock, controller.page.update).assert_not_called()

    def test_live_stream_releases_frame_gate_after_malformed_image(self):
        controller = self._live_stream_controller()

        asyncio.run(controller.process_stream_frame(SimpleNamespace(bytes=b"not-an-image")))

        self.assertFalse(controller.stream_frame_in_progress)
        cast(AsyncMock, controller.handle_decoded_barcode).assert_not_awaited()

    def test_stale_lookup_cannot_clear_new_lookup_state(self):
        controller = self._live_stream_controller()
        old_overlay = SimpleNamespace(visible=False)
        new_overlay = SimpleNamespace(visible=True)
        controller.lookup_overlay = old_overlay
        controller.status_text = SimpleNamespace(value="")
        controller.on_barcode_detected = AsyncMock()
        controller.handle_decoded_barcode = (
            BarcodeScannerController.handle_decoded_barcode.__get__(
                controller,
                BarcodeScannerController,
            )
        )

        async def replace_lookup(_barcode):
            controller.camera_generation += 1
            controller.active_lookup_token = object()
            controller.lookup_in_progress = True
            controller.lookup_overlay = new_overlay
            return True

        controller.on_barcode_detected.side_effect = replace_lookup

        asyncio.run(controller.handle_decoded_barcode("0898999000022"))

        self.assertTrue(controller.lookup_in_progress)
        self.assertTrue(new_overlay.visible)

    def test_photo_debug_is_disabled_on_android(self):
        controller = _TestScannerController("android")

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pages.barcode_page.IMAGE_PROCESSING_DEBUG_ROOT", new=Path(temp_dir)):
                self.assertIsNone(controller.create_photo_debug_folder())
                self.assertEqual(os.listdir(temp_dir), [])

    def test_photo_debug_writes_meaningful_processing_stage_names(self):
        controller = _TestScannerController("windows")
        image = np.full((120, 320, 3), 35, dtype=np.uint8)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pages.barcode_page.IMAGE_PROCESSING_DEBUG_ROOT", new=Path(temp_dir)):
                debug_folder = controller.create_photo_debug_folder()
                self.assertIsNotNone(debug_folder)
                controller.write_debug_image(debug_folder, "00_original_camera_frame.png", image)
                asyncio.run(controller.decode_scan_window(image, debug_folder))

                self.assertEqual(
                    sorted(os.listdir(debug_folder)),
                    [
                        "00_original_camera_frame.png",
                        "01_scanning_box_crop.png",
                        "02_grayscale.png",
                        "03_brightness_corrected.png",
                        "04_local_contrast_clahe.png",
                        "05_lightly_sharpened.png",
                        "06_illumination_normalized.png",
                        "07_low_threshold_thin_bars.png",
                        "08_balanced_otsu_threshold.png",
                        "09_high_threshold_thick_bars.png",
                        "10_grayscale_with_border.png",
                        "11_brightness_with_border.png",
                        "12_clahe_with_border.png",
                        "13_sharpened_with_border.png",
                        "14_thin_bars_with_border.png",
                        "15_balanced_otsu_with_border.png",
                        "16_thick_bars_with_border.png",
                        "pyzbar_input_01_grayscale.png",
                        "pyzbar_input_02_brightness.png",
                        "pyzbar_input_03_clahe.png",
                        "pyzbar_input_04_sharpened.png",
                        "pyzbar_input_05_thin_bars.png",
                        "pyzbar_input_06_balanced_otsu.png",
                        "pyzbar_input_07_thick_bars.png",
                    ],
                )

    def test_successful_decode_writes_candidate_with_barcode_in_filename(self):
        controller = _TestScannerController("windows")
        image = np.full((120, 320, 3), 35, dtype=np.uint8)
        decoded_barcode = SimpleNamespace(data=b"9781566377928")

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("pages.barcode_page.IMAGE_PROCESSING_DEBUG_ROOT", new=Path(temp_dir)),
                patch("pages.barcode_page.decode", return_value=[decoded_barcode]),
            ):
                debug_folder = controller.create_photo_debug_folder()
                self.assertIsNotNone(debug_folder)
                assert debug_folder is not None
                barcodes = asyncio.run(controller.decode_scan_window(image, debug_folder))

                self.assertEqual(barcodes, [decoded_barcode])
                self.assertTrue(
                    (debug_folder / "decoded_barcode_9781566377928_pyzbar_input.png").is_file()
                )
                self.assertTrue((debug_folder / "pyzbar_input_01_grayscale.png").is_file())

    def test_opencv_decode_writes_scan_region_with_barcode_in_filename(self):
        controller = _TestScannerController("windows")
        image = np.full((120, 320, 3), 35, dtype=np.uint8)

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("pages.barcode_page.IMAGE_PROCESSING_DEBUG_ROOT", new=Path(temp_dir)),
                patch("pages.barcode_page.decode", return_value=[]),
                patch.object(
                    controller,
                    "detect_and_rectify_barcode",
                    return_value=(["9781566377928"], None),
                ),
            ):
                debug_folder = controller.create_photo_debug_folder()
                self.assertIsNotNone(debug_folder)
                assert debug_folder is not None
                barcodes = asyncio.run(controller.decode_scan_window(image, debug_folder))

                self.assertEqual(barcodes, ["9781566377928"])
                self.assertTrue(
                    (debug_folder / "decoded_barcode_9781566377928_opencv_input.png").is_file()
                )

    def test_opencv_tries_enhanced_candidates_after_pyzbar_fails(self):
        controller = _TestScannerController("windows")
        image = np.full((120, 320, 3), 35, dtype=np.uint8)
        detector = Mock()
        detector.detectAndDecodeWithType.side_effect = [
            (False, (), (), None),
            (False, (), (), None),
            (True, ("898999000022",), ("UPC_A",), None),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("pages.barcode_page.IMAGE_PROCESSING_DEBUG_ROOT", new=Path(temp_dir)),
                patch("pages.barcode_page.decode", return_value=[]),
                patch("pages.barcode_page.cv2.barcode_BarcodeDetector", return_value=detector),
            ):
                debug_folder = controller.create_photo_debug_folder()
                self.assertIsNotNone(debug_folder)
                assert debug_folder is not None
                barcodes = asyncio.run(controller.decode_scan_window(image, debug_folder))

                self.assertEqual(barcodes, ["898999000022"])
                self.assertEqual(detector.detectAndDecodeWithType.call_count, 3)
                self.assertTrue(
                    (
                        debug_folder
                        / "decoded_barcode_898999000022_opencv_clahe_input.png"
                    ).is_file()
                )

    def test_detected_barcode_crop_includes_surrounding_margin(self):
        controller = _TestScannerController("windows")
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        detector = Mock()
        detector.detectAndDecodeWithType.return_value = (
            False,
            (),
            (),
            np.array([[[10, 10], [60, 10], [60, 30], [10, 30]]], dtype=np.float32),
        )

        with patch("pages.barcode_page.cv2.barcode_BarcodeDetector", return_value=detector):
            decoded_values, rectified = controller.detect_and_rectify_barcode(image)

        self.assertEqual(decoded_values, [])
        self.assertIsNotNone(rectified)
        self.assertEqual(rectified.shape[:2], (30, 58))

    def test_preview_dimensions_follow_shell_width(self):
        mobile_size = get_camera_preview_dimensions(
            {"shell_width": 390, "shell_height": 760, "is_desktop": False}
        )
        desktop_size = get_camera_preview_dimensions(
            {"shell_width": 1000, "shell_height": 700, "is_desktop": True}
        )

        self.assertEqual(mobile_size, (358, 477))
        self.assertEqual(desktop_size, (533, 400))

    def test_phone_portrait_uses_taller_camera_preview(self):
        portrait_metrics = {
            "shell_width": 390,
            "shell_height": 760,
            "is_desktop": False,
            "is_tablet": False,
        }
        landscape_metrics = {
            "shell_width": 760,
            "shell_height": 390,
            "is_desktop": False,
            "is_tablet": True,
        }

        self.assertEqual(
            get_camera_preview_aspect_ratio(portrait_metrics),
            CAMERA_PORTRAIT_ASPECT_RATIO,
        )
        self.assertEqual(
            get_camera_preview_aspect_ratio(landscape_metrics),
            CAMERA_LANDSCAPE_ASPECT_RATIO,
        )

    def test_preview_shrinks_to_keep_camera_buttons_visible(self):
        preview_size = get_camera_preview_dimensions(
            {"shell_width": 900, "shell_height": 680, "is_desktop": False}
        )

        self.assertEqual(preview_size, (507, 380))

    def test_resize_updates_mounted_camera_without_replacing_it(self):
        controller = BarcodeScannerController.__new__(BarcodeScannerController)
        controller.camera = SimpleNamespace(width=0, height=0)
        controller.camera_panel = SimpleNamespace(width=0, height=0)
        controller.scan_container = SimpleNamespace(width=0, height=0)

        controller.resize_view(
            {
                "shell_width": 600,
                "shell_height": 720,
                "is_desktop": False,
            }
        )

        self.assertEqual((controller.camera.width, controller.camera.height), (552, 414))
        self.assertEqual((controller.camera_panel.width, controller.camera_panel.height), (552, 414))
        self.assertEqual((controller.scan_container.width, controller.scan_container.height), (600, 720))

    def test_crop_matches_clear_scan_window(self):
        frame = np.zeros((1000, 500, 3), dtype=np.uint8)

        cropped = BarcodeScannerController.crop_to_scan_window(frame)

        self.assertEqual(cropped.shape, (380, 390, 3))

    def test_preprocessing_brightens_dark_scan_region(self):
        controller = BarcodeScannerController.__new__(BarcodeScannerController)
        image = np.full((120, 320, 3), 35, dtype=np.uint8)

        candidates = asyncio.run(controller.preprocess_for_pyzbar(image))
        brightness_corrected = candidates[1]
        thresholded = candidates[-1]

        self.assertEqual(len(candidates), 7)
        self.assertGreater(float(np.mean(brightness_corrected)), 35)
        self.assertEqual(brightness_corrected.shape, (160, 360))
        self.assertEqual(thresholded.shape, (160, 360))

    def test_capture_guidance_prioritizes_barcode_size_and_focus(self):
        controller = BarcodeScannerController.__new__(BarcodeScannerController)
        controller.last_barcode_width_ratio = 0.20
        controller.last_barcode_sharpness = 100
        self.assertIn("Move closer", controller.capture_quality_guidance())

        controller.last_barcode_width_ratio = 0.50
        controller.last_barcode_sharpness = 20
        self.assertIn("Hold", controller.capture_quality_guidance())

    def test_navigation_stop_does_not_queue_calls_for_unmounted_camera(self):
        controller = BarcodeScannerController.__new__(BarcodeScannerController)
        controller.camera_generation = 0
        controller.camera_starting = False
        controller.running = True
        controller.capture_in_progress = True
        controller.lookup_in_progress = False
        controller.active_lookup_token = None
        controller.stream_frame_in_progress = True
        controller.camera_light_on = False
        controller.streaming_supported = False
        controller.camera = SimpleNamespace()
        controller.capture_button = None
        controller.camera_light_button = None
        controller.status_text = None
        controller.result_text = None
        controller.camera_action_button = None
        run_task_mock = Mock()
        controller.page = cast(ft.Page, SimpleNamespace(run_task=run_task_mock))
        controller.append_debug = Mock()

        controller.stop_camera()

        run_task_mock.assert_not_called()
        self.assertFalse(controller.running)
        self.assertFalse(controller.capture_in_progress)
        self.assertFalse(controller.stream_frame_in_progress)

    def test_release_awaits_camera_calls_while_control_is_mounted(self):
        controller = BarcodeScannerController.__new__(BarcodeScannerController)
        page = cast(ft.Page, object())
        camera = SimpleNamespace(
            page=page,
            pause_preview=AsyncMock(),
            set_description=AsyncMock(),
            stop_image_stream=AsyncMock(),
            set_flash_mode=AsyncMock(),
        )
        controller.page = page
        controller.camera_generation = 0
        controller.camera_starting = False
        controller.running = True
        controller.capture_in_progress = False
        controller.lookup_in_progress = False
        controller.active_lookup_token = None
        controller.stream_frame_in_progress = False
        controller.camera_light_on = False
        controller.streaming_supported = False
        controller.camera = camera
        controller.capture_button = None
        controller.camera_light_button = None
        controller.status_text = None
        controller.result_text = None
        controller.camera_action_button = None
        controller.append_debug = Mock()

        asyncio.run(controller.stop_camera_and_release())

        camera.pause_preview.assert_awaited_once()
        camera.set_description.assert_awaited_once_with(None)


if __name__ == "__main__":
    unittest.main()
