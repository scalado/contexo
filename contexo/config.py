
# TODO: better error handling.

import re
import string
import os.path
import os

__name__ = 'config'

NAMED_VALUE     = 1
NAMED_VALUE_ADD = 2
NAMED_VALUE_SUB = 3
SECTION         = 4
VALUE_ONLY      = 5

#------------------------------------------------------------------------------
# Regular Expresion definitions
#------------------------------------------------------------------------------
named_value_regexp = '(.+)=(.+)'
add_value_regexp =  '(.+)\+=(.+)'
sub_value_regexp =  '(.+)\-=(.+)'

section_regexp = '\[.+\]'

value_chars_re = '\w|\$|\(|\)|\[|\]|\%|\{|\}'

#presuffix_regexp = '((\{(\w+)\})|(\{\$\((\w+)\)\}))?'

preffix_regexp = '\%\{((' + value_chars_re + ')+)\}'

list_regexp = '(' + value_chars_re + ',)*' + value_chars_re

value_subst_regexp1 = '\$\((\w+)\)'
value_subst_regexp2 = '\$\((\w+\.\w+)\)'

list_subst_regexp = '\$\[((\w|\.)+)\]'

named_value = re.compile (named_value_regexp)
add_value = re.compile (add_value_regexp)
sub_value = re.compile (sub_value_regexp)
section = re.compile (section_regexp)

value_subst1 = re.compile (value_subst_regexp1)
value_subst2 = re.compile (value_subst_regexp2)
list_subst = re.compile (list_subst_regexp)
preffix_subst = re.compile (preffix_regexp)

is_list = re.compile (list_regexp)

resolve_value_ext = []


current_preffix = None


#------------------------------------------------------------------------------
#
#   read_list_file( file_path )
#
#   Reads each line of the given file into a list and returns it. Lines
#   beginning with '#' are ignored.
#
#------------------------------------------------------------------------------
def parse_list_file( file_path ):

    thelist = []
    if os.path.exists (file_path):
        file = open( file_path, "r" )

        for line in file.readlines():
            line = line.strip ()

            if line != "" and line[0] != '#':
                thelist.append( line )

        file.close()

    return thelist

#------------------------------------------------------------------------------
def parse_list_value ( value ):
    comma_list = value.split (',')
    tmp_list = [x.split(";") for x in comma_list]
    parse_list = []
    for x in tmp_list:
        parse_list.extend (x)

    return parse_list

def parse_value ( value, cur_section, section_dict ):
    # Perform the variable substitution
    resolve_value_ext.append (cur_section)
    resolve_value_ext.append (section_dict)

    value = value_subst1.sub (resolve_value, value)
    value = value_subst2.sub (resolve_value, value)

    resolve_value_ext.pop()
    resolve_value_ext.pop()

    # Perform list substitution
    value = list_subst.sub (resolve_list, value)

    # Parse list value
    value_list = parse_list_value (value)
    if len (value_list) > 1:
        striped_list = []
        for v in value_list:
            striped_list.append (v.strip())
        return striped_list

    else:
        # Convert datatypes
        tmpvalue = string.lower( value )

        if tmpvalue.isdigit():
            return int( tmpvalue )

        elif tmpvalue == 'yes' or tmpvalue == 'true' or tmpvalue == 'on':
            return  bool( True )

        elif tmpvalue == 'no' or tmpvalue == 'false' or tmpvalue == 'off':
            return  bool( False )
        else:
            return value

#------------------------------------------------------------------------------
def resolve_value ( match_object ):

    cur_section  = resolve_value_ext[0]
    section_dict = resolve_value_ext[1]

    value = match_object.group(1)

    # Use correct scope

    value = value.split('.')

    if len (value) > 1:
        cur_section = value[0]
        value = value[1]
    else:
        value = value[0]

    # resolve
    if section_dict[cur_section].has_key (value):
        subst_value = section_dict[cur_section][value]
    elif section_dict['default'].has_key (value):
        subst_value = section_dict['default'][value]
    else:
        subst_value =  match_object.group(0)

    if isinstance (subst_value,list):
        return string.join (subst_value,',')

    return subst_value

#------------------------------------------------------------------------------
def resolve_list ( match_object ):
    value_list = parse_list_file ( match_object.group(1) )

    #prefix = match_object.group(3)
    #suffix = match_object.group(9)

    return string.join (value_list, ',')

def apply_preffix ( match_object ):
    # Check if string after this match is a list
    dummy = 0


#------------------------------------------------------------------------------

#------------------------------------------------------------------------------

def parse_line( src_line, cur_section, section_dict ):
    line = src_line.strip ()
    
    
    exprs = [ (add_value, NAMED_VALUE_ADD),\
              (sub_value, NAMED_VALUE_SUB),\
              (named_value, NAMED_VALUE) ]

    # parse named values
    for e in exprs:
        m = e[0].match( line )
        if m != None:
            name = m.groups()[0].strip()
            value = string.join(m.groups()[1].strip().split())
            value = parse_value ( value, cur_section, section_dict )
            return ( e[1], (name, value) )

    # Check if it is a new section
    if section.match (line):
        return ( SECTION, line[1:-1] )

    # Value alone
    return parse_value ( line, cur_section, section_dict )

#------------------------------------------------------------------------------
def parse_file (filename, section_dict):

    try:
        file = open (filename, "r")
    except IOError, (errno, strerror):
        print "*** Error opening file %s"%filename
        raise IOError

    cur_section = 'default'

    src = file.read ()

    src_lines = src.split('\n')

    # Preprocess lines a bit (strip and join lines)
    src_lines_proc = []
    concat_line = 0

    for line in src_lines:
        if concat_line:
            cur_line = cur_line + line
        else:
            cur_line = line.strip ()  # strip spaces

        cur_line_len = len (cur_line)
        if cur_line_len > 0:
            if cur_line[cur_line_len-1] == '\\':
                concat_line = 1
                cur_line = cur_line[:-1]
            else:
                concat_line = 0
                src_lines_proc.append (string.join(cur_line.split()))

    for line in src_lines_proc:
        # Include file
        if line[0] == '!' :
            try:
                parse_file ( line[1:], section_dict )
            except IOError, (errno, strerror):
                raise IOError

        # TODO: remove line comments
        if line[0] != '#':
            result = parse_line (line, cur_section, section_dict)

            if result[0] == NAMED_VALUE:
                section_dict[cur_section][result[1][0]] = result[1][1]
            if result[0] == SECTION:
                cur_section = result[1]

                # Check if section already exists and merge values in that case
                section_available = False
                for s in section_dict:
                    if s == cur_section:
                        section_available = True

                if not section_available:
                    section_dict[cur_section] = dict()

    file.close ()


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
def get_environment ():
    d = dict ()
    e = os.environ

    for key, value in e.iteritems ():
        d[key] = parse_value (value, 'var', e)

    return d

#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
# Config Class
#
#
#------------------------------------------------------------------------------
class Config:
    section_dict = None

    def __init__(self, filename = None):
        self.section_dict = {'default': dict(), 'var': get_environment ()}

        if filename != None:
            self.merge_config ( filename )

    def merge_config (self, filename):
        config_dir = os.path.dirname (filename)

        if config_dir != '':
            cur_dir = os.getcwd()
            os.chdir (config_dir)

        parse_file (os.path.basename(filename), self.section_dict)

        if config_dir != '':
            os.chdir (cur_dir)

    def get_section_list (self):
        section_list = []

        for section in self.section_dict:
            section_list.append (section)

        return section_list

    def get_section (self, section):
        return self.section_dict[section]

    def has_section (self, section):
        return self.section_dict.has_key(section)

    def add_section (self, section ):
        if not self.has_section ( section ):
            self.section_dict[section] = dict ()

    def get_item ( self, section, item ):
        if self.has_section ( section ):
            return self.section_dict[section][item]

    def add_item ( self, section, item, value ):
        if self.has_section ( section ):
            self.section_dict[section][item] = value

    def save ( self, path ):
        file_string = str()

        # Output default section keys
        file_string += self.serialize_section ( 'default' )

        for key in self.section_dict.iterkeys():
            if key is not 'default' and key is not 'var':
                file_string += self.serialize_section ( key )

        f = open ( path, 'w' )
        f.write ( file_string )
        f.close ()

    def serialize_section ( self, section ):
        s = str()
        if section is not 'default':
            s += '[' + section + ']\n'

        for item_value in self.section_dict[section].iteritems():
            s += item_value[0] + ' = '
            if isinstance (item_value[1], list):
                s += ";".join(item_value[1])

            elif isinstance ( item_value[1], bool ):
                if item_value[1]:
                    s += "Yes"
                else:
                    s += "No"
            else:
                s += str( item_value[1] )
            s += '\n'
        return s
