from __future__ import annotations

import traceback

import grpc


def create_grpc_channel_credentials(
    tls_certificate_chain: bytes | None = None,
    tls_private_key: bytes | None = None,
    tls_root_certificates: bytes | None = None,
) -> grpc.ChannelCredentials:
    return grpc.ssl_channel_credentials(
        certificate_chain=tls_certificate_chain,
        private_key=tls_private_key,
        root_certificates=tls_root_certificates,
    )


def create_grpc_channel(
    target: str | tuple[str, int],
    credentials: grpc.ChannelCredentials | None = None,
) -> grpc.Channel:
    if isinstance(target, tuple):
        address, port = target
        target = f"{address}:{port}"

    if credentials:
        return grpc.secure_channel(target, credentials)
    else:
        return grpc.insecure_channel(target)


def _generate_request_with_traceback(generator_func):
    def wrap(*args, **kwargs):
        try:
            yield from generator_func(*args, **kwargs)
        except:
            traceback.print_exc()
            raise

    return wrap
