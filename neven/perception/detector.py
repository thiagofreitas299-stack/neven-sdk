"""
NEVEN Object Detector

Provides object detection using YOLOv8 (via ultralytics) or a lightweight
built-in detector for demo/testing purposes.

In production, this runs on edge hardware with RT-DETR or YOLOv10.
For the MVP, it supports:
    - YOLOv8 (if ultralytics is installed)
    - Built-in motion-based detection (always available)
"""

import time
import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("neven.perception.detector")


@dataclass
class Detection:
    """A single object detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    timestamp: float = 0.0

    @property
    def centroid(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def area(self) -> float:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


# COCO class names for common objects
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    39: "bottle",
    56: "chair",
    57: "couch",
    58: "potted_plant",
    59: "bed",
    60: "dining_table",
    62: "tv",
    63: "laptop",
    64: "mouse",
    66: "keyboard",
    67: "cell_phone",
}

# Map COCO to NEVEN entity classes
NEVEN_CLASS_MAP = {
    "person": "person",
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "motorcycle": "vehicle",
    "bicycle": "vehicle",
    "backpack": "package",
    "suitcase": "package",
    "handbag": "package",
}


class ObjectDetector:
    """
    NEVEN Object Detector.

    Supports multiple backends:
        - "yolov8n" / "yolov8s" / "yolov8m": Ultralytics YOLO models
        - "builtin": Lightweight motion-based detection (no dependencies)
    """

    def __init__(
        self,
        model_name: str = "yolov8n",
        confidence_threshold: float = 0.35,
        target_classes: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.target_classes = target_classes or ["person", "vehicle", "package"]
        self._model = None
        self._backend = "builtin"
        self._prev_frame = None
        self._frame_count = 0

        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load the detection model."""
        if self.model_name.startswith("yolo"):
            try:
                from ultralytics import YOLO
                self._model = YOLO(f"{self.model_name}.pt")
                self._backend = "yolo"
                logger.info(f"Loaded YOLO model: {self.model_name}")
            except ImportError:
                logger.info(
                    "Ultralytics not installed. Using built-in motion detector. "
                    "Install with: pip install ultralytics"
                )
                self._backend = "builtin"
            except Exception as e:
                logger.warning(f"Failed to load YOLO model: {e}. Using builtin.")
                self._backend = "builtin"
        else:
            self._backend = "builtin"

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run object detection on a frame.

        Args:
            frame: Input image as numpy array (H, W, C) in BGR format

        Returns:
            List of Detection objects
        """
        self._frame_count += 1

        if self._backend == "yolo":
            return self._detect_yolo(frame)
        else:
            return self._detect_builtin(frame)

    def _detect_yolo(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLO detection."""
        results = self._model(frame, verbose=False, conf=self.confidence_threshold)
        detections = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = result.names.get(class_id, "unknown")
                neven_class = NEVEN_CLASS_MAP.get(class_name, "unknown")

                # Filter by target classes
                if neven_class not in self.target_classes and class_name not in self.target_classes:
                    continue

                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=neven_class,
                        confidence=confidence,
                        bbox=(x1, y1, x2, y2),
                        timestamp=time.time(),
                    )
                )

        return detections

    def _detect_builtin(self, frame: np.ndarray) -> List[Detection]:
        """
        Built-in motion-based detection using frame differencing.

        This is a lightweight fallback that detects moving objects without
        requiring any ML model. Suitable for demos and testing.
        """
        detections = []
        gray = np.mean(frame, axis=2).astype(np.uint8) if len(frame.shape) == 3 else frame

        if self._prev_frame is not None:
            # Frame differencing
            diff = np.abs(gray.astype(np.int16) - self._prev_frame.astype(np.int16)).astype(np.uint8)

            # Threshold
            threshold = 30
            motion_mask = (diff > threshold).astype(np.uint8)

            # Find contours via connected components
            detections = self._find_motion_regions(motion_mask, frame.shape)

        self._prev_frame = gray.copy()
        return detections

    def _find_motion_regions(
        self, mask: np.ndarray, frame_shape: tuple
    ) -> List[Detection]:
        """Find bounding boxes of motion regions."""
        detections = []
        h, w = mask.shape

        # Simple grid-based region detection
        grid_size = 64
        for gy in range(0, h - grid_size, grid_size // 2):
            for gx in range(0, w - grid_size, grid_size // 2):
                region = mask[gy : gy + grid_size, gx : gx + grid_size]
                motion_ratio = np.mean(region)

                if motion_ratio > 0.15:  # 15% of pixels moving
                    # Estimate bounding box
                    x1 = float(gx)
                    y1 = float(gy)
                    x2 = float(min(gx + grid_size * 2, w))
                    y2 = float(min(gy + grid_size * 3, h))

                    # Classify based on aspect ratio and size
                    aspect_ratio = (y2 - y1) / max(x2 - x1, 1)
                    area = (x2 - x1) * (y2 - y1)
                    total_area = h * w

                    if aspect_ratio > 1.5 and area / total_area < 0.3:
                        class_name = "person"
                    elif area / total_area > 0.15:
                        class_name = "vehicle"
                    else:
                        class_name = "unknown"

                    confidence = min(motion_ratio * 2, 0.95)

                    detections.append(
                        Detection(
                            class_id=0 if class_name == "person" else 2,
                            class_name=class_name,
                            confidence=confidence,
                            bbox=(x1, y1, x2, y2),
                            timestamp=time.time(),
                        )
                    )

        # Deduplicate overlapping detections
        return self._non_max_suppression(detections)

    def _non_max_suppression(
        self, detections: List[Detection], iou_threshold: float = 0.5
    ) -> List[Detection]:
        """Simple NMS to remove overlapping detections."""
        if not detections:
            return []

        # Sort by confidence
        detections.sort(key=lambda d: d.confidence, reverse=True)
        kept = []

        for det in detections:
            overlap = False
            for kept_det in kept:
                iou = self._compute_iou(det.bbox, kept_det.bbox)
                if iou > iou_threshold:
                    overlap = True
                    break
            if not overlap:
                kept.append(det)

        return kept[:20]  # Max 20 detections per frame

    @staticmethod
    def _compute_iou(
        box1: Tuple[float, float, float, float],
        box2: Tuple[float, float, float, float],
    ) -> float:
        """Compute Intersection over Union."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / max(union, 1e-6)

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_ready(self) -> bool:
        return True
