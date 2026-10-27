"""Firefox native messaging endpoint. It queues captures; it never starts downloads."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import core

def read_exact(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise EOFError("Truncated native message.")
        data.extend(chunk)
    return bytes(data)

def receive(stream):
    size = struct.unpack("<I", read_exact(stream, 4))[0]
    if not 0 < size <= 1048576:
        raise ValueError("Invalid message length.")
    return json.loads(read_exact(stream, size))

def reply(stream, value):
    encoded = json.dumps(value).encode("utf-8")
    stream.write(struct.pack("<I", len(encoded)) + encoded)
    stream.flush()

def launch_app():
    target = core.APP_DIR / "LinkCapture.exe"
    if getattr(sys, "frozen", False):
        args = [str(target)]
    else:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        args = [str(pythonw if pythonw.exists() else Path(sys.executable)), str(core.APP_DIR / "src" / "app.py")]
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=core.NO_WINDOW, close_fds=True)

def main():
    if os.name == "nt":
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    try:
        if len(sys.argv) > 1 and sys.argv[-1] != core.EXTENSION_ID:
            raise ValueError("Unrecognized extension.")
        payload = core.validate_capture(receive(sys.stdin.buffer))
        ident = core.add_capture(payload)
        launch_app()
        reply(sys.stdout.buffer, {"ok": True, "id": ident, "message": "Sent to Link Capture."})
    except Exception as exc:
        reply(sys.stdout.buffer, {"ok": False, "error": str(exc)})

if __name__ == "__main__":
    main()
