from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseCrawler(ABC):
    def __init__(self, page):
        self.page = page

    @abstractmethod
    def crawl(self, url: str, latest_index: int) -> tuple[List[Dict[str, Any]], int]:
        """
        특정 사이트를 크롤링하여 새로운 공고 리스트와 최신 인덱스를 반환해야 함
        """
        pass
    
    @abstractmethod
    def parse_detail(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        상세 페이지에 들어가서 본문, 실제 지원 링크 등을 가져옴
        """
        pass