from pathlib import Path
import numpy as np

from pytest import fixture

from pyramid.model.events import NumericEventList
from pyramid.model.signals import SignalChunk
from pyramid.neutral_zone.readers.plexon import PlexonPlxReader


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_default_to_all_channels(fixture_path):
    plx_file = Path(fixture_path, "plexon", "16sp_lfp_with_2coords.plx")
    with PlexonPlxReader(plx_file) as reader:
        initial = reader.get_initial()

    assert reader.raw_reader.plx_stream is None

    # The example .plx file has:
    #   - 64 spike channels
    #   - 49 event channels
    #   - 64 "WB" signal channels
    #   - 64 "SPK" signal channels
    #   - 64 "FP" signal channels
    assert len(initial) == 64 + 49 + 64 + 64 + 64
    assert isinstance(initial["SPK01_spikes"], NumericEventList)
    assert isinstance(initial["SPK64_spikes"], NumericEventList)
    assert isinstance(initial["Event01"], NumericEventList)
    assert isinstance(initial["Event46"], NumericEventList)
    assert isinstance(initial["Start"], NumericEventList)
    assert isinstance(initial["Stop"], NumericEventList)
    assert isinstance(initial["Strobed"], NumericEventList)
    assert isinstance(initial["WB01"], SignalChunk)
    assert isinstance(initial["WB64"], SignalChunk)
    assert isinstance(initial["SPK01"], SignalChunk)
    assert isinstance(initial["SPK64"], SignalChunk)
    assert isinstance(initial["FP01"], SignalChunk)
    assert isinstance(initial["FP64"], SignalChunk)


def test_read_whole_file(fixture_path):
    plx_file = Path(fixture_path, "plexon", "16sp_lfp_with_2coords.plx")
    with PlexonPlxReader(plx_file) as reader:
        initial = reader.get_initial()
        next = reader.read_next()
        while next is not None:
            for key in next:
                assert key in initial
            next = reader.read_next()
