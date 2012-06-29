
from multiprocessing import Event, Process, Queue
from Queue import Empty as QueueEmpty

import os
import regex
import sys


class Events(object):

    def __init__(self):
        self.files_enqueued = Event()
        self.results_enqueued = Event()
        self.interrupted = Event()


class Queues(object):

    def __init__(self):
        self.files_queue = Queue()
        self.results_queue = Queue()


def enqueue_files(events, queues, root):
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if events.interrupted.is_set():
                return

            for filename in filenames:
                path = os.path.join(dirpath, filename)
                queues.files_queue.put(path)

        events.files_enqueued.set()
    except KeyboardInterrupt:
        events.interrupted.set()


def enqueue_results(events, queues, term):
    try:
        while not events.interrupted.is_set():
            try:
                path = queues.files_queue.get(block=False)
                queues.results_queue.put(path)
            except QueueEmpty:
                if events.files_enqueued.is_set():
                    events.results_enqueued.set()
                    return
    except KeyboardInterrupt:
        events.interrupted.set()


def print_results(events, queues):
    try:
        while not events.interrupted.is_set():
            try:
                path = queues.results_queue.get(block=False)
                sys.stdout.write(path+'\n')
            except QueueEmpty:
                if events.results_enqueued.is_set():
                    return
    except KeyboardInterrupt:
        events.interrupted.set()


def main():
    try:
        term = sys.argv[1]
        root = sys.argv[2]

        events = Events()
        queues = Queues()
        processes = []

        # one process looks in directories and queues up files
        args = (events, queues, root)
        processes.append(Process(target=enqueue_files, args=args))

        # one process looks in files and queues up results
        args = (events, queues, term)
        processes.append(Process(target=enqueue_results, args=args))

        # one process prints results
        args = (events, queues,)
        processes.append(Process(target=print_results, args=args))

        map(Process.start, processes)
        while True in map(Process.is_alive, processes):
            print 'what'
            if events.interrupted.is_set():
                for process in processes:
                    print 'terminating'
                    process.terminate()

            for process in processes:
                process.join(timeout=0.1)

    except KeyboardInterrupt:
        events.interrupted.set()
        map(Process.terminate, processes)

    finally:
        sys.stdout.flush()
        sys.stdout.write('\n')

