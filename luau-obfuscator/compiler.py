"""AST → custom stack-based bytecode."""

CONST, NIL, TRUE, FALSE, POP, DUP = 1, 2, 3, 4, 5, 6
ADD, SUB, MUL, DIV, MOD, POW, IDIV = 7, 8, 9, 10, 11, 12, 13
NEG, NOT, LEN, CONCAT = 14, 15, 16, 17
EQ, NE, LT, LE, GT, GE = 18, 19, 20, 21, 22, 23
GETLOCAL, SETLOCAL, GETGLOBAL, SETGLOBAL = 24, 25, 26, 27
GETUPVAL, SETUPVAL = 28, 29
NEWTABLE, GETFIELD, SETFIELD, GETINDEX, SETINDEX = 30, 31, 32, 33, 34
CALL, GETSELF, RETURN, RETURN0 = 35, 36, 37, 38
JMP, JT, JF, CLOSURE, VARARG = 39, 40, 41, 42, 43

BINOP_MAP = {
    "+": ADD, "-": SUB, "*": MUL, "/": DIV, "%": MOD, "^": POW,
    "//": IDIV, "..": CONCAT,
    "==": EQ, "~=": NE, "<": LT, "<=": LE, ">": GT, ">=": GE,
}


class Proto:
    def __init__(self):
        self.insts = []
        self.consts = []
        self.const_map = {}
        self.upvals = []
        self.upval_map = {}
        self.num_params = 0
        self.is_vararg = False
        self.nlocals = 0

    def add_const(self, v):
        key = (type(v).__name__, str(v))
        if key in self.const_map:
            return self.const_map[key]
        self.consts.append(v)
        idx = len(self.consts) - 1
        self.const_map[key] = idx
        return idx

    def emit(self, op, a=0, b=0):
        self.insts.append([op, a, b])
        return len(self.insts)

    def patch_jump(self, at, target):
        self.insts[at - 1][1] = target - at


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.locals = {}
        self.next_slot = parent.next_slot if parent else 0

    def declare(self, name):
        slot = self.next_slot
        self.locals[name] = slot
        self.next_slot += 1
        return slot

    def resolve(self, name):
        s = self
        while s:
            if name in s.locals:
                return s.locals[name]
            s = s.parent
        return None


class Compiler:
    def __init__(self):
        self.protos = []

    def new_proto(self):
        p = Proto()
        self.protos.append(p)
        return p, len(self.protos) - 1

    def resolve_upval(self, scope, name, p):
        if not scope.parent:
            return None
        if name in scope.parent.locals:
            slot = scope.parent.locals[name]
            key = f"s:{slot}"
            if key in p.upval_map:
                return p.upval_map[key]
            p.upvals.append({"inStack": True, "idx": slot})
            p.upval_map[key] = len(p.upvals) - 1
            return len(p.upvals) - 1
        return None

    def compile_expr(self, e, scope, p):
        t = e["type"]
        if t == "nil":
            p.emit(NIL)
        elif t == "true":
            p.emit(TRUE)
        elif t == "false":
            p.emit(FALSE)
        elif t in ("number", "string"):
            p.emit(CONST, p.add_const(e["value"]))
        elif t == "vararg":
            p.emit(VARARG)
        elif t == "name":
            slot = scope.resolve(e["name"])
            if slot is not None:
                p.emit(GETLOCAL, slot)
            else:
                uv = self.resolve_upval(scope, e["name"], p)
                if uv is not None:
                    p.emit(GETUPVAL, uv)
                else:
                    p.emit(GETGLOBAL, p.add_const(e["name"]))
        elif t == "index":
            self.compile_expr(e["obj"], scope, p)
            if isinstance(e["key"], str):
                p.emit(GETFIELD, p.add_const(e["key"]))
            else:
                self.compile_expr(e["key"], scope, p)
                p.emit(GETINDEX)
        elif t == "binop":
            op = e["op"]
            if op == "and":
                self.compile_expr(e["left"], scope, p)
                p.emit(DUP)
                j = p.emit(JF)
                p.emit(POP)
                self.compile_expr(e["right"], scope, p)
                p.patch_jump(j, len(p.insts) + 1)
            elif op == "or":
                self.compile_expr(e["left"], scope, p)
                p.emit(DUP)
                j = p.emit(JT)
                p.emit(POP)
                self.compile_expr(e["right"], scope, p)
                p.patch_jump(j, len(p.insts) + 1)
            else:
                self.compile_expr(e["left"], scope, p)
                self.compile_expr(e["right"], scope, p)
                p.emit(BINOP_MAP[op])
        elif t == "unop":
            self.compile_expr(e["operand"], scope, p)
            if e["op"] == "-":
                p.emit(NEG)
            elif e["op"] == "not":
                p.emit(NOT)
            elif e["op"] == "#":
                p.emit(LEN)
        elif t == "call":
            self.compile_expr(e["fn"], scope, p)
            for a in e["args"]:
                self.compile_expr(a, scope, p)
            p.emit(CALL, len(e["args"]))
        elif t == "methodcall":
            self.compile_expr(e["obj"], scope, p)
            p.emit(GETSELF, p.add_const(e["name"]))
            for a in e["args"]:
                self.compile_expr(a, scope, p)
            p.emit(CALL, len(e["args"]) + 1)
        elif t == "table":
            p.emit(NEWTABLE)
            pos = 0
            for entry in e["entries"]:
                p.emit(DUP)
                if entry["kind"] == "pos":
                    pos += 1
                    p.emit(CONST, p.add_const(pos))
                elif entry["kind"] == "name":
                    p.emit(CONST, p.add_const(entry["key"]))
                else:
                    self.compile_expr(entry["key"], scope, p)
                self.compile_expr(entry["value"], scope, p)
                p.emit(SETINDEX)
        elif t == "func":
            cp, ci = self.new_proto()
            cp.num_params = len(e["params"])
            cp.is_vararg = e["isVararg"]
            cs = Scope(scope)
            for nm in e["params"]:
                cs.declare(nm)
            self.compile_block(e["body"], cs, cp)
            cp.nlocals = cs.next_slot
            p.emit(CLOSURE, ci)

    def compile_stmt(self, s, scope, p):
        t = s["type"]
        if t == "local":
            for i, nm in enumerate(s["names"]):
                if i < len(s["values"]):
                    self.compile_expr(s["values"][i], scope, p)
                else:
                    p.emit(NIL)
                slot = scope.declare(nm)
                p.emit(SETLOCAL, slot)
        elif t == "localfunction":
            scope.declare(s["name"])
            cp, ci = self.new_proto()
            cp.num_params = len(s["params"])
            cp.is_vararg = s["isVararg"]
            cs = Scope(scope)
            for nm in s["params"]:
                cs.declare(nm)
            self.compile_block(s["body"], cs, cp)
            cp.nlocals = cs.next_slot
            p.emit(CLOSURE, ci)
            p.emit(SETLOCAL, scope.locals[s["name"]])
        elif t == "assign":
            if len(s["targets"]) != 1 or len(s["values"]) != 1:
                raise NotImplementedError("multiple assignment unsupported")
            target = s["targets"][0]
            if target["type"] == "name":
                self.compile_expr(s["values"][0], scope, p)
                slot = scope.resolve(target["name"])
                if slot is not None:
                    p.emit(SETLOCAL, slot)
                else:
                    uv = self.resolve_upval(scope, target["name"], p)
                    if uv is not None:
                        p.emit(SETUPVAL, uv)
                    else:
                        p.emit(SETGLOBAL, p.add_const(target["name"]))
            elif target["type"] == "index":
                self.compile_expr(target["obj"], scope, p)
                if isinstance(target["key"], str):
                    self.compile_expr(s["values"][0], scope, p)
                    p.emit(SETFIELD, p.add_const(target["key"]))
                else:
                    self.compile_expr(target["key"], scope, p)
                    self.compile_expr(s["values"][0], scope, p)
                    p.emit(SETINDEX)
        elif t == "call_stmt":
            self.compile_expr(s["call"], scope, p)
            p.emit(POP)
        elif t == "if":
            jumps = []
            for br in s["branches"]:
                self.compile_expr(br["cond"], scope, p)
                j = p.emit(JF)
                self.compile_block(br["body"], scope, p)
                end_j = p.emit(JMP)
                p.patch_jump(j, len(p.insts) + 1)
                jumps.append(end_j)
            if s["elseBody"]:
                self.compile_block(s["elseBody"], scope, p)
            for j in jumps:
                p.patch_jump(j, len(p.insts) + 1)
        elif t == "while":
            top = len(p.insts) + 1
            self.compile_expr(s["cond"], scope, p)
            exit_j = p.emit(JF)
            self.compile_block(s["body"], scope, p)
            p.emit(JMP, top - (len(p.insts) + 1))
            p.patch_jump(exit_j, len(p.insts) + 1)
        elif t == "repeat":
            top = len(p.insts) + 1
            self.compile_block(s["body"], scope, p)
            self.compile_expr(s["cond"], scope, p)
            exit_j = p.emit(JT)
            p.emit(JMP, top - (len(p.insts) + 1))
            p.patch_jump(exit_j, len(p.insts) + 1)
        elif t == "fornum":
            slot = scope.declare(s["var"])
            self.compile_expr(s["startE"], scope, p)
            p.emit(SETLOCAL, slot)
            self.compile_expr(s["stopE"], scope, p)
            stop_slot = scope.next_slot
            scope.next_slot += 1
            p.emit(SETLOCAL, stop_slot)
            step_slot = scope.next_slot
            scope.next_slot += 1
            if s["stepE"]:
                self.compile_expr(s["stepE"], scope, p)
            else:
                p.emit(CONST, p.add_const(1))
            p.emit(SETLOCAL, step_slot)
            top = len(p.insts) + 1
            p.emit(GETLOCAL, slot)
            p.emit(GETLOCAL, stop_slot)
            p.emit(LE)
            exit_j = p.emit(JF)
            self.compile_block(s["body"], scope, p)
            p.emit(GETLOCAL, slot)
            p.emit(GETLOCAL, step_slot)
            p.emit(ADD)
            p.emit(SETLOCAL, slot)
            p.emit(JMP, top - (len(p.insts) + 1))
            p.patch_jump(exit_j, len(p.insts) + 1)
        elif t == "return":
            if not s["exprs"]:
                p.emit(RETURN0)
            else:
                for e in s["exprs"]:
                    self.compile_expr(e, scope, p)
                p.emit(RETURN, len(s["exprs"]))
        elif t == "break":
            raise NotImplementedError("break unsupported")
        elif t == "do":
            self.compile_block(s["body"], scope, p)
        else:
            raise NotImplementedError(f"statement {t!r} unsupported")

    def compile_block(self, body, scope, p):
        for s in body:
            self.compile_stmt(s, scope, p)

    def compile(self, ast):
        main, _ = self.new_proto()
        scope = Scope()
        self.compile_block(ast, scope, main)
        main.nlocals = scope.next_slot
        main.emit(RETURN0)
        return self.protos


def compile_ast(ast):
    return Compiler().compile(ast)
