# ezstate
Unpacks and decodes .esd files from Dark Souls.

Open `unpack_esd.py`, specify your file path at the bottom, and run. Set raw=True to see the
unpacked data without my painstakingly-developed custom interpreter. Set full_brackets=True
for explicit logical operation order. Read the notes at the top of each interpreted output 
file.

This is currently a READER ONLY, and it only works for the /talk/ .esd files. The files in
/menu/ and /chr/ use slightly different formats that I can't handle yet.

These files are quite complex. The comments in the code are hopefully enough for you for now.
I am very tired of these files and can't promise when I will press on with the remaining .esd
file structures.

Feel free to provide any hypotheses and evidence about the identities of function indices.
