# -*- coding: utf-8 -*-
"""
@author: grimrhapsody

Current only works for .esd files in \talk\ (NPCs and bonfires). Does not work for \menu\ or \chr\ .esd files.
"""

from contextlib import redirect_stdout
from struct import unpack

import ezstate_parser


command_names = {

    # Names of functions called from the command table.

    -1: '(NULL)',             # no command
    1: 'Play Dialogue',       # (text_id)    matches sound file ID, I believe
    6: 'Action Prompt',       # (text_id)    -1 == no prompt
    11: 'Set Event Flag',     # (event_flag_id, state)

    # Unknown indices are left as "Unknown (index)". Note that the largest command index I've seen is 67.
}


def unpack_tables(filename):

    file_header_length = 27 * 4   # 108 bytes at the start of the .esd file

    # 1. Directly unpack all six sections of data, replacing byte offsets with table row indices (except for the
    #    packed data table).

    with open(filename, 'rb') as file:
        
        # The header contains structural information about the file.
        data = file.read(file_header_length)
        file_header_format = '<' + 'i' * (file_header_length // 4)
        file_header = list(unpack(file_header_format, data))

        # Offset 0 starts here.
        if filename in ['enemyCommon', 'dummy']:
            state_table_header_length = 19 * 4   # information about double state table, 76 bytes
        else:
            state_table_header_length = 15 * 4   # information about single state table, 60 bytes

        state_table_offset = 0 + state_table_header_length
        state_table_rows = file_header[12]   # number of states
        state_table_width = file_header[11]   # bytes per row
        state_table_format = '<iiiiiiiii'
        
        next_state_table_offset = state_table_offset + (state_table_rows * state_table_width)
        next_state_table_rows = file_header[14]
        next_state_table_width = file_header[13]
        next_state_table_format = '<iiiiiii'
        
        command_table_offset = next_state_table_offset + (next_state_table_rows * next_state_table_width)
        command_table_rows = file_header[16]
        command_table_width = file_header[15]
        command_table_format = '<iiii'
        
        command_arg_table_offset = command_table_offset + (command_table_rows * command_table_width)
        command_arg_table_rows = file_header[18]
        command_arg_table_width = file_header[17]
        command_arg_table_format = '<ii'

        # This offset is also given in the header (offset 19).
        next_state_pointer_table_offset = command_arg_table_offset + (command_arg_table_rows * command_arg_table_width)
        next_state_pointer_table_rows = file_header[20]
        next_state_pointer_table_width = 4
        next_state_pointer_table_format = '<i'
        
        # The remainder of the file is packed data, which is used as command arguments and conditions. It is accessed
        # using a byte offset and byte length. Each command line ends with byte `\xa1`, but this byte can also appear
        # earlier in the line (e.g. as part of a four-byte integer or float), so it's not safe to unpack the data here
        # using this end-line marker.
        packed_data_offset = next_state_pointer_table_offset + (next_state_pointer_table_rows * next_state_pointer_table_width)

        # State table has a header describing its length. More complex .esd files, like enemyCommon.esd, have TWO
        # state tables, and the length of each is described here. Note that for this reason, enemyCommon and c0000 have
        # a 19-byte state table header instead of a 15-byte header. For now, just skipping these bytes.
        file.read(state_table_header_length)
        
        state_table = []
        for r in range(state_table_rows):
            row = list(unpack(state_table_format, file.read(state_table_width)))
            # Convert pointer to table 5.
            if row[1] != -1:
                row[1] = (row[1] - next_state_pointer_table_offset) // next_state_pointer_table_width
                # row[2] is already just the number of rows to get.
            # Convert pointers to table 3.
            for i in [3, 5]:
                if row[i] != -1:
                    row[i] = (row[i] - command_table_offset) // command_table_width
            state_table.append(row)
    
        next_state_table = []
        for r in range(next_state_table_rows):
            row = list(unpack(next_state_table_format, file.read(next_state_table_width)))
            # Convert pointer to table 1.
            if row[0] != -1:
                row[0] = (row[0] - state_table_offset) // state_table_width
            # Convert pointer to table 3.
            if row[1] != -1:
                row[1] = (row[1] - command_table_offset) // command_table_width
            # Convert pointer to table 5.
            if row[3] != -1:
                row[3] = (row[3] - next_state_pointer_table_offset) // next_state_pointer_table_width
            # Convert pointer to table 6 (still byte index).
            if row[5] != -1:
                row[5] = (row[5] - packed_data_offset)
            next_state_table.append(row)
            
        command_table = []
        for r in range(command_table_rows):
            row = list(unpack(command_table_format, file.read(command_table_width)))
            # Convert pointer to table 4.
            if row[2] != -1:
                row[2] = (row[2] - command_arg_table_offset) // command_arg_table_width
            command_table.append(row)
            
        command_arg_table = []
        for r in range(command_arg_table_rows):
            row = list(unpack(command_arg_table_format, file.read(command_arg_table_width)))
            # Convert pointer to table 6.
            if row[0] != -1:
                row[0] = (row[0] - packed_data_offset)
            command_arg_table.append(row)

        next_state_pointer_table = []
        for r in range(next_state_pointer_table_rows):
            row = list(unpack(next_state_pointer_table_format, file.read(next_state_pointer_table_width)))
            # Convert pointer to table 2.
            if row[0] != -1:
                row[0] = (row[0] - next_state_table_offset) // next_state_table_width
            next_state_pointer_table.append(row)

        packed_data = []
        data = file.read(1).hex()
        while data != '':
            packed_data.append(data)
            data = file.read(1).hex()

    return [state_table, next_state_table, command_table, command_arg_table, next_state_pointer_table, packed_data]


def resolve_tables(state_table, next_state_table, command_table,
                   command_arg_table, next_state_pointer_table, packed_data):
    """ Resolve next state pointers and packed data pointers, leaving just the state, next state, and command tables.
    """

    for row in state_table:
        # Note: does not remove the trailing (-1, 0) fields on the off chance that they are used at some rare point.

        off_commands = [row[5] + i for i in range(row[6])]
        row[5] = off_commands
        row.pop(6)

        on_commands = [row[3] + i for i in range(row[4])]
        row[3] = on_commands
        row.pop(4)

        next_states = [next_state_pointer_table[row[1] + i][0] for i in range(row[2])]
        row[1] = next_states
        row.pop(2)

    for row in next_state_table:

        row[5] = packed_data[row[5]:row[5]+row[6]]
        row.pop(6)

        next_states = [next_state_pointer_table[row[3] + i][0] for i in range(row[4])]
        row[3] = next_states
        row.pop(4)

        commands = [row[1] + i for i in range(row[2])]
        row[1] = commands
        row.pop(2)

    for row in command_table:
        args = []
        for arg_index in range(row[3]):
            arg_offset, arg_length = command_arg_table[row[2]+arg_index]
            args.append(packed_data[arg_offset:arg_offset+arg_length])
        row[2] = args
        row.pop()

    # Final formats. The starred fields in the next state table rarely appear (never in talk files) and I don't yet
    # understand their purpose. They may take effect if the condition evaluates to false (so it runs commands and/or
    # checks additional conditions for a new set of potential next states contingent on the first condition failing).

    # State table:      [ state_index,  [next_state_indices], [on_command_indices],  [off_command_indices] ]
    # Next state table: [ state_index, *[command_indices],   *[next_state_indices],  condition             ]
    # Command table:    [ 1,            command_id,           [command_args]      ]

    return [state_table, next_state_table, command_table]


def write_tables(output, tables):
    """ Write list of input tables to a text file, row by row. """
    with open(output+'.txt', 'w') as file:
        for table in tables:
            for row in table:
                file.write(str(table)+'\n')
            file.write('\n')


def write_state_title_bar(index):

    print()
    print('#######################{}'.format('#'*len(str(index))))
    print('# EzState Index:   {}   #'.format(index))
    print('#######################{}'.format('#'*len(str(index))))
    print()


def display_esd(state_table, next_state_table, command_table, rows=None, raw=False, full_brackets=False):
    
    # Display ESD files in a more readable format.
    # rows: specify which rows (states) to interpret.
    # raw: write bytes without interpretation from ezstate_parser.
    # full_brackets: include full brackets for logical AND/OR operations to see explicit order.
    
    if rows is None:
        rows = range(len(state_table))

    print("NOTES:\n"
          "  - Including all logic grouping brackets is ugly, so I have disabled them by default. It is generally\n"
          "    safe to assume that logical operations evaluate from left to right when they are all one type, and\n"
          "    that later OR operations are evaluated before earlier AND operations. Set full_brackets=True for\n"
          "    explicit order.\n"
          "  - &: values that have been previously computed in the current condition evaluation for this state and\n"
          "    loaded from registers.\n"
          "  - ^: interpreter should continue even if the previous value is false.\n"
          "  - !: interpreter should stop if the previous value is false. (Yes, this is not logically consistent\n"
          "    with the above, but I'm not certain exactly what makes the interpreter halt during a line. It may\n"
          "    halt whenever a zero value is not saved to a register, hence why this 'null register' is used.)\n")

    for row in rows:

        state_index = state_table[row][0]
        next_states = [next_state_table[i] for i in state_table[row][1]]
        on_commands = [command_table[i] for i in state_table[row][2]]
        off_commands = [command_table[i] for i in state_table[row][3]]

        write_state_title_bar(state_index)
        
        print('(ON)  Commands: ')
        for _, id, args in on_commands:
            name = command_names.get(id, 'Unknown ({})'.format(id))
            if raw:
                print('    {}: {}({})'.format(name, ' ' * (20 - len(name)),
                                              ', '.join([' '.join(arg) for arg in args])))
            else:
                print('    {}: {}({})'.format(name, ' '*(20-len(name)),
                                              ', '.join([ezstate_parser.parse(arg) for arg in args])))
        print()
        print('Next State Conditions:')
        ezstate_parser.reset_registers()
        for next_state_index, alt_commands, alt_next_states, condition in next_states:
            print('  ---> State {}:'.format(next_state_index))
            if alt_commands:
                print('     ALT Commands: ')
            for _, id, args in alt_commands:
                name = command_names.get(id, 'Unknown ({})'.format(id))
                if raw:
                    print('    {}: {}({})'.format(name, ' ' * (20 - len(name)),
                                                  ', '.join([' '.join(arg) for arg in args])))
                else:
                    print('    {}: {}({})'.format(name, ' ' * (20 - len(name)),
                                                  ', '.join([ezstate_parser.parse(arg, full_brackets) for arg in args])))
            if alt_next_states:
                print('     ALT Next States: {}'.format(alt_next_states))
            if raw:
                print('   {}'.format(' '.join(condition)))
            else:
                print('     {}'.format(ezstate_parser.parse(condition)))
        print()
        print('(OFF)  Commands: ')
        for _, id, args in off_commands:
            name = command_names.get(id, 'Unknown ({})'.format(id))
            print('    {}: {}({})'.format(name, ' ' * (20 - len(name)),
                                          ', '.join([ezstate_parser.parse(args, full_brackets) for args in args])))

if __name__ == '__main__':

    in_filename = 'talk/t100000.esd'   # .esd file path
    out_filename = 't100000_interpreted.txt'   # output file path
    tables = unpack_tables(in_filename)   # raw unpacked tables (with offsets converted to row indices)
    tables = resolve_tables(*tables)   # interpreted tables reduced to state table, next state table, and command table

    with open(out_filename, 'w') as file:
        with redirect_stdout(file):
            display_esd(*tables, raw=False, full_brackets=False)
