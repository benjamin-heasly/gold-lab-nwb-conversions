from types import TracebackType
from typing import ContextManager, Self
import uuid
import json

import numpy as np
import zmq


# Where did all these message formats come from?
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

    # For some reason, spike envelope is "EVENT" -- why not "SPIKE"?
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


class Client(ContextManager):

    def __init__(
        self,
        host: str,
        port: int,
        scheme: str = "tcp",
        encoding: str = 'utf-8',
        uuid: str = str(uuid.uuid4())
    ) -> None:
        self.address = f"{scheme}://{host}:{port}"
        self.encoding = encoding
        self.heartbeat_message = format_heartbeat(uuid)

        self.context = None
        self.poller = None
        self.socket = None

    def __enter__(self) -> Self:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.address)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
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
        self.socket = None

    def send_request(self, messages: list[str]) -> None:
        parts = [message.encode(self.encoding) for message in messages]
        self.socket.send_multipart(parts)

    def poll_reply(self, timeout_ms: int = 100) -> list[str]:
        ready = dict(self.poller.poll(timeout_ms))
        if self.socket in ready:
            parts = self.socket.recv_multipart(zmq.NOBLOCK)
            if parts:
                messages = [part.decode(self.encoding) for part in parts]
                return messages
        return None


class Server(ContextManager):

    def __init__(self, host: str, port: int, scheme: str = "tcp", encoding: str = 'utf-8') -> None:
        self.address = f"{scheme}://{host}:{port}"
        self.encoding = encoding

        self.context = None
        self.poller = None
        self.socket = None

    def __enter__(self) -> Self:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.address)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
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
        self.socket = None

    def poll_request(self, timeout_ms: int = 100) -> list[str]:
        ready = dict(self.poller.poll(timeout_ms))
        if self.socket in ready:
            parts = self.socket.recv_multipart(zmq.NOBLOCK)
            if parts:
                messages = [part.decode(self.encoding) for part in parts]
                return messages
        return None

    def send_reply(self, messages: list[str]) -> None:
        parts = [message.encode(self.encoding) for message in messages]
        self.socket.send_multipart(parts)
