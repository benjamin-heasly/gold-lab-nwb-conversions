import zmq
from pyramid.neutral_zone.readers.open_ephys_zmq import Client, Server


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
