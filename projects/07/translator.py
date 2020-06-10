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
log_2_args = "D=M-D"

log_cmp = """
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
(LOG_{cmp}_false.{uuid})
"""

arth_1_arg = "M={op}M // *SP=D"

log_1_arg = "D=M" # Unused


def one_arg_asm(*args, logic=True, **kwargs):
    asm = load_1_arg
    asm += (log_1_arg+log_cmp) if logic else arth_1_arg
    return asm.format(*args, **kwargs)

def two_arg_asm(*args, logic=True, extra="", **kwargs):
    asm = load_2_args
    asm += (log_2_args+log_cmp) if logic else arth_2_args
    return asm.format(*args, extra=extra, **kwargs)

arithmetic_operations = {
    # arithmetic
    'add': lambda _: two_arg_asm(op='+', logic=False),
    'sub': lambda _: two_arg_asm(op='-', logic=False),
    'neg': lambda _: one_arg_asm(op='-', logic=False),

    # logical
    'eq': lambda uuid: two_arg_asm(cmp='EQ', uuid=uuid),
    'gt': lambda uuid: two_arg_asm(cmp='GT', uuid=uuid),
    'lt': lambda uuid: two_arg_asm(cmp='LT', uuid=uuid),

    # These work if the boolean arguments are _always_ represented as -1/0.
    'and': lambda _: two_arg_asm(op='&', logic=False),
    'or': lambda _: two_arg_asm(op='|', logic=False),
    'not': lambda uuid: one_arg_asm(op='!', logic=False)
}

push_op = """@{segment}
D=M // D=base_addr
@{addr}
A=D+A // A=base_addr+offset
D=M // D=val
@SP
A=M
M=D
@SP
M=M+1
"""

pop_op = """
@{segment}
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
M=D
"""

static_pop = """
@SP
AM=M-1
D=M
@Static.{i}
M=D
"""

static_push = """
@Static.{i}
D=M
@SP
A=M
M=D
@SP
M=M+1
"""

tmp_ptr = {'pointer': 3, 'temp': 5}

ptr_tmp_pop = """
@SP
AM=M-1 //SP--
D=M // D=val
@{tmp_ptr} // +i
M=D
"""

ptr_tmp_push = """
@{tmp_ptr} // +i
D=M // D=val
@SP
A=M
M=D
@SP
M=M+1
"""

cnst_push = """
@{constant}
D=A // D=val
@SP
A=M
M=D
@SP
M=M+1
"""

push_segments = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS', 'that': 'THAT'} # add vars pointer=3, temp=5

# remove duplicate
def push(segment, offset):
    if segment in push_segments:
        return push_op.format(segment=push_segments[segment], addr=offset)
    elif segment in tmp_ptr:
        return ptr_tmp_push.format(tmp_ptr=tmp_ptr[segment] + int(offset))
    elif segment == 'constant':
        return cnst_push.format(constant=offset)
    elif segment == 'static':
        return static_push.format(i=offset)
    else: raise ValueError(segment, offset)

def pop(segment, offset):
    if segment in push_segments:
        return pop_op.format(segment=push_segments[segment], addr=offset)
    elif segment in tmp_ptr:
        return ptr_tmp_pop.format(tmp_ptr=tmp_ptr[segment] + int(offset))
    elif segment == 'static':
        return static_pop.format(i=offset)
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

def translator(filename):
    print(filename[:-2] + 'asm')
    with open(filename[:-2] + 'asm', 'w') as f:
        for i,line in enumerate(get_lines(filename)):
            words = line.split(' ')
            if len(words) == 1:
                print(parse_arithmetic(words, i), file=f)
            elif len(words) == 3:
                print(parse_memory(words), file=f)
            else:
                raise ValueError('Line not recognized:', line)

def get_command(cmd):
    return

def parse_arithmetic(words, n):
    return arithmetic_operations[words[0]](n)

def parse_memory(words):
    if words[0] == 'push':
        return push(words[1], words[2])
    else:
        return pop(words[1], words[2])

# translator('./StackArithmetic/StackTest/StackTest.vm')
# translator('./StackArithmetic/SimpleAdd/SimpleAdd.vm')
# translator('./MemoryAccess/BasicTest/BasicTest.vm')
translator('./MemoryAccess/PointerTest/PointerTest.vm')
translator('./MemoryAccess/StaticTest/StaticTest.vm')
