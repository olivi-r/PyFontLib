import os
import struct
import zlib


class WoffTable:
    def __init__(self, tag, data, orig_checksum):
        self.tag = tag
        self.data = data
        self.orig_checksum = orig_checksum

    @classmethod
    def parse(cls, fp):
        # read table directory entry
        (
            tag,
            offset,
            comp_length,
            orig_length,
            orig_checksum,
        ) = struct.unpack(">4s4I", fp.read(20))

        # read table data
        location = fp.tell()
        fp.seek(offset)
        data = fp.read(comp_length)
        fp.seek(location)

        # table is compressed
        if comp_length != orig_length:
            data = zlib.decompress(data)

        return offset, cls(tag, data, orig_checksum)


class Woff:
    def __init__(
        self, flavor, version_major, version_minor, tables, meta=None, priv=None
    ):
        self.flavor = flavor
        self.version_major = version_major
        self.version_minor = version_minor
        self.tables = tables
        self.meta = meta
        self.priv = priv

    @classmethod
    def parse(cls, fp):
        (
            signature,
            flavor,
            length,
            num_tables,
            reserved,
            total_sfnt_size,
            version_major,
            version_minor,
            meta_offset,
            meta_length,
            meta_orig_length,
            priv_offset,
            priv_length,
        ) = struct.unpack(">4s2I2HI2H5I", fp.read(44))

        assert signature == b"wOFF", "Incorrect file signature"
        assert os.stat(fp.fileno()).st_size == length, "Incorrect file length"
        assert reserved == 0, "Reserved bytes must be 0"
        assert total_sfnt_size % 4 == 0, "Total sfnt size must be multiple of 4"

        tables = [
            i[1]
            for i in sorted(
                (WoffTable.parse(fp) for _ in range(num_tables)), key=lambda x: x[0]
            )
        ]

        if meta_offset == meta_length == meta_orig_length == 0:
            meta = None

        else:
            fp.seek(meta_offset)
            meta = zlib.decompress(fp.read(meta_length))

        if priv_offset == priv_length == 0:
            priv = None

        else:
            fp.seek(priv_offset)
            priv = fp.read(priv_length)

        return cls(flavor, version_major, version_minor, tables, meta, priv)
