from typing import Any, Self
from dataclasses import dataclass
import numpy as np

from pyramid.model.model import InteropData


@dataclass
class SignalChunk(InteropData):
    """Wrap a 2D array with a chunk of signal data where rows are samples and columns are channels."""

    sample_data: np.ndarray
    """2D array backing the signal chunk.

    signal_data must have shape (n, m) where:
     - n is the number of samples (evenly spaced in time)
     - m is the number of channels
    """

    sample_frequency: float
    """Frequency in Hz of the samples in signal_data."""

    first_sample: int
    """Index of the first sample in signal_data.
    
    The sample index should refer to the overall acquisition of which this signal chunk is a subrange.

    first_sample / sample_frequency would give the time in seconds of the first sample of this chunk.
    """

    channel_ids: list[str | int]
    """Identifiers for the channels represented in this signal chunk.
    
    channel_ids should have m elements, where m is the number of columns in signal_data.
    """

    def __eq__(self, other: object) -> bool:
        """Compare signal_data arrays as-a-whole instead of element-wise."""
        if isinstance(other, self.__class__):
            arrays_equal = (
                (self.sample_data.size == 0 and other.sample_data.size == 0)
                or np.array_equal(self.sample_data, other.sample_data)
            )
            return (
                arrays_equal
                and self.sample_frequency == other.sample_frequency
                and self.first_sample == other.first_sample
                and self.channel_ids == other.channel_ids
            )
        else:
            return False

    def copy(self) -> Self:
        return SignalChunk(
            self.sample_data.copy(),
            self.sample_frequency,
            self.first_sample,
            self.channel_ids
        )

    def to_interop(self) -> Any:
        return {
            "signal_data": self.sample_data.tolist(),
            "sample_frequency": self.sample_frequency,
            "first_sample": self.first_sample,
            "channel_ids": self.channel_ids
        }

    @classmethod
    def from_interop(cls, interop) -> Self:
        return cls(
            np.array(interop["signal_data"]),
            interop["sample_frequency"],
            interop["first_sample"],
            interop["channel_ids"]
        )

    def sample_count(self) -> int:
        """Get the number of samples in the chunk."""
        return self.sample_data.shape[0]

    def channel_count(self) -> int:
        """Get the number of channels in the chunk."""
        return self.sample_data.shape[1]

    def get_times(self) -> np.ndarray:
        """Get all the sample times, ignoring channel values."""
        sample_indexes = np.array(range(self.sample_count())) + self.first_sample
        return sample_indexes / self.sample_frequency

    def get_channel_values(self, channel_id: str | int) -> np.ndarray:
        """Get sample values from one channel, by id.
        """
        channel_index = self.channel_ids.index(channel_id)
        return self.sample_data[:, channel_index]

    def append(self, other: Self) -> None:
        """Add new samples at the end of the existing signal chunk.

        The sample_frequency, first_sample, and channel_ids of the other signal chunk object
        should all be consistent with this object -- though that is not currently enforced.

        This modifies the signal_data of this object.
        """
        self.sample_data = np.concatenate([self.sample_data, other.sample_data])

    def discard_before(self, start_time: float) -> None:
        """Discard samples that are strictly before the given start_time.

        This modifies the signal_data of this object.
        """
        rows_to_keep = self.get_times() >= start_time
        self.sample_data = self.sample_data[rows_to_keep, :]

    def shift_times(self, shift: float) -> None:
        """Shift all sample times by a constant, rounded to the nearest whole sample.

        This modifies the first_sample of this object.
        """
        shift_samples = shift * self.sample_frequency
        self.first_sample += round(shift_samples)

    def apply_offset_then_gain(self, offset: float = 0, gain: float = 1, channel_id: str | int = None) -> None:
        """Transform sample data by a constant gain and offset.

        Uses a convention of applying offset first, then gain.

        By default this modifies samples on all channels.
        Pass in a channel_id to select one specific channel.

        This modifies the signal_data in place.
        """
        if channel_id:
            channel_index = self.channel_ids.index(channel_id)
        else:
            channel_index = True

        self.event_data[:, channel_index] += offset
        self.event_data[:, channel_index] *= gain

    def copy_time_range(self, start_time: float = None, end_time: float = None) -> None:
        """Make a new signal chunk containing only samples with times in half open interval [start_time, end_time).

        Omit start_time to copy all samples strictly before end_time.
        Omit end_time to copy all samples at and after start_time.

        This returns a new SignalChunk with a copy of events in the requested range.
        """
        sample_times = self.get_times()
        if start_time:
            tail_selector = sample_times >= start_time
        else:
            tail_selector = True

        if end_time:
            head_selector = sample_times < end_time
        else:
            head_selector = True

        rows_in_range = tail_selector & head_selector
        range_sample_data = self.sample_data[rows_in_range, :]
        return SignalChunk(
            range_sample_data,
            self.sample_frequency,
            self.first_sample,
            self.channel_ids
        )


class SignalChunkBuffer():
    """Manage signal chunks from a reader within a sliding, finite time range."""

    def __init__(
        self,
        sample_frequency: float,
        channel_ids: list[str | int],
        first_sample: int = 0
    ) -> None:
        self.signal_chunk = SignalChunk(np.empty([0, len(channel_ids)]), sample_frequency, first_sample, channel_ids)

    def __eq__(self, other: object) -> bool:
        """Compare buffers field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return self.signal_chunk == other.signal_chunk
        else:  # pragma: no cover
            return False

    def start_time(self, default: float = 0.0) -> float:
        """The time of the earliest sample currently in the buffer, or the default when empty."""
        times = self.signal_chunk.get_times()
        if times.size > 0:
            return times.min()
        else:
            return default

    def end_time(self, default: float = 0.0) -> float:
        """The time of the last sample currently in the buffer, or the default when empty."""
        times = self.signal_chunk.get_times()
        if times.size > 0:
            return times.max()
        else:
            return default

    def discard_before(self, start_time: float) -> None:
        """Discard buffered samples that have times strictly less than the given start_time."""
        self.signal_chunk.discard_before(start_time)

    def append(self, new_signal_chunk: SignalChunk) -> None:
        """Add new samples to the buffer, at the end."""
        self.signal_chunk.append(new_signal_chunk)
