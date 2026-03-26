from asr_client import create_grpc_channel


def test_insecure_channel_string_address() -> None:
    channel = create_grpc_channel("localhost:50051")
    assert channel is not None
    channel.close()


def test_insecure_channel_tuple_address() -> None:
    channel = create_grpc_channel(("localhost", 50051))
    assert channel is not None
    channel.close()


def test_channel_with_no_credentials() -> None:
    channel = create_grpc_channel("localhost:50051", credentials=None)
    assert channel is not None
    channel.close()
