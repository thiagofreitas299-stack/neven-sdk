"""
NEVEN Multi-Object Tracker

Implements a simplified ByteTrack-style multi-object tracker that:
- Assigns persistent IDs to detected objects across frames
- Tracks velocity and trajectory
- Handles object entry/exit events
- Maintains dwell time per tracked object
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from neven.perception.detector import Detection

logger = logging.getLogger("neven.perception.tracker")


@dataclass
class Track:
    """A tracked object with persistent identity."""
    track_id: int
    class_name: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    frames_tracked: int = 1
    frames_lost: int = 0
    velocity: Tuple[float, float] = (0.0, 0.0)
    trajectory: List[Tuple[float, float]] = field(default_factory=list)
    is_active: bool = True

    @property
    def centroid(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def dwell_time(self) -> float:
        """Time in seconds this object has been tracked."""
        return self.last_seen - self.first_seen

    @property
    def age(self) -> float:
        """Time since last seen."""
        return time.time() - self.last_seen


class MultiObjectTracker:
    """
    Multi-object tracker using IoU-based assignment.

    Features:
        - Persistent ID assignment across frames
        - Velocity estimation
        - Dwell time tracking
        - Entry/exit event detection
        - Configurable max age for lost tracks
    """

    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
    ):
        self.max_age = max_age  # Frames before a lost track is removed
        self.min_hits = min_hits  # Min detections before track is confirmed
        self.iou_threshold = iou_threshold
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1
        self._frame_count = 0

        # Event callbacks
        self._on_enter_callbacks = []
        self._on_exit_callbacks = []

    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Update tracker with new detections.

        Args:
            detections: List of detections from current frame

        Returns:
            List of active tracks
        """
        self._frame_count += 1
        current_time = time.time()

        if not detections:
            # No detections — age all tracks
            self._age_tracks()
            return self.active_tracks

        if not self._tracks:
            # First frame — create new tracks for all detections
            for det in detections:
                self._create_track(det, current_time)
            return self.active_tracks

        # Match detections to existing tracks using IoU
        matched, unmatched_dets, unmatched_tracks = self._match_detections(detections)

        # Update matched tracks
        for track_id, det_idx in matched:
            self._update_track(track_id, detections[det_idx], current_time)

        # Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            self._create_track(detections[det_idx], current_time)

        # Age unmatched tracks
        for track_id in unmatched_tracks:
            self._tracks[track_id].frames_lost += 1
            if self._tracks[track_id].frames_lost > self.max_age:
                self._remove_track(track_id)

        return self.active_tracks

    def _match_detections(
        self, detections: List[Detection]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Match detections to existing tracks using IoU."""
        if not self._tracks or not detections:
            return [], list(range(len(detections))), list(self._tracks.keys())

        track_ids = list(self._tracks.keys())
        track_bboxes = [self._tracks[tid].bbox for tid in track_ids]
        det_bboxes = [d.bbox for d in detections]

        # Compute IoU matrix
        iou_matrix = np.zeros((len(track_bboxes), len(det_bboxes)))
        for i, tb in enumerate(track_bboxes):
            for j, db in enumerate(det_bboxes):
                iou_matrix[i, j] = self._compute_iou(tb, db)

        # Greedy matching
        matched = []
        matched_tracks = set()
        matched_dets = set()

        while True:
            if iou_matrix.size == 0:
                break
            max_iou = iou_matrix.max()
            if max_iou < self.iou_threshold:
                break

            idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
            track_idx, det_idx = idx

            matched.append((track_ids[track_idx], det_idx))
            matched_tracks.add(track_idx)
            matched_dets.add(det_idx)

            # Zero out matched row and column
            iou_matrix[track_idx, :] = 0
            iou_matrix[:, det_idx] = 0

        unmatched_dets = [i for i in range(len(detections)) if i not in matched_dets]
        unmatched_tracks = [
            track_ids[i] for i in range(len(track_ids)) if i not in matched_tracks
        ]

        return matched, unmatched_dets, unmatched_tracks

    def _create_track(self, detection: Detection, current_time: float) -> Track:
        """Create a new track from a detection."""
        track = Track(
            track_id=self._next_id,
            class_name=detection.class_name,
            bbox=detection.bbox,
            confidence=detection.confidence,
            first_seen=current_time,
            last_seen=current_time,
            trajectory=[detection.centroid],
        )
        self._tracks[self._next_id] = track
        self._next_id += 1

        # Fire enter event
        for callback in self._on_enter_callbacks:
            callback(track)

        return track

    def _update_track(self, track_id: int, detection: Detection, current_time: float) -> None:
        """Update an existing track with a new detection."""
        track = self._tracks[track_id]
        old_centroid = track.centroid
        new_centroid = detection.centroid

        # Update velocity
        dt = current_time - track.last_seen
        if dt > 0:
            vx = (new_centroid[0] - old_centroid[0]) / dt
            vy = (new_centroid[1] - old_centroid[1]) / dt
            track.velocity = (vx, vy)

        # Update track state
        track.bbox = detection.bbox
        track.confidence = detection.confidence
        track.last_seen = current_time
        track.frames_tracked += 1
        track.frames_lost = 0
        track.is_active = True

        # Update trajectory (keep last 100 points)
        track.trajectory.append(new_centroid)
        if len(track.trajectory) > 100:
            track.trajectory = track.trajectory[-100:]

    def _remove_track(self, track_id: int) -> None:
        """Remove a track and fire exit event."""
        track = self._tracks.pop(track_id, None)
        if track:
            track.is_active = False
            for callback in self._on_exit_callbacks:
                callback(track)

    def _age_tracks(self) -> None:
        """Age all tracks by one frame."""
        to_remove = []
        for track_id, track in self._tracks.items():
            track.frames_lost += 1
            if track.frames_lost > self.max_age:
                to_remove.append(track_id)

        for track_id in to_remove:
            self._remove_track(track_id)

    @staticmethod
    def _compute_iou(
        box1: Tuple[float, float, float, float],
        box2: Tuple[float, float, float, float],
    ) -> float:
        """Compute IoU between two bounding boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / max(union, 1e-6)

    def on_enter(self, callback) -> None:
        """Register a callback for when a new object enters the scene."""
        self._on_enter_callbacks.append(callback)

    def on_exit(self, callback) -> None:
        """Register a callback for when an object exits the scene."""
        self._on_exit_callbacks.append(callback)

    @property
    def active_tracks(self) -> List[Track]:
        """Get all currently active tracks."""
        return [t for t in self._tracks.values() if t.is_active and t.frames_tracked >= self.min_hits]

    @property
    def all_tracks(self) -> List[Track]:
        """Get all tracks including lost ones."""
        return list(self._tracks.values())

    @property
    def track_count(self) -> int:
        return len(self.active_tracks)

    def reset(self) -> None:
        """Reset the tracker state."""
        self._tracks.clear()
        self._next_id = 1
        self._frame_count = 0
