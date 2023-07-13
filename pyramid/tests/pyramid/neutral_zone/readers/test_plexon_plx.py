from datetime import datetime
from pathlib import Path
import json

from pytest import fixture

import numpy as np

from pyramid.neutral_zone.readers.plexon import RawPlexonReader

# Load some Plexon .plx files and verify the contents.
# The .plx files and expected contents are from Plexon's "OmniPlex and MAP Offline SDK Bundle" / "Matlab Offline Files SDK".
# For details see: pyramid/tests/pyramid/neutral_zone/readers/fixture_files/plexon/README.txt


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def assert_global_header(header: dict, expected: dict) -> None:
    assert header['MagicNumber'] == 1480936528
    assert header['Version'] == expected['Version']
    assert header['Comment'] == expected['Comment']
    assert header['ADFrequency'] in expected['adfreqs']
    assert header['NumDSPChannels'] == len(expected['spk_names'])
    assert header['NumEventChannels'] == len(expected['evnames'])
    assert header['NumSlowChannels'] == len(expected['adnames'])
    assert header['NumPointsWave'] == expected['NPW']
    assert header['NumPointsPreThr'] == expected['PreThresh']
    date = datetime(header['Year'], header['Month'], header['Day'], header['Hour'], header['Minute'], header['Second'])
    expected_date = datetime.strptime(expected['DateTime'].strip(), '%m/%d/%Y %H:%M:%S')
    assert date == expected_date
    assert header['WaveformFreq'] == expected['Freq']
    assert header['LastTimestamp'] / header['WaveformFreq'] == expected['Duration']
    assert header['Trodalness'] == expected['Trodalness']
    assert header['BitsPerSpikeSample'] == expected['SpikeADResBits']
    assert header['BitsPerSlowSample'] == expected['SlowADResBits']
    assert header['SpikeMaxMagnitudeMV'] == expected['SpikePeakV']
    assert header['SlowMaxMagnitudeMV'] == expected['SlowPeakV']

    # Expected timestamp and waveform counts are weirdly shaped but the numbers are there.
    # To select and compare relevant chunks of data we need to know:
    #  - channels are one-based, with nothing in channel 0
    #  - each channel has up to 5 units, as far as this global header knows
    channel_range = range(header["NumDSPChannels"] + 1)
    unit_range = range(5)

    ts_counts = header['TSCounts'][channel_range, :]
    expected_ts_counts = np.array(expected['tscounts'])[unit_range, :].T
    assert np.array_equal(ts_counts, expected_ts_counts)

    wf_counts = header['WFCounts'][channel_range, :]
    expected_wf_counts = np.array(expected['wfcounts'])[unit_range, :].T
    assert np.array_equal(wf_counts, expected_wf_counts)

    # Expected event counts are also weirdly shaped.
    # To build a comparable array of counts we need to know:
    #  - expected data were "pre-selected" out of a big array of 512
    #  - starting at index 300, this same array records continuous channel samples, not event samples!
    ev_counts = header['EVCounts']
    expected_ev_counts = np.zeros((512,), dtype=ev_counts.dtype)
    expected_ev_chans = expected['evchans']
    expected_chan_ev_counts = np.array(expected['evcounts'])
    expected_ev_counts[expected_ev_chans] = expected_chan_ev_counts
    expected_slow_counts = expected["slowcounts"]
    slow_range = range(300, 300 + len(expected_slow_counts))
    expected_ev_counts[slow_range] = expected_slow_counts
    assert np.array_equal(ev_counts, expected_ev_counts)


def assert_dsp_channel_headers(headers: list[dict], expected: dict) -> None:
    assert len(headers) == len(expected['spk_names'])
    for index, header in enumerate(headers):
        assert header["Name"] == expected["spk_names"][index].replace('\x00', '')
        assert header["Channel"] == index + 1
        assert header["SIG"] == index + 1
        assert header["Gain"] == expected["spk_gains"][index]
        assert header["Filter"] == expected["spk_filters"][index]
        assert header["Threshold"] == expected["spk_threshs"][index]
        assert header["Method"] in {1, 2}


def assert_event_channel_headers(headers: list[dict], expected: dict) -> None:
    assert len(headers) == len(expected['evnames'])
    for index, header in enumerate(headers):
        assert header["Name"] == expected['evnames'][index].replace('\x00', '')
        assert header["Channel"] == expected['evchans'][index]


def assert_slow_channel_headers(headers: list[dict], expected: dict) -> None:
    assert len(headers) == len(expected['adnames'])
    for index, header in enumerate(headers):
        assert header["Name"] == expected['adnames'][index].replace('\x00', '')
        assert header["Channel"] == index
        assert header["ADFreq"] == expected["adfreqs"][index]
        assert header["Gain"] == expected["adgains"][index]
        assert header["Enabled"] in {0, 1}
        assert header["PreampGain"] > 0
        assert header["SpikeChannel"] <= len(expected['spk_names'])


# TODO: block type conversion and comparison to expected
def scan_blocks(raw_reader: RawPlexonReader):
    previous_timestamps = {
        1: {},
        4: {},
        5: {},
    }
    block = raw_reader.next_block()
    while block:
        if block["channel"] not in previous_timestamps[block["type"]]:
            previous_timestamps[block["type"]][block["channel"]] = -1

        block_timestamp = block["timestamp"]
        assert block_timestamp > previous_timestamps[block["type"]][block["channel"]]
        previous_timestamps[block["type"]][block["channel"]] = block_timestamp
        block = raw_reader.next_block()


def test_opx141spkOnly004(fixture_path):
    plx_file = Path(fixture_path, "plexon", "opx141spkOnly004.plx")
    json_file = Path(fixture_path, "plexon", "opx141spkOnly004.json")

    with open(json_file) as f:
        expected = json.load(f)
        with RawPlexonReader(plx_file) as raw_reader:
            assert_global_header(raw_reader.global_header, expected)
            assert_dsp_channel_headers(raw_reader.dsp_channel_headers, expected)
            assert_event_channel_headers(raw_reader.event_channel_headers, expected)
            assert_slow_channel_headers(raw_reader.slow_channel_headers, expected)
            scan_blocks(raw_reader)

def test_opx141ch1to3analogOnly003(fixture_path):
    plx_file = Path(fixture_path, "plexon", "opx141ch1to3analogOnly003.plx")
    json_file = Path(fixture_path, "plexon", "opx141ch1to3analogOnly003.json")

    with open(json_file) as f:
        expected = json.load(f)
        with RawPlexonReader(plx_file) as raw_reader:
            assert_global_header(raw_reader.global_header, expected)
            assert_dsp_channel_headers(raw_reader.dsp_channel_headers, expected)
            assert_event_channel_headers(raw_reader.event_channel_headers, expected)
            assert_slow_channel_headers(raw_reader.slow_channel_headers, expected)
            scan_blocks(raw_reader)


def test_16sp_lfp_with_2coords(fixture_path):
    plx_file = Path(fixture_path, "plexon", "16sp_lfp_with_2coords.plx")
    json_file = Path(fixture_path, "plexon", "16sp_lfp_with_2coords.json")

    with open(json_file) as f:
        expected = json.load(f)
        with RawPlexonReader(plx_file) as raw_reader:
            assert_global_header(raw_reader.global_header, expected)
            assert_dsp_channel_headers(raw_reader.dsp_channel_headers, expected)
            assert_event_channel_headers(raw_reader.event_channel_headers, expected)
            assert_slow_channel_headers(raw_reader.slow_channel_headers, expected)
            scan_blocks(raw_reader)
