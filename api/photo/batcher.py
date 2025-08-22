"""Smart photo batching for comparison operations"""
from typing import List, Dict, Any, Tuple, Optional

class SmartPhotoBatcher:
    """Intelligently select photos for comparison when total exceeds limit"""
    
    def __init__(self, max_photos: int = 40):
        self.max_photos = max_photos
        self.reserved_recent = 5  # Always include last 5 photos
        self.reserved_baseline = 1  # Always include first photo
        
    def select_photos_for_comparison(
        self, 
        all_photos: List[Dict], 
        all_analyses: Optional[List[Dict]] = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Select most relevant photos for comparison
        Returns: (selected_photos, selection_info)
        """
        if len(all_photos) <= self.max_photos:
            return all_photos, {
                "total_photos": len(all_photos),
                "photos_shown": len(all_photos),
                "selection_method": "all_photos",
                "omitted_periods": []
            }
        
        selected = []
        selection_info = {
            "total_photos": len(all_photos),
            "photos_shown": self.max_photos,
            "selection_reasoning": [],
            "omitted_periods": []
        }
        
        # Sort photos by date
        sorted_photos = sorted(all_photos, key=lambda x: x.get('uploaded_at', ''))
        
        # Phase 1: Always include first photo (baseline)
        if sorted_photos:
            selected.append(sorted_photos[0])
            selection_info["selection_reasoning"].append("Included baseline (first) photo")
        
        # Phase 2: Always include most recent photos
        recent_photos = sorted_photos[-self.reserved_recent:]
        selected.extend(recent_photos)
        selection_info["selection_reasoning"].append(f"Included {len(recent_photos)} most recent photos")
        
        # Phase 3: Fill remaining slots intelligently
        remaining_slots = self.max_photos - len(selected)
        middle_photos = sorted_photos[1:-self.reserved_recent] if len(sorted_photos) > self.reserved_recent + 1 else []
        
        if middle_photos and remaining_slots > 0:
            # Calculate importance scores
            scored_photos = []
            for i, photo in enumerate(middle_photos):
                score = self._calculate_photo_importance(photo, i, middle_photos, all_analyses)
                scored_photos.append((score, photo))
            
            # Sort by score and take top photos
            scored_photos.sort(key=lambda x: x[0], reverse=True)
            selected_middle = [photo for score, photo in scored_photos[:remaining_slots]]
            
            # Insert in chronological order
            for photo in sorted(selected_middle, key=lambda x: x.get('uploaded_at', '')):
                # Find correct position to maintain chronological order
                insert_pos = 1  # After baseline
                for i in range(1, len(selected) - len(recent_photos)):
                    if selected[i].get('uploaded_at', '') > photo.get('uploaded_at', ''):
                        break
                    insert_pos = i + 1
                selected.insert(insert_pos, photo)
            
            selection_info["selection_reasoning"].append(
                f"Selected {len(selected_middle)} photos from middle period based on importance"
            )
        
        # Calculate omitted periods
        selection_info["omitted_periods"] = self._calculate_omitted_periods(sorted_photos, selected)
        
        return selected, selection_info
    
    def _calculate_photo_importance(
        self, 
        photo: Dict, 
        index: int, 
        all_middle_photos: List[Dict],
        all_analyses: Optional[List[Dict]]
    ) -> float:
        """Calculate importance score for a photo"""
        score = 0.0
        
        # 1. Temporal distribution - prefer evenly spaced photos
        total_photos = len(all_middle_photos)
        ideal_spacing = total_photos / (self.max_photos - self.reserved_recent - self.reserved_baseline)
        distance_from_ideal = abs(index % ideal_spacing)
        temporal_score = 100 * (1 - distance_from_ideal / ideal_spacing)
        score += temporal_score
        
        # 2. Quality score if available
        if photo.get('quality_score'):
            score += photo['quality_score'] * 0.5
        
        # 3. Check if photo has associated analysis with significant findings
        if all_analyses:
            photo_analysis = next(
                (a for a in all_analyses if photo['id'] in a.get('photo_ids', [])), 
                None
            )
            if photo_analysis:
                # High confidence changes
                if photo_analysis.get('confidence_score', 0) < 70:
                    score += 50  # Uncertain cases are important
                
                # Red flags present
                if photo_analysis.get('analysis_data', {}).get('red_flags'):
                    score += 100
                
                # Marked as significant change in comparison
                if photo_analysis.get('comparison', {}).get('trend') == 'worsening':
                    score += 80
        
        # 4. User notes or follow-up flag
        if photo.get('followup_notes'):
            score += 75
        
        return score
    
    def _calculate_omitted_periods(
        self, 
        all_photos: List[Dict], 
        selected_photos: List[Dict]
    ) -> List[Dict]:
        """Calculate time periods that were omitted from selection"""
        omitted_periods = []
        selected_dates = {p['uploaded_at'][:10] for p in selected_photos}
        
        current_gap_start = None
        for i, photo in enumerate(all_photos):
            photo_date = photo['uploaded_at'][:10]
            
            if photo_date not in selected_dates:
                if current_gap_start is None:
                    current_gap_start = photo_date
            else:
                if current_gap_start is not None:
                    # Gap ended
                    prev_photo_date = all_photos[i-1]['uploaded_at'][:10] if i > 0 else current_gap_start
                    omitted_periods.append({
                        "start": current_gap_start,
                        "end": prev_photo_date,
                        "photos_omitted": sum(
                            1 for p in all_photos 
                            if current_gap_start <= p['uploaded_at'][:10] <= prev_photo_date
                        )
                    })
                    current_gap_start = None
        
        return omitted_periods