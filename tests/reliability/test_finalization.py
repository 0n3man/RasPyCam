import threading
import unittest
from unittest.mock import MagicMock, patch

from utilities.record import stop_recording
from utilities.video_output import RecordingOutput


class FinalizationTests(unittest.TestCase):
    def test_finalize_runs_after_camera_lock_is_released(self):
        output = RecordingOutput('/tmp/test.mp4')
        lock = threading.Lock()
        cam = MagicMock(capturing_video=True)
        cam.video_encoder.output = output
        def encoder_stop(encoder):
            with lock:
                output.stop()
        cam.picam2.stop_encoder.side_effect = encoder_stop
        def finish():
            self.assertTrue(lock.acquire(blocking=False), 'camera lock held during finish')
            lock.release()
        with patch.object(output, 'finish', side_effect=finish) as finalize:
            self.assertTrue(stop_recording(cam))
            finalize.assert_called_once()
        cam.set_status.assert_called_once_with('ready')

    def test_finalize_failure_reports_error_and_leaves_camera_ready(self):
        output = RecordingOutput('/tmp/test.mp4')
        cam = MagicMock(capturing_video=True)
        cam.video_encoder.output = output
        with patch.object(output, 'finish', side_effect=RuntimeError('timeout')), patch('utilities.record.diagnostics.incident'), self.assertLogs(level='ERROR'):
            self.assertFalse(stop_recording(cam))
        cam.set_status.assert_called_once_with('ready')
        self.assertFalse(cam.capturing_video)
        self.assertIsNone(cam.recording_error)
        self.assertFalse(output.defer_finalization)

    def test_encoder_stop_failure_still_propagates(self):
        output = RecordingOutput('/tmp/test.mp4')
        cam = MagicMock(capturing_video=True)
        cam.video_encoder.output = output
        cam.picam2.stop_encoder.side_effect = RuntimeError('driver failed')
        with self.assertRaisesRegex(RuntimeError, 'driver failed'):
            stop_recording(cam)
        cam.set_status.assert_not_called()
