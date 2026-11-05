"""Bytecode → binary, then XOR-encrypt for embedding in source."""

import random


def bxor(a, b):
    return a ^ b


def _u8(buf, n):
    buf.append(n & 0xFF)


def _u16(buf, n):
    buf.append(n & 0xFF)
    buf.append((n >> 8) & 0xFF)


def _raw(buf, s):
    buf.extend(s)


def serialize(protos, op_map, seed):
    rng = random.Random(seed)
    buf = bytearray()

    strings = []
    str_map = {}
    for p in protos:
        for c in p.consts:
            if isinstance(c, str) and c not in str_map:
                str_map[c] = len(strings) + 1
                strings.append(c)

    _u16(buf, len(protos))
    _u16(buf, len(strings))
    _u8(buf, 43)
    for real in range(1, 44):
        _u8(buf, op_map[real])

    for s in strings:
        key = rng.randint(1, 255)
        _u8(buf, key)
        enc = bytes(bxor(b, key) for b in s.encode("utf-8"))
        _u16(buf, len(enc))
        _raw(buf, enc)

    for p in protos:
        _u8(buf, p.num_params)
        _u8(buf, 1 if p.is_vararg else 0)
        _u16(buf, p.nlocals)
        _u16(buf, len(p.insts))
        _u16(buf, len(p.consts))
        _u8(buf, len(p.upvals))

        for inst in p.insts:
            _u8(buf, op_map.get(inst[0], 0))
            _u16(buf, inst[1])
            _u16(buf, inst[2])

        for c in p.consts:
            if c is None:
                _u8(buf, 0)
            elif isinstance(c, bool):
                _u8(buf, 1)
                _u8(buf, 1 if c else 0)
            elif isinstance(c, (int, float)):
                _u8(buf, 2)
                enc = str(c).encode("utf-8")
                _u16(buf, len(enc))
                _raw(buf, enc)
            elif isinstance(c, str):
                _u8(buf, 3)
                _u16(buf, str_map[c])

        for uv in p.upvals:
            _u8(buf, 1 if uv["inStack"] else 0)
            _u8(buf, uv["idx"])

    return bytes(buf)


def encrypt(bytecode, key):
    parts = []
    for i, b in enumerate(bytecode):
        parts.append("\\%d" % bxor(b, (key + i) & 0xFF))
    return "".join(parts)


def make_op_map(seed):
    rng = random.Random(seed + 1)
    pool = list(range(1, 101))
    rng.shuffle(pool)
    return {real: pool[real - 1] for real in range(1, 44)}
