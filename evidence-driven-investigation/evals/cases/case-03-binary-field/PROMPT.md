`level_a.dat` and `level_b.dat` are two saves of our own toy game (`loader.py` loads
them; treat it as a black box and do not read its source). Between the two saves the
player moved from level "Forest" to level "Ice Caves", and byte 0x10 changed.
What does byte 0x10 mean? We want to write a level editor.
