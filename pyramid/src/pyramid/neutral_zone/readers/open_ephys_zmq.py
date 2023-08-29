from types import TracebackType
from typing import Any, ContextManager, Self
import logging
import uuid
import time
import json

import numpy as np
import zmq


# OpenEphys ZMQ message formats -- where did these come from?
# Nice but incomplete/informal docs here:
#   https://open-ephys.github.io/gui-docs/User-Manual/Plugins/ZMQ-Interface.html
# Messy sample client code here:
#   https://github.com/open-ephys-plugins/zmq-interface/blob/main/Resources/python_client/plot_process_zmq.py
# Actual concrete, legible server source code here:
#   https://github.com/open-ephys-plugins/zmq-interface/blob/main/Source/ZmqInterface.cpp#L359


def format_heartbeat(
    uuid: str,
    application: str = "Pyramid",
    encoding: str = 'utf-8'
) -> bytes:
    heartbeat_info = {
        "application": application,
        "uuid": uuid,
        "type": "heartbeat"
    }
    heartbeat_bytes = json.dumps(heartbeat_info).encode(encoding=encoding)
    return heartbeat_bytes


def parse_heartbeat(
    message: bytes,
    encoding: str = 'utf-8'
) -> dict[str, str]:
    return json.loads(message.decode(encoding=encoding))


def format_continuous_data(
    data: np.ndarray,
    stream_name: str,
    channel_num: int,
    sample_num: int,
    sample_rate: float,
    message_num: int = 0,
    timestamp: int = 0,
    encoding: str = 'utf-8',
) -> list[bytes]:
    content_info = {
        "stream": stream_name,
        "channel_num": channel_num,
        "num_samples": data.size,
        "sample_num": sample_num,
        "sample_rate": sample_rate
    }

    header_info = {
        "message_num": message_num,
        "type": "data",
        "content": content_info,
        "data_size": data.size * data.itemsize,
        "timestamp": timestamp
    }

    envelope_bytes = "DATA".encode(encoding=encoding)
    header_bytes = json.dumps(header_info).encode(encoding=encoding)
    return [envelope_bytes, header_bytes, data.tobytes()]


def parse_continuous_data(
    parts: list[bytes],
    dtype=np.float32,
    encoding: str = 'utf-8',
) -> tuple[str, dict, np.ndarray]:
    envelope = parts[0].decode(encoding=encoding)
    header_info = json.loads(parts[1].decode(encoding=encoding))
    data = np.frombuffer(parts[2], dtype=dtype)
    return (envelope, header_info, data)


def event_data_to_bytes(
    event_line: int,
    event_state: int,
    ttl_word: int,
) -> bytes:
    return bytes([event_line, event_state]) + ttl_word.to_bytes(length=8)


def event_data_from_bytes(
    data: bytes
) -> tuple[int, int, int]:
    event_line = int(data[0])
    event_state = int(data[1])
    ttl_word = int.from_bytes(data[2:10])
    return (event_line, event_state, ttl_word)


def format_event(
    data: bytes,
    stream_name: str,
    source_node: int,
    type: int,
    sample_num: int,
    message_num: int = 0,
    timestamp: int = 0,
    encoding: str = 'utf-8',
) -> list[bytes]:
    content_info = {
        "stream": stream_name,
        "source_node": source_node,
        "type": type,
        "sample_num": sample_num
    }

    if data is not None:
        data_size = len(data)
    else:
        data_size = 0
    header_info = {
        "message_num": message_num,
        "type": "event",
        "content": content_info,
        "data_size": data_size,
        "timestamp": timestamp
    }

    envelope_bytes = "EVENT".encode(encoding=encoding)
    header_bytes = json.dumps(header_info).encode(encoding=encoding)
    if data is not None:
        return [envelope_bytes, header_bytes, data]
    else:
        return [envelope_bytes, header_bytes]


def parse_event(
    parts: list[bytes],
    encoding: str = 'utf-8'
) -> tuple[str, dict, bytes]:
    envelope = parts[0].decode(encoding=encoding)
    header_info = json.loads(parts[1].decode(encoding=encoding))
    if len(parts) > 2:
        return (envelope, header_info, parts[2])
    else:
        return (envelope, header_info, None)


def format_spike(
    waveform: np.ndarray,
    stream_name: str,
    source_node: int,
    electrode: str,
    sample_num: int,
    sorted_id: int,
    threshold: list[float],
    message_num: int = 0,
    timestamp: int = 0,
    encoding: str = 'utf-8',
) -> list[bytes]:
    if len(waveform.shape) == 2:
        num_channels = waveform.shape[0]
        num_samples = waveform.shape[1]
    else:
        num_channels = 1
        num_samples = waveform.size
    spike_info = {
        "stream": stream_name,
        "source_node": source_node,
        "electrode": electrode,
        "sample_num": sample_num,
        "num_channels": num_channels,
        "num_samples": num_samples,
        "sorted_id": sorted_id,
        "threshold": threshold
    }

    # For some reason, spike content is called "spike" instead of "content" (condinuous data and events are both "content").
    # For some reason, spike headers don't include a data_size.
    header_info = {
        "message_num": message_num,
        "type": "spike",
        "spike": spike_info,
        "timestamp": timestamp
    }

    # For some reason, spike envelope is "EVENT", which makes it useless -- why not "SPIKE" to make it distinct?
    envelope_bytes = "EVENT".encode(encoding=encoding)
    header_bytes = json.dumps(header_info).encode(encoding=encoding)
    return [envelope_bytes, header_bytes, waveform.tobytes()]


def parse_spike(
    parts: list[bytes],
    dtype=np.float32,
    encoding: str = 'utf-8',
) -> tuple[str, dict, np.ndarray]:
    envelope = parts[0].decode(encoding=encoding)
    header_info = json.loads(parts[1].decode(encoding=encoding))
    spike_info = header_info.get("spike", {})
    num_channels = spike_info.get("num_channels", 1)
    num_samples = spike_info.get("num_samples", -1)
    waveform = np.frombuffer(parts[2], dtype=dtype).reshape([num_channels, num_samples])
    return (envelope, header_info, waveform)


class OpenEphysZmqServer(ContextManager):
    """Mimic the server side the Open Ephys ZMQ plugin -- as a standin for the actual Open Ephys application.

    The Open Ephys ZMQ plugin docs are here:
      https://open-ephys.github.io/gui-docs/User-Manual/Plugins/ZMQ-Interface.html

    This class is really only used for Pyramid automated testing.
    It's so closely related to the Pyramid reader and client code that it's convenient to include it here.
    """

    def __init__(
        self,
        host: str,
        data_port: int,
        heartbeat_port: int = None,
        scheme: str = "tcp",
        timeout_ms: int = 100,
        encoding: str = 'utf-8'
    ) -> None:
        self.data_address = f"{scheme}://{host}:{data_port}"

        if heartbeat_port is None:
            heartbeat_port = data_port + 1
        self.heartbeat_address = f"{scheme}://{host}:{heartbeat_port}"

        self.timeout_ms = timeout_ms
        self.encoding = encoding

        self.message_number = None
        self.last_heartbeat = None
        self.heartbeat_count = None
        self.heartbeat_response_bytes = "heartbeat received".encode(encoding)

        self.context = None
        self.data_socket = None
        self.heartbeat_socket = None
        self.poller = None

    def __enter__(self) -> Self:
        self.context = zmq.Context()

        self.data_socket = self.context.socket(zmq.PUB)
        self.data_socket.bind(self.data_address)

        self.heartbeat_socket = self.context.socket(zmq.REP)
        self.heartbeat_socket.bind(self.heartbeat_address)

        self.poller = zmq.Poller()
        self.poller.register(self.heartbeat_socket, zmq.POLLIN)

        self.message_number = 0
        self.last_heartbeat = None
        self.heartbeat_count = 0

        return self

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        if self.context is not None:
            self.context.destroy()

        self.context = None
        self.poller = None
        self.data_socket = None
        self.heartbeat_socket = None

    def poll_heartbeat_and_reply(self) -> bool:
        ready = dict(self.poller.poll(self.timeout_ms))
        if self.heartbeat_socket in ready:
            bytes = self.heartbeat_socket.recv(zmq.NOBLOCK)
            if bytes:
                self.last_heartbeat = parse_heartbeat(bytes, self.encoding)
                self.heartbeat_count += 1
                self.heartbeat_socket.send(self.heartbeat_response_bytes)
                return True

        return False

    def send_continuous_data(
        self,
        data: np.ndarray,
        stream_name: str,
        channel_num: int,
        sample_num: int,
        sample_rate: float,
    ) -> None:
        timestamp = round(time.time() * 1000)
        parts = format_continuous_data(
            data,
            stream_name,
            channel_num,
            sample_num,
            sample_rate,
            self.message_number,
            timestamp,
            self.encoding
        )
        self.data_socket.send_multipart(parts)
        self.message_number +=1

    def send_ttl_event(
        self,
        event_line: int,
        event_state: int,
        ttl_word: int,
        stream_name: str,
        source_node: int,
        type: int,
        sample_num: int,
    ) -> None:
        data = event_data_to_bytes(event_line, event_state, ttl_word)
        timestamp = round(time.time() * 1000)
        parts = format_event(
            data,
            stream_name,
            source_node,
            type,
            sample_num,
            self.message_number,
            timestamp,
            self.encoding
        )
        self.data_socket.send_multipart(parts)
        self.message_number +=1

    def send_spike(
        self,
        waveform: np.ndarray,
        stream_name: str,
        source_node: int,
        electrode: str,
        sample_num: int,
        sorted_id: int,
        threshold: list[float],
    ) -> None:
        timestamp = round(time.time() * 1000)
        parts = format_spike(
            waveform,
            stream_name,
            source_node,
            electrode,
            sample_num,
            sorted_id,
            threshold,
            self.message_number,
            timestamp,
            self.encoding
        )
        self.data_socket.send_multipart(parts)
        self.message_number +=1


class OpenEphysZmqClient(ContextManager):
    """Connect and subscribe as a client to an Open Ephys app running the ZMQ plugin.

    The Open Ephys ZMQ plugin docs are here:
      https://open-ephys.github.io/gui-docs/User-Manual/Plugins/ZMQ-Interface.html
    """

    def __init__(
        self,
        host: str,
        data_port: int,
        heartbeat_port: int = None,
        scheme: str = "tcp",
        timeout_ms: int = 100,
        encoding: str = 'utf-8',
        client_uuid: str = None
    ) -> None:
        self.data_address = f"{scheme}://{host}:{data_port}"

        if heartbeat_port is None:
            heartbeat_port = data_port + 1
        self.heartbeat_address = f"{scheme}://{host}:{heartbeat_port}"

        self.timeout_ms = timeout_ms
        self.encoding = encoding

        if client_uuid is None:
            client_uuid = str(uuid.uuid4())
        self.client_uuid = client_uuid

        self.last_heartbeat_time = None
        self.heartbeat_bytes = format_heartbeat(client_uuid)

        self.context = None
        self.data_socket = None
        self.heartbeat_socket = None
        self.poller = None

    def __enter__(self) -> Self:
        self.context = zmq.Context()

        self.data_socket = self.context.socket(zmq.SUB)
        self.data_socket.bind(self.data_address)

        self.heartbeat_socket = self.context.socket(zmq.REQ)
        self.heartbeat_socket.bind(self.heartbeat_address)

        self.poller = zmq.Poller()
        self.poller.register(self.data_socket, zmq.POLLIN)
        self.poller.register(self.heartbeat_socket, zmq.POLLIN)

        self.last_heartbeat_time = 0

        return self

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        if self.context is not None:
            self.context.destroy()

        self.context = None
        self.poller = None
        self.data_socket = None
        self.heartbeat_socket = None

    def send_heartbeat(self) -> None:
        self.heartbeat_socket.send(self.heartbeat_bytes)

    def poll_and_receive(self) -> dict[str, Any]:
        received = {}
        ready = dict(self.poller.poll(self.timeout_ms))
        if self.heartbeat_socket in ready:
            heartbeat_reply_bytes = self.heartbeat_socket.recv(zmq.NOBLOCK)
            if heartbeat_reply_bytes:
                heartbeat_reply = heartbeat_reply_bytes.decode(self.encoding)
                received["heartbeat_reply"] = heartbeat_reply

        if self.data_socket in ready:
            parts = self.data_socket.recv_multipart(zmq.NOBLOCK)
            if parts:
                header_info = json.loads(parts[1].decode(self.encoding))
                data_type = header_info["type"]
                if data_type == "data":
                    (envelope, header_info, data) = parse_continuous_data(parts, self.encoding)
                    received["data"] = {
                        "envelope": envelope,
                        "header_info": header_info,
                        "data": data
                    }

                elif data_type == "event":
                    (envelope, header_info, data) = parse_event(parts, encoding=self.encoding)
                    (event_line, event_state, ttl_word) = event_data_from_bytes(data)
                    received["event"] = {
                        "envelope": envelope,
                        "header_info": header_info,
                        "event_line": event_line,
                        "event_state": event_state,
                        "ttl_word": ttl_word
                    }

                elif data_type == "spike":
                    (envelope, header_info, waveform) = parse_spike(parts, encoding=self.encoding)
                    received["event"] = {
                        "envelope": envelope,
                        "header_info": header_info,
                        "waveform": waveform
                    }
                else:
                    logging.warning(f"OpenEphysZmqClient ignoring unknown data type: {data_type}")

        return received
