"""Built-in data-compression packets.

Every payload that crosses an internal boundary — cache entries, sub-agent
results, inter-agent messages — is serialized into a self-describing packet:

    +--------+---------+-------+-----------+====================+
    | MAGIC  | version | flags | orig_len  |   body (zlib|raw)  |
    | 4 bytes|  1 byte | 1 byte|  4 bytes  |        ...         |
    +--------+---------+-------+-----------+====================+

Compression is "smart / built-in": payloads under a threshold are stored raw
(the zlib header would cost more than it saves), larger ones are zlib-deflated.
`stats()` reports the realized ratio so the optimization is measurable, not
assumed.
"""

from __future__ import annotations

import base64
import json
import struct
import zlib
from dataclasses import dataclass

MAGIC = b"NPKT"
VERSION = 1
_FLAG_COMPRESSED = 0x01
_HEADER = struct.Struct(">4sBBI")  # magic, version, flags, original length
_MIN_COMPRESS_BYTES = 256
_LEVEL = 6


@dataclass(frozen=True)
class PacketStats:
    raw_bytes: int
    packet_bytes: int
    compressed: bool

    @property
    def ratio(self) -> float:
        """packet / raw — lower is better. 1.0 means no saving."""
        return round(self.packet_bytes / self.raw_bytes, 4) if self.raw_bytes else 1.0

    @property
    def saved_bytes(self) -> int:
        return max(self.raw_bytes - self.packet_bytes, 0)

    def as_dict(self) -> dict:
        return {
            "raw_bytes": self.raw_bytes,
            "packet_bytes": self.packet_bytes,
            "compressed": self.compressed,
            "ratio": self.ratio,
            "saved_bytes": self.saved_bytes,
        }


def _serialize(obj) -> bytes:
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj)
    return json.dumps(obj, separators=(",", ":"), default=str).encode("utf-8")


def pack(obj) -> bytes:
    """Serialize and (smartly) compress an object into a packet."""
    raw = _serialize(obj)
    if len(raw) >= _MIN_COMPRESS_BYTES:
        body = zlib.compress(raw, _LEVEL)
        if len(body) < len(raw):
            return _HEADER.pack(MAGIC, VERSION, _FLAG_COMPRESSED, len(raw)) + body
    return _HEADER.pack(MAGIC, VERSION, 0, len(raw)) + raw


def unpack(packet: bytes) -> object:
    """Inverse of pack(). Returns the decoded JSON object (or bytes)."""
    magic, version, flags, orig_len = _HEADER.unpack(packet[: _HEADER.size])
    if magic != MAGIC:
        raise ValueError("not a NoblePort packet")
    if version != VERSION:
        raise ValueError(f"unsupported packet version {version}")
    body = packet[_HEADER.size:]
    raw = zlib.decompress(body) if flags & _FLAG_COMPRESSED else body
    if len(raw) != orig_len:
        raise ValueError("packet length check failed")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw


def stats(obj) -> PacketStats:
    raw = _serialize(obj)
    packet = pack(obj)
    return PacketStats(
        raw_bytes=len(raw),
        packet_bytes=len(packet),
        compressed=bool(_HEADER.unpack(packet[: _HEADER.size])[2] & _FLAG_COMPRESSED),
    )


# --- Redis-safe (text) helpers --------------------------------------------
def pack_b64(obj) -> str:
    return base64.b64encode(pack(obj)).decode("ascii")


def unpack_b64(text: str) -> object:
    return unpack(base64.b64decode(text.encode("ascii")))
