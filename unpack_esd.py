# -*- coding: utf-8 -*-
"""
@author: grimrhapsody
"""

from contextlib import redirect_stdout
import struct

import ezstate_parser


MASTER_OFFSET = 0  # NOTE: Starts *after* header.


command_names = {

    # Names of functions called from the command table.

    -1: ['(NULL)'],             # no command
    0: ['State Description'],
    1: ['Play Dialogue', 'dialogue_id', 'arg2', 'arg3'],  # dialogue_id looks up both the sound file and subtitle text
    6: ['Action Prompt', 'text_id'],       # text_id = -1 removes the prompt
    11: ['Set Event Flag', 'event_flag_id', 'state'],  # 0 = disable, 1 = enable
    17: ['Display Dialogue', 'arg1', 'text_id', 'button_type', 'number_buttons', 'display_distance'],
    19: ['Display Menu Item', 'menu_index', 'item_name', 'required_flag'],
    22: ['Add Shop Lineup', 'param_start', 'param_end'],
    49: ['Add Ascension Menu', 'required_flag', '?menu?'],

    # Unknown indices are left as "Unknown (index)". Note that the largest command index I've seen is 67.
}


def read_integers(file, n, update_master=False):
    """ Read n integers from an open bytes file. """
    global MASTER_OFFSET
    fmt = '<{n}i'.format(n=n)
    if update_master:
        MASTER_OFFSET += struct.calcsize(fmt)
    return struct.unpack(fmt, file.read(struct.calcsize(fmt)))


class EzState(object):
    """ Contains all states, conditions for switching states, and commands. """

    COMMAND_SIZE = 16

    def data(self, offset, size):
        return self.__esd['data'][offset - self.__esd['data_offset']:offset - self.__esd['data_offset'] + size]

    def __init__(self, ezstate_dict):
        
        self.__esd = ezstate_dict
        self.states = self.parse_states()

        self.PDO = ezstate_dict['data_offset']

    def parse_states(self):

        states = []
        for state in self.__esd['state_table'].values():
            index = state[0]
            conditions = self.parse_conditions(state[1], state[2])
            onset_commands = self.parse_commands(state[3], state[4])
            offset_commands = self.parse_commands(state[5], state[6])
            unknown_commands = self.parse_commands(state[7], state[8])
            states.append(State(index, conditions, onset_commands, offset_commands, unknown_commands))
        return states

    def parse_commands(self, first_command_offset, number_commands, indent=0):
        if first_command_offset == -1:
            return []
        commands = []
        for i in range(number_commands):
            command = self.__esd['command_table'][first_command_offset + self.COMMAND_SIZE * i]
            unknown, command_index, first_arg_offset, number_args = command
            if first_arg_offset == -1:
                # Command has no arguments.
                commands.append(Command(unknown, command_index, indent=indent))
            else:
                command_args = []
                for j in range(number_args):
                    arg_offset, arg_size = self.__esd['command_arg_table'][command[2] + 8 * j]
                    command_args.append(self.data(arg_offset, arg_size))
                commands.append(Command(unknown, command_index, command_args, indent=indent))
        return commands

    def parse_conditions(self, first_condition_pointer_offset, number_conditions, indent=0):
        if first_condition_pointer_offset == -1:
            return []
        conditions = []
        for i in range(number_conditions):
            condition_pointer, = self.__esd['condition_pointer_table'][first_condition_pointer_offset + 4 * i]
            condition = self.__esd['condition_table'][condition_pointer]
            if condition[0] == -1:
                next_state_index = None
            else:
                next_state_index = self.__esd['state_table'][condition[0]][0]
            if condition[1] == -1:
                # No command.
                commands = None
            else:
                commands = self.parse_commands(condition[1], condition[2], indent=indent + 4)
            if condition[3] == -1:
                alternate_conditions = None
            else:
                alternate_conditions = self.parse_conditions(condition[3], condition[4], indent=indent + 4)
            condition_code = self.data(condition[5], condition[6])
            conditions.append(Condition(next_state_index, condition_code, commands, alternate_conditions,
                                        indent=indent))
        return conditions

    def __str__(self):

        s = ("\nNOTES:\n"
             "  - Including all logic grouping brackets is ugly, so I have disabled them by default. It is generally\n"
             "    safe to assume that logical operations evaluate from left to right when they are all one type, and\n"
             "    that later OR operations are evaluated before earlier AND operations. Set full_brackets=True for\n"
             "    explicit order.\n"
             "  - &: values that have been previously computed in the current condition evaluation for this state "
             "and\n"
             "    loaded from registers.\n"
             "  - ^: interpreter should continue even if the previous value is false.\n"
             "  - !: interpreter should stop if the previous value is false. (Yes, this is not logically consistent\n"
             "    with the above, but I'm not certain exactly what makes the interpreter halt during a line. It may\n"
             "    halt whenever a zero value is not saved to a register, hence why this 'null register' is used.)\n")

        for state in self.states:
            s += str(state)

        return s


class Command(object):

    def __init__(self, unknown, index, command_args=(), indent=0):
        self.unknown = unknown
        self.index = index
        self.args = command_args
        self.indent = indent

    def __str__(self, raw=False):
        names = command_names.get(self.index, None)
        string = ''
        if raw and names is not None:
            string += '\n{}    {}: {}({})'.format(' ' * self.indent, names[0], ' ' * (20 - len(names[0])),
                                                  ', '.join([' '.join(arg) for arg in self.args]))
        elif names is None or (len(names) != len(self.args) + 1 and len(names) != 1):
            name = '{}Unknown ({})'.format(' ' * self.indent, self.index)
            print(self.args)
            string += '\n{}    {}: {}({})'.format(' ' * self.indent, name, ' ' * (20 - len(name)),
                                                  ', '.join([ezstate_parser.parse(arg) for arg in self.args]))
        elif len(names) == 1:
            string += '\n{}    {}: {}({})'.format(' ' * self.indent, names[0], ' ' * (20 - len(names[0])),
                                                  ', '.join([ezstate_parser.parse(arg) for arg in self.args]))
        else:
            string += '\n{}    {}: {}({})'.format(' ' * self.indent, names[0], ' ' * (20 - len(names[0])),
                                                  ', '.join([names[i + 1] + '=' + ezstate_parser.parse(arg)
                                                             for i, arg in enumerate(self.args)]))
        return string

    
class Condition(object):
    
    def __init__(self, next_state_index, condition_code, commands=None, alternate_conditions=None, indent=0):
        self.next_state = next_state_index
        self.code = condition_code
        self.commands = commands
        self.alternate_conditions = alternate_conditions
        self.indent = indent

    def __str__(self, raw=False, full_brackets=False):

        string = ''

        next_state_string = '(IF)' if self.next_state is None else self.next_state

        string += '\n{}  ---> State {}:'.format(' ' * self.indent, next_state_string)
        if raw:
            string += '\n{}     {}'.format(' ' * self.indent, ' '.join(self.code))
        else:
            string += '\n{}     {}'.format(' ' * self.indent, ezstate_parser.parse(self.code, full_brackets))
        if self.commands:
            string += '\n{}      Commands:'.format(' ' * self.indent)
            for command in self.commands:
                string += str(command)
        if self.alternate_conditions:
            string += '\n{}      THEN:'.format(' ' * self.indent)
            for condition in self.alternate_conditions:
                string += str(condition)
        return string
    
    
class State(object):
    
    def __init__(self, index, conditions, onset_commands, offset_commands, unknown_commands):
        self.index = index
        self.conditions = conditions
        self.onset_commands = onset_commands
        self.offset_commands = offset_commands
        self.unknown_commands = unknown_commands

    def __str__(self):

        s = state_title_bar(self.index)

        s += '\n\n(ON)  Commands: '
        for command in self.onset_commands:
            s += str(command)

        s += '\n\nNext State Conditions:'
        ezstate_parser.reset_registers()
        for condition in self.conditions:
            s += str(condition)

        s += '\n\n(OFF)  Commands: '
        for command in self.offset_commands:
            s += str(command)

        return s


def unpack_states(filename, long_state_header=False, print_tables=False):

    global MASTER_OFFSET
    MASTER_OFFSET = 0

    ezstate_dict = {}

    with open(filename, 'rb') as file:

        # HEADER

        header = ezstate_dict['header'] = read_integers(file, 27)
        if print_tables:
            print(header)

        ###############
        # STATE TABLE #
        ###############

        # (state_index, next_state_pointer_offset, next_state_count, on_command_offset, ?, off_command_offset, ?,
        # -1, 0)

        if long_state_header:
            state_table_header_size = 19 * 4
        else:
            state_table_header_size = 15 * 4
        state_table_header = ezstate_dict['state_table_header'] = read_integers(file, state_table_header_size // 4)
        MASTER_OFFSET += state_table_header_size
        if print_tables:
            print(state_table_header)

        state_table_row_size = header[11]  # bytes per row
        state_table_row_count = header[12]  # number of rows
        if print_tables:
            print('Number of state table rows:', state_table_row_count)

        state_table = {}
        for _ in range(state_table_row_count):
            state_table[MASTER_OFFSET] = read_integers(file, state_table_row_size // 4)
            MASTER_OFFSET += state_table_row_size
        ezstate_dict['state_table'] = state_table

        if print_tables:
            print('\nState Table:')
            [print(offset, ':', row) for offset, row in state_table.items()]

        ####################
        # NEXT STATE TABLE #
        ####################

        # (state_offset, command_id / -1, 0 / 1, first_command_arg_offset, arg_count, packed_data_offset,
        #  packed_data_length

        condition_table_row_size = header[13]
        condition_table_row_count = header[14]

        condition_table = {}
        for _ in range(condition_table_row_count):
            condition_table[MASTER_OFFSET] = read_integers(file, condition_table_row_size // 4)
            MASTER_OFFSET += condition_table_row_size
        ezstate_dict['condition_table'] = condition_table

        if print_tables:
            print('\nNext State Table:')
            [print(offset, ':', row) for offset, row in condition_table.items()]

        #################
        # COMMAND TABLE #
        #################

        # (1, command_id, first_command_arg_offset, arg_count)

        command_table_row_size = header[15]  # should always be 16
        command_table_row_count = header[16]

        command_table = {}
        for i in range(command_table_row_count):
            command_table[MASTER_OFFSET] = read_integers(file, command_table_row_size // 4)
            MASTER_OFFSET += command_table_row_size
        ezstate_dict['command_table'] = command_table

        if print_tables:
            print('\nCommand Table:')
            [print(offset, ':', row) for offset, row in command_table.items()]

        #####################
        # COMMAND ARG TABLE #
        #####################

        # (packed_data_offset, packed_data_length)

        command_arg_table_row_size = header[17]
        command_arg_table_row_count = header[18]

        command_arg_table = {}
        for _ in range(command_arg_table_row_count):
            command_arg_table[MASTER_OFFSET] = read_integers(file, command_arg_table_row_size // 4)
            MASTER_OFFSET += command_arg_table_row_size
        ezstate_dict['command_arg_table'] = command_arg_table

        if print_tables:
            print('\nCommand Arg Table:')
            [print(offset, ':', row) for offset, row in command_arg_table.items()]

        ############################
        # NEXT STATE POINTER TABLE #
        ############################

        # (next_state_offset)

        condition_pointer_table_offset = MASTER_OFFSET  # also header[19]
        if condition_pointer_table_offset != MASTER_OFFSET:
            raise ValueError("Next State Pointer Table offset ({}) should be equal to header[19] ({})."
                             .format(condition_pointer_table_offset, MASTER_OFFSET))
        condition_pointer_table_row_count = header[20]
        condition_pointer_table_row_size = 4

        condition_pointer_table = {}
        for _ in range(condition_pointer_table_row_count):
            condition_pointer_table[MASTER_OFFSET] = read_integers(file, condition_pointer_table_row_size // 4)
            MASTER_OFFSET += condition_pointer_table_row_size
        ezstate_dict['condition_pointer_table'] = condition_pointer_table

        if print_tables:
            print('\nNext State Pointer Table:')
            [print(offset, ':', row) for offset, row in condition_pointer_table.items()]

        ###############
        # PACKED DATA #
        ###############

        # (variable byte code chunks, always ends in `a1`, chunk lengths are given with offsets)

        ezstate_dict['data_offset'] = MASTER_OFFSET
        ezstate_dict['data'] = file.read()  # rest of file

        # ASSEMBLING THE TABLES

        return EzState(ezstate_dict)


def write_tables(output, tables):
    """ Write list of input tables to a text file, row by row. """
    with open(output+'.txt', 'w') as file:
        for table in tables:
            for _ in table:
                file.write(str(table)+'\n')
            file.write('\n')


def state_title_bar(index):

    return '\n'.join(('\n',
                      '#######################{}'.format('#'*len(str(index))),
                      '# EzState Index:   {}   #'.format(index),
                      '#######################{}'.format('#'*len(str(index))),
                      '',
                      ))


if __name__ == '__main__':

    # NOTE: You must set `long_state_header=True` for enemyCommon.esd, and `False` otherwise.

    in_filename = 'enemyCommon.esd'   # .esd file path
    ezstate = unpack_states(in_filename, long_state_header=False, print_tables=False)
    print(ezstate)

    # Print to a file:

    out_filename = 'enemyCommon.esd.txt'   # output file path
    with open(out_filename, 'w', encoding='utf-16le') as file:
        with redirect_stdout(file):
            print(ezstate)