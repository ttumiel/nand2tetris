"Tokenize jack files into tokens and token types."

from enum import IntEnum
import re

class TokenType(IntEnum):
    KEYWORD = 1
    SYMBOL = 2
    INTCNST = 3
    STRCNST = 4
    IDENTIFIER = 5

class JackTokenizer:
    def __init__(self, filename):
        self.file = filename
        self.symbols = set('{}()[].,;+-*/&|<>=~')
        self.keywords = {'class', 'constructor', 'function', 'method',
                        'field', 'static', 'var', 'int', 'char', 'boolean',
                        'void', 'true', 'false', 'null', 'this', 'let', 'do',
                        'if', 'else', 'while', 'return'}
        self.identifiers = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        self.splits = re.compile('([ {}()[\].,;+\-*/&|<>=~])(?![\w ]+")')

    def __iter__(self):
        for line in self.get_lines():
            for token in self.splits.split(line):
                if len(token)>0 and token != ' ':
                    yield token, self.get_token_type(token)

    def get_token_type(self, token):
        if token in self.symbols:
            return TokenType.SYMBOL
        if token in self.keywords:
            return TokenType.KEYWORD
        if token[0] == '"' and token[-1] == '"':
            return TokenType.STRCNST
        if token.isdigit():
            return TokenType.INTCNST
        if set(token).issubset(self.identifiers) and not token[0].isdigit():
            return TokenType.IDENTIFIER
        raise ValueError('Token %s not recognized.' % token)

    def get_lines(self):
        "Generate stripped code lines from a text file."
        with open(self.file, 'r') as f:
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
