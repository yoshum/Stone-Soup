from typing import Union

from ..base import prop
from ..hypothesiser import Hypothesiser


class Gater(Hypothesiser):
    """Gater base class

    Gaters wrap :class:`.Hypothesiser` objects and can be used to modify (typically reduce) the
    returned hypotheses.
    """

    hypothesiser: Union[Hypothesiser, 'Gater'] = prop(
        doc="Hypothesiser or Gater that is being wrapped.")
