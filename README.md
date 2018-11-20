# ezstate

Unpack, explore (in HTML), edit, and repack .esd files from Dark Souls 1.

Edit and repack supported for all files except enemyCommon.esd, which has two state tables (coming sometime).

Open `unpack_esd.py`, specify your file path at the bottom, and run. Example methods to convert the file to a 
fully-interlinked HTML, edit state fields, and repack an edited file are shown. Obviously, be careful not to 
overwrite your original files when repacking.

There are a large number of unsolved function/method indices, which seem to usually (but maybe not always) be 
enumerated separately for the `Command` functions and `Condition` expressions. Feel free to provide any hypotheses 
and evidence about their identifies in `command_names.py` and/or `notes.txt`.

As a bonus, now includes a semi-descriptive .drb unpacker, which has only been tested for menu.drb. Not really 
interested in pursuing that file format at the moment, though.

You can find me on reddit as u/Grimrukh or u/grimrhapsody, and on SpeedSouls Discord as chara. 
