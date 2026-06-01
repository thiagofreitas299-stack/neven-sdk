"""
NEVEN Perception Pipeline

Orchestrates the full perception flow:
    Video Source -> Frame Extraction -> Object Detection -> Tracking -> State Update

Supports:
    - Webcam (device index)
    - RTSP streams
    - Video files
    - Image directories (for testing)
"""

import time
import threading
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import numpy as np

from neven.perception.detector import ObjectDetector, Detection
from neven.perception.tracker import MultiObjectTracker, Track
from neven.core.models import DetectedEntity, BoundingBox, SpatialPosition, EntityClass

logger = logging.getLogger("neven.perception.pipeline")


class VideoSource:
    """Manages video capture from various sources."""

    def __init__(self, source: Any = 0, frame_rate: int = 15):
        self.source = source
        self.frame_rate = frame_rate
        self._cap = None
        self._running = False
        self._frame_count = 0
        self._last_frame = None

    def open(self) -> bool:
        """Open the video source."""
        try:
            import cv2
            self._cap = cv2.VideoCapture(self.source)
            if not self._cap.isOpened():
                logger.error(f"Failed to open video source: {self.source}")
                return False
            logger.info(f"Video source opened: {self.source}")
            self._running = True
            return True
        except ImportError:
            logger.warning(
                "OpenCV not installed. Using synthetic frames. "
                "Install with: pip install opencv-python"
            )
            self._running = True
            return True

    def read(self) -> Optional[np.ndarray]:
        """Read a frame from the video source."""
        if self._cap is not None:
            ret, frame = self._cap.read()
            if ret:
                self._frame_count += 1
                self._last_frame = frame
                return frame
            return None
        else:
            # Generate synthetic frame for testing
            return self._generate_synthetic_frame()

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generate a synthetic frame with simulated movement for testing."""
        self._frame_count += 1
        h, w = 480, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Background
        frame[:] = (20, 20, 30)  # Dark background

        # Simulate moving objects
        t = time.time()
        num_objects = 3 + int(np.sin(t * 0.1) * 2)

        for i in range(num_objects):
            # Simulate person-like rectangles moving
            x = int((np.sin(t * 0.5 + i * 1.5) + 1) * 0.4 * w + 50)
            y = int((np.cos(t * 0.3 + i * 2.0) + 1) * 0.3 * h + 50)
            pw, ph = 40 + i * 5, 100 + i * 10

            # Draw rectangle (simulated person)
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w, x + pw), min(h, y + ph)
            frame[y1:y2, x1:x2] = (
                100 + i * 30,
                150 + i * 20,
                200 - i * 20,
            )

        # Add some noise
        noise = np.random.randint(0, 10, (h, w, 3), dtype=np.uint8)
        frame = np.clip(frame.astype(np.int16) + noise.astype(np.int16), 0, 255).astype(np.uint8)

        self._last_frame = frame
        return frame

    def release(self) -> None:
        """Release the video source."""
        self._running = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_open(self) -> bool:
        return self._running

    @property
    def frame_count(self) -> int:
        return self._frame_count


class PerceptionPipeline:
    """
    The NEVEN Perception Pipeline.

    Orchestrates video capture, object detection, tracking, and state updates.
    Runs as a background thread and publishes detected entities.
    """

    def __init__(
        self,
        source: Any = 0,
        model_name: str = "yolov8n",
        confidence_threshold: float = 0.35,
        frame_rate: int = 15,
        max_track_age: int = 30,
    ):
        self.video_source = VideoSource(source=source, frame_rate=frame_rate)
        self.detector = ObjectDetector(
            model_name=model_name,
            confidence_threshold=confidence_threshold,
        )
        self.tracker = MultiObjectTracker(max_age=max_track_age)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_rate = frame_rate
        self._callbacks: List[Callable] = []
        self._current_entities: List[DetectedEntity] = []
        self._stats = {
            "frames_processed": 0,
            "total_detections": 0,
            "active_tracks": 0,
            "fps": 0.0,
            "started_at": None,
        }

    def start(self) -> bool:
        """Start the perception pipeline in a background thread."""
        if self._running:
            logger.warning("Pipeline already running")
            return True

        if not self.video_source.open():
            logger.error("Failed to open video source")
            return False

        self._running = True
        self._stats["started_at"] = datetime.utcnow().isoformat()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Perception pipeline started (backend={self.detector.backend})")
        return True

    def stop(self) -> None:
        """Stop the perception pipeline."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.video_source.release()
        logger.info("Perception pipeline stopped")

    def _run_loop(self) -> None:
        """Main processing loop."""
        frame_interval = 1.0 / self._frame_rate
        fps_counter = 0
        fps_start = time.time()

        while self._running:
            loop_start = time.time()

            # Read frame
            frame = self.video_source.read()
            if frame is None:
                time.sleep(0.1)
                continue

            # Detect objects
            detections = self.detector.detect(frame)

            # Update tracker
            tracks = self.tracker.update(detections)

            # Convert to NEVEN entities
            entities = self._tracks_to_entities(tracks)
            self._current_entities = entities

            # Update stats
            self._stats["frames_processed"] += 1
            self._stats["total_detections"] += len(detections)
            self._stats["active_tracks"] = len(tracks)

            # FPS calculation
            fps_counter += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                self._stats["fps"] = fps_counter / elapsed
                fps_counter = 0
                fps_start = time.time()

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(entities, frame)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            # Rate limiting
            processing_time = time.time() - loop_start
            sleep_time = frame_interval - processing_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _tracks_to_entities(self, tracks: List[Track]) -> List[DetectedEntity]:
        """Convert tracker tracks to NEVEN DetectedEntity objects."""
        entities = []
        for track in tracks:
            # Map class name to EntityClass
            class_map = {
                "person": EntityClass.PERSON,
                "vehicle": EntityClass.VEHICLE,
                "package": EntityClass.PACKAGE,
                "obstacle": EntityClass.OBSTACLE,
            }
            entity_class = class_map.get(track.class_name, EntityClass.UNKNOWN)

            entity = DetectedEntity(
                entity_id=f"ent_{track.track_id:04d}",
                class_label=entity_class,
                confidence=track.confidence,
                bbox=BoundingBox(
                    x1=track.bbox[0],
                    y1=track.bbox[1],
                    x2=track.bbox[2],
                    y2=track.bbox[3],
                ),
                spatial_position=SpatialPosition(
                    x=track.centroid[0],
                    y=track.centroid[1],
                ),
                velocity={"vx": track.velocity[0], "vy": track.velocity[1]},
                first_seen=datetime.fromtimestamp(track.first_seen),
                last_seen=datetime.fromtimestamp(track.last_seen),
                track_id=track.track_id,
                metadata={
                    "dwell_time": track.dwell_time,
                    "frames_tracked": track.frames_tracked,
                },
            )
            entities.append(entity)

        return entities

    def on_update(self, callback: Callable) -> None:
        """Register a callback for entity updates."""
        self._callbacks.append(callback)

    @property
    def current_entities(self) -> List[DetectedEntity]:
        """Get the current detected entities."""
        return self._current_entities

    @property
    def stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self._stats.copy()

    @property
    def is_running(self) -> bool:
        return self._running
