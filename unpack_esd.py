# -*- coding: utf-8 -*-
"""
@author: grimrhapsody

TODO: Support for repacking double tables (enemyCommon.esd).
"""

from collections import OrderedDict
from contextlib import redirect_stdout
from io import BytesIO
from struct import calcsize, pack, unpack
from command_names import COMMAND_NAMES
from ezstate_parser import ezparse, reset_registers


class EzStruct(OrderedDict):

    def unpack(self, buffer, count=1, header_size=27 * 4):
        if isinstance(buffer, bytes):
            buffer = BytesIO(buffer)
        outputs = {}
        for i in range(count):
            output = {}
            offset = buffer.tell() - header_size
            for field_name, field_fmt in self.items():
                unpacked = unpack(field_fmt, buffer.read(calcsize(field_fmt)))
                if len(unpacked) == 1:
                    # Expand tuple automatically for single value.
                    output[field_name] = unpacked[0]
                else:
                    output[field_name] = unpacked
            outputs[offset] = output
        return outputs

    def pack(self, sequences):
        if not isinstance(sequences, (list, tuple)):
            sequences = (sequences,)
        output = b''
        for sequence in sequences:
            if isinstance(sequence, (list, tuple)):
                # Check number of entries matches number of fields in struct.
                if len(sequence) != len(self.keys()):
                    print('EzStruct keys:', self.keys())
                    print('Sequence values ({}):'.format(len(sequence)), sequence)
                    raise ValueError('List/tuple must have correct number of fields.')
                for i, field_fmt in enumerate(self.values()):
                    field = sequence[i]
                    if not isinstance(field, (tuple, list)):
                        field = (field,)
                    # print(pack(field_fmt, *field))
                    output += pack(field_fmt, *field)
            elif isinstance(sequence, dict):
                # Check keys match.
                if set(self.keys()) != set(sequence.keys()):
                    print('EzStruct keys:', self.keys())
                    print('Dictionary keys:', sequence.keys())
                    raise ValueError('Dictionary keys must match fields in EzStruct.')
                for field_name, field_fmt in self.items():
                    field = sequence[field_name]
                    if not isinstance(field, (tuple, list)):
                        field = (field,)
                    # print(pack(field_fmt, *field))
                    output += pack(field_fmt, *field)
        return output

    @property
    def size(self):
        return calcsize(''.join(fmt for fmt in self.values()))


HEADER = EzStruct(
    version='4s',
    version_tail='iii',  # (1, 1, 1)
    table_size_offset='i',  # 84
    file_size_offset='i',  # excludes header size
    unknowns='iiii',  # (6, 44, 1, 16)  probably offsets or sizes of something obvious
    state_table_count='i',  # 1 or 2 (for enemyCommon.esd)
    state_row_size='i',
    state_row_count='i',
    condition_row_size='i',
    condition_row_count='i',
    command_row_size='i',
    command_row_count='i',
    command_arg_row_size='i',
    command_arg_row_count='i',
    condition_pointers_offset='i',
    condition_pointers_count='i',
    esd_name_0_offset='i',
    esd_name_0_size='i',
    esd_name_1_offset='i',
    esd_name_1_size='i',
    esd_name_2_offset='i',
    esd_name_2_size='i',
)


SINGLE_STATE_HEADER = EzStruct(
    unknowns_1='5i',  # (1, big, big, big, big)
    esd_names_offset='i',
    esd_names_count='i',
    esd_name_0_offset='i',
    esd_name_0_size='i',
    zeroes='ii',
    first_state_table_index='i',
    first_state_table_offset='i',
    first_state_table_size='i',  # number of states
    first_state_table_offset_2='i',  # duplicate
)


DOUBLE_STATE_HEADER = EzStruct(
    unknowns_1='5i',  # (1, big, big, big, big)
    esd_names_offset='i',
    esd_names_count='i',
    esd_name_0_offset='i',
    esd_name_0_size='i',
    zeroes='ii',
    first_state_table_index='i',
    first_state_table_offset='i',
    first_state_table_size='i',  # number of states
    first_state_table_offset_2='i',  # duplicate
    second_state_table_index='i',
    second_state_table_offset='i',
    second_state_table_size='i',  # number of states
    second_state_table_offset_2='i',  # duplicate
)


STATE = EzStruct(
    index='i',
    condition_pointers_offset='i',
    condition_pointers_count='i',
    enter_commands_offset='i',
    enter_commands_count='i',
    exit_commands_offset='i',
    exit_commands_count='i',
    unknown_commands_offset='i',
    unknown_commands_count='i',
)


CONDITION = EzStruct(
    next_state_offset='i',
    commands_offset='i',
    commands_count='i',
    subcondition_pointers_offset='i',
    subcondition_pointers_count='i',
    packed_expression_offset='i',
    packed_expression_size='i',
)


COMMAND = EzStruct(
    unknown='i',  # Always 1
    index='i',
    args_offset='i',
    args_count='i',
)


COMMAND_ARG = EzStruct(
    packed_expression_offset='i',
    packed_expression_size='i',
)


CONDITION_POINTER = EzStruct(
    condition_offset='i',
)


class State(object):

    def __init__(self, index, conditions, onset_commands, offset_commands, unknown_commands):
        self.index = index
        self.conditions = conditions
        self.enter_commands = onset_commands
        self.exit_commands = offset_commands
        self.unknown_commands = unknown_commands

    def __eq__(self, other_state):
        return self.__dict__ == other_state.__dict__

    def __str__(self):

        s = state_title_bar(self.index)

        fmt = '<br><div style="font-size:20px;font-weight:bold;margin-left:10px">{}</div>'

        if self.enter_commands:
            s += fmt.format('(ENTER) Commands:')
            for command in self.enter_commands:
                s += str(command)

        if self.conditions:
            s += fmt.format('State Change Conditions:')
            reset_registers()
            for condition in self.conditions:
                s += str(condition)

        if self.exit_commands:
            s += fmt.format('(EXIT) Commands:')
            for command in self.exit_commands:
                s += str(command)

        if self.unknown_commands:
            s += fmt.format('(UNKNOWN) Commands:')
            for command in self.unknown_commands:
                s += str(command)

        return s


class Condition(object):

    def __init__(self, next_state_index, expression, commands=(), subconditions=(), print_indent=0):
        self.next_state_index = next_state_index
        self.expression = expression
        self.commands = commands
        self.subconditions = subconditions
        self.__indent = print_indent

    def __eq__(self, other_condition):
        return (self.next_state_index == other_condition.next_state_index
                and self.expression == other_condition.expression
                and self.commands == other_condition.commands
                and self.subconditions == other_condition.subconditions)

    def __hash__(self):
        return hash((self.next_state_index, self.expression, tuple(self.commands), tuple(self.subconditions)))

    def __str__(self, raw=False, full_brackets=False):

        state_fmt = '<br><div style="color:black;line-height:0.5;margin-left:{}px;">{}</div>'
        expression_fmt = ('<br><div style="color:black;line-height:1;margin-left:{}px;font-family:sans-serif">IF: '
                          '{}</div>')
        command_fmt = '<br><div style="color:black;font-weight:bold;line-height:0.5;margin-left:{}px;">{}</div>'
        string = ''

        if raw:
            string += expression_fmt.format(30 * (2 + self.__indent), ''.join(str(self.expression.hex())))
        string += expression_fmt.format(20 * (2 + self.__indent), ezparse(self.expression, full_brackets))

        if self.next_state_index != -1:
            string += state_fmt.format(20 * (3 + self.__indent), '---> <a href="#ezstate_{index}">State {index}'
                                                                 '</a>:'.format(index=self.next_state_index))

        if self.commands:
            string += command_fmt.format(20 * (2 + self.__indent), 'Commands:')
            for command in self.commands:
                string += str(command)
        if self.subconditions:
            for condition in self.subconditions:
                string += str(condition)
        return string


class Command(object):

    def __init__(self, unknown, index, command_args=(), indent=0):
        self.unknown = unknown
        self.index = index
        self.args = command_args
        self.__indent = indent

    def __eq__(self, other_command):
        return (self.unknown == other_command.unknown
                and self.index == other_command.index
                and self.args == other_command.args)

    def __hash__(self):
        return hash((self.unknown, self.index, tuple(self.args)))

    def __str__(self, raw=False):
        names = COMMAND_NAMES.get(self.index, None)
        fmt = '<br><div style="color:black;line-height:1;margin-left:{}px;">{}({})</div>'
        string = ''
        if raw and names is not None:
            string += fmt.format(20 * (2 + self.__indent), names[0], ', '.join([' '.join(arg) for arg in self.args]))
        elif names is None or (len(names) != len(self.args) + 1 and len(names) != 1):
            name = 'function_{}'.format(self.index)
            red_fmt = fmt.replace('color:black', 'color:red')
            string += red_fmt.format(20 * (2 + self.__indent), name, ', '.join([ezparse(arg) for arg in self.args]))
        elif len(names) == 1:
            string += fmt.format(20 * (2 + self.__indent), names[0], ', '.join([ezparse(arg) for arg in self.args]))
        else:
            string += fmt.format(20 * (2 + self.__indent), names[0],
                                 ', '.join([names[i + 1] + '=' + ezparse(arg) for i, arg in enumerate(self.args)]))
        return string


class EzState(object):

    def __init__(self, input_path):

        self.input_path = input_path
        self.states = []

        with open(input_path, 'rb') as file:

            self.header = HEADER.unpack(file)[-27 * 4]

            if self.header['state_table_count'] == 1:
                self.state_table_count = 1
                self.state_header = SINGLE_STATE_HEADER.unpack(file)[0]
            elif self.header['state_table_count'] == 2:
                self.state_table_count = 2
                self.state_header = DOUBLE_STATE_HEADER.unpack(file)[0]

            self.state_table = STATE.unpack(file, count=self.header['state_row_count'])
            self.condition_table = CONDITION.unpack(file, count=self.header['condition_row_count'])
            self.command_table = COMMAND.unpack(file, count=self.header['command_row_count'])
            self.command_arg_table = COMMAND_ARG.unpack(file, count=self.header['command_arg_row_count'])
            self.condition_pointer_table = CONDITION_POINTER.unpack(file, count=self.header['condition_pointers_count'])
            self.packed_offset = file.tell() - HEADER.size
            self.packed_expressions = file.read()  # Rest of file.

            if self.state_header['esd_names_count'] == 1:
                esd_name_offset = self.state_header['esd_name_0_offset']
                esd_size = self.state_header['esd_name_0_size']
                if esd_size > 0:
                    self.esd_name = self.get_packed_expression(esd_name_offset, 2 * esd_size).decode('utf-16le')
                    self.file_tail = self.packed_expressions[esd_name_offset + 2 * esd_size - self.packed_offset:]
            else:
                self.esd_name = None
                self.file_tail = self.packed_expressions[self.header['esd_name_2_offset']:]

            # Unpack and parse expressions for inspection (indexed with offset).
            self.unpacked_expressions = {}
            self.parsed_expressions = {}
            for condition in self.condition_table.values():
                start = condition['packed_expression_offset'] - self.packed_offset
                end = condition['packed_expression_offset'] + condition['packed_expression_size'] - self.packed_offset
                expression = self.packed_expressions[start:end]
                self.unpacked_expressions[condition['packed_expression_offset']] = expression
                self.parsed_expressions[condition['packed_expression_offset']] = ezparse(expression)
            for arg in self.command_arg_table.values():
                start = arg['packed_expression_offset'] - self.packed_offset
                end = arg['packed_expression_offset'] + arg['packed_expression_size'] - self.packed_offset
                expression = self.packed_expressions[start:end]
                self.unpacked_expressions[arg['packed_expression_offset']] = expression
                self.parsed_expressions[arg['packed_expression_offset']] = ezparse(expression)

            self.build()

    def get_packed_expression(self, offset, size):
        return self.packed_expressions[offset - self.packed_offset:offset - self.packed_offset + size]

    def build(self):

        self.states = []
        for state in self.state_table.values():
            conditions = self.parse_conditions(state['condition_pointers_offset'], state['condition_pointers_count'])
            enter_commands = self.parse_commands(state['enter_commands_offset'], state['enter_commands_count'])
            exit_commands = self.parse_commands(state['exit_commands_offset'], state['exit_commands_count'])
            unknown_commands = self.parse_commands(state['unknown_commands_offset'], state['unknown_commands_count'])
            self.states.append(
                State(state['index'], conditions, enter_commands, exit_commands, unknown_commands)
            )

    def parse_conditions(self, condition_pointers_offset, condition_pointers_count, print_indent=0):
        """ Get list of Conditions from condition pointers. """
        if condition_pointers_offset == -1:
            # No conditions.
            return []
        conditions = []
        for i in range(condition_pointers_count):
            condition_offset = self.condition_pointer_table[condition_pointers_offset + 4 * i]['condition_offset']
            condition = self.condition_table[condition_offset]

            next_state_offset = condition['next_state_offset']

            next_state_index = -1 if next_state_offset == -1 else self.state_table[next_state_offset]['index']
            if condition['commands_offset'] == -1:
                # No command.
                commands = ()
            else:
                commands = self.parse_commands(condition['commands_offset'],
                                               condition['commands_count'],
                                               print_indent=print_indent + 4)
            if condition['subcondition_pointers_offset'] == -1:
                subconditions = ()
            else:
                subconditions = self.parse_conditions(condition['subcondition_pointers_offset'],
                                                      condition['subcondition_pointers_count'],
                                                      print_indent=print_indent + 4)
            condition_expression = self.get_packed_expression(
                condition['packed_expression_offset'], condition['packed_expression_size'])
            conditions.append(
                Condition(next_state_index, condition_expression, commands, subconditions, print_indent=print_indent)
            )
        return conditions

    def parse_commands(self, commands_offset, commands_count, print_indent=0):
        """ Get Commands and their arguments. """
        if commands_offset == -1:
            return []
        commands = []
        for i in range(commands_count):
            command = self.command_table[commands_offset + COMMAND.size * i]
            if command['args_offset'] == -1:
                # Command has no arguments.
                commands.append(Command(command['unknown'], command['index'], indent=print_indent))
            else:
                command_args = []
                for j in range(command['args_count']):
                    command_arg = self.command_arg_table[command['args_offset'] + COMMAND_ARG.size * j]
                    command_args.append(self.get_packed_expression(command_arg['packed_expression_offset'],
                                                                   command_arg['packed_expression_size']))
                commands.append(Command(command['unknown'], command['index'], command_args, indent=print_indent))
        return commands

    @staticmethod
    def pack_commands(tables, commands):
        if not commands:
            return -1, 0  # offset = -1, count = 0
        offset = len(tables['command_table']) * COMMAND.size
        count = len(commands)
        for command in commands:
            if command.args:
                command_args_offset = len(tables['command_arg_table']) * COMMAND_ARG.size
            else:
                command_args_offset = -1
            for arg in command.args:
                tables['command_arg_table'].append([len(tables['packed_arg_expressions']), len(arg)])
                tables['packed_arg_expressions'] += arg
            tables['command_table'].append(
                [command.unknown, command.index, command_args_offset, len(command.args)]
            )
        return offset, count

    def pack_conditions(self, tables, conditions):

        if not conditions:
            # Should only occur for subconditions.
            return -1, 0  # offset = -1, count = 0

        offset = len(tables['condition_pointer_table']) * CONDITION_POINTER.size
        count = len(conditions)

        for condition in conditions:
            try:
                tables['condition_pointer_table'].append(tables['existing_conditions'][condition].copy())
            except KeyError:

                condition_offset = len(tables['condition_table']) * CONDITION.size

                # TODO: for double tables, conditions will need to remember which table they are part of
                condition_commands_offset, condition_commands_count = self.pack_commands(tables, condition.commands)
                subconditions_offset, subconditions_count = self.pack_conditions(tables, condition.subconditions)

                tables['condition_table'].append(
                    [condition.next_state_index,  # will be replaced by state offset in final sweep
                     condition_commands_offset, condition_commands_count,
                     subconditions_offset, subconditions_count,
                     len(tables['packed_condition_expressions']), len(condition.expression)]
                )
                tables['packed_condition_expressions'] += condition.expression
                tables['existing_conditions'][condition] = [condition_offset]
                tables['condition_pointer_table'].append([condition_offset])

        return offset, count

    def pack_esd(self, print_repacked_tables=False):

        tables = {
            'header': [],
            'state_header': [],
            'state_table': [],
            'condition_table': [],
            'command_table': [],
            'command_arg_table': [],
            'condition_pointer_table': [],
            'packed_condition_expressions': b'',
            'packed_arg_expressions': b'',
            'esd_name': b'',
            'file_tail': self.file_tail,
            'existing_conditions': {}  # {condition: condition_table_offset}
        }

        for state in self.states:

            enter_commands_offset, enter_commands_count = self.pack_commands(tables, state.enter_commands)
            exit_commands_offset, exit_commands_count = self.pack_commands(tables, state.exit_commands)
            unknown_commands_offset, unknown_commands_count = self.pack_commands(tables, state.unknown_commands)
            condition_pointers_offset, condition_pointers_count = self.pack_conditions(tables, state.conditions)
            tables['state_table'].append(
                [state.index,
                 condition_pointers_offset, condition_pointers_count,
                 enter_commands_offset, enter_commands_count,
                 exit_commands_offset, exit_commands_count,
                 unknown_commands_offset, unknown_commands_count]
            )

        if self.esd_name is not None:
            tables['esd_name'] = self.esd_name.encode('utf-16le')

        # Update final offsets (header is discounted). TODO: double state table.
        state_table_offset = SINGLE_STATE_HEADER.size
        condition_table_offset = state_table_offset + len(tables['state_table']) * STATE.size
        command_table_offset = condition_table_offset + len(tables['condition_table']) * CONDITION.size
        command_arg_table_offset = command_table_offset + len(tables['command_table']) * COMMAND.size
        condition_pointer_table_offset = command_arg_table_offset + len(tables['command_arg_table']) * COMMAND_ARG.size
        packed_condition_expressions_offset = (condition_pointer_table_offset
                                               + len(tables['condition_pointer_table']) * CONDITION_POINTER.size)
        packed_arg_expressions_offset = (packed_condition_expressions_offset +
                                         len(tables['packed_condition_expressions']))
        esd_name_offset = packed_arg_expressions_offset + len(tables['packed_arg_expressions'])
        file_tail_offset = esd_name_offset + len(tables['esd_name'])
        eof_offset = file_tail_offset + len(self.file_tail)

        if print_repacked_tables:
            print('State offset:', state_table_offset)
            print('Condition offset:', condition_table_offset)
            print('Command offset:', command_table_offset)
            print('Command arg offset:', command_arg_table_offset)
            print('Condition pointer offset:', condition_pointer_table_offset)
            print('Packed expressions offset:', packed_condition_expressions_offset)

        for state in tables['state_table']:
            if state[1] != -1:
                state[1] += condition_pointer_table_offset
            if state[3] != -1:
                state[3] += command_table_offset
            if state[5] != -1:
                state[5] += command_table_offset
            if state[7] != -1:
                state[7] += command_table_offset

        for condition in tables['condition_table']:
            if condition[0] != -1:
                # Find offset of state with this index. TODO: should be the correct state table if double tables.
                for i, state in enumerate(tables['state_table']):
                    if condition[0] == state[0]:
                        condition[0] = state_table_offset + i * STATE.size
                        break
                if condition[1] != -1:
                    condition[1] += command_table_offset
                if condition[3] != -1:
                    condition[3] += condition_table_offset
                if condition[5] != -1:  # should never be -1
                    condition[5] += packed_condition_expressions_offset

        for command in tables['command_table']:
            if command[2] != -1:
                command[2] += command_arg_table_offset

        for command_arg in tables['command_arg_table']:
            if command_arg[0] != -1:  # should never be -1
                command_arg[0] += packed_arg_expressions_offset

        for condition_pointer in tables['condition_pointer_table']:
            if condition_pointer[0] != -1:  # should never be -1
                condition_pointer[0] += condition_table_offset

        if print_repacked_tables:
            [print(state) for state in tables['state_table']]
            [print(condition) for condition in tables['condition_table']]
            [print(command) for command in tables['command_table']]
            [print(command_arg) for command_arg in tables['command_arg_table']]
            [print(condition_pointer) for condition_pointer in tables['condition_pointer_table']]

        # Create headers.
        esd_name_0_offset = eof_offset if self.esd_name is None else esd_name_offset
        esd_name_0_size = 0 if self.esd_name is None else len(self.esd_name)
        tables['header'] = dict(
            version=self.header['version'],
            version_tail=self.header['version_tail'],
            table_size_offset=self.header['table_size_offset'],
            file_size_offset=eof_offset,  # excludes header size
            unknowns=self.header['unknowns'],
            state_table_count=self.state_table_count,
            state_row_size=STATE.size,
            state_row_count=len(tables['state_table']),
            condition_row_size=CONDITION.size,
            condition_row_count=len(tables['condition_table']),
            command_row_size=COMMAND.size,
            command_row_count=len(tables['command_table']),
            command_arg_row_size=COMMAND_ARG.size,
            command_arg_row_count=len(tables['command_arg_table']),
            condition_pointers_offset=condition_pointer_table_offset,
            condition_pointers_count=len(tables['condition_pointer_table']),
            esd_name_0_offset=esd_name_0_offset,
            esd_name_0_size=esd_name_0_size,
            esd_name_1_offset=file_tail_offset,
            esd_name_1_size=0,
            esd_name_2_offset=file_tail_offset,
            esd_name_2_size=0,
        )

        tables['state_header'] = dict(
            unknowns_1=self.state_header['unknowns_1'],
            esd_names_offset=self.state_header['esd_names_offset'],  # 44
            esd_names_count=self.state_header['esd_names_count'],  # 1
            esd_name_0_offset=esd_name_0_offset,
            esd_name_0_size=esd_name_0_size,
            zeroes=self.state_header['zeroes'],  # (0, 0)
            first_state_table_index=self.state_header['first_state_table_index'],  # 0
            first_state_table_offset=state_table_offset,
            first_state_table_size=len(self.states) - 1,  # number of states (no 0 repeat)
            first_state_table_offset_2=state_table_offset,  # duplicate
        )

        return tables

    def write(self, file_name, tables=None, print_repacked_tables=False):

        if tables is None:
            tables = self.pack_esd(print_repacked_tables=print_repacked_tables)

        with open(file_name, 'wb') as file:
            file.write(HEADER.pack(tables['header']))
            if tables['header']['state_table_count'] == 1:
                file.write(SINGLE_STATE_HEADER.pack(tables['state_header']))
            elif tables['header']['state_table_count'] == 2:
                file.write(DOUBLE_STATE_HEADER.pack(tables['state_header']))
            file.write(STATE.pack(tables['state_table']))
            file.write(CONDITION.pack(tables['condition_table']))
            file.write(COMMAND.pack(tables['command_table']))
            file.write(COMMAND_ARG.pack(tables['command_arg_table']))
            file.write(CONDITION_POINTER.pack(tables['condition_pointer_table']))
            file.write(tables['packed_condition_expressions'])
            file.write(tables['packed_arg_expressions'])
            file.write(tables['esd_name'])
            file.write(tables['file_tail'])

    def print_tables(self):
        print('\nState table:')
        [print(state) for state in self.state_table.items()]
        print('\nCondition table:')
        [print(condition) for condition in self.condition_table.items()]
        print('\nCommand table:')
        [print(command) for command in self.command_table.items()]
        print('\nCommand arg table:')
        [print(command_arg) for command_arg in self.command_arg_table.items()]
        print('\nCondition pointer table:')
        [print(condition_pointer) for condition_pointer in self.condition_pointer_table.items()]
        print('Packed expressions offset:', self.packed_offset)

    def print_expressions(self):
        for key in sorted(self.parsed_expressions.keys()):
            print('{}: {}'.format(key, self.parsed_expressions[key]))

    def __str__(self):

        s = ("<html><head></head><body>"
             "<meta charset=\"shift-jis\"><br>"
             "NOTES:<br>"
             "  - Including all logic grouping brackets is ugly, so I have disabled them by default. It is<br> "
             "    generally safe to assume that logical operations evaluate from left to right when they are all<br>"
             "    one type, and that later OR operations are evaluated before earlier AND operations. Set<br>"
             "    `full_brackets=True` for explicit order.<br>"
             "  - &: values that have been previously computed in the current condition evaluation for this state<br>"
             "    and loaded from registers.<br>"
             "  - ^: interpreter should continue even if the previous value is false.<br>"
             "  - !: interpreter should stop if the previous value is false. (Yes, this is not logically consistent<br>"
             "    with the above, but I'm not certain exactly what makes the interpreter halt during a line. It may<br>"
             "    halt whenever a zero value is not saved to a register, hence why this 'null register' is used.)<br>")

        for state in self.states:
            s += str(state)

        s += '</body></html>'

        return s

    def unpack_to_html_file(self, output_path=None):
        if output_path is None:
            output_path = self.input_path + '.html'
        with open(output_path, 'w', encoding='shift-jis') as output_file:
            with redirect_stdout(output_file):
                print(self)


def state_title_bar(index):
    return ('<br><div style="font-size:35px;font-weight:bold;margin-top:10px"><a name="ezstate_{index}">EzState {index}'
            '</a></div>'.format(index=index))


if __name__ == '__main__':

    # Example:
    esd_file_path = 'talk/t100000.esd'   # .esd file path
    ezstate = EzState(esd_file_path)

    # Print to a HTML file with easy hyperlinks (defaults to '[esd_file_path].html'):
    ezstate.unpack_to_html_file()

    # Make a change:
    new_state_description = b'\xa5' + 'Hello there'.encode('utf-16le') + b'\x00\x00'
    ezstate.states[1].enter_commands[0].args[0] = new_state_description

    Repack:
    ezstate.write(esd_file_path[:-4] + '.repack.esd')
