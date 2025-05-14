* More formats
* encryption
* StartFirst vs EndFirst vs Stream
* credits section
* examples?
	* example "vuln" by design libs/software
	* example ctf challs
* zip64 support
	* other extensions
* fork/extend zipfile/tarfile to enable more granular control without implementing formats from scratch
	* enables "marked as directory in archive but entry does not end with /"
	* enables "LFH says A CDH says B"
* "spray" flag in add? ../bla, ../../bla, /proc/X/cwd/bla, /proc/X/cwd/../bla, /proc/Y/bla etc
* refactor recursive add dir
* zip MS-DOS attributes, HIDDEN/READONLY support?
* support for other file types in tar (FIFO etc)