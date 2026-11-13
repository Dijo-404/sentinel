from ._base import PeerStub


def web_shell_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="web-shell.v1", case=case, component="stub-web-shell")
