
from collections import OrderedDict
import struct

FILE = None
MASTER_OFFSET = 0


def read_integers(n, update_master=True):
    """ Read n integers from an open bytes file. """
    global FILE, MASTER_OFFSET
    fmt = '<{n}i'.format(n=n)
    if update_master:
        MASTER_OFFSET += struct.calcsize(fmt)
    return struct.unpack(fmt, FILE.read(struct.calcsize(fmt)))


def read_utf16_string():
    global FILE, MASTER_OFFSET
    string = ''
    hex_chr = FILE.read(2)
    MASTER_OFFSET += 2
    while hex_chr != b'\x00\x00':
        string += hex_chr.decode('utf-16le')
        hex_chr = FILE.read(2)
        MASTER_OFFSET += 2
    return string


def read_format(fmt, update_master=True):
    global FILE, MASTER_OFFSET
    if fmt == 's':
        return read_utf16_string()
    if update_master:
        MASTER_OFFSET += struct.calcsize(fmt)
    return struct.unpack(fmt, FILE.read(struct.calcsize(fmt)))


def forward_to(target_offset):
    global MASTER_OFFSET
    if MASTER_OFFSET == target_offset:
        return
    if MASTER_OFFSET > target_offset:
        raise ValueError("Master offset {} is already ahead of target offset {}.".format(MASTER_OFFSET, target_offset))
    read_format('{}c'.format(target_offset - MASTER_OFFSET))


def read_bytes(number_bytes):
    global MASTER_OFFSET
    MASTER_OFFSET += number_bytes
    return FILE.read(number_bytes)


TABLE_FORMATS = {
    'STR': {'fmt': 's'},
    'TEXI': {'fmt': '<4i',
             'args': ('STR', 'STR', 'i', 'i'),
             'names': ('texture_name', 'texture_path')},
    'SHPR': {'fmt': None},
    'CTPR': {'fmt': None},
    'ANIP': {'fmt': None},
    'INTP': {'fmt': None},
    'SCDP': {'fmt': None},
    'SHAP': {'fmt': '<2i',
             'args': ('i', 'SHPR'),
             'names': ('shap_type', 'shpr_offset'),
             'funcs': {
                 28: {'fmt': '<4h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 74: {'fmt': '<12h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 348: {'fmt': '<19h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 492: {'fmt': '<14h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 196: {'fmt': '<27h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 1164: {'fmt': '<10h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 16226: {'fmt': '<14h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 56336: {'fmt': '<10h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 56842: {'fmt': '<18h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                 57304: {'fmt': '<11h', 'names': ('x_start', 'y_start', 'x_end', 'y_end')},
                }
             },
    'CTRL': {'fmt': '<2i',
             'args': ('STR', 'CTPR')},
    'ANIK': {'fmt': '<8i',
             'args': ('STR', 'i', 'i', 'i', 'i', 'i', 'i', 'i')},
    'ANIO': {'fmt': '<4i',
             'args': ('i', 'i', 'ANIK', 'i')},
    'ANIM': {'fmt': '<12i',
             'args': ('STR', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i')},
    'SCDK': {'fmt': '<8i',
             'args': ('STR', 'i', 'i', 'i', 'SCDP', 'i', 'i', 'i')},
    'SCDO': {'fmt': '<4i',
             'args': ('STR', 'i', 'SCDK', 'i')},
    'SCDL': {'fmt': '<4i',
             'args': ('STR', 'i', 'SCDO', 'i')},
    'DLGO': {'fmt': '<8i',
             'args': ('STR', 'SHAP', 'CTRL', 'i', 'i', 'i', 'i', 'i')},
    'DLG': {'fmt': '<10i12h',
            'args': ('STR', 'SHAP', 'CTRL', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i', 'i')},
}


def read_drb_table(drb, read=True):
    """ `drb` should be a dictionary. It will be modified in place. """
    name, size, count, _ = read_format('<4s3i')
    name = name.decode().strip('\x00')
    if name == 'END':
        return name, size, count
    drb[name] = OrderedDict()
    row_size = size // count
    start_offset = MASTER_OFFSET
    fmt = TABLE_FORMATS[name]['fmt']
    if read and count != 1:
        for i in range(count):
            o = MASTER_OFFSET - start_offset
            drb[name][o] = read_format(fmt)
    else:
        for i in range(count):
            o = MASTER_OFFSET - start_offset
            drb[name][o] = read_bytes(row_size)
    forward_to(start_offset + size)
    return name, size, count


def read_shpr(shpr_data, shap_type, offset):
    # Read packed SHPR data. Size is calculated from offset gap.
    data = shpr_data[offset:offset + struct.calcsize(TABLE_FORMATS['SHAP']['funcs'][shap_type]['fmt'])]
    if shap_type in TABLE_FORMATS['SHAP']['funcs']:
        data = struct.unpack(TABLE_FORMATS['SHAP']['funcs'][shap_type]['fmt'], data)
        if 'names' in TABLE_FORMATS['SHAP']['funcs'][shap_type]:
            names = TABLE_FORMATS['SHAP']['funcs'][shap_type]['names']
            data = tuple(['{}={}'.format(names[i], data[i]) for i in range(len(names))]) + data[len(names):]
    else:
        data = struct.unpack('<{}h'.format(len(data) // 2), data[:2 * (len(data) // 2)])
    return data


def process_drb(drb):
    """ Convert string offsets and show other table indices. """
    out_drb = {}
    for name, table in drb.items():
        if name in 'STR' or TABLE_FORMATS[name]['fmt'] is None:
            # Don't process string table or any packed data tables.
            continue
        fmt = TABLE_FORMATS[name]['args']
        out_table = {}
        offsets = list(table.keys())
        rows = list(table.values())
        names = TABLE_FORMATS[name].get('names', ())
        for r, row in enumerate(rows):
            out_row = []
            for i, arg in enumerate(fmt):
                if arg in drb.keys():
                    # Arg is an offset into another table.
                    if arg == 'SHPR':
                        data = read_shpr(drb[arg][0], shap_type=row[0], offset=row[1])
                        out_row.append(data)
                    elif arg == 'CTPR':
                        # Read a packed int.
                        data = drb['CTPR'][0][row[1]:row[1] + 4]
                        out_row.append(struct.unpack('<i', data)[0])
                    elif arg == 'SCDP':
                        data = drb[arg][0][row[1]:row[1] + 8]
                        out_row.append(struct.unpack('<2i', data)[0])
                    elif name == 'ANIO' and i == 2 and row[3] == 0:
                        out_row.append('X')
                    else:
                        try:
                            try:
                                out_row.append('{}={}'.format(names[i], out_drb[arg][row[i]]))
                            except IndexError:
                                out_row.append(out_drb[arg][row[i]])
                        except KeyError:
                            try:
                                try:
                                    out_row.append('{}={}'.format(names[i], drb[arg][row[i]]))
                                except IndexError:
                                    out_row.append(drb[arg][row[i]])
                            except KeyError:
                                print(name, arg, row, i)
                                raise
                else:
                    try:
                        out_row.append('{}={}'.format(names[i], row[i]))
                    except IndexError:
                        out_row.append(row[i])
            out_table[offsets[r]] = tuple(out_row)
        out_drb[name] = out_table
    return out_drb


def unpack_drb(filename, print_tables=True, print_processed=True):

    global FILE, MASTER_OFFSET
    MASTER_OFFSET = 0

    drb = {}

    with open(filename, 'rb') as FILE:

        read_format('<4s3i')  # Header

        table_name = ''
        while table_name != 'END':
            table_name, size, count = read_drb_table(drb, True)
            if table_name == 'END':
                print('\nFinished.')
                break
            print('\n{} loaded. (ends at {} offset with {} entries, {} size.)'.format(
                table_name, MASTER_OFFSET, count, size))
            if print_tables and TABLE_FORMATS[table_name] is not None:
                [print('{}: {}'.format(offset, row)) for offset, row in list(drb[table_name].items())[:5]]
                print('...')
                [print('{}: {}'.format(offset, row)) for offset, row in list(drb[table_name].items())[-5:]]

        processed_drb = process_drb(drb)

        with open('menu.drb.txt', 'w', encoding='utf-16le') as out_file:
            for name, table in processed_drb.items():
                out_file.write('\n\n{}:'.format(name))
                [out_file.write('\n  {}'.format(row)) for row in table.values()]

        if print_processed:
            for name, table in processed_drb.items():
                print('{}:'.format(name))
                [print('{}: {}'.format(o, r)) for o, r in table.items()]
        return drb


if __name__ == '__main__':

    in_filename = 'menu.drb'  # not tested with other .drb files
    unpack_drb(in_filename, print_tables=False, print_processed=False)
