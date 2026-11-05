"""Luau tokenizer. Produces a flat list of token dicts."""

KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while", "continue",
}

# Longest first — order matters for correct greedy matching
MULTI_OPS = [
    "...", "..=", "//=", "==", "~=", "<=", ">=", "::", "->",
    "//", "+=", "-=", "*=", "/=", "%=", "^=", "..",
]


def tokenize(src: str) -> list[dict]:
    tokens: list[dict] = []
    i, n = 0, len(src)

    def peek(off: int = 0) -> str:
        j = i + off
        return src[j] if j < n else ""

    while i < n:
        ch = src[i]

        if ch in " \t\r\n":
            i += 1
            continue

        if ch == "-" and peek(1) == "-":
            if peek(2) == "[":
                j = i + 3
                eqs = ""
                while j < n and src[j] == "=":
                    eqs += "="
                    j += 1
                if j < n and src[j] == "[":
                    closer = "]" + eqs + "]"
                    end = src.find(closer, j + 1)
                    i = n if end < 0 else end + len(closer)
                    continue
            end = src.find("\n", i)
            i = n if end < 0 else end + 1
            continue

        if ch == "[":
            j = i + 1
            eqs = ""
            while j < n and src[j] == "=":
                eqs += "="
                j += 1
            if j < n and src[j] == "[":
                closer = "]" + eqs + "]"
                start = j + 1
                end = src.find(closer, start)
                content = src[start:end] if end >= 0 else src[start:]
                if content.startswith("\n"):
                    content = content[1:]
                tokens.append({"type": "string", "value": content})
                i = n if end < 0 else end + len(closer)
                continue
            tokens.append({"type": "op", "value": "["})
            i += 1
            continue

        if ch in ('"', "'"):
            quote = ch
            i += 1
            buf: list[str] = []
            while i < n:
                c = src[i]
                if c == "\\":
                    esc = peek(1)
                    if esc == "n":
                        buf.append("\n"); i += 2
                    elif esc == "t":
                        buf.append("\t"); i += 2
                    elif esc == "r":
                        buf.append("\r"); i += 2
                    elif esc == "\\":
                        buf.append("\\"); i += 2
                    elif esc == '"':
                        buf.append('"'); i += 2
                    elif esc == "'":
                        buf.append("'"); i += 2
                    elif esc.isdigit():
                        num = esc
                        j = 2
                        while j < 4 and peek(j).isdigit():
                            num += peek(j)
                            j += 1
                        buf.append(chr(int(num) & 0xFF))
                        i += 1 + (j - 1)
                    else:
                        buf.append(esc); i += 2
                elif c == quote:
                    i += 1
                    break
                else:
                    buf.append(c); i += 1
            tokens.append({"type": "string", "value": "".join(buf)})
            continue

        if ch.isdigit() or (ch == "." and peek(1).isdigit()):
            start = i
            while i < n and (src[i].isalnum() or src[i] == "."):
                if src[i] == "." and peek(1) == ".":
                    break
                i += 1
            try:
                val = float(src[start:i])
                if val.is_integer():
                    val = int(val)
            except ValueError:
                val = 0
            tokens.append({"type": "number", "value": val})
            continue

        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (src[i].isalnum() or src[i] == "_"):
                i += 1
            word = src[start:i]
            tokens.append({
                "type": "kw" if word in KEYWORDS else "name",
                "value": word,
            })
            continue

        matched = False
        for op in MULTI_OPS:
            if src.startswith(op, i):
                tokens.append({"type": "op", "value": op})
                i += len(op)
                matched = True
                break
        if matched:
            continue

        tokens.append({"type": "op", "value": ch})
        i += 1

    tokens.append({"type": "eof", "value": "<eof>"})
    return tokens
