# ezstate
Unpacks and decodes .esd files from Dark Souls. As a bonus, now includes a semi-descriptive .drb
unpacker, which has only been tested for menu.drb.

Open `unpack_esd.py`, specify your file path at the bottom, and run. Set raw=True to see the
unpacked data without my interpreter. Set full_brackets=True for explicit logical operation order. 
Read the notes at the top of each interpreted output file.

This is currently a READER ONLY.

These files are quite complex. The comments in the code are hopefully enough for you for now.
I am very tired of these files and can't promise when I will press on with figuring out the
many remaining function indices (there are two sets of these: commands, and conditions).

Feel free to provide any hypotheses and evidence about the identities of function indices.
