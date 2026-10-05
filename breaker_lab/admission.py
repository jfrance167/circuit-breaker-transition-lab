"""Bounded JSON gates adapted from Jake's reviewed structured-log lab (MIT).

The standard library remains syntax authority. Limits are fixed for this lab.
"""

import json


MAX_BYTES = 65536
MAX_DEPTH = 8
MAX_STRING_BYTES = 128
MAX_INTEGER_TEXT = 16
MAX_KEYS = 1024
MAX_ARRAY = 128
MAX_NODES = 4096
MAX_OUTPUT = 262144
CODES = frozenset({"input.invalid_json", "input.encoding", "input.limit", "input.number",
                   "input.duplicate", "input.io", "schema.invalid", "output.error",
                   "arguments.invalid", "internal.error", "trace.invalid"})


class LabError(Exception):
    """Closed, content-free error code; no input or exception string attached."""

    def __init__(self, code):
        self.code = code if code in CODES else "internal.error"
        super().__init__(self.code)


def lexical_gate(raw: bytes):
    """Count encoded string-body bytes, excluding quote delimiters.

    Includes backslashes and escape spelling, UTF-8 bytes and escaped quotes.
    Parity identifies delimiters; json.loads validates escape syntax afterward.
    Depth counts brackets outside strings only. This is not a general parser.
    """
    if type(raw) is not bytes:
        raise LabError("input.invalid_json")
    if len(raw) > MAX_BYTES:
        raise LabError("input.limit")
    inside = escaped = False
    depth = count = 0
    for byte in raw:
        if inside:
            if byte == 34 and not escaped:
                inside = False
                continue
            count += 1
            if count > MAX_STRING_BYTES:
                raise LabError("input.limit")
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
        elif byte == 34:
            inside, escaped, count = True, False, 0
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_DEPTH:
                raise LabError("input.limit")
        elif byte in (93, 125):
            depth -= 1
            if depth < 0:
                raise LabError("input.invalid_json")
    if inside or depth != 0:
        raise LabError("input.invalid_json")


def _integer(text):
    if len(text) > MAX_INTEGER_TEXT:
        raise LabError("input.number")
    return int(text)


def _no_number(_text):
    raise LabError("input.number")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LabError("input.duplicate")
        result[key] = value
    return result


def check_tree(value):
    """Exact builtin tree admission; cycles rejected, aliases count per visit.

    Native caller allocations/concurrent mutation are not contained. No custom
    conversion/iteration hooks run. Decoded container limits are postallocation.
    """
    pending = [(value, 0, False)]
    active = set()
    keys = nodes = 0
    while pending:
        node, depth, leaving = pending.pop()
        if leaving:
            active.remove(id(node))
            continue
        nodes += 1
        if nodes > MAX_NODES:
            raise LabError("input.limit")
        kind = type(node)
        if kind in (dict, list):
            if id(node) in active:
                raise LabError("input.invalid_json")
            depth += 1
            if depth > MAX_DEPTH:
                raise LabError("input.limit")
            if kind is dict:
                keys += len(node)
                if keys > MAX_KEYS:
                    raise LabError("input.limit")
                if any(type(key) is not str for key in node):
                    raise LabError("input.invalid_json")
                children = [item for pair in node.items() for item in pair]
            else:
                if len(node) > MAX_ARRAY:
                    raise LabError("input.limit")
                children = node
            active.add(id(node))
            pending.append((node, depth, True))
            pending.extend((child, depth, False) for child in reversed(children))
        elif kind is str:
            if len(node) > MAX_STRING_BYTES:
                raise LabError("input.limit")
            if any(0xD800 <= ord(char) <= 0xDFFF for char in node):
                raise LabError("input.encoding")
            spelling = json.dumps(node, ensure_ascii=False)
            if len(spelling.encode("utf-8")) - 2 > MAX_STRING_BYTES:
                raise LabError("input.limit")
        elif kind is int:
            # Bound conversion before str() (including Python's huge-int guard).
            if node.bit_length() > 54 or len(str(node)) > MAX_INTEGER_TEXT:
                raise LabError("input.number")
        elif kind is float:
            raise LabError("input.number")
        elif node is not None and kind is not bool:
            raise LabError("input.invalid_json")


def parse(raw: bytes):
    """Return bounded native JSON values, or a fixed LabError code."""
    lexical_gate(raw)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        text = None
    if text is None:
        # Raise outside the handler: no raw Unicode exception in __context__.
        raise LabError("input.encoding")
    failed = False
    try:
        value = json.loads(text, parse_int=_integer, parse_float=_no_number,
                           parse_constant=_no_number, object_pairs_hook=_pairs)
    except (ValueError, RecursionError):
        failed = True
    if failed:
        # JSONDecodeError retains its entire doc; do not attach it to LabError.
        raise LabError("input.invalid_json")
    check_tree(value)
    return value
