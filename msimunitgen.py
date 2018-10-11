"""
A simple unit test framework for Model Sim which allows for the generation of .do files which rigorously tests Verilog projects.
Author: Griffin Yacynuk
"""

import sys
import re

filename = 'meta_test.txt'

OPEN_BRACKETS = ['(', '{', '[']
CLOSE_BRACKETS = [')', '}', ']']

REQUIRED_META = ['vfile', 'vmodule']
meta_commands = []
meta_dict = {'vlib': 'work', 'timescale': '1ns/1ns', 'timestep': '4ns', 'logfile': 'output.txt', 'genfile': 'out.do'}
meta = []


def log_bracket_error(lines, line, pos, open=True):
    """
    Logs an error due to a missing closing bracket, or an extra closing bracket.
    """
    if open:
        print('Syntax Error - Unclosed bracket on line {0:d} at position {1:d}:'.format(line+1, pos))
    else:
        print('Syntax Error - Extra closing bracket on line {0:d} at position {1:d}:'.format(line+1, pos))
    print('\t\"'+str(lines[line].strip()) + '\"')
    print('\t ' + ' '*pos + '^')


def check_bracket_pairing(lines):
    """
    Ensures all brackets come in pairs.
    """
    global OPEN_BRACKETS, CLOSE_BRACKETS
    passed = True
    stacks = [[], [], []]
    for i in range(len(lines)):
        line = lines[i].strip()
        # ignore comments
        if not line.startswith("#"):
            for j in range(len(line)):
                if line[j] in OPEN_BRACKETS:
                    stacks[OPEN_BRACKETS.index(line[j])].append((i, j))
                elif line[j] in CLOSE_BRACKETS:
                    if len(stacks[CLOSE_BRACKETS.index(line[j])]) != 0:
                        stacks[CLOSE_BRACKETS.index(line[j])].pop()
                    else:
                        log_bracket_error(lines, i, j, False)
                        passed = False

    for stack in stacks:
        for unclosed in stack:
            line, pos = unclosed
            log_bracket_error(lines, line, pos)
            passed = False

    return passed


def check_assert_double_equals(lines):
    """
    Ensures double equals (==) are used in assertion statements. Single equals
    are reserved for assignment.
    """
    passed = True
    for l in lines:
        match = re.search(r'assert\s+[\w\:\[\]]+\s*\=\s*\d+', l)
        if match is not None:
            passed = False
            print('Syntax Error - double equals (\"==\") must be used in assert statements:\n\t\"{0:s}\"'.format(match.group()))
            print('\t ' + ' '*match.group().index('=') + '^')

    return passed


def find_block_end(file_string, start_index=0, bracket_type='{}'):
    """
    Given a string, starting fron the start index, assuming that one bracket
    exists at start_index -1, return the index of the last bracket + 1.
    """
    bcount = 1
    for i in range(start_index, len(file_string)):
        if file_string[i] == bracket_type[0]:
            bcount += 1
        elif file_string[i] == bracket_type[1]:
            bcount -= 1
        if bcount == 0:
            return i + 1
    return len(file_string) - start_index


def generate_7seg_func(testblocks):
    """
    Convert the shorthand 7seg syntax into its full expanded form.
    """
    for i in range(len(testblocks)):
        match = re.search(r'7seg\s*\(', testblocks[i])
        while match is not None:
            end = find_block_end(testblocks[i][match.end(0):], bracket_type='()') - 1
            arg = testblocks[i][match.end(0):match.end(0) + end]
            binval = 0

            if arg.startswith('0x'):
                try:
                    binval = int(arg, 16)
                except NameError or SyntaxError or ZeroDivisionError:
                    print('Semantic Error - the equation (\"{0:s}\") passed to the 7seg() function cannot be evaluated.'.format(arg))
                    return False
            else:
                try:
                    binval = int(eval(arg))
                except NameError or SyntaxError or ZeroDivisionError:
                    print('Semantic Error - the equation (\"{0:s}\") passed to the 7seg() function cannot be evaluated.'.format(arg))
                    return False

            if binval > 15 or binval < 0:
                print('Semantic Error - the equation (\"{0:s}\") passed to the 7seg() evaluates to {1:d} and cannot be displayed on a 7 segment display.'.format(arg, binval))
                return False

            decoder = {
                0: '1000000',
                1: '1111001',
                2: '0100100',
                3: '0110000',
                4: '0011001',
                5: '0010010',
                6: '0000010',
                7: '1111000',
                8: '0000000',
                9: '0010000',
                10: '0001000',
                11: '0000011',
                12: '1000110',
                13: '0100001',
                14: '0000110',
                15: '0001110'
            }

            testblocks[i] = testblocks[i][:match.start()] + decoder[binval] + testblocks[i][end + match.end() + 1:]
            match = re.search(r'7seg\s*\(', testblocks[i])


def generate_bin_func(testblocks):
    """
    Convert the shorthand bin function into its full expanded form.
    """
    for i in range(len(testblocks)):
        match = re.search(r'bin\s*\(', testblocks[i])
        dec_val = 0
        num_bits = 0
        bin_val = ''
        while match is not None:
            end = find_block_end(testblocks[i][match.end(0):], bracket_type='()') - 1
            args = testblocks[i][match.end(0):match.end(0) + end].split(',')
            if len(args) != 2:
                print('Semantic Error - the bin() function takes exactly 2 arguments.')
                return False, ''

            if args[0].startswith('0x'):
                try:
                    dec_val = int(args[0], 16)
                except ValueError:
                    print('Semantic Error - the first argument to the bin function "{0:s}" is invalid. Only integer or hex values are accepted.'.format(args[0]))
                    return False, ''
            else:
                try:
                    dec_val = int(eval(args[0]))
                except NameError or SyntaxError or ZeroDivisionError:
                    print('Semantic Error - the equation (\"{0:s}\") passed to the bin() function cannot be evaluated.'.format(args[0]))
                    return False, ''

            try:
                num_bits = int(eval(args[1]))
            except NameError or SyntaxError or ZeroDivisionError:
                print('Semantic Error - the equation (\"{0:s}\") passed to the bin() function cannot be evaluated.'.format(args[1]))
                return False, ''

            bin_val = format(dec_val, '0' + str(num_bits) + 'b')

            if len(bin_val) > int(num_bits):
                print('Semantic Error - overflow from the bin() function: {0:d} cannot be represented with {1:s} binary bits.'.format(dec_val, num_bits))
                return False, ''

            testblocks[i] = testblocks[i][:match.start()] + bin_val + testblocks[i][end + match.end() + 1:]
            match = re.search(r'bin\s*\(', testblocks[i])

    return True


def generate_force_calls(testblocks):
    """
    Expand the shorthand assignment statements into ModelSim force statements.
    """
    for b in range(len(testblocks)):
        formatted_block = testblocks[b].replace('{', ';')
        formatted_block = formatted_block.replace('}', ';')
        tokens = [t.strip() for t in formatted_block.split(';') if t != '']

        for t in tokens:
            gen_code = ''
            if re.search(r'^[\w\+\-\*\/\:\[\]]+\s*=\s*\d+$', t):
                sub_tokens = [st.strip() for st in t.split('=')]
                variable = sub_tokens[0]
                assignment = sub_tokens[1]

                # List variable force
                match = re.search(r'\[.+?:.+?\]', variable)
                if match is not None:
                    indices_string = variable[match.start():match.end()]
                    variable = variable.replace(indices_string, '')

                    indices = []
                    try:
                        indices = [int(eval(i)) for i in indices_string[1:-1].split(':')]
                    except NameError or SyntaxError or ZeroDivisionError:
                        print('Semantic Error - the equation used to index the vairable (\"{0:s}\") cannot be evaluated.'.format(variable + indices_string))
                        return False

                    magnitude = abs(indices[0] - indices[1]) + 1
                    increment = 1
                    if indices[0] - indices[1] > 0:
                        increment = -1

                    if len(assignment) == 1:
                        for i in range(indices[0], indices[1] + increment, increment):
                            gen_code += 'force {{{0:s}[{1:d}]}} {2:s};'.format(variable, i, assignment)
                    elif len(assignment) == magnitude:
                        ai = 0
                        for i in range(indices[0], indices[1] + increment, increment):
                            gen_code += 'force {{{0:s}[{1:d}]}} {2:s};'.format(variable, i, assignment[ai])
                            ai += 1
                    else:
                        print('Syntax Error - wrong amount of values passed to assignment: \"{0:s}\"'.format(t))
                        print('             - in this case provide 1 or {0:d} values instead.'.format(magnitude))
                        return False

                # Single variable force
                else:
                    # Index evaluation
                    match = re.search(r'\[.+?\]', variable)
                    if match is not None:
                        try:
                            indices_string = str(int(eval(match.group()[1:-1])))
                            variable = variable.replace(match.group(), '[{0:s}]'.format(indices_string))
                        except NameError or SyntaxError or ZeroDivisionError:
                            print('Semantic Error - the equation used to index the vairable (\"{0:s}\") cannot be evaluated.'.format(variable))
                            return False

                    gen_code = 'force {{{0:s}}} {1:s};'.format(variable, assignment)

                testblocks[b] = testblocks[b].replace(t, gen_code, 1)


def generate_assert_func(testblocks):
    """
    Convert the shorthand asserion statements into ModelSim assertions.
    """
    for b in range(len(testblocks)):
        formatted_block = testblocks[b].replace('{', ';')
        formatted_block = formatted_block.replace('}', ';')
        tokens = [t.strip() for t in formatted_block.split(';') if t != '']

        test_name = ''
        test_name_tokens = tokens[0].split()
        if len(test_name_tokens) == 2:
            test_name = test_name_tokens[1]

        for t in tokens:
            if re.search(r'^assert\s+[\w\+\-\*\/\:\[\]]+\s*\=\=\s*[01]+$', t):
                assert_string = t
                subtokens = t.split('==')
                variable = subtokens[0].strip().split(' ')[-1]
                expected = subtokens[1].strip()

                gen_code = ''

                # List variable assertion
                match = re.search(r'\[.+?:.+?\]', variable)
                if match is not None:
                    indices_string = variable[match.start():match.end()]
                    variable = variable.replace(indices_string, '')

                    indices = []
                    try:
                        indices = [int(eval(i)) for i in indices_string[1:-1].split(':')]
                    except NameError or SyntaxError or ZeroDivisionError:
                        print('Semantic Error - the equation used to index the vairable (\"{0:s}\") cannot be evaluated.'.format(variable + indices_string))
                        return False

                    magnitude = abs(indices[0] - indices[1]) + 1
                    increment = 1
                    if indices[0] - indices[1] > 0:
                        increment = -1

                    if len(expected) == 1:
                        gen_code = 'run {0:s};echo \"assert {1:s} {2:s}\";'.format(meta_dict['timestep'], expected * magnitude, test_name)
                    elif len(expected) == magnitude:
                        gen_code = 'run {0:s};echo \"assert {1:s} {2:s}\";'.format(meta_dict['timestep'], expected, test_name)
                    else:
                        print('Syntax Error - wrong amount of values passed to assert function: \"{0:s}\"'.format(assert_string))
                        print('             - in this case provide 1 or {0:d} values instead.'.format(magnitude))
                        return False

                    for i in range(indices[0], indices[1]+increment, increment):
                        gen_code += 'examine {{{0:s}[{1:d}]}};'.format(variable, i)

                # Single variable assertion
                else:
                    # Index evaluation
                    match = re.search(r'\[.+?\]', variable)
                    if match is not None:
                        try:
                            indices_string = str(int(eval(match.group()[1:-1])))
                            variable = variable.replace(match.group(), '[{0:s}]'.format(indices_string))
                        except NameError or SyntaxError or ZeroDivisionError:
                            print('Semantic Error - the equation used to index the vairable (\"{0:s}\") cannot be evaluated.'.format(variable))
                            return False

                    if len(expected) != 1:
                        print('Syntax Error - too many values passed to assert for the single variable \"{0:s}\".'.format(variable))
                        print('             - to assert multiple variables at once use a list variable instead.')
                        return False
                    else:
                        gen_code = 'run {0:s};echo \"assert {1:s} {2:s}\";examine {{{3:s}}};'.format(meta_dict['timestep'], expected, test_name, variable)

                testblocks[b] = testblocks[b].replace(assert_string, gen_code, 1)


def generate_for_blocks(testblocks):
    """
    Expand the shorthand for statement into its expanded form.
    """
    found_match = False

    for i in range(len(testblocks)):
        pattern = re.compile(r'for\s+\w\s+in\s+\[\d+:\d+\]\s*\{')
        match = pattern.search(testblocks[i])

        if match is not None:
            found_match = True
            end = find_block_end(testblocks[i], match.end())
            find = testblocks[i][match.start():end]
            find_mut = find
            replace = ''

            tokens = [t.strip() for t in match.group().split(' ') if t != '']
            variable = str(tokens[1])
            raw_range = tokens[3][1:-1]
            if raw_range[-1] == ']':
                raw_range = raw_range[:-1]

            indices = [int(t) for t in raw_range.split(':')]
            magnitude = abs(indices[0] - indices[1]) + 1
            increment = 1
            if indices[0] - indices[1] > 0:
                increment = -1

            for j in range(indices[0], indices[1] + increment, increment):
                var_pattern = re.compile(r'[\s:%\[\^\*\+\-\/\(\=]' + variable + r'[\s;:%\]\^\*\+\-\/\),]')
                var_match = var_pattern.search(find_mut)
                while var_match is not None:
                    find_mut = find_mut.replace(var_match.group(), var_match.group().replace(variable, str(j)))
                    var_match = var_pattern.search(find_mut)
                replace += find_mut[find_mut.index('{') + 1:-1] + ';'
                find_mut = find

            testblocks[i] = testblocks[i].replace(find, replace)

    # repeat until all for blocks are generated
    if found_match:
        generate_for_blocks(testblocks)


def add_meta_command(command, value):
    """
    Add meta command to dict if it has not already been declared.
    """
    if command in meta_dict or command in REQUIRED_META:
        meta_dict[command] = value
    else:
        meta_commands.append(command + ' ' + value)


def generate_meta(meta_string):
    """
    Generate ModelSim metadata.
    """
    global meta, meta_commands, meta_dict

    lines = [t.strip() for t in meta_string.replace('=', ' ').split(';') if t != '']
    for line in lines:
        tokens = [t.strip() for t in line.split(' ') if t != '']
        command = tokens[0]
        value = ' '.join(tokens[1:])
        add_meta_command(command, value)

    try:
        meta.append('vlib ' + meta_dict['vlib'])
        meta.append('vlog -timescale ' + meta_dict['timescale'] + ' ' + meta_dict['vfile'])
        meta.append('vsim ' + meta_dict['vmodule'] + ' -l ' + meta_dict['logfile'])
        meta += meta_commands
    except KeyError as e:
        print('Syntax Error - missing a definition for {0:s} in the meta block.'.format(str(e)))
        return False

    return True


def parse_blocks(lines):
    """
    Parse the different program blocks from the user's input file, and process
    it into a format compatable with ModelSim.
    """
    file_string = ''.join([l.strip() if not l.strip().startswith("#") else '' for l in lines])

    # Parse top level blocks (meta, test) since they cannot be nested
    # Meta blocks
    match = re.search(r'meta\s*\{', file_string)
    if match is not None:
        metablock = file_string[match.end():find_block_end(file_string, match.end())-1]
        generate_meta(metablock)
    else:
        print('Syntax Error - No meta block found.')

    # Test blocks
    testblocks_indices = [(m.start(0), m.end(0)) for m in re.finditer(r'test\s*(\w+)?\s*\{', file_string)]
    testblocks = [file_string[indices[0]:indices[1] + find_block_end(file_string[indices[1]:])] for indices in testblocks_indices]

    # For blocks need to be generated before permute blocks
    generate_for_blocks(testblocks)

    # Recursively parse permute blocks (which can only exist in testblocks. Permute blocks cannot be nested in one another)
    # Permute block
    permute_blocks = []
    for block in testblocks:
        formatted_block = block[block.index('{') + 1:-1]
        # Check for nested test blocks
        if re.search(r'test\s*(\w+)?\s*\{', formatted_block) is not None:
            print('Semantic Error - Nested test blocks are not valid. Generation Failed.')
            return False

        match = re.search(r'permute\s*\{', formatted_block)
        while match is not None:
            end = match.end() + find_block_end(formatted_block[match.end():])
            permute_blocks.append(formatted_block[match.start(): end])
            formatted_block = formatted_block[end:]
            match = re.search(r'permute\s*\{', formatted_block)

    for block in permute_blocks:
        # Assert that permute blocks are not nested
        formatted_block = block[block.index('{') + 1:-1]
        if re.search(r'permute\s*\{', formatted_block) is not None:
            print('Semantic Error - Nested permute blocks are not valid. Generation Failed.')
            return False

        perm_sub_blocks = [formatted_block]
        match = re.search(r'[\w\:\[\]]+\s*\=\s*\*;', perm_sub_blocks[0])
        while match is not None:
            new_blocks = []

            # List assignment
            list_match = re.search(r'\w+\[\d+\:\d+\]\s*\=\s*\*;', perm_sub_blocks[0])
            if list_match is not None and match.start() == list_match.start():
                var_pattern = re.compile(r'\[\d+:\d+\]')
                var_match = var_pattern.search(perm_sub_blocks[0], match.start())
                src_line = match.group()
                gen_code = ''

                indices_string = var_match.group()
                variable = perm_sub_blocks[0][match.start():var_match.start()]
                indices = [int(i) for i in indices_string[1:-1].split(':')]
                magnitude = abs(indices[0] - indices[1]) + 1
                increment = 1
                if indices[0] - indices[1] > 0:
                    increment = -1

                for i in range(indices[0], indices[1] + increment, increment):
                    gen_code += src_line.replace(indices_string, '[{0:d}]'.format(i))

                for b in perm_sub_blocks:
                    new_blocks.append(b.replace(src_line, gen_code, 1))

            # Single variable assignment
            else:
                for b in perm_sub_blocks:
                    new_blocks.append(b.replace('*;', '0;', 1))
                    new_blocks.append(b.replace('*;', '1;', 1))

            perm_sub_blocks = new_blocks
            match = re.search(r'[\w\:\[\]]+\s*\=\s*\*;', perm_sub_blocks[0])

        for i in range(len(testblocks)):
            if block in testblocks[i]:
                testblocks[i] = testblocks[i].replace(block, "".join(perm_sub_blocks), 1)
                continue

    generate_7seg_func(testblocks)
    generate_bin_func(testblocks)
    generate_assert_func(testblocks)
    generate_force_calls(testblocks)

    out_test_blocks = meta

    for i in range(len(testblocks)):
        out_test_blocks.append(testblocks[i][testblocks[i].index('{') + 1:-1])
    with open(meta_dict['genfile'], 'w') as out:
        out.writelines(';'.join(out_test_blocks).replace(';', '\n'))

    return True

if __name__ == '__main__':
    if len(sys.argv) == 1:
        filename = input('Enter filename of unit test file: ')
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        print('A unit test file must be passed in as an argument.')
        sys.exit(0)

    with open(filename, 'r') as file:
        lines = file.readlines()
        passed_syntax = check_bracket_pairing(lines)
        passed_syntax = passed_syntax and check_assert_double_equals(lines)

        if passed_syntax and parse_blocks(lines):
            print('File generation successful')
        else:
            print('Syntax errors are present - file generation aborted')
