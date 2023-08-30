import uuid

import numpy as np

from pyramid.neutral_zone.readers.open_ephys_zmq import (
    format_heartbeat,
    parse_heartbeat,
    format_continuous_data,
    parse_continuous_data,
    event_data_to_bytes,
    event_data_from_bytes,
    format_event,
    parse_event,
    format_spike,
    parse_spike,
    OpenEphysZmqClient,
    OpenEphysZmqServer,
)


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
    message_num = 42
    timestamp = 424242
    parts = format_continuous_data(
        data,
        stream_name,
        channel_num,
        sample_num,
        sample_rate,
        message_num,
        timestamp
    )
    (envelope, header, data_2) = parse_continuous_data(parts)
    assert envelope == "DATA"
    assert header["message_num"] == message_num
    assert header["type"] == "data"
    assert header["content"]["sample_rate"] == sample_rate
    assert header["content"]["stream"] == stream_name
    assert header["content"]["channel_num"] == channel_num
    assert header["content"]["sample_num"] == sample_num
    assert header["content"]["sample_rate"] == sample_rate
    assert header["content"]["num_samples"] == data.size
    assert header["data_size"] == data.size * data.itemsize
    assert header["timestamp"] == timestamp
    assert np.array_equal(data_2, data)


def test_event_format_with_data():
    event_line = 7
    event_state = 1
    ttl_word = 65535
    data = event_data_to_bytes(event_line, event_state, ttl_word)

    stream_name = "Test"
    source_node = 42
    type = 3
    sample_num = 43
    message_num = 42
    timestamp = 424242
    parts = format_event(
        data,
        stream_name,
        source_node,
        type,
        sample_num,
        message_num,
        timestamp
    )
    (envelope, header, data_2) = parse_event(parts)
    assert envelope == "EVENT"
    assert header["message_num"] == message_num
    assert header["type"] == "event"
    assert header["content"]["stream"] == stream_name
    assert header["content"]["source_node"] == source_node
    assert header["content"]["type"] == type
    assert header["content"]["sample_num"] == sample_num
    assert header["data_size"] == len(data)
    assert header["timestamp"] == timestamp
    assert data_2 == data

    (event_line_2, event_state_2, ttl_word_2) = event_data_from_bytes(data_2)
    assert event_line_2 == event_line
    assert event_state_2 == event_state
    assert ttl_word_2 == ttl_word


def test_event_format_without_data():
    stream_name = "Test"
    source_node = 42
    type = 3
    sample_num = 43
    message_num = 42
    timestamp = 424242
    parts = format_event(
        None,
        stream_name,
        source_node,
        type,
        sample_num,
        message_num,
        timestamp
    )
    (envelope, header, data_2) = parse_event(parts)
    assert envelope == "EVENT"
    assert header["message_num"] == message_num
    assert header["type"] == "event"
    assert header["content"]["stream"] == stream_name
    assert header["content"]["source_node"] == source_node
    assert header["content"]["type"] == type
    assert header["content"]["sample_num"] == sample_num
    assert header["data_size"] == 0
    assert header["timestamp"] == timestamp
    assert data_2 == None


def test_spike_format_single_channel():
    num_samples = 1000
    waveform = np.arange(num_samples, dtype=np.float32)
    stream_name = "Test"
    source_node = 42
    electrode = "Testrode"
    sample_num = 123
    sorted_id = 7
    threshold = [20, 21]
    message_num = 42
    timestamp = 424242
    parts = format_spike(
        waveform,
        stream_name,
        source_node,
        electrode,
        sample_num,
        sorted_id,
        threshold,
        message_num,
        timestamp
    )
    (envelope, header, waveform_2) = parse_spike(parts)
    assert envelope == "EVENT"
    assert header["message_num"] == message_num
    assert header["type"] == "spike"
    assert header["spike"]["stream"] == stream_name
    assert header["spike"]["source_node"] == source_node
    assert header["spike"]["electrode"] == electrode
    assert header["spike"]["sample_num"] == sample_num
    assert header["spike"]["num_channels"] == 1
    assert header["spike"]["num_samples"] == num_samples
    assert header["spike"]["sorted_id"] == sorted_id
    assert header["spike"]["threshold"] == threshold
    assert header["timestamp"] == timestamp
    assert waveform_2.shape == (1, num_samples)
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
    message_num = 42
    timestamp = 424242
    parts = format_spike(
        waveform,
        stream_name,
        source_node,
        electrode,
        sample_num,
        sorted_id,
        threshold,
        message_num,
        timestamp
    )
    (envelope, header, waveform_2) = parse_spike(parts)
    assert envelope == "EVENT"
    assert header["message_num"] == message_num
    assert header["type"] == "spike"
    assert header["spike"]["stream"] == stream_name
    assert header["spike"]["source_node"] == source_node
    assert header["spike"]["electrode"] == electrode
    assert header["spike"]["sample_num"] == sample_num
    assert header["spike"]["num_channels"] == num_channels
    assert header["spike"]["num_samples"] == num_samples
    assert header["spike"]["sorted_id"] == sorted_id
    assert header["spike"]["threshold"] == threshold
    assert header["timestamp"] == timestamp
    assert waveform_2.shape == (num_channels, num_samples)
    assert np.array_equal(waveform_2, waveform)


def test_open_ephys_zmq_heartbeats():
    host = "127.0.0.1"
    data_port = 10001
    with OpenEphysZmqServer(host=host, data_port=data_port) as server:
        assert server.last_heartbeat is None
        assert server.heartbeat_count == 0
        assert server.poll_heartbeat_and_reply() is False

        with OpenEphysZmqClient(host=host, data_port=data_port) as client:
            assert client.heartbeat_send_count == 0
            assert client.heartbeat_reply_count == 0
            assert client.poll_and_receive_heartbeat() == None

            for index in range(1, 100):
                # Send a new heartbeat request.
                assert client.send_heartbeat() is True
                assert client.heartbeat_send_count == index

                # Sending a request should be a safe no-op when a heartbeat request is already outstanding.
                assert client.send_heartbeat() is False
                assert client.heartbeat_send_count == index

                # Receive the outstanding heartbeat request and reply to it.
                assert server.poll_heartbeat_and_reply() is True
                assert server.heartbeat_count == index
                assert server.last_heartbeat["uuid"] == client.client_uuid

                # Receiving a request should be a safe no-op, once the outstanding request has been handled.
                assert server.poll_heartbeat_and_reply() is False
                assert server.heartbeat_count == index

                # Receive the outstanding heartbeat reply to complete this round trip.
                assert client.poll_and_receive_heartbeat() == server.heartbeat_reply
                assert client.heartbeat_reply_count == index

                # Receiving a reply should be a safe no-op, once the outstanding reply has been handled.
                assert client.poll_and_receive_heartbeat() == None
                assert client.heartbeat_reply_count == index


def test_open_ephys_zmq_continuous_data():
    host = "127.0.0.1"
    data_port = 10001
    with OpenEphysZmqServer(host=host, data_port=data_port) as server:
        assert server.message_number is 0

        with OpenEphysZmqClient(host=host, data_port=data_port) as client:
            assert client.poll_and_receive_data() == {}

            for index in range(0, 100):
                # Send some random continuous data to the client.
                data = np.random.rand(100).astype(np.float32)
                stream_name = "test_stream"
                channel_num = 42
                sample_num = index * 100
                sample_rate = 1000.42
                message_num = server.send_continuous_data(
                    data,
                    stream_name,
                    channel_num,
                    sample_num,
                    sample_rate
                )
                assert message_num == index

                # Receive the same data at the client.
                results = client.poll_and_receive_data()
                while not results:
                    results = client.poll_and_receive_data()
                assert results["envelope"] == "DATA"
                assert results["message_num"] == message_num
                assert results["type"] == "data"
                assert results["content"]["sample_rate"] == sample_rate
                assert results["content"]["stream"] == stream_name
                assert results["content"]["channel_num"] == channel_num
                assert results["content"]["sample_num"] == sample_num
                assert results["content"]["sample_rate"] == sample_rate
                assert results["content"]["num_samples"] == data.size
                assert results["data_size"] == data.size * data.itemsize
                assert results["timestamp"] > 0
                assert np.array_equal(results["data"], data)

                # Receiving again should be a safe no-op.
                assert client.poll_and_receive_data() == {}


def test_open_ephys_zmq_ttl_event():
    host = "127.0.0.1"
    data_port = 10001
    with OpenEphysZmqServer(host=host, data_port=data_port) as server:
        assert server.message_number is 0

        with OpenEphysZmqClient(host=host, data_port=data_port) as client:
            assert client.poll_and_receive_data() == {}

            for index in range(0, 100):
                # Send a random ttl event to the client.
                event_line = np.random.randint(0, 255)
                event_state = np.random.randint(0, 1)
                ttl_word = np.random.randint(0, 1e6)
                stream_name = "test_stream"
                source_node = 42
                sample_num = index
                message_num = server.send_ttl_event(
                    event_line,
                    event_state,
                    ttl_word,
                    stream_name,
                    source_node,
                    sample_num
                )
                assert message_num == index

                # Receive the same data at the client.
                results = client.poll_and_receive_data()
                while not results:
                    results = client.poll_and_receive_data()
                assert results["envelope"] == "EVENT"
                assert results["message_num"] == message_num
                assert results["type"] == "event"
                assert results["content"]["stream"] == stream_name
                assert results["content"]["source_node"] == source_node
                assert results["content"]["type"] == 3  # ttl event
                assert results["content"]["sample_num"] == sample_num
                assert results["data_size"] == 10
                assert results["timestamp"] > 0
                assert results["event_line"] == event_line
                assert results["event_state"] == event_state
                assert results["ttl_word"] == ttl_word

                # Receiving again should be a safe no-op.
                assert client.poll_and_receive_data() == {}


def test_open_ephys_zmq_spike():
    host = "127.0.0.1"
    data_port = 10001
    with OpenEphysZmqServer(host=host, data_port=data_port) as server:
        assert server.message_number is 0

        with OpenEphysZmqClient(host=host, data_port=data_port) as client:
            assert client.poll_and_receive_data() == {}

            for index in range(0, 100):
                # Send a random spike waveform to the client.
                num_channels = np.random.randint(1, 3)
                num_samples = 100
                waveform = np.random.rand(num_channels, num_samples).astype(np.float32)
                stream_name = "test_stream"
                source_node = 42
                electrode = "test_electrode"
                sample_num = index * 100
                sorted_id = 7
                threshold = np.ones(num_channels).tolist()
                message_num = server.send_spike(
                    waveform,
                    stream_name,
                    source_node,
                    electrode,
                    sample_num,
                    sorted_id,
                    threshold
                )
                assert message_num == index

                # Receive the same data at the client.
                results = client.poll_and_receive_data()
                while not results:
                    results = client.poll_and_receive_data()
                assert results["envelope"] == "EVENT"
                assert results["message_num"] == message_num
                assert results["type"] == "spike"
                assert results["spike"]["stream"] == stream_name
                assert results["spike"]["source_node"] == source_node
                assert results["spike"]["electrode"] == electrode
                assert results["spike"]["sample_num"] == sample_num
                assert results["spike"]["num_channels"] == num_channels
                assert results["spike"]["num_samples"] == num_samples
                assert results["spike"]["sorted_id"] == sorted_id
                assert results["spike"]["threshold"] == threshold
                assert results["timestamp"] > 0
                assert np.array_equal(results["waveform"], waveform)

                # Receiving again should be a safe no-op.
                assert client.poll_and_receive_data() == {}


def test_open_ephys_zmq_mixed_data():
    host = "127.0.0.1"
    data_port = 10001
    with OpenEphysZmqServer(host=host, data_port=data_port, timeout_ms=100) as server:
        with OpenEphysZmqClient(host=host, data_port=data_port) as client:

            # Send mixed bunches of data for the client to handle.
            for index in range(0, 100):
                # Set up a heartbeat reply for the client to consume.
                assert client.send_heartbeat() is True
                assert server.poll_heartbeat_and_reply() is True

                # Send some random continuous data to the client.
                server.send_continuous_data(
                    data=np.random.rand(100).astype(np.float32),
                    stream_name="test_stream",
                    channel_num=42,
                    sample_num=index * 100,
                    sample_rate=1000.42
                )

                # Send a random ttl event to the client.
                server.send_ttl_event(
                    event_line=np.random.randint(0, 255),
                    event_state=np.random.randint(0, 1),
                    ttl_word=np.random.randint(0, 1e6),
                    stream_name="test_stream",
                    source_node=42,
                    sample_num=index
                )

                # Send a random spike waveform to the client.
                server.send_spike(
                    waveform=np.random.rand(2, 100).astype(np.float32),
                    stream_name="test_stream",
                    source_node=42,
                    electrode="test_electrode",
                    sample_num=index * 100,
                    sorted_id=7,
                    threshold=[1, 1]
                )

                # Let the client receive various data in the order sent.
                results = client.poll_and_receive_data()
                while not results:
                    results = client.poll_and_receive_data()
                assert results["type"] == "data"

                results = client.poll_and_receive_data()
                while not results:
                    results = client.poll_and_receive_data()
                assert results["type"] == "event"

                results = client.poll_and_receive_data()
                while not results:
                    results = client.poll_and_receive_data()
                assert results["type"] == "spike"

                assert client.poll_and_receive_data() == {}

                # Let the client receive the initial heartbeat, out of order, which should not matter.
                assert client.poll_and_receive_heartbeat() == server.heartbeat_reply
                assert client.poll_and_receive_heartbeat() is None
