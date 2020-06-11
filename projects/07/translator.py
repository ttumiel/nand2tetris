"""
Translates Jack virtual machine code into hack assembly code.

Process:
Loop through the virtual machine code, ignoring comments.
Translate each line into the corresponding set of assembly instructions
"""


# Loads 2 args off the stack into M and D
# M = arg1, D = arg2
load_2_args = """@SP
M=M-1 // SP--
A=M
D=M // D=*SP
@SP
A=M-1 // SP--
"""

# Load one arg off the stack into D
load_1_arg = """@SP
A=M-1 // SP--
"""

# Apply an arithmetic operation to 2 args
arth_2_args = "M=M{op}D // *SP+D"

# Apply a logic operation to 2 args
log_2_args = """D=M-D
@LOG_{cmp}_true.{uuid}
D;J{cmp}
@SP
A=M-1
M=0
@LOG_{cmp}_false.{uuid}
0;JMP
(LOG_{cmp}_true.{uuid})
@SP
A=M-1
M=-1
(LOG_{cmp}_false.{uuid})"""

# apply an operation to 1 arg
asm_1_arg = "M={op}M // *SP=D"

def one_arg_asm(*args, **kwargs):
    asm = load_1_arg + asm_1_arg
    return asm.format(*args, **kwargs)

def two_arg_asm(*args, logic=True, extra="", **kwargs):
    asm = load_2_args
    asm += log_2_args if logic else arth_2_args
    return asm.format(*args, extra=extra, **kwargs)

arithmetic_operations = {
    # arithmetic
    'add': lambda _: two_arg_asm(op='+', logic=False),
    'sub': lambda _: two_arg_asm(op='-', logic=False),
    'neg': lambda _: one_arg_asm(op='-'),

    # logical
    'eq': lambda uuid: two_arg_asm(cmp='EQ', uuid=uuid),
    'gt': lambda uuid: two_arg_asm(cmp='GT', uuid=uuid),
    'lt': lambda uuid: two_arg_asm(cmp='LT', uuid=uuid),

    # These work if the boolean arguments are _always_ represented as -1/0.
    'and': lambda _: two_arg_asm(op='&', logic=False),
    'or': lambda _: two_arg_asm(op='|', logic=False),
    'not': lambda uuid: one_arg_asm(op='!')
}

seg_push = """@{segment}
D=M // D=base_addr
@{addr}
A=D+A // A=base_addr+offset
D=M // D=val
@SP
A=M
M=D
@SP
M=M+1"""

seg_pop = """@{segment}
D=M // D=base_addr
@{addr} // offset
D=D+A // D = base_addr+offset
@R13
M=D
@SP
AM=M-1 //SP--
D=M // D=val
@R13
A=M
M=D"""

address_pop = """@SP
AM=M-1
D=M
@{addr}
M=D"""

address_push = """@{addr}
D={val}
@SP
A=M
M=D
@SP
M=M+1"""

addr_segments = {
    'pointer':  lambda i: {'addr':3+int(i),    'val':'M'},
    'temp':     lambda i: {'addr':5+int(i),    'val':'M'},
    'constant': lambda i: {'addr':i,           'val':'A'},
    'static':   lambda i: {'addr':'Static.'+i, 'val':'M'}
}
push_segments = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS', 'that': 'THAT'}

# remove duplicate
def push(segment, offset):
    if segment in push_segments:
        return seg_push.format(segment=push_segments[segment], addr=offset)
    elif segment in addr_segments:
        return address_push.format(**addr_segments[segment](offset))
    else: raise ValueError(segment, offset)

def pop(segment, offset):
    assert segment != 'constant'
    if segment in push_segments:
        return seg_pop.format(segment=push_segments[segment], addr=offset)
    elif segment in addr_segments:
        return address_pop.format(**addr_segments[segment](offset))
    else: raise ValueError(segment, offset)


def get_lines(filename):
    with open(filename, 'r') as f:
        block_comment=False
        for line in f:
            line = line[:-1]
            comment = line.find('/')
            if comment != -1:
                if block_comment and comment!=0:
                    if line[comment-1] == '*':
                        block_comment = False
                elif line[comment+1] in '/*':
                    block_comment = (line[comment+1] == '*'
                        and not line[comment+2:].find('*/')>=0)
                    line = line[:comment]
                    if len(line)>0:
                        yield line
            elif not block_comment:
                if len(line)>0:
                    yield line

def translator(filename, fileout=None, annotate=False):
    fileout = fileout or filename[:-2] + 'asm'
    with open(fileout, 'w') as f:
        for i,line in enumerate(get_lines(filename)):
            words = line.split(' ')
            if annotate: print('\n// '+line, file=f)
            if len(words) == 1:
                print(parse_arithmetic(words, i), file=f)
            elif len(words) == 3:
                print(parse_memory(words), file=f)
            else:
                raise ValueError('Line not recognized:', line)

def parse_arithmetic(words, n):
    return arithmetic_operations[words[0]](n)

def parse_memory(words):
    if words[0] == 'push':
        return push(words[1], words[2])
    else:
        return pop(words[1], words[2])

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VM to Hack Translator.')
    parser.add_argument('filename', type=str, nargs='*',
                        help='Filenames to process.')
    parser.add_argument('--outputs', '-o', type=str, nargs='+',
                        help='Filenames of the outputs.')
    parser.add_argument('--test', action='store_true',
                        help='Generate test files.')
    parser.add_argument('--annotate', action='store_true',
                        help='Annotate the asm file with comments.')

    args = parser.parse_args()

    if args.test:
        translator('./StackArithmetic/StackTest/StackTest.vm', annotate=args.annotate)
        translator('./StackArithmetic/SimpleAdd/SimpleAdd.vm', annotate=args.annotate)
        translator('./MemoryAccess/BasicTest/BasicTest.vm', annotate=args.annotate)
        translator('./MemoryAccess/PointerTest/PointerTest.vm', annotate=args.annotate)
        translator('./MemoryAccess/StaticTest/StaticTest.vm', annotate=args.annotate)

    if args.outputs is None: args.outputs = [None]*len(args.filename)
    assert len(args.filename) == len(args.outputs)

    for fn, fo in zip(args.filename, args.outputs):
        translator(fn, fo, annotate=args.annotate)
