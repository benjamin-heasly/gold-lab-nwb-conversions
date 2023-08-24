from types import TracebackType
from typing import Any, ContextManager, Self
import zmq


class Client(ContextManager):

    def __init__(self, host: str, port: int, scheme: str = "tcp", encoding: str = 'utf-8') -> None:
        self.address = f"{scheme}://{host}:{port}"
        self.encoding = encoding

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

