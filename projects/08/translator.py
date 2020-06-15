"""
Translates Jack virtual machine code into hack assembly code.

Process:
Loop through the virtual machine code, ignoring comments.
Translate each line into the corresponding set of assembly instructions
"""

from pathlib import Path


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
    'add': lambda **k: two_arg_asm(op='+', logic=False),
    'sub': lambda **k: two_arg_asm(op='-', logic=False),
    'neg': lambda **k: one_arg_asm(op='-'),

    # logical
    'eq': lambda i,**k: two_arg_asm(cmp='EQ', uuid=i),
    'gt': lambda i,**k: two_arg_asm(cmp='GT', uuid=i),
    'lt': lambda i,**k: two_arg_asm(cmp='LT', uuid=i),

    # These work if the boolean arguments are _always_ represented as -1/0.
    'and': lambda **k: two_arg_asm(op='&', logic=False),
    'or': lambda **k: two_arg_asm(op='|', logic=False),
    'not': lambda **k: one_arg_asm(op='!')
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

def push(segment, offset, **kwargs):
    if segment in push_segments:
        return seg_push.format(segment=push_segments[segment], addr=offset)
    elif segment in addr_segments:
        return address_push.format(**addr_segments[segment](offset))
    else: raise ValueError(segment, offset)

def pop(segment, offset, **kwargs):
    assert segment != 'constant'
    if segment in push_segments:
        return seg_pop.format(segment=push_segments[segment], addr=offset)
    elif segment in addr_segments:
        return address_pop.format(**addr_segments[segment](offset))
    else: raise ValueError(segment, offset)

def label(name, **kwargs):
    return "("+name+")"

def goto(name, **kwargs):
    return "@"+name+"\n0;JMP"

def if_goto(name, **kwargs):
    return """@SP
AM=M-1
D=M
@"""+name+"\nD;JNE"


def init():
    return """@256
D=A
@SP
M=D // SP = 256
""" + call('Sys.init', '0', '0')

call_asm = """@{offset}
D=A
@SP
D=M-D // D=SP-5-nargs
@ARG
M=D // ARG = SP-5-nargs
@SP
D=M
@LCL
M=D
@{name}
0;JMP
({name}$ret.{i})
"""

def call(func_name, nargs, i, **kwargs):
    out = "\n".join([push('constant', '{name}$ret.{i}'), push('constant', 'LCL'),
           push('constant', 'ARG'), push('constant', 'THIS'), push('constant', 'THAT')])
    out += "\n" + call_asm
    return out.format(name=func_name, i=i, offset=int(nargs)+5)


func_asm = "({filename}.{funcname})\n"

def function(func_name, nlocals, filename, **kwargs):
    out = func_asm.format(funcname=func_name, filename=filename)
    out += "\n".join(push('local', '0') for _ in range(int(nlocals)))
    return out


return_asm = pop('argument', 0) + """// RETURN
@ARG
D=M+1
@SP
M=D

@LCL
D=M-1 // LCL-1
@R14
AM=D
D=M
@THAT
M=D // THAT = *(LCL-1)

@R14
D=M-1 // LCL-2
@R14
AM=D
D=M
@THIS
M=D // THIS = *(LCL-2)

@R14
D=M-1 // LCL-3
@R14
AM=D
D=M
@ARG
M=D // ARG = *(LCL-3)

@R14
D=M-1 // LCL-4
@R14
AM=D
D=M
@LCL
M=D // LCL = *(LCL-4)

@R14
A=M-1 // LCL-5
0;JMP // goto lcl-5 == retAddr
// END RETURN
"""


def return_func(**kwargs):
    return return_asm

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
                        yield line.strip()
            elif not block_comment:
                if len(line)>0:
                    yield line.strip()

# Common api: args, filename, line i
memory_commands = {'push': push, 'pop': pop}
branch_commands = {'goto': goto, 'if-goto': if_goto, 'label': label}
func_commands = {'function': function, 'return': return_func, 'call': call}

def get_command(cmd):
    if cmd in arithmetic_operations:
        return arithmetic_operations[cmd]
    if cmd in memory_commands:
        return memory_commands[cmd]
    if cmd in branch_commands:
        return branch_commands[cmd]
    if cmd in func_commands:
        return func_commands[cmd]
    raise ValueError('Command not recognized:', cmd)

def translate_file(filename, fileout, annotate=False):
    fn = Path(filename).stem
    for i,line in enumerate(get_lines(filename)):
        words = [w for w in line.split(' ') if len(w)>0]
        if annotate: print('\n// '+line, file=fileout)
        cmd = get_command(words[0])
        print(cmd(*words[1:], i=i, filename=fn), file=fileout)

def translator(filenames, fileout, annotate=False):
    if annotate: print("// Generated hack asm file.\n\n// Init sys call.", file=fileout)
    # print(init(), file=fileout)
    for f in filenames:
        print(f'Translating {f}')
        translate_file(f, fileout, annotate)

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VM to Hack Translator.')
    parser.add_argument('filename', type=str, nargs='+',
                        help='Filenames to process.')
    parser.add_argument('--output', '-o', type=str,
                        help='Filename of the output.')
    parser.add_argument('--annotate', action='store_true',
                        help='Annotate the asm file with comments.')

    args = parser.parse_args()

    f0 = Path(args.filename[0])
    if len(args.filename)==1 and f0.is_dir():
        args.filename = [str(p) for p in f0.iterdir() if p.suffix == '.vm']

    if args.output is None:
        fout = str(f0/f0.stem)+'.asm' if f0.is_dir() else str(f0.parent/f0.stem)+'.asm'

    with open(args.output or fout, 'w') as fout:
        translator(args.filename, fout, annotate=args.annotate)
