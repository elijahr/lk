#!/usr/bin/env python
"""
A programmer's search tool
"""
import re
from multiprocessing import Pool, Manager, Process
import sys
from os import sep as directory_separator, getcwd, path, walk

class NullDevice():
    def write(self, s):
        pass

def build_parser():
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
    parser.add_argument('--exclude', '-x', dest='exclude',
                        action='store', default=None, type=str,
                        help='exclude')
    parser.add_argument('--debug', '-d', dest='debug',
                        action='store_true', default=False,
                        help='print debug output')
    parser.add_argument('directory', metavar='DIRECTORY', nargs='?',
                        default=getcwd(), help='a directory to search in (default cwd)')
    return parser


def get_text_file_contents(path):
    # if this isn't a text file, we should raise an IOError
    f = open(path, 'r')
    file_contents = f.read()
    f.close()
    if file_contents.find('\000') >= 0:
        raise IOError('Not a text file')
    return file_contents

class SearchManager(object):
    def __init__(self, regex, number_processes=10, chunk_size=10,
                 search_hidden=False, follow_links=False):
        self.regex = regex
        self.search_hidden = search_hidden
        self.follow_links = follow_links
        self.pool = Pool(processes=number_processes)
        self.chunk_size = chunk_size
        self.manager = Manager()

    def search(self, directory):
        all_results = {}

        if self.search_hidden:
            def filtered(names):
                return names
        else:
            def filtered(names):
                return [name for name in names if not name.startswith('.')]

        def search_walk():
            for packed in walk(directory, followlinks=self.follow_links):
                directory_path, directory_names, file_names = packed
                directory_names[:] = filtered(directory_names)
                file_names[:] = filtered(file_names)
                yield directory_path, directory_names, file_names

        for directory_path, directory_names, file_names in search_walk():
            args = (self.regex, directory_path, file_names)
            self.pool.apply_async(search_path, args, callback=print_result)

class ColorWriter(object):
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
    result = DirectoryResult(directory_path)
    def find_matches(name):
        full_path = path.join(directory_path, name)
        file_contents = get_text_file_contents(full_path)
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

    def get_line_results(self):
        return self._line_results.items()

class LineResult(object):
    def __init__(self, line_number, left_offset, left_of_group,
                 group, right_of_group):
        self.line_number = line_number
        self.left_offset = left_offset
        self.left_of_group = left_of_group # left of group
        self.group = group
        self.right_of_group = right_of_group # right of group

def print_result(directory_result):
    writer = ColorWriter(sys.stdout)
    for file_name, line_results in directory_result.get_line_results():
        full_path = path.join(directory_result.directory_path, file_name)
        writer.write_green(full_path+':')
        writer.write('\n')
        for line_result in line_results:
            writer.write('%s: ' % (line_result.line_number))
            writer.write(line_result.left_of_group)
            writer.write_blue(line_result.group)
            writer.write(line_result.right_of_group+'\n')

def main():
    # parse arguments
    parser = build_parser()

    """
    options:
    install - make a symlink at /usr/local/bin/lk
    replace
    ignore files matching glob or pattern
    config (set config options, like git)
    open files with app (including mac friendly syntax using the "open -a" cmd)
    default: ignore .git, .svn, .hg, etc
    """

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

    regex = re.compile(args.pattern, flags)
    directory = args.directory

#    TODO: fix this
#    if not args.debug:
#        sys.stderr = NullDevice()

    search_manager = SearchManager(regex, number_processes=args.number_processes,
                                   search_hidden=args.search_hidden,
                                   follow_links=args.follow_links)

    search_manager.search(directory)

if __name__ == '__main__':
    main()
