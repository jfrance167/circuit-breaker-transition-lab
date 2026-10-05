import json
import unittest

from breaker_lab.admission import LabError, lexical_gate, parse


class AdmissionTests(unittest.TestCase):
    def rejected(self, raw, code):
        with self.assertRaises(LabError) as caught:
            parse(raw)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.args, (code,))
        self.assertIsNone(caught.exception.__context__)

    def test_bytes_boundary(self):
        self.assertEqual(parse(b"0" + b" " * 65535), 0)
        self.rejected(b"0" + b" " * 65536, "input.limit")
        self.rejected("{}", "input.invalid_json")

    def test_depth_and_brackets_in_strings(self):
        self.assertEqual(parse(b"[" * 8 + b"0" + b"]" * 8), [[[[[[[[0]]]]]]]])
        self.rejected(b"[" * 9 + b"0" + b"]" * 9, "input.limit")
        self.assertEqual(parse(b'"[{}]"'), "[{}]")
        for raw in (b"[}", b"]", b"[0", b'"unterminated'):
            self.rejected(raw, "input.invalid_json")

    def test_encoded_string_boundary_and_escape_parity(self):
        self.assertEqual(len(parse(b'"' + b"x" * 128 + b'"')), 128)
        self.rejected(b'"' + b"x" * 129 + b'"', "input.limit")
        for value in ('a"b', 'a\\', 'a\\"[', "é" * 64):
            self.assertEqual(parse(json.dumps(value, ensure_ascii=False).encode()), value)
        self.rejected(('"' + "é" * 65 + '"').encode(), "input.limit")
        self.assertEqual(len(parse(b'"' + b"\\u0061" * 21 + b'"')), 21)
        self.rejected(b'"' + b"\\u0061" * 22 + b'"', "input.limit")

    def test_integer_float_nonfinite_and_duplicate(self):
        self.assertEqual(parse(b"9999999999999999"), 9999999999999999)
        self.rejected(b"99999999999999999", "input.number")
        for raw in (b"1.0", b"1e1", b"NaN", b"Infinity", b"-Infinity"):
            self.rejected(raw, "input.number")
        self.rejected(b'{"x":1,"\\u0078":2}', "input.duplicate")
        self.rejected(b"01", "input.invalid_json")

    def test_unicode_encoding_and_syntax_context(self):
        self.rejected(b'"\xff"', "input.encoding")
        for raw in (b'"\\ud800"', b'{"\\udfff":0}', b'{"x":"\\ud800"}'):
            self.rejected(raw, "input.encoding")
        self.assertEqual(parse(b'"\\ud83d\\ude00"'), "😀")
        self.rejected(b'{"x":}', "input.invalid_json")

    def test_postdecode_array_key_limits(self):
        self.assertEqual(len(parse(json.dumps([0] * 128).encode())), 128)
        self.rejected(json.dumps([0] * 129).encode(), "input.limit")
        raw = json.dumps({str(index): 0 for index in range(1024)}).encode()
        self.assertEqual(len(parse(raw)), 1024)
        self.rejected(json.dumps({str(index): 0 for index in range(1025)}).encode(), "input.limit")

    def test_lexical_gate_is_not_syntax_authority(self):
        raw = b'{"x": [1,]}'
        lexical_gate(raw)
        self.rejected(raw, "input.invalid_json")


if __name__ == "__main__":
    unittest.main()
