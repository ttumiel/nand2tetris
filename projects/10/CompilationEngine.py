"Compile the tokenized jack file into syntactical components."

from JackTokenizer import JackTokenizer, TokenType

STATEMENTS = {'let', 'do', 'while', 'if', 'return'}
END_TERMS = set('+-*/&|<>=~')

class CompilationEngine:
    def __init__(self, filename, fileout):
        self.file = filename
        self.outname = fileout
        self.tokenizer = JackTokenizer(self.file)
        self.iter_tokens = iter(self.tokenizer)
        self.stack = []
        self.methods = {
            'class': self.compile_class, 'static': self.compile_class_var_dec, 'else': self._compile_else,
            'field': self.compile_class_var_dec, 'constructor': self.compile_subroutine_dec,
            'function': self.compile_subroutine_dec, 'method': self.compile_subroutine_dec,
            'var': self.compile_var_dec, 'let': self.compile_let, 'if': self.compile_if,
            'while': self.compile_while, 'do': self.compile_do, 'return': self.compile_return,
        }

    def compile(self):
        self.fileout = open(self.outname, 'w')
        try:
            self._compile()
        finally:
            self.fileout.close()

    def _compile(self, until=None, before=None):
        for token,token_type in self.iter_tokens:
            if before is not None:
                if isinstance(before, str) and token==before:
                    return token,token_type
                if isinstance(before, set) and token in before:
                    return token,token_type
            if token_type == TokenType.KEYWORD and token in self.methods:
                self.methods[token](token,token_type)
            else:
                self.tag_token(token, token_type)
            if until is not None:
                if token == until:
                    return

    def compile_class(self, token, token_type):
        self.open_tag(token)
        self.tag_token(token, token_type)
        self._compile()
        self.close_tag()

    def compile_class_var_dec(self, token, token_type):
        self.open_tag('classVarDec')
        self.tag_token(token, token_type)
        self._compile(until=';')
        self.close_tag()

    def compile_subroutine_dec(self, token, token_type):
        self.open_tag('subroutineDec')
        self.tag_token(token, token_type)
        self._compile(until='(')
        self.compile_param_list()
        self.compile_subroutine_body()
        self.close_tag()

    def compile_param_list(self):
        self.open_tag('parameterList')
        token,token_type = self._compile(before=')')
        self.close_tag()
        self.tag_token(token, token_type)

    def compile_subroutine_body(self):
        self.open_tag('subroutineBody')
        end = STATEMENTS.copy()
        end.add('}')
        token,token_type = self._compile(before=end)
        self.compile_statements(token,token_type)
        self.close_tag()

    def compile_var_dec(self, token, token_type):
        self.open_tag('varDec')
        self.tag_token(token, token_type)
        self._compile(until=';')
        self.close_tag()

    def compile_statements(self, first_token=None, first_type=None):
        self.open_tag('statements')
        if first_type is not None: self.methods[first_token](first_token, first_type)
        token,token_type = self._compile(before='}')
        self.close_tag()
        self.tag_token(token, token_type)

    def compile_let(self, token, token_type):
        self.open_tag('letStatement')
        self.tag_token(token, token_type)
        self._compile(until='=')
        self.compile_expression(end=';')
        self.close_tag()

    def compile_if(self, token, token_type):
        self.open_tag('ifStatement')
        self.tag_token(token, token_type)
        self._compile(until='(')
        self.compile_expression()
        self._compile(until='{')
        self.compile_statements()

        end = STATEMENTS.copy()
        end.add('}')
        token,token_type = self._compile(before=end)
        self.close_tag()
        self.tag_token(token, token_type)

    def _compile_else(self, token, token_type):
        self.tag_token(token, token_type)
        self._compile(until='{')
        self.compile_statements()

    def compile_while(self, token, token_type):
        self.open_tag('whileStatement')
        self.tag_token(token, token_type)
        self._compile(until='(')
        self.compile_expression()
        self._compile(until='{')
        self.compile_statements()
        self.close_tag()

    def compile_do(self, token, token_type):
        self.open_tag('doStatement')
        self.tag_token(token, token_type)
        self._compile(until='(')
        self.compile_param_list()
        self._compile(until=';')
        self.close_tag()

    def compile_return(self, token, token_type):
        self.open_tag('returnStatement')
        self.tag_token(token, token_type)
        out = self.compile_expression(';', skip_empty=True)
        if out is not None: self.tag_token(out[0], out[1])
        self.close_tag()

    def compile_expression(self, end=')', skip_empty=False): #TODO
        pass

    def compile_term(self, first_token=None, first_type=None, end=')'):
        pass

    def tag_token(self, token, token_type):
        self.open_tag(token_type.value, True)
        self.write_val(token)
        self.close_tag(True)

    def compile_expression_list(self):
        pass

    def xml(self, tag, close=False):
        return ("</" if close else "<")+tag+">"

    def open_tag(self, tag, term=False):
        indent = 2*len(self.stack)
        print(indent*' ' + self.xml(tag), file=self.fileout, end='' if term else '\n')
        self.stack.append(self.xml(tag,True))

    def write_val(self, val):
        indent = 2*len(self.stack)
        print(' '+val+' ', file=self.fileout, end='')

    def close_tag(self, term=False):
        indent = 2*len(self.stack)-2 if not term else 0
        print(indent*' ' + self.stack.pop(), file=self.fileout)



c= CompilationEngine('ExpressionLessSquare/Main.jack', 'out.xml')
c.compile()
