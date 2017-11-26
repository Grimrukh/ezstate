# -*- coding: utf-8 -*-
"""
@author: grimrhapsody
"""

from struct import unpack


REGISTERS = [''] * 8


def reset_registers():
    global REGISTERS
    REGISTERS = [''] * 8


marker_lookup = {
    '91': '<=',
    '92': '>=',
    '93': '<',
    '94': '>',
    '95': '==',
}

function_lookup = {
    # Not all of these are confirmed. Feel free to study the code and present evidence.
    # Note that these indices are completely different to the on/off command IDs.
    1:  'GetPlayerDistance',
    2:  'IsDialogueFinished',
    4:  'GetActionButton',
    5:  'DamagedByPlayer',
    6:  'HealthPercentage',  # from 0 to 100.
    8:  'PlayerFacingAngle',  # angle away from the NPC that player is facing. Max is 180.
    9:  'IsFriendly',
    14: 'GetPromptState',
    15: 'GetEventFlagState',  # takes an event flag as an argument.
}


def parse(input_line, full_brackets=False):
    # input_line is a list of hex byte strings.

    global REGISTERS

    output_line = []
    offset = 0
    condition_start = 0

    while offset < len(input_line):

        byte = input_line[offset]
        offset += 1

        if '3f' <= byte <= '7f':
            # Interpret byte as an integer offset by +64.
            output_line.append(str(int(byte, 16) - 64))

        else:

            if byte == 'a5':
                # This byte appears at the start of arguments to command (0), often at the start of the ON command of
                # the main waiting state. I haven't figured out what data type it represents yet, so I'm ignoring the
                # rest of the line for now.
                return ' '.join(input_line)

            elif byte == '80':
                # Next four bytes form a float.
                float_value = unpack('<f', bytearray.fromhex(''.join(input_line[offset:offset + 4])))[0]
                offset += 4
                output_line.append(str(float_value))

            # Byte '81' represents another data type I haven't identified, but doesn't appear often in the talk files.

            elif byte == '82':
                # Next four bytes form an integer.
                integer = unpack('<i', bytearray.fromhex(''.join(input_line[offset:offset + 4])))[0]
                offset += 4
                output_line.append(str(integer))

            # I haven't seen byte '83' yet but it's safe to say it will indicate a data type - maybe a string.

            elif byte == '84':
                # Previous integer is a function index with no arguments.
                function_index = int(output_line[-1])
                function_name = function_lookup.get(function_index, 'F-{}'.format(function_index))
                output_line[-1] = function_name + '()'

            elif byte == '85':
                # Previous two values represent a function index and one argument (in that order).
                function_index = int(output_line[-2])
                function_name = function_lookup.get(function_index, 'F-{}'.format(function_index))
                output_line[-2] = function_name + '({})'.format(output_line[-1])
                output_line.pop()   # function and argument have been combined

            elif byte == '86':
                # Previous three values represent a function index and two arguments (in that order).
                function_index = int(output_line[-3])
                function_name = function_lookup.get(function_index, 'F-{}'.format(function_index))
                output_line[-3] = function_name + '({}, {})'.format(output_line[-2], output_line[-1])
                output_line.pop()   # function and arguments have been combined
                output_line.pop()

            # I assume bytes 87-90 mark functions that take more arguments but haven't encountered them yet to confirm.

            elif '91' <= byte <= '95':
                # Applies comparison operator to the last two values (left and right, respectively).
                comparison_operator = marker_lookup[byte]
                output_line[-2] = '({} {} {})'.format(output_line[-2], comparison_operator, output_line[-1])
                output_line.pop()

            elif byte == '98':
                # Applies AND operation to the last two values.
                if full_brackets:
                    output_line[-2] = '({}) and ({})'.format(output_line[-2], output_line[-1])
                else:
                    output_line[-2] = '{} and {}'.format(output_line[-2], output_line[-1])
                output_line.pop()

            elif byte == '99':
                # Applies OR operation to the last two values.
                if full_brackets:
                    output_line[-2] = '({}) or ({})'.format(output_line[-2], output_line[-1])
                else:
                    output_line[-2] = '{} or {}'.format(output_line[-2], output_line[-1])
                output_line.pop()

            elif byte == 'a1':
                # End of line. Not printed. Note that it is NOT responsible for registering the state change conditions,
                # as it appears in command argument data as well. It's strictly an end line marker. Also note that it
                # can appear elsewhere in the code, such as in the value of an integer or float, and it is therefore NOT
                # safe to blindly parse the packed data based solely on this byte.
                pass

            elif byte == 'a6':
                # My leading hypothesis for this byte is that it forces the command to continue even when the previous
                # value is false (0), which would normally stop the condition line from continuing. I have left this
                # byte out of the normal display mode, but you can enable it (and b7) with show_continuation=True.
                output_line[-1] += '^'
                pass

            elif 'a7' <= byte <= 'ae':
                # Save previous value to register.
                REGISTERS[int(byte, 16) - 167] = output_line[-1]

            elif 'af' <= byte <= 'b6':
                # Load value from register. The ampersand indicates that this value has been computed earlier in the
                # state conditions, which ensures that values do not change during a single evaluation of the conditions
                # for each potential state change.
                output_line.append('&'+REGISTERS[int(byte, 16) - 175])

            elif byte == 'b7':
                # My leading hypothesis for this byte is that it stops the current line from continuing evaluation if
                # the previous value is false (0). It usually occurs later in the state because early conditions often
                # *must* finish evaluating to save computed values for later loading. It also occurs in situations like
                # "1 and (2 or 3 or 4)", when the AND command does not occur until the end of the command.
                #
                # Obviously, this hypothesis isn't fully consistent with my hypothesis about 'a6', which assumed that
                # values of 0 can halt a command. It's possible that the developers occasionally used these continuation
                # instructions superfluously. Or I could be wrong about one or both of them.
                output_line[-1] += '!'

            else:
                marker = marker_lookup.get(byte, None)
                if marker is None:
                    output_line.append('[{}]'.format(byte))
                else:
                    output_line.append(marker)

    return ' '.join(output_line)
