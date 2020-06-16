"""
Translates Jack virtual machine code into hack assembly code.

Process:
Loop through the virtual machine code, ignoring comments.
Translate each line into the corresponding set of assembly instructions
Handles memory segments, logical and arithmetic operations,
branching and function calling.
"""

from pathlib import Path
from translator_asm import *

def one_arg_asm(*args, **kwargs):
    "Create an unary operation"
    asm = load_1_arg + asm_1_arg
    return asm.format(*args, **kwargs)


def two_arg_asm(*args, logic=True, extra="", **kwargs):
    "Create a binary operation"
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

addr_segments = {
    'pointer':  lambda o,**k: {'addr':3+int(o),    'val':'M'},
    'temp':     lambda o,**k: {'addr':5+int(o),    'val':'M'},
    'constant': lambda o,**k: {'addr':o,           'val':'A'},
    'static':   lambda o,filename,**k: {'addr':filename+'.Static.'+o, 'val':'M'}
}
push_segments = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS', 'that': 'THAT'}


def push(segment, offset, **kwargs):
    "Push a value from a particular memory segment to the stack"
    if segment in push_segments:
        return seg_push.format(segment=push_segments[segment], addr=offset)
    elif segment in addr_segments:
        return address_push.format(**addr_segments[segment](offset, **kwargs))
    else: raise ValueError(segment, offset)


def pop(segment, offset, **kwargs):
    "Pop a value from the stack to a particular memory segment"
    assert segment != 'constant'
    if segment in push_segments:
        return seg_pop.format(segment=push_segments[segment], addr=offset)
    elif segment in addr_segments:
        return address_pop.format(**addr_segments[segment](offset, **kwargs))
    else: raise ValueError(segment, offset)


def label(name, **kwargs):
    "Add an assembly label"
    return "("+name+")"


def goto(name, **kwargs):
    "Unconditionally jump to `name`"
    return "@"+name+"\n0;JMP"


def if_goto(name, **kwargs):
    "Conditionally jump to `name` on the last value in the stack."
    return """@SP
AM=M-1
D=M
@"""+name+"\nD;JNE"


def init():
    "Init SP to 256 and call Sys.init"
    return """@256
D=A
@SP
M=D // SP = 256
""" + call('Sys.init', '0', '0')


def call(func_name, nargs, i, **kwargs):
    """Call an assembly function with n arguments
    Stores callers state and sets functions stack"""
    out = "\n".join([push('constant', '{name}$ret.{i}'),
                    address_push.format(addr='LCL',val='M'),
                    address_push.format(addr='ARG',val='M'),
                    address_push.format(addr='THIS',val='M'),
                    address_push.format(addr='THAT',val='M')])
    out += "\n" + call_asm
    return out.format(name=func_name, i=i, offset=int(nargs)+5)


def function(func_name, nlocals, **kwargs):
    "Create an assembly function. Initialises `nlocals` local vars to 0"
    out = func_asm.format(funcname=func_name)
    if int(nlocals)>0: out += '\n'
    out += "\n".join(push('constant', '0') for _ in range(int(nlocals)))
    return out


def return_func(**kwargs):
    """Return from a function call by restoring the state
    and popping the returned value."""
    return return_asm_pre + pop('argument', 0) + return_asm_post


def get_lines(filename):
    "Generate stripped code lines from a text file."
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

# Common arguments for commands: args (from vm), filename, line id
memory_commands = {'push': push, 'pop': pop}
branch_commands = {'goto': goto, 'if-goto': if_goto, 'label': label}
func_commands = {'function': function, 'return': return_func, 'call': call}

def get_command(cmd):
    "Get the command for a particular VM function."
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
    "Translate a single file into fileout. Annotate adds block comments."
    fn = Path(filename).stem
    for i,line in enumerate(get_lines(filename)):
        words = [w for w in line.split(' ') if len(w)>0]
        if annotate: print('\n// '+line, file=fileout)
        cmd = get_command(words[0])
        print(cmd(*words[1:], i=i, filename=fn), file=fileout)

def translator(filenames, fileout, annotate=False):
    """Translate a set of files into a single output file `fileout`.
    Initialises the stack pointer to 256 and calls the sys function
    init before translating other code.

    Parameters:
        filenames (list): a list of .vm filenames the translate.
        fileout (str): the file handle to write to.
        annotate (bool): add block comments to the generated asm.
    """
    if annotate: print("// Generated hack asm file.\n\n// Init sys call.", file=fileout)
    print(init(), file=fileout)
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
