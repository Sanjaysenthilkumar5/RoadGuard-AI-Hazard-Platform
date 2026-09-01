import pytest
from app.cv_service.tracker import RoadHazardTracker
from app.cv_service.duplicate_filter import haversine_distance_meters

def test_object_tracking_across_frames():
    tracker = RoadHazardTracker(iou_threshold=0.30)
    
    # Frame 1 detection
    frame1_dets = [
        {"class_name": "pothole", "bbox": {"x1": 200, "y1": 200, "x2": 300, "y2": 300}, "confidence": 0.90}
    ]
    res1 = tracker.update(frame1_dets, frame_idx=1)
    assert len(res1) == 1
    track_id = res1[0]["track_id"]
    assert res1[0]["is_new_track"] is True
    
    # Frame 2 detection with slightly shifted bbox (moving car)
    frame2_dets = [
        {"class_name": "pothole", "bbox": {"x1": 205, "y1": 210, "x2": 308, "y2": 315}, "confidence": 0.92}
    ]
    res2 = tracker.update(frame2_dets, frame_idx=2)
    assert len(res2) == 1
    assert res2[0]["track_id"] == track_id  # Persistent ID retained!
    assert res2[0]["is_new_track"] is False
    assert res2[0]["track_hits"] == 2

def test_haversine_distance_meters():
    # San Francisco points ~ 250m apart
    lat1, lon1 = 37.7749, -122.4194
    lat2, lon2 = 37.7765, -122.4175
    dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
    assert 200.0 < dist < 300.0
    
    # Same point distance should be 0
    zero_dist = haversine_distance_meters(lat1, lon1, lat1, lon1)
    assert zero_dist < 0.01
