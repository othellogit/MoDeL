from functools import wraps
import itertools
import plyyacc

def build_variable(name):
    ('VarName', ('VarId', (name,)), None, None)

def traverse(func):
    def wrapped_func(ast):
        try:
            ret = func(ast)
        except TypeError:
             # func doesn't take care of terminals
            return ()
        else:
            if ret is not None:
                return ret
            else:
                return traverse_with_wrapped_func(ast)

    @wraps(func)
    def traverse_with_wrapped_func(ast):
        if ast[0] == 'VarName':
            return wrapped_func(ast[1]) + wrapped_func(ast[2]) + wrapped_func(ast[3])
        elif ast[0] == 'VarId':
            return tuple(itertools.chain.from_iterable(wrapped_func(a) for a in ast[1]))
        elif ast[0] == 'Placeholder':
            return wrapped_func(ast[1])
        elif ast[0] == 'Index':
            return wrapped_func(ast[1])
        elif ast[0] == 'ExprList':
            return tuple(itertools.chain.from_iterable(wrapped_func(a) for a in ast[1]))
        elif ast[0] == 'ExprBinary':
            return wrapped_func(ast[2]) + wrapped_func(ast[3])
        elif ast[0] == 'ExprGroup':
            return wrapped_func(ast[1])
        elif ast[0] == 'FunctionCallArgs':
            return wrapped_func(ast[2])
        elif ast[0] == 'QualifiedExprList':
            return tuple(itertools.chain.from_iterable(wrapped_func(a) for a in ast[1]))
        elif ast[0] == 'Qualified':
            return wrapped_func(ast[1]) + wrapped_func(ast[2]) + wrapped_func(ast[3])
        elif ast[0] == 'EquationDef':
            return wrapped_func(ast[2]) + wrapped_func(ast[3])
        else:
            return ()

    return traverse_with_wrapped_func


@traverse
def extract_varnames(expr):
    if expr[0] == 'VarName':
        return (expr, )

@traverse
def extract_simple_varids(expr):
    if expr[0] == 'VarId' and len(expr[1]) == 1 and isinstance(expr[1][0], basestring):
        return expr[1]

@traverse
def extract_iterators(expr):
    if expr[0] == 'Index':
        return extract_simple_varids(expr[1])
    elif expr[0] == 'Placeholder':
        return expr[1]

class CompilerError(Exception):
    pass

class Compiler:
    def error(self, msg):
        raise CompilerError("Error at line %s.\n\n%s\n\n%s\n" % (self.current_line, self.lines[self.current_line - 1], msg))

    def get_if_exists(self, key, hsh, msg):
        if key in hsh:
            return hsh[key]
        else:
            self.error("%s `%s` is not defined." % (msg, key))


    # Set
    # ('SetLiteral', tuple)
    #
    def compile_set(self, ast):
        if ast[0] == 'SetLiteral':
            return zip(ast[1], range(1, len(ast[1]) + 1))


    # Expressions
    #
    def compile_expression(self, ast, iterators):
        # Find iterators used in this expression
        iterator_names = extract_iterators(ast)

        # Get the corresponding lists
        for i in iterator_names:
            # Must check if already defined locally, since local definitions replace
            # global iterators by default
            iterators.update({i: self.get_if_exists(i, iterators, "Iterator")})

            print iterators


    # whereClause
    # ('Where', iteratorList)
    # Each iterator in iteratorList can be one of:
    # - ('IteratorSetLiteral', ID, set)
    # - ('IteratorLocal', ID, localId)
    # - ('IteratorParallelSet', idGroup, setGroup)
    # - ('IteratorParallelLocal', idGroup, localGroup)
    #
    def compile_whereClause(self, ast):
        iterator_list = ast[1][1]
        local_iterators = {}
        parallel_iterators = []

        for iter in iterator_list:
            if iter[0] == 'IteratorLocal':
                local_iterators.update({ iter[1]: self.get_if_exists(iter[2], self.heap, "Local variable") })
            elif iter[0] == 'IteratorSetLiteral':
                local_iterators.update({ iter[1]: self.compile_set(iter[2]) })
            elif iter[0] == 'IteratorParallelSet':
                local_iterators.update( dict(zip(iter[1][1], (self.compile_set(l) for l in iter[2][1]))) )
                parallel_iterators.append(iter[1][1])

        return local_iterators, parallel_iterators

    # Qualified Expressions
    # ('Qualified', expr, ifClause, whereClause)
    #
    def compile_qualified(self, ast, iterators):
        # Compile whereClause to add explicit iterators, if any
        if not ast[3] is None:
            local_iterators, parallel_iterators = self.compile_whereClause(ast[3])
            iterators.update( local_iterators )

        # Compile ifClause, if any

        # Compile expr
        print iterators
        print parallel_iterators
        self.compile_expression(ast[1], iterators)

    def compile(self, program):
        self.heap = {}
        self.iterators = {}
        self.lines = program.split('\n')
        self.current_line = 0

        # Parse the program
        ast = plyyacc.parser.parse(program)

        # Check for errors
        if len(plyyacc.errors) == 0:
            print ast, "\n"

            try:
                # Go through each statement
                for a in ast[1]:
                    s = a[1]
                    self.current_line = a[2]

                    if s[0] == 'EquationDef':
                        self.compile_qualified(s[3], self.iterators)
            except CompilerError as e:
                print e

        else:
            for e in plyyacc.errors:
                self.current_line = e[1]
                self.error(e[0])


def compile(program, heap):
    print "Compiling:\n", program
    ast = plyyacc.parser.parse(program)
    print ast, "\n"

    # Go through statements
    for a in ast[1]:
        # Extract statement
        s = a[1]
        self.current_line = a[2]

        # if s[0] == 'LocalDef':
        #     heap[s[1]] = s[2][1]
        #     #print heap

        if s[0] == 'EquationDef':
            # Identify iterators
            print(extract_varnames(s))
            print(extract_iterators(s))


def test():
    # compile("""%test := {"15", "05"}
    # test = X|O|[42, c]{t-1}
    # """, {})
    compiler = Compiler()
    compiler.compile("""V = x[c] where c in {'01', '02'}
    test = X|O| where (O, V) in ({'D', 'M'}, {'X', 'IA'})\n""")

if __name__ == "__main__":
    test()
    # import timeit
    # print(timeit.timeit('test()', setup="from __main__ import test", number=3000)/3000)
    # print plyyacc.parser.parse("""test = X|O|[1, 2]{t-1} if test > 2 where i in %c
    #                       %test := {"15", "05"}
    #                       functionTest = function()
    #                       functionTest2 = function(hello[c] where (c, s) in ({"01"}, {"05"}), world)
    #                       """)