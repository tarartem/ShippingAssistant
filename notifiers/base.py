from abc import ABC, abstractmethod
from extractors.base import ShipmentInfo

class BaseNotifier(ABC):
    @abstractmethod
    def send(self, info: ShipmentInfo) -> bool:
        pass
