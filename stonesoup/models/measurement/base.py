from abc import abstractmethod, ABC
from collections.abc import Sequence

from ..base import Model
from ...base import prop


class MeasurementModel(Model, ABC):
    """Measurement Model base class"""

    ndim_state: int = prop(doc="Number of state dimensions")
    mapping: Sequence[int] = prop(doc="Mapping between measurement and state dims")

    @property
    def ndim(self) -> int:
        return self.ndim_meas

    @property
    @abstractmethod
    def ndim_meas(self) -> int:
        """Number of measurement dimensions"""
        pass
