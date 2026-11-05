"""Orchestrator: source → obfuscated Luau source."""

import random
import time

from lexer import tokenize
from parser import Parser
from compiler import compile_ast
from serializer import serialize, encrypt, make_op_map
from vm_template import VM_TEMPLATE

HEADER = """-- [[ Script was obfuscated by Fedora (Group A) ]] --
-- [[ A.T.K i miss you i love you i hope u alive rn.  ]] --

"""


def obfuscate(source, seed=None):
    if seed is None:
        seed = int(time.time() * 1000) ^ random.getrandbits(32)

    rng = random.Random(seed)

    tokens = tokenize(source)
    ast = Parser(tokens).parse_block(set())

    protos = compile_ast(ast)
    op_map = make_op_map(seed)

    bytecode = serialize(protos, op_map, seed)
    SD = rng.randint(100_000, 999_999)
    K = (SD * 31 + 7) % 251 + 1
    payload = encrypt(bytecode, K)

    vm = VM_TEMPLATE.replace("{SEED}", str(SD))
    return HEADER + vm + f'\nreturn runX("{payload}")'


if __name__ == "__main__":
    import sys
    src = sys.stdin.read()
    print(obfuscate(src))
