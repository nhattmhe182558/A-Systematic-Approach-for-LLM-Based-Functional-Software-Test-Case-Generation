from typing import List, Set, Dict
import math

class CoverageMonitor:    
    def __init__(self, window_size: int = 20, initial_threshold: float = 0.05):
        self.coverage_history: List[float] = []
        self.growth_rates: List[float] = []
        self.window_size = window_size
        self.threshold = initial_threshold
        self.min_threshold = 0.01
        self.unique_pages: Set[str] = set()
        self.interactions_count = 0
    
    def add_coverage(self, page_url: str) -> bool:
        self.interactions_count += 1
        self.unique_pages.add(page_url)
        
        # Calculate coverage as percentage of unique pages explored
        coverage = len(self.unique_pages) / max(self.interactions_count, 1)
        self.coverage_history.append(coverage)
        
        if len(self.coverage_history) < 2:
            return False
        
        # Calculate growth rate
        prev_coverage = self.coverage_history[-2]
        if prev_coverage > 0:
            growth_rate = (coverage - prev_coverage) / prev_coverage
            self.growth_rates.append(growth_rate)
            
            # Update dynamic threshold
            self._update_threshold(growth_rate)
            
            # Check if in low growth state
            if len(self.growth_rates) >= self.window_size:
                recent_rates = self.growth_rates[-self.window_size:]
                return all(rate < self.threshold for rate in recent_rates)
        
        return False
    
    def _update_threshold(self, current_growth: float):
        """Dynamically adjust threshold using exponential function"""
        if len(self.growth_rates) < 2:
            return
        
        avg_growth = sum(self.growth_rates) / len(self.growth_rates)
        delta = current_growth - avg_growth
        
        # Update threshold: T_n = T_{n-1} * e^{delta}
        self.threshold = self.threshold * math.exp(delta)
        
        # Apply minimum threshold
        self.threshold = max(self.threshold, self.min_threshold)
    
    def get_stats(self) -> Dict:
        """Get coverage statistics"""
        return {
            "unique_pages": len(self.unique_pages),
            "total_interactions": self.interactions_count,
            "current_coverage": self.coverage_history[-1] if self.coverage_history else 0,
            "current_threshold": self.threshold
        }
