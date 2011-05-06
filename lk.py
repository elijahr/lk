#!/usr/bin/env python

"""
A programmer's search tool
"""


import re
from multiprocessing import Pool, Manager
import thread
import socket
import sys
from os import sep as directory_separator, getcwd, path, walk

class NullDevice():
    def write(self, s):
        pass

def build_parser():
    import argparse
    parser = argparse.ArgumentParser(description='A programmer\'s search tool')
    parser.add_argument('pattern', metavar='PATTERN', action='store',
                       help='a python re regular expression')
    parser.add_argument('--ignore-case', '-i',  dest='ignorecase', action='store_true',
                       default=False, help='ignore case when searching')
    parser.add_argument('--no-unicode', '-x', dest='unicode', action='store_false',
                       default=True, help='unicode-unfriendly searching')
    parser.add_argument('--no-multiline', '-l', dest='multiline',
                       action='store_false', default=True,
                       help='don\'t search over multiple lines')
    parser.add_argument('--follow-links', '-s', dest='followlinks',
                       action='store_true', default=False,
                       help='follow symlinks')
    parser.add_argument('--hidden', '-n', dest='searchhidden',
                       action='store_true', default=False,
                       help='search hidden files and directories')
    parser.add_argument('--num-processes', '-p', dest='numprocesses',
                       action='store', default=10, type=int,
                       help='number of child processes to concurrently search with')
    parser.add_argument('--debug', '-d', dest='debug',
                       action='store_true', default=False,
                       help='print debug output')
    parser.add_argument('directory', metavar='DIRECTORY', nargs='?',
                       default=getcwd())

    return parser

def get_text_file_contents(path):
    # if this isn't a text file, we should raise an IOError
    f = open(path, 'r')
    contents = f.read()
    f.close()
    if contents.find('\000') >= 0:
        raise IOError('Not a text file')
    return contents

def get_linebreak_positions(text):
    while True:
        position = text.find

class SearchManager(object):
    def __init__(self, regex, numprocesses=10, searchhidden=False, followlinks=False):
        self.regex = regex
        self.searchhidden = searchhidden
        self.followlinks = followlinks
        self.pool = Pool(processes=numprocesses)

    def search(self, directory, followlinks=False):
        def is_excluded(name):
            if not self.searchhidden and name.startswith('.'):
                return True

        def search_walk():
            for packed in walk(directory, followlinks=followlinks):
                dirpath, dirnames, filenames = packed
                dirnames[:] = [
                    dn for dn in dirnames
                    if not is_excluded(dn)]

                yield dirpath, dirnames, filenames

        all_results = {}
        try:
            mutex = Manager().Lock()
            async_results = []
            for packed in search_walk():
                dirpath, dirnames, filenames = packed
                args = (self.regex, dirpath, filenames, mutex)
                async_result = self.pool.apply_async(finder_wrapper, args)
                async_results.append(async_result)

            for async_result in async_results:
                dirname, results = async_result.get()
                if len(results.keys()):
                    all_results[dirname] = results

        except KeyboardInterrupt, KeyboardInterruptError:
            try:
                self.pool.terminate()
            except socket.error:
                pass
        return all_results

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class KeyboardInterruptError(Exception):
    pass

def finder_wrapper(*args, **kwargs):
    try:
        return finder(*args, **kwargs)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()

def finder(regex, dirname, names, mutex):
    results = {}
    def find_matches(name):
        fullpath = path.join(dirname, name)
        contents = get_text_file_contents(fullpath)
#        linebreaks = get_linebreak_positions(contents)
        start = 0
        while True:
            match = regex.search(contents, start)
            if match:
                if not len(results.keys()):
                    mutex.acquire()
                    sys.stdout.write(bcolors.OKGREEN + fullpath + ':' + \
                                    bcolors.ENDC + '\n')
                group = match.group()
                match_start = match.start()
                linenum = contents.count('\n', 0, match_start) + 1
                offset = match_start - contents.rfind('\n', 0, match_start)
                roffset = contents.find('\n', match_start)
                line = contents[1+match_start-offset:match_start] + bcolors.OKBLUE + \
                       group + bcolors.ENDC + contents[match_start+len(group):roffset]
                packed = (group, linenum, offset)
                sys.stdout.write('%s: %s\n' % (linenum, line))
                if name in results:
                    results[name].append(packed)
                else:
                    results[name] = [packed]

                start = match.end()
            else:
                if name in results:
                    try:
                        mutex.release()
                    except thread.error:
                        pass
                break
    for name in names:
        try:
            find_matches(name)
        except IOError:
            pass
    return dirname, results

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
    flags = re.LOCALE | re.DOTALL

    if args.ignorecase:
        flags |= re.IGNORECASE

    if args.unicode:
        flags |= re.UNICODE

    if args.multiline:
        flags |= re.MULTILINE

    regex = re.compile(args.pattern, flags)
    directory = args.directory

    if not args.debug:
        sys.stderr = NullDevice()

    search_manager = SearchManager(regex, args.numprocesses)
    results = search_manager.search(directory, followlinks=args.followlinks)

#    from pprint import pprint
#    pprint(results)

if __name__ == '__main__':
    main()
