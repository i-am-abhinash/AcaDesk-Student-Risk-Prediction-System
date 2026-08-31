import numpy as np

class MarkingSchemeDetector:
    def detect(self, all_academic_records: list[dict]) -> dict:
        """
        Analyzes the distribution of marks and scores in the college's actual data
        to detect the scale of each numeric column and the typical pass/fail boundary.
        """
        # Look for standard numerical columns used in prediction
        cols = ['internal_marks', 'attendance_pct', 'cgpa', 'mid_exam_score', 
                'lab_performance', 'assignment_marks', 'tenth_percentage', 
                'inter_percentage', 'diploma_percentage', 'backlogs']
                
        data = {c: [] for c in cols}
        
        for record in all_academic_records:
            for c in cols:
                # The data might be in nested dictionaries if mapped differently,
                # but we assume flat dictionaries mapped by AdaptiveLabelGenerator / CollegeModelTrainer
                if c in record and record[c] is not None:
                    try:
                        val = float(record[c])
                        data[c].append(val)
                    except (ValueError, TypeError):
                        pass
                        
        scheme = {}
        for c, values in data.items():
            if not values:
                continue
            
            arr = np.array(values)
            # Filter out extreme negatives for scale detection
            arr = arr[arr >= 0]
            if len(arr) == 0:
                continue
                
            scheme[c] = self._detect_scale(c, arr.tolist())
            
        return scheme

    def _detect_scale(self, col_name: str, values: list) -> dict:
        """
        Detects the scale and threshold for a specific column.
        The pass threshold is detected as the value at the 15th percentile 
        of the distribution.
        """
        arr = np.array(values)
        v_max = np.max(arr)
        v_min = np.min(arr)
        
        # 15th percentile represents the natural clustering point between 
        # students who passed and those who failed in historical data.
        p_15 = np.percentile(arr, 15)  
        
        scale = "unknown"
        detected_max = v_max
        
        # Backlogs are a special case (count, not scale)
        if col_name == 'backlogs':
            return {
                "detected_max": float(v_max),
                "detected_min": float(v_min),
                "danger_threshold": 1.0 if v_max > 0 else 0.0, # 1 backlog is danger
                "scale": "count",
                "normalized_pass_pct": 0.0
            }
            
        if col_name == 'cgpa':
            if v_max <= 4.5:
                scale = "4_point"
                detected_max = 4.0 if v_max <= 4.0 else 4.5
            elif v_max <= 5.5:
                scale = "5_point"
                detected_max = 5.0
            elif v_max <= 7.5:
                scale = "7_point"
                detected_max = 7.0
            elif v_max <= 10.5:
                scale = "10_point"
                detected_max = 10.0
            else:
                scale = "percentage"
                detected_max = 100.0
        elif col_name in ['attendance_pct', 'tenth_percentage', 'inter_percentage', 'diploma_percentage']:
            scale = "percentage"
            detected_max = 100.0
        else:
            # Marks or scores
            if v_max <= 12:
                scale = "out_of_10"
                detected_max = 10.0
            elif v_max <= 22:
                scale = "out_of_20"
                detected_max = 20.0
            elif 23 <= v_max <= 32:
                scale = "out_of_30"
                detected_max = 30.0
            elif 38 <= v_max <= 42:
                scale = "out_of_40"
                detected_max = 40.0
            elif 48 <= v_max <= 52:
                scale = "out_of_50"
                detected_max = 50.0
            elif 58 <= v_max <= 62:
                scale = "out_of_60"
                detected_max = 60.0
            elif 73 <= v_max <= 77:
                scale = "out_of_75"
                detected_max = 75.0
            elif 95 <= v_max <= 105:
                scale = "percentage"
                detected_max = 100.0
            else:
                scale = f"custom_max_{int(v_max)}"
                detected_max = float(v_max)
                
        # Handle cases where data anomalously exceeds the theoretical max
        if v_max > detected_max and detected_max > 0:
            detected_max = v_max

        danger_threshold = p_15
        
        # Override with sensible bounds if distribution is heavily skewed
        if col_name == 'attendance_pct' and danger_threshold < 60:
            danger_threshold = 65.0
        
        return {
            "detected_max": float(detected_max),
            "detected_min": float(v_min),
            "danger_threshold": float(danger_threshold),
            "scale": scale,
            "normalized_pass_pct": float((danger_threshold / detected_max) * 100) if detected_max > 0 else 0.0
        }

    def normalize_to_percentage(self, value: float, scheme: dict) -> float:
        """
        Converts any value to 0-100 percentage scale using the detected scheme.
        """
        if not scheme or "detected_max" not in scheme or scheme["detected_max"] == 0:
            return 0.0
        
        norm = (value / scheme["detected_max"]) * 100.0
        return max(0.0, min(100.0, norm))
