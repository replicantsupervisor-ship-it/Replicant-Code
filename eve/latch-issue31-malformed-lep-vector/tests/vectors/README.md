# LEP public test vectors

`lep-v1-basic.hex` is a canonical 34-byte LEP v1 envelope. It contains sequence 7, event ID 9 and one TLV with type 1 and bytes `aa bb`. Both the C and Rust decoders use the same layout and `tools/check_test_vector.py` independently verifies its lengths and CRCs.

`invalid/` holds negative golden vectors with stable public decoder-error categories. `tools/check_test_vector.py` asserts they fail plain validation with the expected category: `magic`, `version`, `flags`, `header_crc`, `payload_crc`, or `corrupt: tlv`. The `tlv-length-overrun.hex` fixture is a well-formed LEP v1 header and payload CRC whose sole malformed condition is a TLV length that extends one byte past the payload boundary; decoders must report it as `corrupt: tlv`.

Existing vectors are immutable compatibility fixtures. A breaking wire-format change requires a new protocol version and a new file rather than rewriting an old vector.
