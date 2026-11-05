# Fedora Obfuscator

A bytecode-VM obfuscator for Luau, written from scratch in Python.

Takes Luau source → parses to AST → compiles to custom bytecode → XOR-encrypts it → ships a Luau VM interpreter that runs the bytecode.

---

## What it does

| Stage | File | Description |
|---|---|---|
| **Lex** | `lexer.py` | Tokenizes Luau: strings, long strings, comments, all operators |
| **Parse** | `parser.py` | Recursive-descent → nested AST |
| **Compile** | `compiler.py` | AST → 43-opcode stack-based bytecode |
| **Serialize** | `serializer.py` | Bytecode → binary, per-run randomized opcodes, per-string XOR keys |
| **Encrypt** | `serializer.py` | XOR the whole payload with a derived key |
| **Emit** | `obfuscator.py` | Prepend watermark, append VM + `runX(...)` call |

---

## Features

- Full Luau expression parser (all operators, precedence, method calls)
- Locals, functions, closures, upvalues (1 level)
- Tables, `if`/`elseif`/`else`, `while`, `repeat`, numeric `for`
- **Randomized opcode map** per run — no fixed opcode numbers to hardcode against
- **Per-string XOR keys** — `"print"` doesn't appear as plaintext in the payload
- **Seeded VM key** — the XOR key is derived from the seed at runtime, not stored in source
- Custom **Fedora watermark** on every output

---

## Quick start

### CLI

```bash
pip install -r requirements.txt
echo 'print("hello")' | python obfuscator.py
