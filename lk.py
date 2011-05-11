#!/usr/bin/env python
"""
A programmer's search tool
"""
import re
import sys
from subprocess import Popen
from multiprocessing import Pool, Manager, Process
from os import sep as directory_separator, getcwd, path, walk

def build_parser():
    """
    Returns an argparse.ArgumentParser instance to parse the command line
    arguments for lk
    """
    import argparse
    parser = argparse.ArgumentParser(description="A programmer's search tool")
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
                        help='dot in pattern matches newline')
    parser.add_argument('--follow-links', '-s', dest='follow_links',
                        action='store_true', default=False,
                        help='follow symlinks')
    parser.add_argument('--hidden', '-n', dest='search_hidden',
                        action='store_true', default=False,
                        help='search hidden files and directories')
    parser.add_argument('--num-processes', '-p', dest='number_processes',
                        action='store', default=10, type=int,
                        help='number of child processes to concurrently search with')
    parser.add_argument('--exclude', '-x', metavar='PATH_PATTERN', dest='exclude_path_patterns',
                        action='append', default=[], type=str,
                        help='exclude paths matching PATH_PATTERN')
    parser.add_argument('--open-with', '-o', metavar='COMMAND',
                        dest='command_strings', action='append', default=[],
                        type=str,
                        help='run each COMMAND where COMMAND is a string with a placeholder, %s, for the absolute path of the matched file')
#    parser.add_argument('--debug', '-d', dest='debug',
#                        action='store_true', default=False,
#                        help='print debug output')
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

    def __init__(self, regex, number_processes=10, chunk_size=10,
                 search_hidden=False, follow_links=False):
        self.regex = regex
        self.search_hidden = search_hidden
        self.follow_links = follow_links
        self.pool = Pool(processes=number_processes)
        self.chunk_size = chunk_size
        self.manager = Manager()

    def search(self, directory, exclude_path_regexes=[], command_strings=[]):
        """
        start a new pool of parallel search processes for self.regex in
        directory
        """
        if not self.search_hidden:
            exclude_path_regexes.append(self.hidden_file_regex)

        def filt(name):
            """
            return True if name matches on of the regexes in
            exclude_path_regexes, False otherwise
            """
            for exclude_path_regex in exclude_path_regexes:
                for found in exclude_path_regex.finditer(name):
                    return False
            return True

        def search_walk():
            for packed in walk(directory, followlinks=self.follow_links):
                directory_path, directory_names, file_names = packed
                directory_names[:] = filter(filt, directory_names)
                file_names[:] = filter(filt, file_names)
                yield directory_path, directory_names, file_names

        def callback(directory_result):
            print_result(directory_result)
            for command_string in command_strings:
                if command_string.find('%s') < 0:
                    command_string += ' %s'
                for file_name, line_result in directory_result.iter_line_results_items():
                    file_path = path.join(directory_result.directory_path, file_name)
                    Popen(command_string % file_path, shell=True)
                    break

        for directory_path, directory_names, file_names in search_walk():
            args = (self.regex, directory_path, file_names)
            self.pool.apply_async(search_path, args, callback=callback)

class ColorWriter(object):
    """'
    an object that wraps a file handler and can output ANSI color codes
    """
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    END_COLOR = '\033[0m'

    def __init__(self, output=None):
        if output == None:
            output = sys.stdout
        self.output = output

    def write(self, text):
        self.output.write(text)

    def write_green(self, text):
        self.output.write(self.GREEN + text + self.END_COLOR)

    def write_blue(self, text):
        self.output.write(self.BLUE + text + self.END_COLOR)

def search_path(regex, directory_path, names):
    """
    build a DirectoryResult for the given regex, directory path, and file names
    """
    result = DirectoryResult(directory_path)
    def find_matches(name):
        full_path = path.join(directory_path, name)
        file_contents = get_file_contents(full_path)
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
    return result

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
            self._line_results[file_name] = []
        self._line_results[file_name].append(line_result)

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
        self.left_of_group = left_of_group # left of group
        self.group = group
        self.right_of_group = right_of_group # right of group

writer = ColorWriter(sys.stdout)
def print_result(directory_result):
    """
    Print out the contents of the directory result, using ANSI color codes if
    supported
    """
    for file_name, line_results in directory_result.iter_line_results_items():
        full_path = path.join(directory_result.directory_path, file_name)
        writer.write_green(full_path+':')
        writer.write('\n')
        for line_result in line_results:
            writer.write('%s: ' % (line_result.line_number))
            writer.write(line_result.left_of_group)
            writer.write_blue(line_result.group)
            writer.write(line_result.right_of_group+'\n')

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

#    if not args.debug:
#        sys.stderr = NullDevice()

    exclude_path_flags = re.UNICODE | re.LOCALE

    regex = re.compile(args.pattern, flags)
    directory = args.directory
    exclude_path_regexes = [
        re.compile(exclude_path_pattern, exclude_path_flags)
        for exclude_path_pattern in args.exclude_path_patterns]

    search_manager = SearchManager(regex, number_processes=args.number_processes,
                                   search_hidden=args.search_hidden,
                                   follow_links=args.follow_links)
    search_manager.search(directory, exclude_path_regexes=exclude_path_regexes,
                          command_strings=args.command_strings)

if __name__ == '__main__':
    main()
