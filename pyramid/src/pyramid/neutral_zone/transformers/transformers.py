from pyramid.model.model import DynamicImport
from pyramid.model.numeric_events import NumericEventList


class Transformer(DynamicImport):
    """Transform values and/or type of Pyramid data, like NumericEventList."""

    def transform(self, data: NumericEventList) -> NumericEventList:
        raise NotImplementedError  # pragma: no cover
