#!/usr/bin/env python
"""
A programmer's search tool, parallel and fast
"""
import re
import sys
import datetime
from subprocess import Popen
from collections import deque
from multiprocessing import Process

from os import sep as directory_separator, getcwd, path, walk

def build_parser():
    """
    Returns an argparse.ArgumentParser instance to parse the command line
    arguments for lk
    """
    import argparse
    description = "A programmer's search tool, parallel and fast"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('pattern', metavar='PATTERN', action='store',
                        help='a python re regular expression')
    parser.add_argument('--ignore-case', '-i',  dest='ignorecase', action='store_true',
                        default=False, help='ignore case when searching')
    parser.add_argument('--no-unicode', '-u', dest='unicode', action='store_false',
                        default=True, help='unicode-unfriendly searching')
    parser.add_argument('--no-multiline', '-l', dest='multiline',
                        action='store_false', default=True,
                        help='don\'t search over multiple lines')
    parser.add_argument('--dot-all', '-a', dest='dot_all',
                        action='store_true', default=False,
                        help='dot in PATTERN matches newline')
    parser.add_argument('--escape', '-e', dest='escape',
                        action='store_true', default=False,
                        help='treat PATTERN as a string instead of a regex')

    if sys.version_info >= (2, 6):
        parser.add_argument('--follow-links', '-s', dest='follow_links',
                            action='store_true', default=False,
                            help='follow symlinks (Python >= 2.6 only)')
    parser.add_argument('--hidden', '-n', dest='search_hidden',
                        action='store_true', default=False,
                        help='search hidden files and directories')
    parser.add_argument('--binary', '-b', dest='search_binary',
                        action='store_true', default=False,
                        help='search binary files')
    parser.add_argument('--no-colors', '-c', dest='use_ansi_colors',
                        action='store_false', default=True,
                        help="don't print ANSI colors")
    parser.add_argument('--stats', '-t', dest='print_stats',
                        action='store_true', default=False,
                        help='print statistics')
    parser.add_argument('--num-processes', '-p', dest='number_processes',
                        action='store', default=10, type=int,
                        help='number of child processes to concurrently search with')
    parser.add_argument('--exclude', '-x', metavar='PATH_PATTERN', dest='exclude_path_patterns',
                        action='append', default=[], type=str,
                        help='exclude paths matching PATH_PATTERN')
    parser.add_argument('--open-with', '-o', metavar='COMMAND',
                        dest='command_strings', action='append', default=[],
                        type=str,
                        help='run each COMMAND where COMMAND is a string with a placeholder, %%s, for the absolute path of the matched file')
    parser.add_argument('directory', metavar='DIRECTORY', nargs='?',
                        default=getcwd(), help='a directory to search in (default cwd)')
    return parser

def get_file_contents(path, binary=False):
    """
    Return the contents of the text file at path.
    If it is a binary file,raise an IOError
    """
    # if this isn't a text file, we should raise an IOError
    f = open(path, 'r')
    file_contents = f.read()
    f.close()
    if not binary and file_contents.find('\000') >= 0:
        raise IOError('Expected text file, got binary file')
    return file_contents

class SearchManager(object):
    """
    An object for handling parallel searches of a regex
    """
    hidden_file_regex = re.compile('^\..*$', re.UNICODE | re.LOCALE)

    def __init__(self, regex, number_processes=10, search_hidden=False,
                 follow_links=False, search_binary=False, use_ansi_colors=True,
                 print_stats=False, exclude_path_regexes=[], command_strings=[]):
        self.regex = regex
        self.queue = deque([])
#        self.pools = []
        self.number_processes = number_processes
        self.search_hidden = search_hidden
        self.follow_links = follow_links
        self.search_binary = search_binary
        self.use_ansi_colors = use_ansi_colors
        self.print_stats = print_stats
        self.exclude_path_regexes = exclude_path_regexes
        self.command_strings = command_strings
        self.mark = None

    def enqueue_directory(self, directory):
        """
        add a search of the directory to the queue
        """

        exclude_path_regexes = self.exclude_path_regexes[:]

        if not self.search_hidden:
            exclude_path_regexes.append(self.hidden_file_regex)
        else:
            exclude_path_regexes.remove(self.hidden_file_regex)

        self.mark = datetime.datetime.now()

        def is_path_excluded(path):
            """
            return True if name matches on of the regexes in
            exclude_path_regexes, False otherwise
            """
            for exclude_path_regex in exclude_path_regexes:
                for found in exclude_path_regex.finditer(path):
                    return False
            return True

        def search_walk():
            try:
                walk_generator = walk(directory, followlinks=self.follow_links)
            except TypeError:
                # for python less than 2.6
                walk_generator = walk(directory)

            for packed in walk_generator:
                directory_path, directory_names, file_names = packed
                directory_names[:] = filter(is_path_excluded, directory_names)
                file_names[:] = filter(is_path_excluded, file_names)
                yield directory_path, directory_names, file_names

        writer = ColorWriter(sys.stdout, self.use_ansi_colors)
        def print_directory_result(directory_result):
            writer.print_result(directory_result)
            for command_string in self.command_strings:
                if command_string.find('%s') < 0:
                    command_string += ' %s'
                for file_name, line_result in directory_result.iter_line_results_items():
                    file_path = path.join(directory_result.directory_path, file_name)
                    Popen(command_string % file_path, shell=True)
                    break

        for directory_path, directory_names, file_names in search_walk():
            process = Process(target=self.search_worker,
                             args=(self.regex,
                                   directory_path,
                                   file_names,
                                   self.search_binary,
                                   print_directory_result))
            self.queue.append(process)

    def search_worker(self, regex, directory_path, names, binary=False,
                      callback=None):
        """
        build a DirectoryResult for the given regex, directory path, and file names
        """
        try:
            result = DirectoryResult(directory_path)
            def find_matches(name):
                full_path = path.join(directory_path, name)
                file_contents = get_file_contents(full_path, binary)
                start = 0
                match = regex.search(file_contents, start)
                while match:
                    result.put(name, file_contents, match)
                    start = match.end()
                    match = regex.search(file_contents, start)
            for name in names:
                try:
                    find_matches(name)
                except IOError:
                    pass
            if callback:
                callback(result)
        except KeyboardInterrupt, e:
            exit(1)

    def process_queue(self):
        counter = 0
        processes = deque([])
        while True:
            if counter < self.number_processes:
                try:
                    process = self.queue.popleft()
                    process.start()
                    processes.append(process)
                    counter += 1
                except IndexError:
                    break
            else:
                try:
                    process = processes.popleft()
                    process.join()
                    counter -= 1
                except IndexError:
                    pass
        if self.print_stats:
            mark = datetime.datetime.now() - self.mark
            print 'search completed in %s seconds ' % mark.seconds

class ColorWriter(object):
    """'
    an object that wraps a file handler and can output ANSI color codes
    """

    def __init__(self, output=None, use_ansi_colors=True):
        self.output = output if output else sys.stdout
        if use_ansi_colors and self.output.isatty():
            self.enable_colors()
        else:
            self.disable_colors()

    def enable_colors(self):
        self.colors = {
            'green': '\033[92m',
            'blue': '\033[94m',
            'end': '\033[0m',
        }

    def disable_colors(self):
        self.colors = {
            'green': '', 'blue': '', 'end': ''
        }

    def write(self, string, color=None):
        s = (self.colors[color]+string+self.colors['end']) if color else string
        self.output.write(s)

    def print_result(self, directory_result):
        """
        Print out the contents of the directory result, using ANSI color codes if
        supported
        """
        for file_name, line_results_dict in directory_result.iter_line_results_items():
            full_path = path.join(directory_result.directory_path, file_name)
            self.write(full_path, 'green')
            self.write('\n')
            for line_number, line_results in sorted(line_results_dict.items()):
                self.write('%s: ' % (line_results[0].line_number))
                out = list(line_results[0].left_of_group + line_results[0].group + line_results[0].right_of_group)
                offset = 0
                for line_result in line_results:
                    group_length = len(line_result.group)
                    out.insert(offset+line_result.left_offset-1, self.colors['blue'])
                    out.insert(offset+line_result.left_offset+group_length, self.colors['end'])
                    offset += group_length + 1
                self.write(''.join(out)+'\n')
            self.write('\n')

class KeyboardInterruptError(Exception):
    def __init__(self, keyboard_interrupt):
        self.keyboard_interrupt = keyboard_interrupt

class DirectoryResult(object):
    """
    A container object for storing LineResult instances for text files within
    the directory at directory_path
    """
    def __init__(self, directory_path):
        self.directory_path = directory_path
        self._line_results = {}

    def put(self, file_name, file_contents, regex_match):
        group = regex_match.group()
        match_start = regex_match.start()
        line_number = file_contents.count('\n', 0, match_start) + 1
        left_offset = match_start - file_contents.rfind('\n', 0, match_start)
        right_offset = file_contents.find('\n', match_start)
        left_of_group = file_contents[1+match_start-left_offset:match_start]
        right_of_group = file_contents[match_start+len(group):right_offset]
        line_result = LineResult(line_number, left_offset,
                                 left_of_group, group, right_of_group)

        if not file_name in self._line_results:
            self._line_results[file_name] = {}
        if not line_result.line_number in self._line_results[file_name]:
            self._line_results[file_name][line_result.line_number] = []

        self._line_results[file_name][line_result.line_number].append(line_result)

    def iter_line_results_items(self):
        for item in self._line_results.iteritems():
            yield item

class LineResult(object):
    """
    An object for storing metadata about search matches on one line of a text
    file
    """
    def __init__(self, line_number, left_offset, left_of_group,
                 group, right_of_group):
        self.line_number = line_number
        self.left_offset = left_offset
        self.left_of_group = left_of_group
        self.group = group
        self.right_of_group = right_of_group

def main():
    """
    if lk.py is run as a script, this function will run
    """
    parser = build_parser()

    args = parser.parse_args()
    flags = re.LOCALE

    if args.dot_all:
        flags |= re.DOTALL

    if args.ignorecase:
        flags |= re.IGNORECASE

    if args.unicode:
        flags |= re.UNICODE

    if args.multiline:
        flags |= re.MULTILINE

    exclude_path_flags = re.UNICODE | re.LOCALE
    exclude_path_regexes = [ re.compile(pattern, exclude_path_flags)
                             for pattern in args.exclude_path_patterns ]

    pattern = re.escape(args.pattern) if args.escape else args.pattern

    try:
        search_manager = SearchManager(regex=re.compile(pattern, flags),
                                       number_processes=args.number_processes,
                                       search_hidden=args.search_hidden,
                                       follow_links=args.follow_links,
                                       search_binary=args.search_binary,
                                       use_ansi_colors=args.use_ansi_colors,
                                       print_stats=args.print_stats,
                                       exclude_path_regexes=exclude_path_regexes,
                                       command_strings=args.command_strings)

        search_manager.enqueue_directory(args.directory)
        search_manager.process_queue()

    except (KeyboardInterruptError, KeyboardInterrupt):
        sys.stdout.write('\n')
        exit(1)

if __name__ == '__main__':
    main()
