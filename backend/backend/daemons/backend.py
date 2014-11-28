# coding: utf-8

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import grp
import multiprocessing
import os
import pwd
import signal
import sys
import time
from collections import defaultdict

import lockfile
import daemon
from retask.queue import Queue
from retask import ConnectionError

from ..exceptions import CoprBackendError
from ..dispatcher import Worker
from ..helpers import BackendConfigReader
from . import CoprJobGrab, CoprLog


class CoprBackend(object):

    """
    Core process - starts/stops/initializes workers
    """

    def __init__(self, config_file=None, ext_opts=None):
        # read in config file
        # put all the config items into a single self.opts bunch

        if not config_file:
            raise CoprBackendError("Must specify config_file")

        self.config_file = config_file
        self.ext_opts = ext_opts  # to stow our cli options for read_conf()
        self.workers_by_group_id = defaultdict(list)
        self.max_worker_num_by_group_id = defaultdict(int)

        self.config_reader = BackendConfigReader(self.config_file, self.ext_opts)
        self.opts = None
        self.update_conf()

        self.lock = multiprocessing.Lock()

        self.task_queues = []
        try:
            for group in self.opts.build_groups:
                group_id = group["id"]
                self.task_queues.append(Queue("copr-be-{0}".format(group_id)))
                self.task_queues[group_id].connect()
        except ConnectionError:
            raise CoprBackendError(
                "Could not connect to a task queue. Is Redis running?")

        # make sure there is nothing in our task queues
        self.clean_task_queues()

        self.events = multiprocessing.Queue()
        # event format is a dict {when:time, who:[worker|logger|job|main],
        # what:str}

        # create logger
        self._logger = CoprLog(self.opts, self.events)
        self._logger.start()

        self.event("Starting up Job Grabber")
        # create job grabber
        self._jobgrab = CoprJobGrab(self.opts, self.events, self.lock)
        self._jobgrab.start()
        self.abort = False

        if not os.path.exists(self.opts.worker_logdir):
            os.makedirs(self.opts.worker_logdir, mode=0o750)

    def event(self, what):
        self.events.put({"when": time.time(), "who": "main", "what": what})

    def update_conf(self):
        self.opts = self.config_reader.read()

    def clean_task_queues(self):
        try:
            for queue in self.task_queues:
                while queue.length:
                    queue.dequeue()
        except ConnectionError:
            raise CoprBackendError(
                "Could not connect to a task queue. Is Redis running?")

    def run(self):
        self.abort = False
        while not self.abort:
            # re-read config into opts
            self.update_conf()

            for group in self.opts.build_groups:
                group_id = group["id"]
                self.event(
                    "# jobs in {0} queue: {1}"
                    .format(group["name"], self.task_queues[group_id].length)
                )
                # this handles starting/growing the number of workers
                if len(self.workers_by_group_id[group_id]) < group["max_workers"]:
                    self.event("Spinning up more workers")
                    for _ in range(group["max_workers"] - len(self.workers_by_group_id[group_id])):
                        self.max_worker_num_by_group_id[group_id] += 1
                        w = Worker(
                            self.opts, self.events,
                            self.max_worker_num_by_group_id[group_id],
                            group_id, lock=self.lock
                        )

                        self.workers_by_group_id[group_id].append(w)
                        w.start()
                self.event("Finished starting worker processes")
                # FIXME - prune out workers
                # if len(self.workers) > self.opts.num_workers:
                #    killnum = len(self.workers) - self.opts.num_workers
                #    for w in self.workers[:killnum]:
                # insert a poison pill? Kill after something? I dunno.
                # FIXME - if a worker bombs out - we need to check them
                # and startup a new one if it happens
                # check for dead workers and abort
                preserved_workers = []
                for w in self.workers_by_group_id[group_id]:
                    if not w.is_alive():
                        self.event("Worker {0} died unexpectedly".format(w.worker_num))
                        if self.opts.exit_on_worker:
                            raise CoprBackendError(
                                "Worker died unexpectedly, exiting")
                        else:
                            w.terminate()  # kill it with a fire
                    else:
                        preserved_workers.append(w)
                self.workers_by_group_id[group_id] = preserved_workers

            time.sleep(self.opts.sleeptime)

    def terminate(self):
        """
        Cleanup backend processes (just workers for now)
        And also clean all task queues as they would survive copr restart
        """

        self.abort = True
        for group in self.opts.build_groups:
            group_id = group["id"]
            for w in self.workers_by_group_id[group_id]:
                self.workers_by_group_id[group_id].remove(w)
                w.terminate()
        self.clean_task_queues()


def run_backend(opts):
    try:
        context = daemon.DaemonContext(
            pidfile=lockfile.FileLock(opts.pidfile),
            gid=grp.getgrnam("copr").gr_gid,
            uid=pwd.getpwnam("copr").pw_uid,
            detach_process=opts.daemonize,
            umask=0o22,
            stderr=sys.stderr,
            signal_map={
                signal.SIGTERM: "terminate",
                signal.SIGHUP: "terminate",
            },
        )
        with context:
            cbe = CoprBackend(opts.config_file, ext_opts=opts)
            cbe.run()
    except (Exception, KeyboardInterrupt):
        sys.stderr.write("Killing/Dying\n")
        if "cbe" in locals():
            cbe.terminate()
        raise