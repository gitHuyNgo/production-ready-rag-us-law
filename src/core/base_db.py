from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseVectorStore(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def batch_load(self, items: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def close(self):
        pass