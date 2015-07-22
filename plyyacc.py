import plylex
import ply.yacc as yacc

# Get the token map
tokens = plylex.tokens

precedence = (
               ('left', 'PLUS','MINUS'),
               ('left', 'TIMES','DIVIDE'),
               # ('left', 'POWER'),
               # ('right','UMINUS')
)


# Entry point

def p_program(p):
    '''program : statement'''
    p[0] = ('Program', [p[1]])

def p_program_recursive(p):
    '''program : program statement'''
    p[1][1].append(p[2])
    p[0] = ('Program', p[1][1])


# Statement

def p_statement(p):
    '''statement : equationDef NEWLINE
                 | seriesDef NEWLINE
                 | localDef NEWLINE
                 | comment NEWLINE'''
    p[0] = ('Statement', p[1], p.lineno(2))

# Comment

def p_comment(p):
    '''comment : COMMENT'''
    p[0] = ('Comment', p[1])

# Variable id

def p_placeholder(p):
    '''placeholder : PLACEHOLDER'''
    p[0] = ('Placeholder', p[1][1:-1])

def p_variable_id_simple(p):
    '''variableId : ID'''
    p[0] = ('VarId', [p[1]])

def p_variable_id_placeholder(p):
    '''variableId : placeholder'''
    p[0] = ('VarId', [p[1]])

def p_variable_id_recursive(p):
    '''variableId : variableId placeholder
                  | variableId ID'''
    p[1][1].append(p[2])
    p[0] = ('VarId', p[1][1])


# Variable name

def p_index(p):
    '''index : LBRACKET exprList RBRACKET'''
    p[0] = ('Index', p[2])

def p_counterid(p):
    '''counterId : COUNTERID'''
    p[0] = ('CounterId', p[1])

def p_time(p):
    '''time : LBRACE expr RBRACE'''
    p[0] = ('Time', p[2])

def p_variable_name(p):
    '''variableName : variableId'''
    p[0] = ('VarName', p[1], None, None)

def p_variable_name_index(p):
    '''variableName : variableId index'''
    p[0] = ('VarName', p[1], p[2], None)

def p_variable_name_time(p):
    '''variableName : variableId time'''
    p[0] = ('VarName', p[1], None, p[2])

def p_variable_name_index_time(p):
    '''variableName : variableId index time'''
    p[0] = ('VarName', p[1], p[2], p[3])


# Set literals

def p_set_element_str(p):
    '''setElement : ID'''
    p[0] = p[1]

def p_set_element_int(p):
    '''setElement : INTEGER'''
    # Get the string representation of the integer,
    # as stored by the lexer
    p[0] = p[1][1]

def p_set(p):
    '''set : setElement'''
    p[0] = [p[1]]

def p_set_recursive(p):
    '''set : set COMMA setElement'''
    p[1].append(p[3])
    p[0] = p[1]

def p_base_set_literal(p):
    '''setLiteral : LBRACE set RBRACE'''
    p[0] = ('SetLiteral', p[2], [])

def p_base_set_literal_2(p):
    '''setLiteral : LBRACE set RBRACE BACKLASH LBRACE set RBRACE'''
    p[0] = ('SetLiteral', p[2], p[6])


# Expressions

def p_expression_terminal(p):
    '''expr : FLOAT
            | LOCALID
            | variableName
            | counterId
            | functionCall'''
    p[0] = p[1]

# Special case for integers, which are stored as a pair
# (int_val, str_representation) by the lexer
def p_expression_terminal_int(p):
    '''expr : INTEGER'''
    p[0] = p[1][0]

def p_expression_binary(p):
    '''expr : expr PLUS expr
            | expr MINUS expr
            | expr TIMES expr
            | expr DIVIDE expr
            | expr LT expr
            | expr GT expr
            | expr LE expr
            | expr GE expr'''
    p[0] = ('ExprBinary', p[2], p[1], p[3])

def p_expression_group(p):
    '''expr : LPAREN expr RPAREN'''
    p[0] = ('ExprGroup', p[2])

def p_expression_list(p):
    '''exprList : expr'''
    p[0] = ('ExprList', [p[1]])

def p_expression_list_recursive(p):
    '''exprList : exprList COMMA expr'''
    p[1][1].append(p[3])
    p[0] =  ('ExprList', p[1][1])


# Lists of LocalID, ID, and Sets

def p_localid_list(p):
    '''localidList : LOCALID'''
    p[0] = ('LocalIDList', [p[1]])

def p_localid_list_recursive(p):
    '''localidList : localidList COMMA LOCALID'''
    p[1][1].append(p[3])
    p[0] =  ('LocalIDList', p[1][1])

def p_localid_group(p):
    '''localidGroup : LPAREN localidList RPAREN'''
    p[0] = ('LocalIDGroup', p[2][1])

def p_id_list(p):
    '''idList : ID'''
    p[0] = ('IDList', [p[1]])

def p_id_list_recursive(p):
    '''idList : idList COMMA ID'''
    p[1][1].append(p[3])
    p[0] =  ('IDList', p[1][1])

def p_id_group(p):
    '''idGroup : LPAREN idList RPAREN'''
    p[0] = ('IDGroup', p[2][1])

def p_set_list(p):
    '''setList : setLiteral'''
    p[0] = ('SetList', [p[1]])

def p_set_list_recursive(p):
    '''setList : setList COMMA setLiteral'''
    p[1][1].append(p[3])
    p[0] =  ('SetList', p[1][1])

def p_set_group(p):
    '''setGroup : LPAREN setList RPAREN'''
    p[0] = ('SetGroup', p[2][1])


# Iterators

def p_iterator_set_literal(p):
    '''iterator : ID IN setLiteral'''
    p[0] = ('IteratorSetLiteral', p[1], p[3])

def p_iterator_local(p):
    '''iterator : ID IN LOCALID'''
    p[0] = ('IteratorLocal', p[1], p[3])

def p_iterator_parallel_set(p):
    '''iterator : idGroup IN setGroup'''
    if len(p[1][1]) == len(p[3][1]):
        p[0] = ('IteratorParallelSet', p[1], p[3])
    # Different number of ids and sets
    else:
        add_error("Syntax error in parallel set iterator. %i variables for %i sets." % (len(p[1][1]), len(p[3][1])), p.lineno(2))

def p_iterator_parallel_local(p):
    '''iterator : idGroup IN localidGroup'''
    if len(p[1][1]) == len(p[3][1]):
        p[0] = ('IteratorParallelLocal', p[1], p[3])
    # Different number of variables and local ids
    else:
        add_error("Syntax error in parallel iterator. %i variables for %i sets." % (len(p[1][1]), len(p[3][1])), p.lineno(2))

def p_iterator_parallel_set_error(p):
    '''iterator : ID IN setGroup'''
    add_error("Syntax error in parallel iterator. 1 variable for %i sets." % len(p[3][1]), p.lineno(2))

def p_iterator_parallel_local_error(p):
    '''iterator : ID IN localidGroup'''
    add_error("Syntax error in parallel iterator. 1 variable for %i sets." % len(p[3][1]), p.lineno(2))

def p_iterator_parallel_set_error_2(p):
    '''iterator : idGroup IN setLiteral'''
    add_error("Syntax error in parallel iterator. %i variables for 1 set." % len(p[1][1]), p.lineno(2))

def p_iterator_parallel_local_error_2(p):
    '''iterator : idGroup IN LOCALID'''
    add_error("Syntax error in parallel iterator. %i variables for 1 set." % len(p[1][1]), p.lineno(2))

def p_iterator_list(p):
    '''iteratorList : iterator'''
    p[0] = ('IteratorList', [p[1]])

def p_iterator_list_recursive(p):
    '''iteratorList : iteratorList COMMA iterator'''
    p[1][1].append(p[3])
    p[0] =  ('IteratorList', p[1][1])


# Qualified expressions

def p_where_clause(p):
    '''whereClause : WHERE iteratorList
                   | ON iteratorList'''
    p[0] = ('Where', p[2])

def p_if_clause(p):
    '''ifClause : IF expr'''
    p[0] = ('If', p[2])

def p_qualified_expression(p):
    '''qualifiedExpr : expr'''
    p[0] = ('Qualified', p[1], None, None)

def p_qualified_expression_where(p):
    '''qualifiedExpr : expr whereClause'''
    p[0] = ('Qualified', p[1], None, p[2])

def p_qualified_expression_if(p):
    '''qualifiedExpr : expr ifClause'''
    p[0] = ('Qualified', p[1], p[2], None)

def p_qualified_expression_if_where(p):
    '''qualifiedExpr : expr ifClause whereClause'''
    p[0] = ('Qualified', p[1], p[2], p[3])

def p_qualified_expression_list(p):
    '''qualifiedExprList : qualifiedExpr'''
    p[0] = ('QualifiedExprList', [p[1]])

def p_qualified_expression_list_recursive(p):
    '''qualifiedExprList : qualifiedExprList COMMA qualifiedExpr'''
    p[1][1].append(p[3])
    p[0] =  ('QualifiedExprList', p[1][1])


# Function

def p_function(p):
    '''functionCall : ID LPAREN RPAREN'''
    p[0] = ('FunctionCallNoArgs', p[1])

def p_function_with_arguments(p):
    '''functionCall : ID LPAREN qualifiedExprList RPAREN'''
    p[0] = ('FunctionCallArgs', p[1], p[3])


# Definitions

def p_equation_definition(p):
    '''equationDef : expr EQUALS qualifiedExpr'''
    p[0] = ('EquationDef', None, p[1], p[3])

def p_series_definition(p):
    '''seriesDef : expr SERIESEQUALS qualifiedExpr'''
    p[0] = ('SeriesDef', None, p[1], p[3])

def p_local_definition_series(p):
    '''localDef : LOCALID SERIESEQUALS setLiteral'''
    p[0] = ('LocalDef', p[1], p[3])

def p_local_definition_integer(p):
    '''localDef : LOCALID SERIESEQUALS INTEGER'''
    p[0] = ('LocalDef', p[1], p[3][0])


# Error
def add_error(msg, line_nb):
    errors.append((msg, line_nb))


parser = yacc.yacc()

errors = []

if __name__ == "__main__":
    print parser.parse("""pouet[c]{x-1} = 15 where (i, j) in ({05, 15, 10} \ {10}, {V, X, O} \ {V})

    #t = X|O|[s, 2]{t-1} if test > 2 where i in %c
                          """)

    print errors

    # """    #                      %test := {"15", "05"}
    # #                      functionTest = function()
    # #                      functionTest2 = function(hello[c] where (c, s) in ({"01"}, {"05"}), world)"""
