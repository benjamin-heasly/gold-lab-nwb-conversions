import uuid

import numpy as np

from pyramid.neutral_zone.readers.open_ephys_zmq import (
    Client,
    Server,
    format_heartbeat,
    parse_heartbeat,
    format_continuous_data,
    parse_continuous_data,
    format_event,
    parse_event,
    format_spike,
    parse_spike
)


def test_zmq_basics():
    host = '127.0.0.1'
    port = 10001

    with Server(host=host, port=port) as server:
        assert not server.poll_request()

        with Client(host=host, port=port) as client:
            assert not client.poll_reply()

            for index in range(100):
                request_at_client = [f"foo{index}", f"bar{index}", f"baz{index}"]
                client.send_request(request_at_client)
                request_at_server = server.poll_request()
                assert request_at_server == request_at_client

                reply_at_server = [f"quux{index}", f"quux{index}", f"baz{index}", f"quux{index}"]
                server.send_reply(reply_at_server)
                reply_at_client = client.poll_reply()
                assert reply_at_client == reply_at_server

    assert server.context is None
    assert client.context is None


def test_heartbeat_format():
    application = "Test"
    id = str(uuid.uuid4())
    message = format_heartbeat(uuid=id, application=application)
    heartbeat = parse_heartbeat(message)
    assert heartbeat["application"] == application
    assert heartbeat["uuid"] == id
    assert heartbeat["type"] == "heartbeat"


def test_continuous_data_format():
    data = np.arange(1000, dtype=np.float32)
    stream_name = "Test"
    channel_num = 41
    sample_num = 42
    sample_rate = 1000
    parts = format_continuous_data(data, stream_name, channel_num, sample_num, sample_rate)
    (header, data_2) = parse_continuous_data(parts)
    assert header["stream"] == stream_name
    assert header["channel_num"] == channel_num
    assert header["sample_num"] == sample_num
    assert header["sample_rate"] == sample_rate
    assert header["num_samples"] == data.size
    assert np.array_equal(data_2, data)


def test_event_format():
    stream_name = "Test"
    source_node = 42
    type = 3
    sample_num = 43
    event_line = 7
    event_state = 1
    ttl_word = 65535
    parts = format_event(stream_name, source_node, type, sample_num, event_line, event_state, ttl_word)
    (header, event_line_2, event_state_2, ttl_word_2) = parse_event(parts)
    assert header["stream"] == stream_name
    assert header["source_node"] == source_node
    assert header["type"] == type
    assert header["sample_num"] == sample_num
    assert event_line_2 == event_line
    assert event_state_2 == event_state
    assert ttl_word_2 == ttl_word


def test_spike_format_single_channel():
    num_samples = 1000
    waveform = np.arange(num_samples, dtype=np.float32)
    stream_name = "Test"
    source_node = 42
    electrode = "Testrode"
    sample_num = 123
    sorted_id = 7
    threshold = [20, 21]
    parts = format_spike(waveform, stream_name, source_node, electrode, sample_num, sorted_id, threshold)
    (header, waveform_2) = parse_spike(parts)
    assert header["stream"] == stream_name
    assert header["source_node"] == source_node
    assert header["electrode"] == electrode
    assert header["sample_num"] == sample_num
    assert header["num_channels"] == 1
    assert header["num_samples"] == num_samples
    assert header["sorted_id"] == sorted_id
    assert header["threshold"] == threshold
    assert np.array_equal(waveform_2, waveform.reshape([1, num_samples]))


def test_spike_format_multiple_channels():
    num_channels = 10
    num_samples = 100
    waveform = np.arange(num_channels * num_samples, dtype=np.float32).reshape([num_channels, num_samples])
    stream_name = "Test"
    source_node = 42
    electrode = "Testrode"
    sample_num = 123
    sorted_id = 7
    threshold = [20, 21]
    parts = format_spike(waveform, stream_name, source_node, electrode, sample_num, sorted_id, threshold)
    (header, waveform_2) = parse_spike(parts)
    assert header["stream"] == stream_name
    assert header["source_node"] == source_node
    assert header["electrode"] == electrode
    assert header["sample_num"] == sample_num
    assert header["num_channels"] == num_channels
    assert header["num_samples"] == num_samples
    assert header["sorted_id"] == sorted_id
    assert header["threshold"] == threshold
    assert np.array_equal(waveform_2, waveform)
