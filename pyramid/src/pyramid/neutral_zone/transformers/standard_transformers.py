from pyramid.model.numeric_events import NumericEventList
from pyramid.neutral_zone.transformers.transformers import Transformer


class OffsetThenGain(Transformer):
    """Apply an offset, then gain, to values in a Pyramid type like NumericEventList."""

    def __init__(self, offset: float = 0.0, gain: float = 1.0, value_index: int = 0, **kwargs) -> None:
        self.offset = offset
        self.gain = gain
        self.value_index = value_index

    def __eq__(self, other: object) -> bool:
        """Compare transformers field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return (
                self.offset == other.offset
                and self.gain == other.gain
                and self.value_index == other.value_index
            )
        else:  # pragma: no cover
            return False

    def transform(self, data: NumericEventList) -> NumericEventList:
        data.apply_offset_then_gain(self.offset, self.gain, self.value_index)
        return data


class FilterRange(Transformer):
    """Filter values, taking only those in the half open interval [min, max), from a Pyramid type like NumericEventList."""

    def __init__(self, min: float = None, max: float = None, value_index: int = 0, **kwargs) -> None:
        self.min = min
        self.max = max
        self.value_index = value_index

    def transform(self, data: NumericEventList) -> NumericEventList:
        return data.copy_value_range(self.min, self.max, self.value_index)
