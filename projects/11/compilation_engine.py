"Compile the tokenized jack file into syntactical components."

from jack_tokenizer import JackTokenizer, TokenType
from symbol_table import SymbolTable
from vm_writer import VMWriter

END_STMT = {'let', 'do', 'while', 'if', 'return', '}'}
SYMBOLS = {'+': 'add', '-': 'sub', '&': 'and', '|': 'or', '<': 'lt', '>':'gt', '=':'eq'}
SYMBOLS_UNARY = {'-': 'neg', '~': 'not'}
KEYWORDS_VALUES = {'null': '0', 'false': '0', 'true': '1'}

class CompilationEngine:
    def __init__(self, filename, fileout):
        self.file = filename
        self.outname = fileout
        self.tokenizer = JackTokenizer(self.file)
        self.iter_tokens = iter(self.tokenizer)
        self.symbol_table = SymbolTable()
        self.writer = VMWriter(fileout)
        self._before = None

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
            print(self.symbol_table)

    def _compile(self, until=None, before=None):
        for token,token_type in self(until, before):
            if token_type == TokenType.KEYWORD and token in self.methods:
                self.methods[token](token,token_type)
            # else:
            #     self.syntax_error('Unknown token found "%s"' % token)

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

    def compile_subroutine_dec(self, subroutine_type, token_type):
        self.local_st = self.symbol_table.new_scope()
        if subroutine_type == 'method':
            self.local_st.define('this', self.classname, 'argument')

        return_type, _ = self.advance() #TODO
        subroutine_name, tt = self.advance()
        self.check_identifier(subroutine_name, tt)
        self.writer.write('function' + self.classname + '.' + subroutine_name)
        if subroutine_type == 'constructor':
            # push number of words to reserve
            self.writer.write_push('constant', len(self.symbol_table)) # is this right? Should the number of words to reserve==the number of statics and fields?
            self.writer.write_call('Memory.alloc', 1)

        self._advance_should_be('(')
        self.compile_param_list()
        self.compile_subroutine_body()
        print(self.local_st)
        if return_type == 'void':
            self.writer.write_push('constant', 0)
            self.writer.write_return()
            # self.writer.write_pop('temp', 0)

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

    def compile_subroutine_body(self):
        self.compile_statements()

    def compile_var_dec(self, token, token_type):
        var_type, tt = self.advance()
        self._define_var(var_type, 'local', local=True)

    def compile_statements(self, token=None, token_type=None):
        self._compile(until='}')

    def compile_let(self, token, token_type):
        identifier = self.advance()
        id_func = self._get_identifier() # This doesnt handle assignment to arrays yet - it would need to save the lookahead until the '=' and then call the id_func
        self._advance_should_be('=') # similarly to the above statement, this would only be '=' if the expression was skipped
        self.compile_expression(end=';')
        id_func(*identifier, define=True)

    def _advance_should_be(self, cmp):
        t,tt = self.advance()
        if not t == cmp:
            self.syntax_error(f'token "{t}" should be "{cmp}"')

    def compile_if(self, token, token_type):
        self._advance_should_be('(')
        self.compile_expression()
        self._advance_should_be('{')
        self.writer.write_arithmetic('not') # go to else
        self.writer.write_if(self.classname+'.funcname.false')
        self.compile_statements()
        self.writer.write_goto(self.classname+'.funcname.end')
        self.writer.write_label(self.classname+'.funcname.false')

        self._compile(before=END_STMT.union({'else'}))
        if self._before[0] == 'else':
            self.advance()
            self._compile_else()

        self.writer.write_label(self.classname+'.funcname.end')

    def _compile_else(self):
        self._advance_should_be('{')
        self.compile_statements()

    def compile_while(self, token, token_type):
        self.writer.write_label(self.classname+'.while-start') # Make unique
        self.compile_expression()
        self._advance_should_be('{')
        self.writer.write_arithmetic('not')
        self.writer.write_if(self.classname+'.while-end')
        self.compile_statements()
        self.writer.write_goto(self.classname+'.while-start')
        self.writer.write_label(self.classname+'.while-end')

    def compile_do(self, token, token_type):
        self._method_call(end=')')
        self._advance_should_be(';')
        self.writer.write_pop('temp', 0)

    def _method_call(self, token=None, token_type=None, end=')'):
        methodname = ''
        if token is not None: methodname += token
        for var,var_type in self(before='('): # Fix method naming: Foo.bar, bar, ??
            if var != '.': self.check_identifier(var, var_type)
            methodname += var
        nlocals = self.compile_expression_list(end)
        self._advance_should_be(')')
        self.writer.write_call(methodname, nlocals)

    def compile_return(self, token, token_type):
        out = self.compile_expression(end=';')
        self.writer.write_return()

    def compile_expression(self, end=')', close_end=True):
        for i,(token, token_type) in enumerate(self(before=end)):
            self.compile_term(token, token_type, n=i)
        if close_end: self.advance()

    def _array_lookup(self, token, token_type, define=False):
        self._advance_should_be('[')
        # _,segment,index = self.local_st[token]
        # self.writer.write_push(segment, index)
        self._identifier_gen(token, token_type)
        self.compile_expression(end=']')
        self.writer.write_arithmetic('add') #base + expression
        if define:
            self.writer.write_pop('temp', 0)    # Save expr2 to temp 0
            self.writer.write_pop('pointer', 1) # save THAT = base+offset
            self.writer.write_push('temp', 0)   # load the saved expr2
            self.writer.write_pop('that', 0)    # set a[base+offset] = expr2
        else:
            # self.writer.write_pop('temp', 0)    # Save expr2 to temp 0
            self.writer.write_pop('pointer', 1)
            self.writer.write_push('that', 0)


    def _identifier_gen(self, token, token_type, define=False):
        _,segment,index = self.local_st[token]
        if segment == 'field':
            self.writer.write_push('argument', 0)
            self.writer.write_pop('pointer', 0)
            segment = 'this'
        f = self.writer.write_pop if define else self.writer.write_push
        f(segment, index)

    def _get_identifier(self):
        self._before = self.advance()
        return self.identifiers.get(self._before[0], self._identifier_gen)

    def compile_term(self, first_token=None, first_type=None, end=')', n=0):
        if first_type == TokenType.SYMBOL:
            if first_token == '(':
                self.compile_expression()
            elif first_token in SYMBOLS or first_token == '~':
                self.compile_term(*self.advance())
                self.writer.write_arithmetic(self._decode_symbol(first_token, first_type, unary=n==0))
            elif first_token in '*/':
                self.compile_term(*self.advance())
                self.writer.write_call('Math.' + ('multiply' if first_token=='*' else 'divide'), 2)
            else:
                self.syntax_error('Unrecognized symbol "%s"' % first_token)

        elif first_type == TokenType.IDENTIFIER:
            id_func = self._get_identifier()
            id_func(first_token, first_type)
        elif first_type == TokenType.STRCNST:
            self._build_string_constant(first_token)
        elif first_type == TokenType.INTCNST:
            self.writer.write_push('constant', first_token)
        else:
            if first_token in {'false', 'true', 'null'}:
                self.writer.write_push('constant', KEYWORDS_VALUES[first_token])
                if first_token == 'true': self.writer.write_arithmetic('neg')
            elif first_token == 'this':
                self.writer.write_push('this', 0)
        else:
                self.syntax_error('Expected expression but found "%s"' % first_token)

    def _decode_symbol(self, token, token_type, unary=False):
        return SYMBOLS_UNARY[token] if unary else SYMBOLS[token]

    def _build_string_constant(self, token):
        self.writer.write_push('constant', len(token))
        self.writer.write_call('String.new', 1)
        for v in token:
            self.writer.write_push('constant', ord(v))
            self.writer.write_call('String.appendChar', 1)

    def compile_expression_list(self, end=')'):
        i = -1
        for i,comma in enumerate(self(before=')')):
            self.compile_expression(end=',)', close_end=False)
        return i + 1

    def syntax_error(self, error):
        raise JackSyntaxError(error)

    def check_identifier(self, token, token_type):
        if token_type != TokenType.IDENTIFIER:
            self.syntax_error('"%s" is not a valid identifier.' % token)

class JackSyntaxError(Exception):
    pass
