import datetime
from typing import Any

from .base import Type
from .time import TimeRange
from ..base import prop


class Metric(Type):
    """Metric type"""

    title: str = prop(doc='Name of the metric')
    value: Any = prop(doc='Value of the metric')
    generator: Any = prop(doc='Generator used to create the metric')


class PlottingMetric(Metric):
    """Metric which is to be visualised as plot, value should be a pyplot
     figure"""


class SingleTimeMetric(Metric):
    """Metric for a specific timestamp"""

    timestamp: datetime.datetime = prop(
        default=None, doc="Timestamp of the state. Default None.")


class TimeRangeMetric(Metric):
    """ Metric for a range of times (e.g. for example an entire run)"""

    time_range: TimeRange = prop(
        default=None,
        doc="Time range over which metric assessment will be conducted over. Default is None")


class TimeRangePlottingMetric(TimeRangeMetric, PlottingMetric):
    """Plotting metric covering a period of time"""


class SingleTimePlottingMetric(SingleTimeMetric, PlottingMetric):
    """Plotting metric covering a specific timestamp"""
