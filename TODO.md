Arguments
---------
- Find and replace
- Implement --exclude GLOB
- Implement --binary to allow searching in binary files
- Implement --debug
    - hide KeyboardInterrupts unless debug is on
- Open matched files in editor (including mac friendly syntax using the "open -a" cmd)

Config
------
- Implement config file support that lets the user:
    - set default exclude globs
    - set colors for output
    - set other defaults, like number of processes
