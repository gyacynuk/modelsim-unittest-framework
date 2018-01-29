import sys
import re

filename = 'fulladder.txt'

OPEN_BRACKETS = ['(', '{', '[']  # order of elements between these sets is crucial
CLOSE_BRACKETS = [')', '}', ']']

TIMESTEP = '2 ns'

def log_bracket_error(lines, line, pos, open=True):
    if open:
        print('Syntax Error - Unclosed bracket on line {0:d} at position {1:d}:'.format(line+1, pos))
    else:
        print('Syntax Error - Extra closing bracket on line {0:d} at position {1:d}:'.format(line+1, pos))
    print('\t\"'+str(lines[line].strip()) + '\"')
    print('\t ' + ' '*pos + '^')

def check_bracket_pairing(lines):
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

#annoying since you have to add one to the index, but it is used heavily
# TODO depricate
def find_block_end(file_string, start_index = 0, bracket_type='{}'):
    bcount = 1
    for i in range(start_index, len(file_string)):
        if file_string[i] == bracket_type[0]:
            bcount += 1
        elif file_string[i] == bracket_type[1]:
            bcount -= 1
        if bcount == 0:
            return i
    return len(file_string)

#new version, much easier to use
# TODO replace the old verison with this one
# Given a string, starting fron the start index, assuming that one bracket exists at start_index -1, return the index of the last bracket + 1
def find_block_end2(file_string, start_index = 0, bracket_type='{}'):
    bcount = 1
    for i in range(start_index, len(file_string)):
        if file_string[i] == bracket_type[0]:
            bcount += 1
        elif file_string[i] == bracket_type[1]:
            bcount -= 1
        if bcount == 0:
            return i + 1
    return len(file_string) - start_index

def generate_sums(testblocks):
    for i in range(len(testblocks)):
        pattern = re.compile(r'\d+(\s*\+\s*\d+)+')
        match = pattern.search(testblocks[i])

        while match is not None:
            sum = 0
            nums = [t.strip() for t in match.group().split('+') if t != '']

            for num in nums:
                sum += int(num)

            testblocks[i] = testblocks[i].replace(match.group(), str(sum), 1)
            match = pattern.search(testblocks[i])


def generate_bin_func(testblocks):
    for i in range(len(testblocks)):
        match = re.search(r'bin\s*\(', testblocks[i])
        dec_val = 0
        num_bits = ''
        bin_val = ''
        while match is not None:
            end = find_block_end(testblocks[i][match.end(0):], bracket_type='()')
            args = [token.strip() for token in testblocks[i][match.end(0):match.end(0) + end].split(',')]
            if len(args) != 2:
                print('Semantic Error - the bin() function takes exactly 2 arguments.')
                return False, ''

            if args[0].isdigit():
                dec_val = int(args[0])
            elif args[0].startswith('0x'):
                try:
                    dec_val = int(args[0], 16)
                except ValueError:
                    print('Semantic Error - the first argument to the bin function "{0:s}" is invalid. Only integer or hex values are accepted.'.format(args[0]))
                    return False, ''
            else:
                print('Semantic Error - the first argument to the bin function "{0:s}" is invalid. Only integer or hex values are accepted.'.format(args[0]))
                return False, ''

            if args[1].isdigit():
                num_bits = args[1]
            else:
                print('Semantic Error - the second argument to the bin function "{0:s}" is invalid. Only integer values are accepted.'.format(args[1]))
                return False, ''

            bin_val = format(dec_val, '0' + num_bits + 'b')

            if len(bin_val) > int(num_bits):
                print('Semantic Error - overflow from the bin() function: {0:d} cannot be represented with {1:s} binary bits.'.format(dec_val, num_bits))
                return False, ''

            testblocks[i] = testblocks[i][:match.start()] + bin_val + testblocks[i][end + match.end() + 1:]
            match = re.search(r'bin\s*\(', testblocks[i])

    return True

def generate_force_calls(testblocks):
    for b in range(len(testblocks)):
        formatted_block = testblocks[b].replace('{', ';')
        formatted_block = formatted_block.replace('}', ';')
        tokens = [t.strip() for t in formatted_block.split(';') if t != '']

        for t in tokens:
            gen_code = ''
            if re.search(r'^[\w\:\[\]]+\s*=\s*\d+$', t):
                sub_tokens = [st.strip() for st in t.split('=')]
                variable = sub_tokens[0]
                assignment = sub_tokens[1]

                # List variable force
                match = re.search(r'\[\d+\:\d+\]', variable)
                if match is not None:
                    indices_string = variable[match.start():match.end()]
                    variable = variable.replace(indices_string, '')
                    indices = [int(i) for i in indices_string[1:-1].split(':')]
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
                    gen_code = 'force {{{0:s}}} {1:s};'.format(variable, assignment)

                testblocks[b] = testblocks[b].replace(t, gen_code, 1)


def generate_assert_func(testblocks):
    for b in range(len(testblocks)):
        formatted_block = testblocks[b].replace('{', ';')
        formatted_block = formatted_block.replace('}', ';')
        tokens = [t.strip() for t in formatted_block.split(';') if t != '']

        test_name = ''
        test_name_tokens = tokens[0].split()
        if len(test_name_tokens) == 2:
            test_name = test_name_tokens[1]

        for t in tokens:
            if re.search(r'^assert\s+[\w\:\[\]]+\s*\=\=\s*\d+$', t):
                assert_string = t
                t = t.replace('==', ' ')
                subtokens = [a for a in t.split(' ') if a != '']
                variable = subtokens[1]
                expected = subtokens[2]

                gen_code = ''

                # List variable assertion
                match = re.search(r'\[\d+\:\d+\]', variable)
                if match is not None:
                    indices_string = variable[match.start():match.end()]
                    variable = variable.replace(indices_string, '')
                    indices = [int(i) for i in indices_string[1:-1].split(':')]
                    magnitude = abs(indices[0] - indices[1]) + 1
                    increment = 1
                    if indices[0] - indices[1] > 0:
                        increment = -1

                    if len(expected) == 1:
                        gen_code = 'run {0:s};echo \"assert {1:s} {2:s}\";'.format(TIMESTEP, expected * magnitude, test_name)
                    elif len(expected) == magnitude:
                        gen_code = 'run {0:s};echo \"assert {1:s} {2:s}\";'.format(TIMESTEP, expected, test_name)
                    else:
                        print('Syntax Error - wrong amount of values passed to assert function: \"{0:s}\"'.format(assert_string))
                        print('             - in this case provide 1 or {0:d} values instead.'.format(magnitude))
                        return False

                    for i in range(indices[0], indices[1]+increment, increment):
                        gen_code += 'examine {{{0:s}[{1:d}]}};'.format(variable, i)

                # Single variable assertion
                else:
                    if len(expected) != 1:
                        print('Syntax Error - too many values passed to assert for the single variable \"{0:s)\".'.format(variable))
                        print('             - to assert multiple variables at once use a list variable instead.')
                        return False
                    else:
                        gen_code = 'run {0:s};echo \"assert {1:s} {2:s}\";examine {{{3:s}}};'.format(TIMESTEP, expected, test_name, variable)

                testblocks[b] = testblocks[b].replace(assert_string, gen_code, 1)


def generate_for_blocks(testblocks):
    found_match = False

    for i in range(len(testblocks)):
        pattern = re.compile(r'for\s+\w\s+in\s+\[\d+:\d+\]\s*\{')
        match = pattern.search(testblocks[i])

        if match is not None:
            found_match = True
            end = find_block_end2(testblocks[i], match.end())
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
                var_pattern = re.compile(r'[\s:\[\*\+\-\/\(\=]' + variable + r'[\s;:\]\*\+\-\/\),]')
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


def generate_meta(meta):
    pass

def generate_test(test):
    pass

def generate_permute(permute):
    pass

def parse_blocks(lines):
    file_string = ''.join([l.strip() if not l.strip().startswith("#") else '' for l in lines])

    # Parse top level blocks (meta, test) since they cannot be nested
    # Meta blocks
    metablock_indices = [(m.start(0), m.end(0)) for m in re.finditer(r'meta\s*\{', file_string)]
    if len(metablock_indices) != 0:
        if len(metablock_indices) > 1:
            print('Semantic Warning - multiple meta blocks detected. Only the first block will be executed.')
        indices = metablock_indices[0]
        metablock = file_string[indices[0]:indices[1] + find_block_end(file_string[indices[1]:]) + 1]
        ## TODO Before execution, check for only one pair of {}

    # Test blocks
    testblocks_indices = [(m.start(0), m.end(0)) for m in re.finditer(r'test\s*(\w+)?\s*\{', file_string)]
    testblocks = [file_string[indices[0]:indices[1] + find_block_end(file_string[indices[1]:]) + 1] for indices in testblocks_indices]

    #TODO Generate for blocks BEFORE PERMUTE
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
            end = match.end() + find_block_end(formatted_block[match.end():]) + 1
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
            if list_match != None and match.start() == list_match.start():
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

    generate_sums(testblocks)
    generate_bin_func(testblocks)
    generate_assert_func(testblocks)
    generate_force_calls(testblocks)

    out_test_blocks = []
    for i in range(len(testblocks)):
        out_test_blocks.append(testblocks[i][testblocks[i].index('{') + 1:-1])
    with open('out.do', 'w') as out:
        out.writelines(';'.join(out_test_blocks).replace(';', '\n'))

    return True


with open(filename, 'r') as file:
    lines = file.readlines()
    passed_syntax = check_bracket_pairing(lines)

    if passed_syntax and parse_blocks(lines):
        print('File generation successful')
    else:
        print('Syntax errors are present - file generation aborted')
