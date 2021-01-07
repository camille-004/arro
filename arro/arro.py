DIGITS = '0123456789'

INT = 'INT'
FLOAT = 'FLOAT'
ADD = 'ADD'
SUB = 'SUB'
MUL = 'MUL'
DIV = 'DIV'
O_PAREN = 'O_PAREN'
C_PAREN = 'C_PAREN'
EOF = 'EOF'


class Error:
    def __init__(self, start, end, name, content):
        self.start = start
        self.end = end
        self.name = name
        self.content = content

    def as_str(self):
        result = f'{self.name} | {self.content}\n'
        result += f'FN {self.start.fn} | line #{self.start.ln + 1}'
        # result += '\n\n' + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
        return result


class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, content):
        super().__init__(pos_start, pos_end, 'Illegal Character', content)


class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, content=''):
        super().__init__(pos_start, pos_end, 'Invalid Syntax', content)


class Pos:
    def __init__(self, idx, ln, col, fn, content):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn
        self.content = content

    def inc(self, curr_char=None):
        self.idx += 1
        self.col += 1

        if curr_char == '\n':
            self.ln += 1
            self.col = 0

        return self

    def copy(self):
        return Pos(self.idx, self.ln, self.col, self.fn, self.content)


class Token:
    def __init__(self, type_, value=None, start=None, end=None):
        self.type = type_
        self.value = value

        if start:
            self.start = start.copy()
            self.end = start.copy()
            self.end.inc()

        if end:
            self.end = end

    def __repr__(self):
        if self.value:
            return f'{self.type} | {self.value}'
        return f'{self.type}'


class Lexer:
    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.position = Pos(-1, 0, -1, fn, text)
        self.curr_char = None
        self.inc()

    def inc(self):
        self.position.inc(self.curr_char)
        self.curr_char = self.text[self.position.idx] \
            if self.position.idx < len(self.text) else None

    def make_tokens(self):
        tokens = []

        while self.curr_char is not None:
            if self.curr_char in ' \t':
                self.inc()
            elif self.curr_char in DIGITS:
                tokens.append(self.gen_num())
            elif self.curr_char == '+':
                tokens.append(Token(ADD, start=self.position))
                self.inc()
            elif self.curr_char == '-':
                tokens.append(Token(SUB, start=self.position))
                self.inc()
            elif self.curr_char == '*':
                tokens.append(Token(MUL, start=self.position))
                self.inc()
            elif self.curr_char == '/':
                tokens.append(Token(DIV, start=self.position))
                self.inc()
            elif self.curr_char == '(':
                tokens.append(Token(O_PAREN, start=self.position))
                self.inc()
            elif self.curr_char == ')':
                tokens.append(Token(C_PAREN, start=self.position))
                self.inc()
            else:
                start = self.position.copy()
                char = self.curr_char
                self.inc()
                return [], IllegalCharError(start, self.position, "'" + char + "'")

        tokens.append(Token(EOF, start=self.position))
        return tokens, None

    def gen_num(self):
        num_str = ''
        pt_count = 0
        start = self.position.copy()

        while self.curr_char is not None and self.curr_char in DIGITS + '.':
            if self.curr_char == '.':
                if pt_count == 1:
                    break
                pt_count += 1
                num_str += '.'
            else:
                num_str += self.curr_char
            self.inc()

        if pt_count == 0:
            return Token(INT, int(num_str), start, self.position)
        else:
            return Token(FLOAT, float(num_str), start, self.position)


class NumNode:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f'{self.token}'


class BinOpNode:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f'({self.left} --> {self.op} --> {self.right})'


class UnaryOpNode:
    def __init__(self, op, node):
        self.op = op
        self.node = node

    def __repr__(self):
        return f'({self.op} --> {self.node})'


class ParseResult:
    def __init__(self):
        self.error = None
        self.node = None

    def register(self, response):
        if isinstance(response, ParseResult):
            if response.error: self.error = response.error
            return response.node

        return response

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        self.error = error
        return self


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.idx = -1
        self.inc()

    def inc(self):
        self.idx += 1
        if self.idx < len(self.tokens):
            self.curr_token = self.tokens[self.idx]
        return self.curr_token

    def parse(self):
        response = self.expr()
        if not response.error and self.curr_token.type != EOF:
            return response.failure(InvalidSyntaxError(
                self.curr_token.start, self.curr_token.end,
                "Expected operator instance ('+', '-', '*', '/')"
            ))
        return response

    def factor(self):
        response = ParseResult()
        token = self.curr_token

        if token.type in (ADD, SUB):
            response.register(self.inc())
            factor = response.register(self.factor())
            if response.error:
                return response
            return response.success(UnaryOpNode(token, factor))

        elif token.type in (INT, FLOAT):
            response.register(self.inc())
            return response.success(NumNode(token))

        elif token.type == O_PAREN:
            response.register(self.inc())
            expr = response.register(self.expr())
            if response.error:
                return response
            if self.curr_token.type == C_PAREN:
                response.register(self.inc())
                return response.success(expr)
            else:
                return response.failure(InvalidSyntaxError(
                    self.curr_token.start, self.curr_token.end,
                    "Expected ')'"
                ))

        return response.failure(InvalidSyntaxError(
            token.start, token.end,
            "Expected number instance (int or float)"
        ))

    def term(self):
        return self.bin_op(self.factor, (MUL, DIV))

    def expr(self):
        return self.bin_op(self.term, (ADD, SUB))

    def bin_op(self, fcn, ops):
        response = ParseResult()
        left = response.register(fcn())
        if response.error:
            return response

        while self.curr_token.type in ops:
            op = self.curr_token
            response.register(self.inc())
            right = response.register(fcn())
            if response.error:
                return response
            left = BinOpNode(left, op, right)

        return response.success(left)


def run(fn, text):
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    # Generate Abstract Syntax Tree (AST)
    parser = Parser(tokens)
    ast = parser.parse()

    return ast.node, ast.error
