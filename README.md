[lk](http://github.com/elijahr/lk/) - A programmer's search tool
==================================================

Notes
-----
- Written in Python
- Inspired by [ack](http://betterthangrep.com/)
- Parallelism: searches directories in parallel using Python's multiprocessing library
- Makes searching from Python programs easy via 'import lk'

Examples
-------
Search for the word 'class' in the current working directory

    $ lk class
    /home/elijah/Development/lk/lk.py:
    10: class NullDevice():
    54: class SearchManager(object):
    85: class ColorWriter:
    122: class DirectoryResult(object):
    145: class LineResult(object):

Search for the regex "line_.*" in /home/elijah/Development/lk/

    $ lk "line_.*" /home/elijah/Development/lk/
    /home/elijah/Development/lk/lk.py:
    129:         self._line_results = {}
    134:         line_number = file_contents.count('\n', 0, match_start) + 1
    139:         line_result = LineResult(line_number, left_offset,
    142:         if not file_name in self._line_results:
    143:             self._line_results[file_name] = []
    144:         self._line_results[file_name].append(line_result)
    146:     def get_line_results(self):
    147:         return self._line_results.items()
    150:     def __init__(self, line_number, left_offset, left_of_group,
    152:         self.line_number = line_number
    160:     for file_name, line_results in directory_result.get_line_results():
    164:         for line_result in line_results:
    165:             writer.write('%s: ' % (line_result.line_number))
    166:             writer.write(line_result.left_of_group)
    167:             writer.write_blue(line_result.group)
    168:             writer.write(line_result.right_of_group+'\n')

Installation
------------
    $ sudo python setup.py install

Bleeding Edge Installation
--------------------------
If you want to use the latest and greatest version of lk:
    $ git clone git://github.com/elijahr/lk.git
    $ cd lk
    $ sudo chmod +x lk.py
    $ sudo ln -s `pwd`/lk.py /usr/local/bin/lk
Then whenever you feel like updating to the latest, just do this:
    $ cd lk && git pull

Usage
-----
    lk [-h] [--ignore-case] [--no-unicode] [--no-multiline] [--dot-all]
              [--follow-links] [--hidden] [--num-processes NUMBER_PROCESSES]
              [--exclude EXCLUDE] [--debug]
              PATTERN [DIRECTORY]

    positional arguments:
      PATTERN               a python re regular expression
      DIRECTORY             a directory to search in (default cwd)

    optional arguments:
      -h, --help            show this help message and exit
      --ignore-case, -i     ignore case when searching
      --no-unicode, -u      unicode-unfriendly searching
      --no-multiline, -l    don't search over multiple lines
      --dot-all, -a         dot in pattern matches newline
      --follow-links, -s    follow symlinks
      --hidden, -n          search hidden files and directories
      --num-processes NUMBER_PROCESSES, -p NUMBER_PROCESSES
                            number of child processes to concurrently search with
      --exclude EXCLUDE, -x EXCLUDE
                            exclude
      --debug, -d           print debug output

Issues?
-------
Please report any encountered bugs at http://github.com/elijahr/lk/issues
