from LLMDroid.dataObject import PageCluster, WebPage, WebElement
from typing import Dict, List, Tuple
from collections import defaultdict


class WebPageManager:    
    def __init__(self, similarity_threshold: float = 0.6):
        self.page_clusters: List[PageCluster] = []
        self.similarity_threshold = similarity_threshold
        self.page_transitions: Dict[Tuple[int, int], int] = defaultdict(int)
        self.page_id_counter = 0
    
    def add_page(self, page: WebPage) -> PageCluster:
        # Find matching cluster
        for cluster in self.page_clusters:
            similarity = self._calculate_similarity(page, cluster.root_page)
            if similarity >= self.similarity_threshold:
                cluster.pages.append(page)
                return cluster
        
        # Create new cluster
        new_cluster = PageCluster(root_page=page, pages=[page])
        self.page_clusters.append(new_cluster)
        return new_cluster
    
    def _calculate_similarity(self, page1: WebPage, page2: WebPage) -> float:
        # Simple URL-based similarity for web pages
        if page1.url.split('?')[0] == page2.url.split('?')[0]:
            return 0.8
        
        # Element-based similarity
        elements1 = set(self._element_signature(e) for e in page1.elements)
        elements2 = set(self._element_signature(e) for e in page2.elements)
        
        if len(elements1) + len(elements2) == 0:
            return 0.0
        
        intersection = len(elements1 & elements2)
        return 2 * intersection / (len(elements1) + len(elements2))
    
    def _element_signature(self, element: WebElement) -> str:
        """Create unique signature for an element"""
        return f"{element.tag_name}|{element.element_id}|{element.classes}|{element.clickable}"
    
    def record_transition(self, from_page_id: int, to_page_id: int):
        """Record page transition"""
        self.page_transitions[(from_page_id, to_page_id)] += 1
    
    def get_next_page_id(self) -> int:
        """Get next page ID"""
        self.page_id_counter += 1
        return self.page_id_counter