This app scan all com ports of pc automatically, load newest binary file and burn to addr: 0x0800_0000.

Put the binary file in the same folder,
and run the main.py: python main.py（python version >= 3.11）.

a real example:
'''
connected to COM3
old version: 2.5.35T
send:7f===1===79
init success
file: .\PCB16R7101B.0S.V2.5.35T.bin, len = 81276
erase flash ...
send:44bb===1===79
send:00040000000100020003000400===2368===79
erase 0..4 pages success
progress: [##################################################] 100%
end cycle, 13.075
update success!!, repower the device !!
'''
