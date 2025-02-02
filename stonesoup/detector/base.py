from ..base import prop
from ..reader import DetectionReader, SensorDataReader


class Detector(DetectionReader):
    """Detector base class

    A Detector processes :class:`~.SensorData` to generate :class:`~.Detection`
    data.
    """

    sensor: SensorDataReader = prop(doc="Source of sensor data")
