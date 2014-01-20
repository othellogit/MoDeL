from itertools import product
from funcy import *
import code

class AST:
    def __init__(self, nodetype, children):
        self.nodetype = nodetype
        self.children = children
        self.compiled = None
        self.generated = None

    def __getitem__(self, i):
        return self.children[i]

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return all(selfc == otherc for (selfc, otherc) in zip(self.children, other.children))
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def is_immediate(self):
        return len(self.children) == 1 and not isinstance(self.children[0], AST)

    @property
    def is_none(self):
        return self.nodetype == "none"

    @property
    def immediate(self):
        if self.is_immediate:
            return self.children[0]
        else:
            raise TypeError

    def __str__(self):
        base = self.nodetype + ": "
        if self.is_immediate:
            return base + repr(self.children[0])
        else:
            return base + '(' + ', '.join([str(e) for e in self.children]) + ')'

ASTNone = AST('none', [])


def compile_ast(ast, bindings = {}, use_bindings = False):
    if ast.is_immediate:
        imm = ast.immediate
        if use_bindings and imm in bindings and ast.nodetype == "variableName":
            ast.compiled = bindings[imm]
        else:
            ast.compiled = imm

    elif ast.nodetype == "formula":
        # First compile iterators
        if not ast.children[3] is None:
            iterators = [compile_ast(c).compiled for c in ast.children[3:]]
            # Get the lists only
            all_lists = [iter['lists'] for iter in iterators]
            # Cartesian product of all the iterators' lists
            prod = product(*all_lists)
            # Names of all the iterators and associated loop counters
            all_names = cat(iter['names'] for iter in iterators)
            # Build the final list containing all the bindings
            all_bindings = [dict(zip(all_names, cat(p))) for p in prod]
        else:
            all_bindings = [{}]
        # Then compile conditions
        if not ast.children[2] is None:
            conditions = (compile_ast(ast.children[2], bindings) for bindings in all_bindings)
        else:
            conditions = []
        # Finally compile the equation / expression for each binding
        equations = (compile_ast(ast.children[1], bindings) for bindings in all_bindings)

        ast.compiled = { 'conditions': conditions,
                         'equations': equations }

    elif ast.nodetype == "function":
        name = compile_ast(ast.children[0]).compiled

        if name == "sum":
            generator = lambda toks: "0" + ' + '.join(toks)
        else:
            generator = lambda toks: toks if type(toks) is str else "".join(toks)

        ast.compiled = { 'name': name,
                         'generator': generator,
                         'arguments': [compile_ast(c, bindings) for c in ast.children[1:]] }

    elif ast.nodetype in ["index", "placeholder", "timeOffset"]:
        ast.compiled = [compile_ast(c, bindings, True) for c in ast.children]

    elif ast.nodetype == "iterator":
        # If the iterator is correctly defined, there are as many iterator names
        # as there are lists. So we divide the children in halves
        list_count = len(ast.children) / 2
        names = [compile_ast(c).compiled for c in ast.children[:list_count]]
        lists = [compile_ast(c).compiled for c in ast.children[list_count:]]
        # HACK !! Used for the loop counters
        listBaseLength = [len(lst.children[0].children) for lst in ast.children[list_count:]]
        # Add the loop counters
        names = names + ['$' + name for name in names]
        lists = lists + [range(1, n + 1) for n in listBaseLength]
        ast.compiled = { 'names': names,
                         'lists': zip(*lists) }

    elif ast.nodetype == "listBase":
        ast.compiled = [compile_ast(c).compiled for c in ast.children]

    elif ast.nodetype == "list":
        base = compile_ast(ast.children[0]).compiled
        excluded = compile_ast(ast.children[1]).compiled
        ast.compiled = [e for e in base if e not in excluded]

    elif ast.is_none:
        ast.compiled = ASTNone

    else:
        ast.compiled = [compile_ast(c, bindings, use_bindings) for c in ast.children]

    return ast


def generate(ast, heap = {}):
    if ast.is_immediate:
        return str(ast.compiled)

    elif ast.nodetype == "array":
        ret = generate(ast.children[0])
        if not ast.children[1].is_none:
            ret += '_' + generate(ast.children[1])
        if not ast.children[2].is_none:
            ret += generate(ast.children[2])
        return ret

    elif ast.nodetype == "expression":
        return ' '.join(generate(c) for c in ast.compiled)

    elif ast.nodetype == "equation":
        return generate(ast.children[0]) + ' = ' + generate(ast.children[1])

    elif ast.nodetype == "formula":
        return [generate(eq) for eq in ast.compiled['equations']]

    elif ast.nodetype == "function":
        generated_args = [generate(a) for a in ast.compiled['arguments']]
        return ast.compiled['name'] + '(' + ', '.join(ast.compiled['generator'](a) for a in generated_args) + ')'

    elif ast.nodetype in ["identifier", "placeholder"]:
        return ''.join(generate(c) for c in ast.compiled)

    elif ast.nodetype == "index":
        return '_'.join(generate(c) for c in ast.compiled)

    elif ast.nodetype == "timeOffset":
        return '(' + generate(ast.children[0]) + ')'

    elif ast.is_none:
        return ""
