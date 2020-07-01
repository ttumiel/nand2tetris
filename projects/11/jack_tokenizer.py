"Tokenize jack files into tokens and token types."

from enum import Enum
import re

class TokenType(Enum):
    KEYWORD = 'keyword'
    SYMBOL = 'symbol'
    INTCNST = 'integerConstant'
    STRCNST = 'stringConstant'
    IDENTIFIER = 'identifier'

class JackTokenizer:
    def __init__(self, filename):
        self.file = filename
        self.symbols = set('{}()[].,;+-*/&|<>=~')
        self.keywords = {'class', 'constructor', 'function', 'method',
                        'field', 'static', 'var', 'int', 'char', 'boolean',
                        'void', 'true', 'false', 'null', 'this', 'let', 'do',
                        'if', 'else', 'while', 'return'}
        self.identifiers = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        self.splits = re.compile('"[^"]*"|\w+|[{}()[\].,;+\-*\/&|<>=~]')
        self.comments = re.compile('//|/\*')

    def __iter__(self):
        for line in self.get_lines():
            for token in self.splits.findall(line):
                token_type = self.get_token_type(token)
                if token_type == TokenType.STRCNST: token = token[1:-1]
                yield token, token_type

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
                if block_comment:
                    if re.search('\*/', line) is not None:
                        block_comment = False
                    continue
                comment = self.comments.search(line)
                if comment is not None:
                    start = comment.start()
                    if comment.group() == '/*':
                        if re.search("\*/", line[start+2:]) is None:
                            block_comment = True
                        continue
                    else:
                        line = line[:start].strip()
                        if len(line)>0:
                            yield line
                elif not block_comment:
                    if len(line)>0:
                        yield line.strip()
