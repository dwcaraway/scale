"""Defines the class that represents running job executions"""
from __future__ import unicode_literals

import threading

from job.resources import NodeResources


class RunningJobExecution(object):
    """This class represents a currently running job execution. This class is thread-safe."""

    def __init__(self, job_exe):
        """Constructor

        :param job_exe: The job execution, which must be in RUNNING status and have its related node, job, job_type and
            job_type_rev models populated
        :type job_exe: :class:`job.models.JobExecution`
        """

        self._lock = threading.Lock()

        # TODO: Future refactor: replace ScaleJobExecution with the new task system, add unit tests
        from scheduler.scale_job_exe import ScaleJobExecution
        self.scale_job_exe = ScaleJobExecution(job_exe, job_exe.cpus_scheduled, job_exe.mem_scheduled,
                                               job_exe.disk_in_scheduled, job_exe.disk_out_scheduled,
                                               job_exe.disk_total_scheduled)

    # TODO: Future refactor: have current_task() method
    def current_task_id(self):
        """Returns the ID of the current task

        :returns: The ID of the current task, possibly None
        :rtype: str
        """

        with self._lock:
            return self.scale_job_exe.current_task()

    def is_finished(self):
        """Indicates whether this job execution is finished with all tasks

        :returns: True if all tasks are finished, False otherwise
        :rtype: bool
        """

        with self._lock:
            return self.scale_job_exe.is_finished()

    def is_next_task_ready(self):
        """Indicates whether the next task in this job execution is ready

        :returns: True if the next task is ready, False otherwise
        :rtype: bool
        """

        with self._lock:
            return self.scale_job_exe.current_task_id is None and len(self.scale_job_exe.remaining_task_ids) > 0

    def next_task_resources(self):
        """Returns the resources that are required by the next task in this job execution. Returns None if there are no
        remaining tasks.

        :returns: The resources required by the next task, possibly None
        :rtype: :class:`job.resources.NodeResources`
        """

        with self._lock:
            if len(self.scale_job_exe.remaining_task_ids) == 0:
                return None

            cpus = self.scale_job_exe.cpus
            mem = self.scale_job_exe.mem
            if not self.scale_job_exe.remaining_task_ids:
                disk = 0.0
            else:
                disk = self.scale_job_exe._get_task_disk_required(self.scale_job_exe.remaining_task_ids[0])

            return NodeResources(cpus=cpus, mem=mem, disk=disk)

    def start_next_task(self):
        """Starts the next task in the job execution and returns it. Returns None if the next task is not ready or no
        tasks remain.

        :returns: The task that was just started, possibly None
        :rtype: :class:`scheduler.scale_job_exe.ScaleJobExecution`
        """

        with self._lock:
            if not self.is_next_task_ready():
                return None

            self.scale_job_exe.start_next_task()
            return self.scale_job_exe

    def task_completed(self, task_id, status):
        """Indicates that a Mesos task for this job execution has completed

        :param task_id: The ID of the task that was completed
        :type task_id: str
        :param status: The task status
        :type status: :class:`mesos_pb2.TaskStatus`
        """

        with self._lock:
            self.scale_job_exe.task_completed(task_id, status)

    def task_failed(self, task_id, status):
        """Indicates that a Mesos task for this job execution has failed

        :param task_id: The ID of the task that failed
        :type task_id: str
        :param status: The task status
        :type status: :class:`mesos_pb2.TaskStatus`
        """

        with self._lock:
            self.scale_job_exe.task_failed(task_id, status)

    def task_running(self, task_id, status):
        """Indicates that a Mesos task for this job execution has started running

        :param task_id: The ID of the task that has started running
        :type task_id: str
        :param status: The task status
        :type status: :class:`mesos_pb2.TaskStatus`
        """

        with self._lock:
            self.scale_job_exe.task_running(task_id, status)
