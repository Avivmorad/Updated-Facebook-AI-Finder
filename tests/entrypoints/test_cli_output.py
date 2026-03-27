from io import BytesIO

from app.entrypoints import cli


class _EncodingSensitiveStdout:
    encoding = "ascii"

    def __init__(self) -> None:
        self.buffer = BytesIO()

    def write(self, value):
        text = str(value)
        text.encode(self.encoding)
        return len(text)

    def flush(self):
        return None


def test_safe_console_print_falls_back_for_unicode(monkeypatch):
    fake_stdout = _EncodingSensitiveStdout()
    monkeypatch.setattr(cli.sys, "stdout", fake_stdout)

    cli._safe_console_print("שלום docking station")

    rendered = fake_stdout.buffer.getvalue().decode("ascii")
    assert "docking station" in rendered
    assert "?" in rendered
