from typing import List, Dict, Any, Tuple
import math

class TrackedObject:
    def __init__(self, track_id: int, class_name: str, bbox: Dict[str, float], confidence: float, frame_idx: int):
        self.track_id = track_id
        self.class_name = class_name
        self.bbox = bbox  # {"x1": ..., "y1": ..., "x2": ..., "y2": ...}
        self.confidence = confidence
        self.first_frame = frame_idx
        self.last_frame = frame_idx
        self.hits = 1
        self.time_since_update = 0
        self.history = [bbox]

    def update(self, bbox: Dict[str, float], confidence: float, frame_idx: int):
        self.bbox = bbox
        self.confidence = max(self.confidence, confidence)
        self.last_frame = frame_idx
        self.hits += 1
        self.time_since_update = 0
        self.history.append(bbox)
        if len(self.history) > 30:
            self.history.pop(0)

class RoadHazardTracker:
    def __init__(self, iou_threshold: float = 0.35, max_disappeared: int = 10, dist_threshold: float = 0.25):
        self.iou_threshold = iou_threshold
        self.max_disappeared = max_disappeared
        self.dist_threshold = dist_threshold  # Normalized centroid distance
        self.next_track_id = 1
        self.tracks: Dict[int, TrackedObject] = {}

    @staticmethod
    def calculate_iou(boxA: Dict[str, float], boxB: Dict[str, float]) -> float:
        # Determine coordinates of intersection rectangle
        xA = max(boxA["x1"], boxB["x1"])
        yA = max(boxA["y1"], boxB["y1"])
        xB = min(boxA["x2"], boxB["x2"])
        yB = min(boxA["y2"], boxB["y2"])

        inter_width = max(0.0, xB - xA)
        inter_height = max(0.0, yB - yA)
        inter_area = inter_width * inter_height

        # Calculate area of both bounding boxes
        boxA_area = max(0.0, (boxA["x2"] - boxA["x1"]) * (boxA["y2"] - boxA["y1"]))
        boxB_area = max(0.0, (boxB["x2"] - boxB["x1"]) * (boxB["y2"] - boxB["y1"]))

        union_area = boxA_area + boxB_area - inter_area
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    @staticmethod
    def calculate_centroid_dist(boxA: Dict[str, float], boxB: Dict[str, float], img_w: float = 1.0, img_h: float = 1.0) -> float:
        cA_x = (boxA["x1"] + boxA["x2"]) / (2.0 * img_w)
        cA_y = (boxA["y1"] + boxA["y2"]) / (2.0 * img_h)
        cB_x = (boxB["x1"] + boxB["x2"]) / (2.0 * img_w)
        cB_y = (boxB["y1"] + boxB["y2"]) / (2.0 * img_h)
        return math.sqrt((cA_x - cB_x) ** 2 + (cA_y - cB_y) ** 2)

    def update(
        self, 
        detections: List[Dict[str, Any]], 
        frame_idx: int,
        img_width: int = 640,
        img_height: int = 480
    ) -> List[Dict[str, Any]]:
        """
        Updates active tracks with new frame detections.
        Matches detections to existing tracks via IoU and Centroid proximity.
        Returns list of matched detections with assigned 'track_id'.
        """
        # Increment time_since_update for existing tracks
        for track in self.tracks.values():
            track.time_since_update += 1

        matched_det_indices = set()
        matched_track_ids = set()
        results = []

        # Match existing tracks with detections of same class
        for track_id, track in list(self.tracks.items()):
            best_iou = 0.0
            best_det_idx = -1

            for idx, det in enumerate(detections):
                if idx in matched_det_indices:
                    continue
                if det.get("class_name") != track.class_name:
                    continue

                iou = self.calculate_iou(track.bbox, det["bbox"])
                dist = self.calculate_centroid_dist(track.bbox, det["bbox"], img_width, img_height)

                # Combine IoU with Centroid Distance fallback
                if iou >= self.iou_threshold or (dist <= self.dist_threshold and iou > 0.1):
                    if iou > best_iou or (best_det_idx == -1 and dist <= self.dist_threshold):
                        best_iou = iou
                        best_det_idx = idx

            if best_det_idx >= 0:
                matched_det_indices.add(best_det_idx)
                matched_track_ids.add(track_id)
                det = detections[best_det_idx]
                track.update(det["bbox"], det["confidence"], frame_idx)

                det_copy = dict(det)
                det_copy["track_id"] = track_id
                det_copy["is_new_track"] = False
                det_copy["track_hits"] = track.hits
                results.append(det_copy)

        # Create new tracks for unmatched detections
        for idx, det in enumerate(detections):
            if idx not in matched_det_indices:
                new_id = self.next_track_id
                self.next_track_id += 1

                new_track = TrackedObject(
                    track_id=new_id,
                    class_name=det["class_name"],
                    bbox=det["bbox"],
                    confidence=det["confidence"],
                    frame_idx=frame_idx
                )
                self.tracks[new_id] = new_track

                det_copy = dict(det)
                det_copy["track_id"] = new_id
                det_copy["is_new_track"] = True
                det_copy["track_hits"] = 1
                results.append(det_copy)

        # Remove stale tracks that disappeared
        stale_ids = [
            t_id for t_id, track in self.tracks.items()
            if track.time_since_update > self.max_disappeared
        ]
        for t_id in stale_ids:
            del self.tracks[t_id]

        return results
