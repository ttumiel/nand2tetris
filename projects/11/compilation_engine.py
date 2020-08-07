"Compile the tokenized jack file into syntactical components."

from contextlib import contextmanager

from jack_tokenizer import JackTokenizer, TokenType
from symbol_table import SymbolTable
from vm_writer import VMWriter

END_STMT = {'let', 'do', 'while', 'if', 'return', '}'}
SYMBOLS = {'+': 'add', '-': 'sub', '&': 'and', '|': 'or', '<': 'lt', '>':'gt', '=':'eq'}
SYMBOLS_UNARY = {'-': 'neg', '~': 'not'}
KEYWORDS_VALUES = {'null': '0', 'false': '0', 'true': '0'}

class CompilationEngine:
    def __init__(self, filename, fileout):
        self.file = filename
        self.outname = fileout
        self.tokenizer = JackTokenizer(self.file)
        self.iter_tokens = iter(self.tokenizer)
        self.symbol_table = SymbolTable()
        self.writer = VMWriter(fileout)
        self._before = None
        self._branch_count = 0

        self.identifiers = {'(': self._method_call, '[': self._array_lookup, '.': self._method_call}
        self.methods = {
            'class': self.compile_class, 'static': self.compile_class_var_dec, 'else': self._compile_else,
            'field': self.compile_class_var_dec, 'constructor': self.compile_subroutine_dec,
            'function': self.compile_subroutine_dec, 'method': self.compile_subroutine_dec,
            'var': self.compile_var_dec, 'let': self.compile_let, 'if': self.compile_if,
            'while': self.compile_while, 'do': self.compile_do, 'return': self.compile_return,
        }

    def advance(self):
        if self._before is not None:
            bfr,self._before = self._before,None
            return bfr
        return next(self.iter_tokens)

    def __call__(self, until=None, before=None):
        while True:
            if self._before is not None:
                if before is not None and self._before[0] in before:
                    return
                bfr,self._before = self._before,None
                yield bfr
                if until is not None and bfr[0] in until:
                    return
            else:
                try: token, token_type = next(self.iter_tokens)
                except StopIteration: return
                if before is not None and token in before:
                    self._before = (token, token_type)
                    return
                yield token, token_type
                if until is not None and token in until:
                    return

    def compile(self):
        with open(self.outname, 'w') as self.fileout:
            self.compile_class()

    def _compile(self, until=None, before=None):
        for token,token_type in self(until, before):
            if token_type == TokenType.KEYWORD and token in self.methods:
                self.methods[token](token,token_type)

    def compile_class(self):
        token = self.advance()[0]
        if token != 'class': self.syntax_error('File should begin with `class` but found', token)
        self.classname, tt = self.advance()
        self.check_identifier(self.classname, tt)
        self._advance_should_be('{')
        self._compile()

    def compile_class_var_dec(self, var_kind, token_type):
        var_type = self.advance()[0]
        self._define_var(var_type, var_kind)

    def _compile_function_name(self, subroutine_name, subroutine_type):
        self.writer.write_function(self.classname+'.'+subroutine_name, self.local_st.var_count("local"))
        if subroutine_type == 'constructor':
            self.writer.write_push('constant', self.symbol_table.var_count('field'))
            self.writer.write_call('Memory.alloc', 1)
            self.writer.write_pop('pointer', 0)
        elif subroutine_type == 'method':
            self.writer.write_push('argument', 0)
            self.writer.write_pop('pointer', 0)

    def compile_subroutine_dec(self, subroutine_type, token_type):
        self._has_returned = False
        self.local_st = self.symbol_table.new_scope()
        if subroutine_type == 'method':
            self.local_st.define('this', self.classname, 'argument')

        return_type, _ = self.advance()
        subroutine_name, tt = self.advance()
        self.check_identifier(subroutine_name, tt)

        self._advance_should_be('(')
        self.compile_param_list()
        self.compile_subroutine_body(subroutine_name, subroutine_type)
        if not self._has_returned:
            if return_type == 'void':
                self.writer.write_push('constant', 0)
                self.writer.write_return()
            else:
                self.syntax_error(f'Function should return type "{return_type}"')

    def _define_var(self, var_type, var_kind, local=False):
        st = self.local_st if local else self.symbol_table
        for var_name, vtype in self(until=';'):
            if vtype == TokenType.IDENTIFIER:
                st.define(var_name, var_type, var_kind)

    def compile_param_list(self):
        for var_type,type_token in self(before=')'):
            if var_type != ',':
                var_id, id_type = self.advance()
                self.check_identifier(var_id, id_type)
                self.local_st.define(var_id, var_type, 'argument')

    def compile_subroutine_body(self, subroutine_name, subroutine_type):
        self._compile(before=END_STMT)
        self._compile_function_name(subroutine_name, subroutine_type)
        self.compile_statements()

    def compile_var_dec(self, token, token_type):
        var_type, tt = self.advance()
        self._define_var(var_type, 'local', local=True)

    def compile_statements(self, token=None, token_type=None):
        self._compile(until='}')

    def compile_let(self, token, token_type):
        identifier = self.advance()
        with self._get_identifier()(*identifier, define=True):
            self._advance_should_be('=')
            self.compile_expression(end=';')

    def _advance_should_be(self, cmp):
        t,tt = self.advance()
        if not t == cmp:
            self.syntax_error(f'token "{t}" should be "{cmp}"')

    def compile_if(self, token, token_type):
        c = str(self._branch_count)
        self._branch_count += 1
        self._advance_should_be('(')
        self.compile_expression()
        self._advance_should_be('{')
        self.writer.write_arithmetic('not')
        self.writer.write_if('IF_FALSE$'+c)
        self.compile_statements()
        self.writer.write_goto('IF_END$'+c)
        self.writer.write_label('IF_FALSE$'+c)

        self._compile(before=END_STMT.union({'else'}))
        if self._before[0] == 'else':
            self.advance()
            self._compile_else()

        self.writer.write_label('IF_END$'+c)

    def _compile_else(self):
        self._advance_should_be('{')
        self.compile_statements()

    def compile_while(self, token, token_type):
        c = str(self._branch_count)
        self._branch_count += 1
        self._advance_should_be('(')
        self.writer.write_label('WHILE_COND$'+c)
        self.compile_expression()
        self._advance_should_be('{')
        self.writer.write_arithmetic('not')
        self.writer.write_if('WHILE_END$'+c)
        self.compile_statements()
        self.writer.write_goto('WHILE_COND$'+c)
        self.writer.write_label('WHILE_END$'+c)

    def compile_do(self, token, token_type):
        identifier = self.advance()
        self._before = self.advance()
        with self._method_call(*identifier, end=')'):
            self._advance_should_be(';')
            self.writer.write_pop('temp', 0)

    @contextmanager
    def _method_call(self, token, token_type, end=')'):
        nlocals = 1
        if self._before[0] == '(' or token == 'this':
            # Local method
            self.writer.write_push('pointer', 0)
            methodname = self.classname
            if token != 'this': methodname += '.'+token
        elif token in self.local_st:
            # Local variable method
            with self._identifier_gen(token, token_type):
                methodname = self.local_st.type_of(token)
        else:
            # Another class' method
            methodname = token
            nlocals = 0

        for var,var_type in self(before='('):
            if var != '.':
                self.check_identifier(var, var_type)
            methodname += var
        self._advance_should_be('(')
        nlocals += self.compile_expression_list(end)
        self._advance_should_be(')')
        self.writer.write_call(methodname, nlocals)
        yield

    def compile_return(self, token, token_type):
        self._before = self.advance()
        if self._before[0] == ';': self.writer.write_push('constant', 0)
        out = self.compile_expression(end=';')
        self.writer.write_return()
        self._has_returned = True

    def compile_expression(self, end=')', close_end=True):
        for i,(token, token_type) in enumerate(self(before=end)):
            self.compile_term(token, token_type, n=i)
        if close_end: self.advance()

    @contextmanager
    def _array_lookup(self, token, token_type, define=False):
        if not define: yield
        self._advance_should_be('[')
        with self._identifier_gen(token, token_type): pass
        self.compile_expression(end=']')
        self.writer.write_arithmetic('add')     # Array base + expression
        if define:
            yield
            self.writer.write_pop('temp', 0)    # Save expr2 to temp 0
            self.writer.write_pop('pointer', 1) # Save THAT = base+offset
            self.writer.write_push('temp', 0)   # Load the saved expr2
            self.writer.write_pop('that', 0)    # Set a[base+offset] = expr2
        else:
            self.writer.write_pop('pointer', 1)
            self.writer.write_push('that', 0)

    @contextmanager
    def _identifier_gen(self, token, token_type, define=False):
        "Push or pop the identifier value to the stack according to define."
        yield
        if token not in self.local_st:
            self.syntax_error(f'Variable "{token}" used before defined.')

        _,segment,index = self.local_st[token]
        if segment == 'field': segment = 'this'
        f = self.writer.write_pop if define else self.writer.write_push
        f(segment, index)

    def _get_identifier(self):
        self._before = self.advance()
        return self.identifiers.get(self._before[0], self._identifier_gen)

    def compile_term(self, token=None, token_type=None, end=')', n=0):
        if token_type == TokenType.SYMBOL:
            if token == '(':
                self.compile_expression()
            elif token in SYMBOLS or token == '~':
                self.compile_term(*self.advance())
                self.writer.write_arithmetic(self._decode_symbol(token, token_type, unary=n==0))
            elif token in '*/':
                self.compile_term(*self.advance())
                self.writer.write_call('Math.' + ('multiply' if token=='*' else 'divide'), 2)
            else:
                self.syntax_error('Unrecognized symbol "%s"' % token)

        elif token_type == TokenType.IDENTIFIER:
            with self._get_identifier()(token, token_type):
                pass
        elif token_type == TokenType.STRCNST:
            self._build_string_constant(token)
        elif token_type == TokenType.INTCNST:
            self.writer.write_push('constant', token)
        else:
            if token in {'false', 'true', 'null'}:
                self.writer.write_push('constant', KEYWORDS_VALUES[token])
                if token == 'true': self.writer.write_arithmetic('not')
            elif token == 'this':
                self._before = self.advance()
                if self._before[0] != '.': self.writer.write_push('pointer', 0)
                else: self._method_call(token, token_type)
            else:
                self.syntax_error('Expected expression but found "%s"' % token)

    def _decode_symbol(self, token, token_type, unary=False):
        return SYMBOLS_UNARY[token] if unary else SYMBOLS[token]

    def _build_string_constant(self, token):
        self.writer.write_push('constant', len(token))
        self.writer.write_call('String.new', 1)
        for v in token:
            self.writer.write_push('constant', ord(v))
            self.writer.write_call('String.appendChar', 2)

    def peek(self):
        self._before = self.advance()
        return self._before

    def compile_expression_list(self, end=')'):
        i = 0
        while True:
            if self.peek()[0] == ')': break
            self.compile_expression(end=',)', close_end=False)
            if self._before[0] == ',': self.advance()
            i += 1
        return i

    def syntax_error(self, error):
        raise JackSyntaxError(error)

    def check_identifier(self, token, token_type):
        if token_type != TokenType.IDENTIFIER:
            self.syntax_error('"%s" is not a valid identifier.' % token)

class JackSyntaxError(Exception):
    pass
