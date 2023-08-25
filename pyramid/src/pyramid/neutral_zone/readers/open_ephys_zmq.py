from types import TracebackType
from typing import ContextManager, Self
import uuid
import json

import numpy as np
import zmq


# TODO: revisit after reviewing source code (seems nice and clear) rather than docs (seems incomplete):
# https://open-ephys.github.io/gui-docs/User-Manual/Plugins/ZMQ-Interface.html
# https://github.com/open-ephys-plugins/zmq-interface/blob/main/Source/ZmqInterface.cpp#L359


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
        encoding: str = 'utf-8'
) -> list[bytes]:
    header_info = {
        "stream": stream_name,
        "channel_num": channel_num,
        "num_samples": data.size,
        "sample_num": sample_num,
        "sample_rate": sample_rate
    }
    header_bytes = json.dumps(header_info).encode(encoding=encoding)
    return [header_bytes, data.tobytes()]


def parse_continuous_data(
    parts: list[bytes],
    encoding: str = 'utf-8',
    dtype = np.float32
) -> tuple[dict, np.ndarray]:
    header_info = json.loads(parts[0].decode(encoding=encoding))
    data = np.frombuffer(parts[1], dtype=dtype)
    return (header_info, data)


def format_event(
    stream_name: str,
    source_node: int,
    type: int,
    sample_num: int,
    event_line: int,
    event_state: int,
    ttl_word: int,
    encoding: str = 'utf-8'
) -> list[bytes]:
    header_info = {
        "stream": stream_name,
        "source_node": source_node,
        "type": type,
        "sample_num": sample_num
    }
    header_bytes = json.dumps(header_info).encode(encoding=encoding)
    data = bytes([event_line, event_state]) + ttl_word.to_bytes(length=8)
    return [header_bytes, data]


def parse_event(
    parts: list[bytes],
    encoding: str = 'utf-8'
) -> tuple[dict, int, int, int]:
    header_info = json.loads(parts[0].decode(encoding=encoding))
    data = parts[1]
    event_line = int(data[0])
    event_state = int(data[1])
    ttl_word = int.from_bytes(data[2:10])
    return (header_info, event_line, event_state, ttl_word)


def format_spike(
    waveform: np.ndarray,
    stream_name: str,
    source_node: int,
    electrode: str,
    sample_num: int,
    sorted_id: int,
    threshold: list[float],
    encoding: str = 'utf-8'
) -> list[bytes]:
    if len(waveform.shape) == 2:
        num_channels = waveform.shape[0]
        num_samples = waveform.shape[1]
    else:
        num_channels = 1
        num_samples = waveform.size
    header_info = {
        "stream": stream_name,
        "source_node": source_node,
        "electrode": electrode,
        "sample_num": sample_num,
        "num_channels": num_channels,
        "num_samples": num_samples,
        "sorted_id": sorted_id,
        "threshold": threshold
    }
    header_bytes = json.dumps(header_info).encode(encoding=encoding)
    return [header_bytes, waveform.tobytes()]


def parse_spike(
    parts: list[bytes],
    encoding: str = 'utf-8',
    dtype = np.float32
) -> tuple[dict, np.ndarray]:
    header_info = json.loads(parts[0].decode(encoding=encoding))
    num_channels = header_info.get("num_channels", 1)
    num_samples = header_info.get("num_samples", -1)
    waveform = np.frombuffer(parts[1], dtype=dtype).reshape([num_channels, num_samples])
    return (header_info, waveform)


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
