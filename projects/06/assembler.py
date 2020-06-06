"""
Process:
- Variables should be stored in a lookup table
- This table can store predefined constants too
- The assembler will first find all variables and add then to the table
- The first pass can also do some preprocessing like removing whitespace and comments.
- The assembler will then go line by line replacing the files with their equivalent binary codes.

e.g.
(OUTPUT_FIRST)
   @R0
   D=M
(OUTPUT_D)
   @R2
   M=D

store OUTPUT_FIRST=linenum
store OUTPUT_D=linenum
remove whitespace and comments

for line in lines:
    line.replace(
        @ => 0
        SYMBOL => binary value
        C-instruction => [1 1 1 ac1 c2 c3 c4 c5 c6 d1 d2 d3 j1 j2 j3]
    )
"""

import re

dests = {
    'M': 1,
    'D': 2,
    'A': 4
}

jumps = {
    'jgt': 1,
    'jeq': 2,
    'jge': 3,
    'jlt': 4,
    'jne': 5,
    'jle': 6,
    'jmp': 7,
}

VALID_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.$')

class SymbolTable:
    def __init__(self):
        registers = {f"R{v}":v for v in range(16)}
        self.symbols = {
            **registers,
            'SCREEN': 16384,
            'KBD': 24576,
            'SP': 0,
            'LCL': 1,
            'ARG': 2,
            'THIS': 3,
            'THAT': 4
        }
        self.counter = 16

    def __getitem__(self, k):
        if k not in self.symbols:
            self.push(k)
        return to_bin(self.symbols[k])

    def __setitem__(self, k, v):
        assert set(k).issubset(VALID_CHARS)
        if k not in self.symbols:
            self.symbols[k] = v

    def push(self, symbol):
        if symbol not in self.symbols:
            self.symbols[symbol] = self.counter
            self.counter += 1

    def __repr__(self):
        return repr(self.symbols)

def to_bin(value, pad=15):
    return f"{{:0>{pad}}}".format(bin(value)[2:])

def remove_comments(generator):
    block_comment=False
    for line in generator:
        line = line[:-1].replace(' ', '')
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

def assembler(filename, output=None):
    assert filename[-4:] == '.asm', "File type should be '.asm'"

    st = SymbolTable()
    cleaned_lines = []
    symbol_count = 0
    with open(filename, 'r') as f:
        for i,line in enumerate(remove_comments(f.readlines())):
            if line[0] == '(' and line[-1] == ')':
                symbol = line[1:-1]
                assert set(symbol).issubset(VALID_CHARS)
                st[symbol] = i - symbol_count
                symbol_count += 1
            else:
                cleaned_lines.append(line)

    out = filename[:-4]+".hack" if output is None else output
    with open(out, 'w') as f:
        for line in cleaned_lines:
            if line[0] == '@':
                print(parse_a_instruction(line, st), file=f)
            else:
                print(parse_c_instruction(line), file=f)

def parse_a_instruction(line, st):
    v = line[1:]
    if v.isdecimal():
        v = int(v)
        assert v < 2**15
        return '0' + to_bin(v)
    else:
        return '0'+"{:0>15}".format(st[v])

def parse_c_instruction(line):
    _j = line.find(';')
    j = to_bin(jumps[line[_j+1:].lower()], pad=3) if _j > 0 else '000'
    line = line if _j==-1 else line[:_j]

    split = line.split('=')
    if len(split)>1:
        dest, comp = split
        d = to_bin(sum(dests[a] for a in dest), 3)
    else:
        comp = split[0]
        d = '000'

    a = str(int('M' in comp))
    c = parse_computation(comp)

    return "111" + a + c + d + j

def parse_computation(comp):
    """While this function is at least clear in the operations,
    it still feels pretty dirty. If I really wanted better
    understanding of each computation code, I could create
    classes for each function and eval them to use pythons
    processing to build the computation but this shall suffice.
    """
    if comp == '0':
        return '101010'
    if comp == '1':
        return '111111'
    if comp == '-1':
        return '111010'
    if comp == 'D':
        return '001100'
    if comp == 'A' or comp =='M':
        return '110000'
    if comp == '!D':
        return '001101'
    if re.match(r'![MA]', comp):
        return '110001'
    if comp == '-D':
        return '001111'
    if re.match(r'-[MA]', comp):
        return '110011'
    if comp == 'D+1' or comp == '1+D':
        return '011111'
    if re.match(r'[MA]\+1', comp) or re.match(r'1\+[MA]', comp):
        return '110111'
    if comp == 'D-1':
        return '001110'
    if re.match(r'[MA]-1', comp):
        return '110010'
    if re.match(r'D\+[MA]', comp) or re.match(r'[MA]\+D', comp):
        return '000010'
    if re.match(r'D-[MA]', comp):
        return '010011'
    if re.match(r'[MA]-D', comp):
        return '000111'
    if re.match(r'D&[MA]', comp) or re.match(r'[MA]&D', comp):
        return '000000'
    if re.match(r'D\|[MA]', comp) or re.match(r'[MA]\|D', comp):
        return '010101'
    raise ValueError(f'Computation not recognized: {comp}')

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Hack assembler.')
    parser.add_argument('filename', type=str, nargs='+',
                        help='Filenames to process.')
    parser.add_argument('--outputs', '-o', type=str, nargs='+',
                        help='Filenames of the outputs.')

    args = parser.parse_args()
    if args.outputs is None: args.outputs = [None]*len(args.filename)
    assert len(args.filename) == len(args.outputs)

    for fn, fo in zip(args.filename, args.outputs):
        assembler(fn, fo)
