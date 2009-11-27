
import re


C_CALL_REGEXP            = r'@NAME ?\(([\'"()a-zA-Z_0-9, ]*)\)'
#tengil_macro_names = ["TESTCASE",  "TESTSUITE"]

C_IDENTIFIER_REGEXP     = '[a-zA-Z_]+([a-zA-Z_]|[0-9])*'
C_COMMENT_REGEXP        = '(/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)|(//.*)'
C_STRING_REGEXP         = '".*"'
C_USER_INCLUDE_REGEXP   = '#include\s*"\S*"'
C_SYSTEM_INCLUDE_REGEXP = '#include\s*<\S*>'
C_SYS_INC_FILE_REGEXP   = '<.*>'
C_SEPARATORS            = '[%&\^\|#><\+\-&!;{},=\(\)\[\]\:\.!~\*/\?]'

regexp_identifier = re.compile (C_IDENTIFIER_REGEXP)

#------------------------------------------------------------------------------
def is_C_identifier ( token ):
    if regexp_identifier.match (token):
        return 1
    else:
        return 0

#------------------------------------------------------------------------------
def purge_comments ( src ):
    return re.sub( C_COMMENT_REGEXP,'', src )


#------------------------------------------------------------------------------
def purge_strings ( src ):
    return re.sub (C_STRING_REGEXP,'', src)

#------------------------------------------------------------------------------
def parseIncludes ( src ):

    src = purge_comments( src )

    includes = re.findall  (C_USER_INCLUDE_REGEXP, src)

    user_includes = []
    regexp = re.compile (C_STRING_REGEXP)
    for i in includes:
        user_includes.append (regexp.findall (i)[0][1:-1])

    includes = re.findall (C_SYSTEM_INCLUDE_REGEXP, src)

    system_includes = []
    regexp = re.compile ( C_SYS_INC_FILE_REGEXP)
    for i in includes:
        system_includes.append (regexp.findall (i)[0][1:-1])

    return (user_includes, system_includes)

def parseTengilTests ( src,  callName ):

    src = purge_comments( src )
    #create a regexpr for a call of a particular macro
    tengil_regexp = re.sub('@NAME',  callName,  C_CALL_REGEXP)
    macro_args_list = re.findall(tengil_regexp,  src)
    #compiled_regexp = re.compile(tengil_regexp)

    tengil_cases = list()

    for args in macro_args_list:
        tengil_cases.append ( map( str.strip, args.split(','))[0] ) #assume one argument - the test case name

    return tengil_cases
#------------------------------------------------------------------------------


