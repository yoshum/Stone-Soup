from ..base import Base, prop
from ..tracker import Tracker
from ..metricgenerator import MetricGenerator


class Writer(Base):
    """Writer base class"""


class MetricsWriter(Writer):
    """Metrics Writer base class.

    Writes out metrics to some form of storage for analysis.
    """

    metric_generator: MetricGenerator = prop(doc="Source of metric to be written out")


class TrackWriter(Writer):
    """Track Writer base class.

    Writes out tracks to some form of storage for analysis.
    """

    tracker: Tracker = prop(doc="Source of tracks to be written out")
