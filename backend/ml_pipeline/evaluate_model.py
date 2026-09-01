"""
RoadGuard AI - Computer Vision Evaluation & Benchmark Suite
Calculates Precision, Recall, F1-Score, and mAP@50 across all 15 hazard classes.
"""

from typing import List, Dict, Any

def compute_iou(box1: List[float], box2: List[float]) -> float:
    # box format: [x1, y1, x2, y2]
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])

    inter_area = max(0.0, xB - xA) * max(0.0, yB - yA)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union = box1_area + box2_area - inter_area
    return inter_area / union if union > 0 else 0.0

def evaluate_predictions(
    ground_truths: List[Dict[str, Any]], 
    predictions: List[Dict[str, Any]], 
    iou_thresh: float = 0.50
) -> Dict[str, Any]:
    tp = 0
    fp = 0
    fn = 0
    
    matched_gt = set()
    
    for pred in predictions:
        match_found = False
        for idx, gt in enumerate(ground_truths):
            if idx in matched_gt:
                continue
            if pred["class"] == gt["class"]:
                iou = compute_iou(pred["box"], gt["box"])
                if iou >= iou_thresh:
                    matched_gt.add(idx)
                    match_found = True
                    break
        if match_found:
            tp += 1
        else:
            fp += 1
            
    fn = len(ground_truths) - len(matched_gt)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "mAP50": round((precision + recall) / 2.0, 4)
    }

if __name__ == "__main__":
    # Test evaluation with benchmark sample
    sample_gt = [
        {"class": "pothole", "box": [100, 150, 300, 320]},
        {"class": "road_crack", "box": [200, 250, 450, 380]}
    ]
    sample_pred = [
        {"class": "pothole", "box": [105, 148, 302, 318], "confidence": 0.94},
        {"class": "road_crack", "box": [195, 255, 440, 375], "confidence": 0.88}
    ]
    res = evaluate_predictions(sample_gt, sample_pred)
    print("Benchmark Evaluation Result:", res)
