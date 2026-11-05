"""Recursive descent Luau parser. Produces a nested AST of dicts."""

from lexer import tokenize

PRECEDENCE = {
    "or": (1, 1),
    "and": (2, 2),
    "<": (3, 3), ">": (3, 3), "<=": (3, 3), ">=": (3, 3),
    "~=": (3, 3), "==": (3, 3),
    "..": (5, 4),
    "+": (6, 6), "-": (6, 6),
    "*": (7, 7), "/": (7, 7), "//": (7, 7), "%": (7, 7),
    "^": (10, 9),
}
UNARY_PREC = 8


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, off=0):
        j = self.pos + off
        return self.tokens[j] if j < len(self.tokens) else {"type": "eof", "value": "<eof>"}

    def advance(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def check(self, ttype, value=None):
        t = self.peek()
        if t["type"] != ttype:
            return False
        return value is None or t["value"] == value

    def match(self, ttype, value=None):
        if self.check(ttype, value):
            return self.advance()
        return None

    def expect(self, ttype, value=None):
        tok = self.match(ttype, value)
        if tok is None:
            raise SyntaxError(
                f"expected {value or ttype!r} got {self.peek()['value']!r}"
            )
        return tok

    def parse_block(self, terms):
        stmts = []
        while True:
            t = self.peek()
            if t["type"] == "eof":
                break
            if t["type"] == "kw" and t["value"] in terms:
                break
            s = self.parse_stmt()
            if s:
                stmts.append(s)
            if self.check("op", ";"):
                self.advance()
        return stmts

    def parse_stmt(self):
        t = self.peek()
        if t["type"] == "kw":
            if t["value"] == "local":
                self.advance()
                if self.check("kw", "function"):
                    self.advance()
                    name = self.expect("name")["value"]
                    params, vararg, body = self.parse_func_body()
                    return {
                        "type": "localfunction", "name": name,
                        "params": params, "isVararg": vararg, "body": body,
                    }
                names = []
                while True:
                    names.append(self.expect("name")["value"])
                    if self.check("op", ":"):
                        self.advance()
                        while not self.check("op", ",") and not self.check("op", "=") \
                              and not self.check("eof"):
                            self.advance()
                    if not self.check("op", ","):
                        break
                    self.advance()
                values = []
                if self.check("op", "="):
                    self.advance()
                    values = self.parse_expr_list()
                return {"type": "local", "names": names, "values": values}

            if t["value"] == "function":
                self.advance()
                first = self.expect("name")["value"]
                parts = [{"name": first, "method": False}]
                while self.check("op", ".") or self.check("op", ":"):
                    sep = self.advance()["value"]
                    parts.append({"name": self.expect("name")["value"], "method": sep == ":"})
                    if sep == ":":
                        break
                is_method = parts[-1]["method"]
                params, vararg, body = self.parse_func_body()
                if is_method:
                    params.insert(0, "self")
                target = {"type": "name", "name": first}
                for p in parts[1:]:
                    target = {"type": "index", "obj": target, "key": p["name"]}
                return {
                    "type": "assign",
                    "targets": [target],
                    "values": [{"type": "func", "params": params,
                                "isVararg": vararg, "body": body}],
                }

            if t["value"] == "if":
                self.advance()
                cond = self.parse_expr()
                self.expect("kw", "then")
                body = self.parse_block({"end", "elseif", "else"})
                branches = [{"cond": cond, "body": body}]
                else_body = None
                while self.check("kw", "elseif"):
                    self.advance()
                    c = self.parse_expr()
                    self.expect("kw", "then")
                    b = self.parse_block({"end", "elseif", "else"})
                    branches.append({"cond": c, "body": b})
                if self.check("kw", "else"):
                    self.advance()
                    else_body = self.parse_block({"end"})
                self.expect("kw", "end")
                return {"type": "if", "branches": branches, "elseBody": else_body}

            if t["value"] == "while":
                self.advance()
                cond = self.parse_expr()
                self.expect("kw", "do")
                body = self.parse_block({"end"})
                self.expect("kw", "end")
                return {"type": "while", "cond": cond, "body": body}

            if t["value"] == "repeat":
                self.advance()
                body = self.parse_block({"until"})
                self.expect("kw", "until")
                cond = self.parse_expr()
                return {"type": "repeat", "body": body, "cond": cond}

            if t["value"] == "for":
                self.advance()
                name = self.expect("name")["value"]
                if self.check("op", "="):
                    self.advance()
                    start = self.parse_expr()
                    self.expect("op", ",")
                    stop = self.parse_expr()
                    step = None
                    if self.check("op", ","):
                        self.advance()
                        step = self.parse_expr()
                    self.expect("kw", "do")
                    body = self.parse_block({"end"})
                    self.expect("kw", "end")
                    return {"type": "fornum", "var": name, "startE": start,
                            "stopE": stop, "stepE": step, "body": body}
                names = [name]
                while self.check("op", ","):
                    self.advance()
                    names.append(self.expect("name")["value"])
                self.expect("kw", "in")
                exprs = self.parse_expr_list()
                self.expect("kw", "do")
                body = self.parse_block({"end"})
                self.expect("kw", "end")
                return {"type": "forin", "vars": names, "exprs": exprs, "body": body}

            if t["value"] == "do":
                self.advance()
                body = self.parse_block({"end"})
                self.expect("kw", "end")
                return {"type": "do", "body": body}

            if t["value"] == "return":
                self.advance()
                exprs = []
                nx = self.peek()
                if not (nx["type"] == "eof" or (nx["type"] == "kw" and nx["value"] in
                        {"end", "elseif", "else", "until"})
                        or (nx["type"] == "op" and nx["value"] == ";")):
                    exprs = self.parse_expr_list()
                return {"type": "return", "exprs": exprs}

            if t["value"] == "break":
                self.advance()
                return {"type": "break"}

        e = self.parse_primary()
        if e["type"] in ("call", "methodcall"):
            return {"type": "call_stmt", "call": e}
        targets = [e]
        while self.check("op", ","):
            self.advance()
            targets.append(self.parse_primary())
        self.expect("op", "=")
        values = self.parse_expr_list()
        return {"type": "assign", "targets": targets, "values": values}

    def parse_expr_list(self):
        exprs = [self.parse_expr()]
        while self.check("op", ","):
            self.advance()
            exprs.append(self.parse_expr())
        return exprs

    def parse_expr(self, min_prec=0):
        t = self.peek()
        if (t["type"] == "kw" and t["value"] == "not") or \
           (t["type"] == "op" and t["value"] in ("-", "#")):
            op = self.advance()["value"]
            left = {"type": "unop", "op": op, "operand": self.parse_expr(UNARY_PREC)}
        else:
            left = self.parse_primary()

        while True:
            op = self.peek()
            if op["type"] not in ("op", "kw"):
                break
            if op["value"] not in PRECEDENCE:
                break
            lp, rp = PRECEDENCE[op["value"]]
            if lp < min_prec:
                break
            self.advance()
            right = self.parse_expr(rp + 1)
            left = {"type": "binop", "op": op["value"], "left": left, "right": right}
        return left

    def parse_primary(self):
        t = self.peek()
        if t["type"] == "number":
            self.advance()
            return {"type": "number", "value": t["value"]}
        if t["type"] == "string":
            self.advance()
            return {"type": "string", "value": t["value"]}
        if t["type"] == "kw":
            if t["value"] == "nil":
                self.advance(); return {"type": "nil"}
            if t["value"] == "true":
                self.advance(); return {"type": "true"}
            if t["value"] == "false":
                self.advance(); return {"type": "false"}
            if t["value"] == "function":
                self.advance()
                params, vararg, body = self.parse_func_body()
                return {"type": "func", "params": params,
                        "isVararg": vararg, "body": body}
        if t["type"] == "op" and t["value"] == "...":
            self.advance(); return {"type": "vararg"}
        if t["type"] == "op" and t["value"] == "{":
            self.advance()
            entries = []
            while not self.check("op", "}"):
                if self.check("op", "["):
                    self.advance()
                    key = self.parse_expr()
                    self.expect("op", "]")
                    self.expect("op", "=")
                    entries.append({"kind": "expr", "key": key, "value": self.parse_expr()})
                elif self.check("name") and self.peek(1)["type"] == "op" \
                     and self.peek(1)["value"] == "=":
                    k = self.advance()["value"]
                    self.advance()
                    entries.append({"kind": "name", "key": k, "value": self.parse_expr()})
                else:
                    entries.append({"kind": "pos", "value": self.parse_expr()})
                if self.check("op", ",") or self.check("op", ";"):
                    self.advance()
            self.expect("op", "}")
            return {"type": "table", "entries": entries}
        if t["type"] == "op" and t["value"] == "(":
            self.advance()
            e = self.parse_expr()
            self.expect("op", ")")
            return self.parse_suffixes(e)
        if t["type"] == "name":
            self.advance()
            return self.parse_suffixes({"type": "name", "name": t["value"]})
        raise SyntaxError(f"unexpected token {t['value']!r}")

    def parse_suffixes(self, e):
        while True:
            if self.check("op", "."):
                self.advance()
                e = {"type": "index", "obj": e, "key": self.expect("name")["value"]}
            elif self.check("op", "["):
                self.advance()
                k = self.parse_expr()
                self.expect("op", "]")
                e = {"type": "index", "obj": e, "key": k}
            elif self.check("op", ":"):
                self.advance()
                nm = self.expect("name")["value"]
                args = []
                if self.check("string"):
                    args.append({"type": "string", "value": self.advance()["value"]})
                elif self.check("op", "{"):
                    args.append(self.parse_primary())
                elif self.check("op", "("):
                    self.advance()
                    if not self.check("op", ")"):
                        args = self.parse_expr_list()
                    self.expect("op", ")")
                e = {"type": "methodcall", "obj": e, "name": nm, "args": args}
            elif self.check("op", "("):
                self.advance()
                args = []
                if not self.check("op", ")"):
                    args = self.parse_expr_list()
                self.expect("op", ")")
                e = {"type": "call", "fn": e, "args": args}
            elif self.check("string") or self.check("op", "{"):
                args = []
                if self.check("string"):
                    args.append({"type": "string", "value": self.advance()["value"]})
                else:
                    args.append(self.parse_primary())
                e = {"type": "call", "fn": e, "args": args}
            else:
                break
        return e

    def parse_func_body(self):
        self.expect("op", "(")
        params, vararg = [], False
        if not self.check("op", ")"):
            while True:
                if self.check("op", "..."):
                    self.advance()
                    vararg = True
                    break
                params.append(self.expect("name")["value"])
                if self.check("op", ":"):
                    self.advance()
                    while not self.check("op", ",") and not self.check("op", ")"):
                        self.advance()
                if not self.check("op", ","):
                    break
                self.advance()
        self.expect("op", ")")
        body = self.parse_block({"end"})
        self.expect("kw", "end")
        return params, vararg, body


def parse(source):
    return Parser(tokenize(source)).parse_block(set())
