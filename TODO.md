Arguments
---------
- Find and replace
- Implement --debug
    - hide KeyboardInterrupts unless debug is on
- Search file paths instead of file contents

Config
------
- Implement config file support that lets the user:
    - set default exclude globs
    - set colors for output
    - set other defaults, like number of processes

Other
-----
- smash LineResults together, at least when printing
- add an output file argument to SearchManager to allow writing to file, stdout,
  etc
- build an alternative to multiprocessing.Pool that can act on class methods
  and joins processes as they finish
- KeyboardInterrupt in any process causes nice abort of other processes
