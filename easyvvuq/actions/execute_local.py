"""Provides element to execute a shell command in a given directory.
"""

import os
import sys
import logging
import subprocess
from . import BaseAction
import concurrent

__license__ = "LGPL"


class ActionStatusLocal():
    def __init__(self):
        pass

    def start(self):
        return None

    def finished(self):
        return True

    def finalise(self):
        return None

    def succeeded(self):
        return True


class ExecuteLocal(BaseAction):

    def __init__(self, run_cmd, interpret=None):
        """
        Provides an action element to run a shell command in a specified
        directory.

        Parameters
        ----------

        run_cmd : str
            Command to execute.
        interpret : str or None
            Interpreter to use to execute cmd.

        """

        if os.name == 'nt':
            msg = ('Local execution is provided for testing on Posix systems'
                   'only. We detect you are using Windows.')
            logger.error(msg)
            raise NotImplementedError(msg)

        # Need to expand users, get absolute path and dereference symlinks
        self.run_cmd = os.path.realpath(os.path.expanduser(run_cmd))
        self.interpreter = interpret

    def act_on_dir(self, target_dir):
        """
        Executes `self.run_cmd` in the shell in `target_dir`.

        target_dir : str
            Directory in which to execute command.

        """

        if self.interpreter is None:
            full_cmd = f'cd "{target_dir}"\n{self.run_cmd}\n'
        else:
            full_cmd = f'cd "{target_dir}"\n{self.interpreter} {self.run_cmd}\n'
        result = os.system(full_cmd)
        if result != 0:
            sys.exit(f'Non-zero exit code from command "{full_cmd}"\n')
        return ActionStatusLocal()


class ExecutePython():
    def __init__(self, function):
        self.function = function
        self.params = None
        self.result = None

    def start(self):
        self.result = self.function(self.params)
        return self.result

    def finished(self):
        if self.result is None:
            return False
        else:
            return True

    def finalise(self):
        self.action.campaign.campaign_db.store_result(self.run_id, self.result)

    def succeeded(self):
        if not self.finished():
            raise RuntimeError('action did not finish yet')
        else:
            return True


class ActionStatusLocalV2():
    def __init__(self, full_cmd, target_dir):
        self.full_cmd = full_cmd
        self.target_dir = target_dir
        self.popen_object = None
        self.ret = None
        self._started = False

    def start(self):
        self.popen_object = subprocess.Popen(self.full_cmd, cwd=self.target_dir)
        self._started = True

    def started(self):
        return self._started

    def finished(self):
        """Returns true if action is finished. In this case if calling poll on
        the popen object returns a non-None value.
        """
        if self.popen_object is None:
            return False
        ret = self.popen_object.poll()
        if ret is not None:
            self.ret = ret
            return True
        else:
            return False

    def finalise(self):
        """Performs clean-up if necessary. In this case it isn't. I think.
        """
        return None

    def succeeded(self):
        """Will return True if the process finished successfully.
        It judges based on the return code and will return False
        if that code is not zero.
        """
        if not self.started():
            return False
        if self.ret != 0:
            return False
        else:
            return True


class ExecuteLocalV2(ExecuteLocal):
    """An improvement over ExecuteLocal that uses Popen and provides the non-blocking
    execution that allows you to track progress. In line with other Action classes in EasyVVUQ.
    """

    def act_on_dir(self, target_dir):
        """
        Executes `self.run_cmd` in the shell in `target_dir`.

        target_dir : str
            Directory in which to execute command.

        """

        if self.interpreter is None:
            full_cmd = self.run_cmd.split()
        else:
            full_cmd = [self.interpreter] + self.run_cmd.split()
        return ActionStatusLocalV2(full_cmd, target_dir)
