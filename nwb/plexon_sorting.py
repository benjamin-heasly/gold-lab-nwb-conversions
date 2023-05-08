import numpy as np

from pynwb import NWBFile

from spikeinterface.core import BaseSorting
from spikeinterface.extractors.neoextractors.neobaseextractor import NeoBaseSortingExtractor, NeoSortingSegment
from neo.rawio import PlexonRawIO
from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface


class PlexonSortingExtractor(NeoBaseSortingExtractor):
    def __init__(
            self,
            plexon_raw_io: PlexonRawIO,
            block_index: int = 0,
            use_natural_unit_ids: bool = False
    ):
        # We already have the neo reader we need, so just assign it to the expected field.
        # This skips the call to _NeoBaseExtractor.__init__()
        # Which normally forces us to create a new extractor based on hard-coded NeoRawIOClass string.
        # We don't need this and we don't want to wait arout to parse the Plexon header again!
        self.neo_reader = plexon_raw_io
        self.block_index = block_index

        # The rest of this code is from NeoBaseRecordingExtractor.__init__(),
        # Following the call to _NeoBaseExtractor.__init__().
        # This kind of sucks, we'd prefer to compose an extractor from explicit components!
        # Just pass the things that the thing needs to the thing's constructor!
        # Stop being magic AKA guessing.
        sampling_frequency = plexon_raw_io._global_ssampling_rate
        if sampling_frequency is None:
            sampling_frequency, stream_id = self._auto_guess_sampling_frequency()
            stream_index = np.where(self.neo_reader.header["signal_streams"]["id"] == stream_id)[0][0]
        else:
            stream_index = None

        # Get the stream index corresponding to the extracted frequency
        spike_channels = self.neo_reader.header['spike_channels']
        self.use_natural_unit_ids = use_natural_unit_ids
        if use_natural_unit_ids:
            unit_ids = spike_channels['id']
            assert np.unique(unit_ids).size == unit_ids.size, 'unit_ids is have duplications'
        else:
            # use interger based unit_ids
            unit_ids = np.arange(spike_channels.size, dtype='int64')

        BaseSorting.__init__(self, sampling_frequency, unit_ids)

        nseg = self.neo_reader.segment_count(block_index=self.block_index)
        for segment_index in range(nseg):
            #     handle_spike_frame_directly = True
            t_start = None
            sorting_segment = NeoSortingSegment(self.neo_reader, self.block_index, segment_index,
                                                self.use_natural_unit_ids, t_start,
                                                sampling_frequency)
            self.add_sorting_segment(sorting_segment)


class PlexonSortingInterface(BaseSortingExtractorInterface):
    def Extractor(
            self,
            plexon_raw_io: PlexonRawIO,
            block_index: int = 0,
            use_natural_unit_ids: bool = False
    ):
        sorting_extractor = PlexonSortingExtractor(plexon_raw_io, block_index, use_natural_unit_ids)
        return sorting_extractor

    def __init__(
        self,
        plexon_raw_io: PlexonRawIO,
        block_index: int = 0,
        use_natural_unit_ids: bool = False,
        verbose: bool = True
    ):
        super().__init__(
            plexon_raw_io=plexon_raw_io,
            block_index=block_index,
            use_natural_unit_ids=use_natural_unit_ids,
            verbose=verbose
        )


def add_plexon_sorting(
    nwb_file: NWBFile,
    plexon_raw_io: PlexonRawIO
):
    """Add manually sorted Plexon units to a working NWB file in memory.

    It seems like this one doesn't accept a starting_time.
    """

    print(f"Reading Plexon sorting data from: {plexon_raw_io.filename}")
    sorting_interface = PlexonSortingInterface(plexon_raw_io=plexon_raw_io)
    sorting_interface.run_conversion(nwbfile=nwb_file, metadata={}, overwrite=False)
