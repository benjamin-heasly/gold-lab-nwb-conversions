from pathlib import Path
import numpy as np

from pytest import fixture
import cProfile, pstats

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


def test_read_whole_plx_file(fixture_path):
    plx_file = Path(fixture_path, "plexon", "16sp_lfp_with_2coords.plx")
    with PlexonPlxReader(plx_file) as reader:

        # The first result should be the "Start" event.
        next = reader.read_next()
        assert next == {
            "Start": NumericEventList(np.array([0.0, 0.0]))
        }

        # Sample arbitrary results throughout the file, every 10000 blocks.
        # These happen to touch on all three block types: spike events, other events, and signal chunks.

        while reader.raw_reader.block_count < 10000:
            next = reader.read_next()
        assert next == {
            "FP07": SignalChunk(
                sample_data=np.array([
                    0.5987548828125,
                    0.5780029296875,
                    0.5872344970703125,
                    0.604705810546875,
                    0.6003570556640625,
                    0.578460693359375
                ]),
                sample_frequency=1000,
                first_sample_time=3.160525,
                channel_ids=[134]
            )
        }

        while reader.raw_reader.block_count < 20000:
            next = reader.read_next()
        assert next == {
            "FP13":
            SignalChunk(
                sample_data=np.array([
                    -0.01800537109375,
                    -0.020294189453125,
                    -0.0335693359375,
                    -0.0395965576171875,
                    -0.03997802734375,
                    -0.042877197265625,
                    -0.047760009765625
                ]),
                sample_frequency=1000,
                first_sample_time=6.116525,
                channel_ids=[140]
            )
        }

        while reader.raw_reader.block_count < 30000:
            next = reader.read_next()
        assert next == {
            "FP11":
            SignalChunk(
                sample_data=np.array([
                    -0.041961669921875,
                    -0.0548553466796875,
                    -0.06195068359375,
                    -0.0603485107421875,
                    -0.051727294921875,
                    -0.047149658203125
                ]),
                sample_frequency=1000,
                first_sample_time=8.973525,
                channel_ids=[138]
            )
        }

        while reader.raw_reader.block_count < 40000:
            next = reader.read_next()
        assert next == {
            "SPK03_spikes": NumericEventList(np.array([12.069825, 3.0,  0.0]))
        }

        while reader.raw_reader.block_count < 50000:
            next = reader.read_next()
        assert next == {
            "FP01":
            SignalChunk(
                sample_data=np.array([
                    -0.1238250732421875,
                    -0.1308441162109375,
                    -0.1483154296875,
                    -0.1685333251953125,
                    -0.1929473876953125,
                    -0.2101898193359375
                ]),
                sample_frequency=1000,
                first_sample_time=15.229525,
                channel_ids=[128]
            )
        }

        # The test file should have 52084 blocks.
        while reader.raw_reader.block_count < 52084:
            next = reader.read_next()

        # The last result should be the "Stop" event.
        assert next == {
            "Stop": NumericEventList(np.array([16.12205, 0.0]))
        }

        # Now read_next() should do nothing.
        assert reader.raw_reader.block_count == 52084
        assert reader.read_next() is None
        assert reader.raw_reader.block_count == 52084
        assert reader.read_next() is None
        assert reader.raw_reader.block_count == 52084


# hatch run test:cov -k test_profile_read_whole_plx_file -s
def test_profile_read_whole_plx_file(fixture_path):
    plx_file = Path(fixture_path, "plexon", "16sp_lfp_with_2coords.plx")
    with PlexonPlxReader(plx_file) as reader:
        with cProfile.Profile() as profiler:
            next = reader.read_next()
            while next is not None:
                next = reader.read_next()
            stats = pstats.Stats(profiler).sort_stats(pstats.SortKey.TIME)
            stats.print_stats()
