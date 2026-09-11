
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class WebElement:
    id: str
    tag_name: str
    element_id: str
    classes: str
    text: str
    clickable: bool
    href: str = ""
    input_type: str = ""
    xpath: str = ""

@dataclass
class WebPage:
    page_id: int
    url: str
    title: str
    elements: List[WebElement]
    
    def to_html(self) -> str:
        html = f"URL: {self.url}\nTitle: {self.title}\nPage ID: {self.page_id}\n\n"
        for elem in self.elements:
            tag = self._get_html_tag(elem)
            attrs = f'id="{elem.id}" class="{elem.classes}" element-id="{elem.element_id}"'
            if elem.href:
                attrs += f' href="{elem.href}"'
            html += f'<{tag} {attrs}>{elem.text[:50]}</{tag}>\n'
        return html
    
    def _get_html_tag(self, element: WebElement) -> str:
        if element.tag_name == "input":
            return "input"
        elif element.tag_name == "button" or element.clickable:
            return "button"
        elif element.tag_name == "a":
            return "link"
        return "element"

@dataclass
class PageCluster:
    root_page: WebPage
    pages: List[WebPage] = field(default_factory=list)
    summary: str = ""
    functionalities: Dict[str, str] = field(default_factory=dict)
    importance_rank: int = 0