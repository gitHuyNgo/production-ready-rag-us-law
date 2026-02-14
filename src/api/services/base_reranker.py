from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass