__all__ = ["AgentServer"]

import asyncio, a107, traceback, time, inspect, serverlib as sl, json, dateutil, datetime, logging
from .taskcodes import *


class AgentServer(sl.DBServer):
    """Agent Server base class

    Args:
        taskcommandsgetter: (not optional) callable that must return an instance of an Intelligence descendant
                            containing methods whose name match the contents of the column `task.command`
                            in the database, and these methods must have a signature of either ```(self)````or
                            ```(self, task)```.
        taskclass: class of the task object. If not specified, defaults to a107.AutoClass
    """

    @property
    def agents(self):
        return self.__agents

    # todo cleanup
    # @property
    # def sleepername(self):
    #     return self.__sleepername

    def __init__(self, *args, taskcommandsgetter, taskclass=None, after_tasks_time=None, **kwargs):
        """
        Agent server

        Args:
            after_tasks_time: if passed, will call _after_tasks() once some task is executed successfully
                              and there is no task in progress for after_tasks_time
        """
        from ._agentservercommands import AgentServerCommands

        super().__init__(*args, **kwargs)

        assert issubclass(self.cfg, sl.AgentCfg)

        self.after_tasks_time = after_tasks_time

        if taskclass is None:
            taskclass = self.AgentTask

        self.__taskcommandsgetter = taskcommandsgetter

        self.__taskclass = taskclass
        # {agentname: (loop task), ...}
        self.__agents = {}
        self._attach_cmd(AgentServerCommands())

    # INHERITABLE

    def _after_tasks(self):
        """Called once some task is executed successfully and there is no task in progress for after_tasks_time"""
        pass

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTERFACE

    def get_new_taskcommands(self):
        return self.__taskcommandsgetter(self)

    def review_agents(self):
        """Causes agents to be reviewed asap."""
        self.wake_up(self.SLEEPERNAME, flag_raise=False)

    async def kill_agents(self):
        """Kills all agents."""
        names = list(self.__agents.keys())

        for name in names:
            await self.kill_agent(name)

    async def kill_agent(self, name):
        self.logger.debug(f"Killing agent '{name}'")
        try:
            task = self.__agents[name]
            task.cancel()
            await asyncio.wait_for(task, timeout=sl.config.killagenttimeout)
            del self.__agents[name]
        except KeyError:
            self.logger.debug(f"Agent '{name}' is already dead")

    def _has_any_in_progress(self):
        n = self.dbfile.get_scalar("select count(*) from task where state=?", (TaskState.in_progress,))
        ret = n > 0
        return ret

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # OVERRIDE

    async def _do_getd_all(self, statedict):
        await super()._do_getd_all(statedict)
        statedict["agents"] = list(self.__agents.keys())

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PRIVATE

    @sl.is_loop
    async def __agentloop(self):
        """Spawns/kills agents."""

        async def review_agents():

            # --- Checks if any agent finished and/or crashed
            # must create list to iterate because self.__agents changes inside loop
            for name in list(self.__agents):
                agent = self.__agents[name]
                if agent.done():
                    # Note: "If the Task has been cancelled, this method [task.done()] raises a
                    # CancelledError exception."
                    # https://docs.python.org/3/library/asyncio-task.html
                    e = agent.exception()
                    if e:
                        # (agent crashes are unusual, usually a bug, as agents shouldn't crash)
                        raise e
                    del self.__agents[name]

            # --- Spawns (and/or kills) new agents as needed
            existingnames = list(self.__agents.keys())
            sql = f"select agentname from task where state = '{TaskState.idle}' group by agentname"
            newnames = self.dbfile.get_singlecolumn(sql)

            # ------ Kills agents
            if self.__FLAG_KILL:
                # 20230912 I think that there is no need to kill any agent ... let them be todo to be revisited
                for name in existingnames:
                    if name not in newnames:
                        self.logger.debug(f"Killing agent '{name}'")
                        try:
                            self.__agents[name].cancel()
                            del self.__agents[name]
                        except KeyError:
                            self.logger.debug(f"Agent '{name}' is already dead")

            # ------ Spawns agents
            for newname in newnames:
                if newname not in existingnames:
                    self.logger.debug(f"Spawning agent '{newname}'")
                    self.__agents[newname] = asyncio.create_task(self.__agentlife(newname), name=newname)


        self._last_finished_time = None

        try:
            while True:
                try:
                    await review_agents()

                    if self.after_tasks_time:
                        self.logger.debug("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
                        if self._last_finished_time and time.time()-self._last_finished_time >= self.after_tasks_time:
                            self._after_tasks()
                            self._last_finished_time = None

                except sl.Retry as e:
                    waittime = self.cfg.waittime_retry_task if e.waittime is None else e.waittime
                    await self.sleep(waittime, self.SLEEPERNAME)
                else:
                    await self.sleep(self.cfg.agentloopinterval, self.SLEEPERNAME)
        finally:
            self.logger.debug(f"{self.__class__.__name__}.__agentloop() on its 'finally:' BEGIN")

            agents = list(self.__agents.values())
            for agent in agents: agent.cancel()
            self.logger.debug(f"{self.__class__.__name__}.__agentloop() on its 'finally:' END")

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def __agentlife(self, agentname):
        """
        Each agent lives inside one call to this method
        """

        # ──────────────────────────────────────────────────────────────
        async def run_tasks_sequentially():
            """Tasks are executed sequentially.

            Returns: (waittime, minnexttime, num_run)
                waittime: time to wait until this method should be called again (seconds); or if preferred,
                minnexttime: minimum next time among all tasks run
                num_run: number of tasks run
            """

            nexttimes = []
            num_run = 0
            for taskid in taskids:
                try:
                    task = self.__taskclass(**self.dbfile.get_singlerow("select * from task where id=?", (taskid,)))
                except a107.NoData:
                    agentlogger.debug(f"Task #{taskid} not found, skipping ...")
                    continue

                if task.state != TaskState.idle:
                    agentlogger.debug(f"Task #{task.id} is '{task.state}', skipping ...")
                    continue

                if task.nexttime < time.time():
                    num_run += 1
                    flag_success = await run_task(task, taskcommands)
                    if flag_success:
                        # waiter is reset when task succeeds
                        waiter_f.reset()
                        self._last_finished_time = time.time()

                    else:
                        # will wait progressively longer at each failed task
                        agentlogger.info(f"Task #{task.id} failed, "
                                         f"will wait {waiter_f.nexttime:.2f} seconds before running next task")
                        await waiter_f.wait()

                nexttimes.append(task.nexttime)

            minnexttime = min(nexttimes) if len(nexttimes) > 0 else None
            waittime = max(0, minnexttime - time.time())
            return waittime, minnexttime, num_run

        # ────────────────────────────────────
        async def run_task(task, taskcommands):
            """Exception handling center. Treats all exceptions except CancelledError, which is re-raised

            Returns:
                flag_success
            """

            async def es(**kwargs):
                for k, v in kwargs.items():
                    setattr(task, k, v)
                sql = "update task set lasttime=?, nexttime=?, lasterror=?, state=?, result=? where id=?"
                self.dbfile.execute(sql,
                    (task.lasttime, task.nexttime, task.lasterror, task.state, task.result, task.id))
                self.dbfile.commit()

            # === BEGIN task execution

            agentlogger.debug(f"taking task {task} at {a107.now_str()}")

            await es(lasterror="", result=TaskResult.none, state=TaskState.in_progress, lasttime=time.time())

            try:
                # Runs task here
                method = getattr(taskcommands, task.command)

                await method(task)

                # I started to use wrappers which mess with the ability to determine the signature of the original
                # "task command", therefore commenting out this of #todo cleanup
                #
                # signature = inspect.signature(method)
                # await method(task)
                #
                # if len(signature.parameters) == 0:
                #     await method()
                # elif len(signature.parameters) == 1:
                #     await method(task)
                # else:
                #     raise AssertionError(f"(Invalid signature for {taskcommands.__class__.__name__}.{method.__name__}()"
                #                          f" (possibilities are: `()` or `(task)`, not `{str(signature)}`)")

            except (asyncio.CancelledError):
                # If cancelled, sets task to be run again asap
                await es(state=TaskState.idle, nexttime=0)
                raise

            except BaseException as e:
                task.lasterror = a107.str_exc(e)
                task.result = TaskResult.fail

                if isinstance(e, sl.Retry):
                    # Fail with retry: computes next time to run task after waiting interval (if there are many tasks in
                    # queue, it may take longer)
                    task.state = TaskState.idle
                    task.nexttime = e.waittime if e.waittime is not None else self.cfg.waittime_retry_task
                else:
                    # General fail case: will suspend the task and set to run as soon as un-suspended
                    task.state = TaskState.suspended
                    task.nexttime = 0.

                agentlogger.error(f"Error executing task #{task.id}! Details:\n"+
                                  json.dumps(task.to_dict(), indent=4))
                agentlogger.exception(f"Error executing task #{task.id}!")
                await es()
                return False

            else:
                task.lasterror = ""
                task.result = TaskResult.success
                task.state = TaskState.idle
                self.calculate_nexttime(task)
                agentlogger.debug(f"next time for command '{task.command}' is {a107.ts2str(task.nexttime)}")
                await es()

            return True

            # === END task execution

        # === BEGIN agent life

        agentlogger = self.get_new_sublogger(f"agent.{agentname}")
        # controls waiting in case of failed task
        waiter_f = sl.Waiter(self, description="Failed task", sleepername=agentname, logger=agentlogger,
                             flag_quiet=True)

        try:
            # dbclient = self.get_dbclient()
            taskcommands = self.get_new_taskcommands()
            await taskcommands.initialize()
            try:
                while True:
                    try:
                        taskids = self.dbfile.get_singlecolumn("select id from task where agentname=? and state=?",
                                                               (agentname, TaskState.idle))

                        if not taskids:
                            # 🕵 says: Probably all tasks were suspended, or even deleted, after I was spawned.
                            #          If this no-task situation persists, the server will soon kill me.
                            agentlogger.debug(f"Got no tasks to care for, so sleeping for a bit ...")

                            await self.sleep(self.cfg.waittime_no_tasks, agentname)
                            continue

                        else:
                            agentlogger.debug(f"Got {len(taskids)} tasks to care for")

                        waittime, minnexttime, num_run = await run_tasks_sequentially()

                        if num_run == 0:
                            await self.sleep(self.cfg.waittime_no_tasks, agentname)
                        elif waittime > 0:
                            await self.sleep(waittime, agentname)

                    except sl.Retry as e:
                        waittime = self.cfg.waittime_retry_task if e.waittime is None else e.waittime
                        agentlogger.error(f"{a107.str_exc(e)} (will retry in {waittime} seconds)")
                        await self.sleep(waittime, agentname)
                        continue

            finally:
                agentlogger.debug(f"on its 'finally:'")
                await taskcommands.close()
                agentlogger.debug(f"succeeded on its 'finally:'")
        except asyncio.CancelledError:
            # I know one could say I should raise this, not no, this is agent logic: agent loop does not raise
            pass
        except BaseException as e:
            agentlogger.debug(f"️💀️ crashed with: '{a107.str_exc(e)}'")
            if not isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
                traceback.print_exc()

        # END agent life

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # STATIC DEFINITIONS

    @staticmethod
    def calculate_nexttime(task):
        a, b = float("inf"), float("inf")
        if task.time_of_day:
            # a contains today's date with time time_of_day
            tmp = dateutil.parser.parse(task.time_of_day)
            if tmp < datetime.datetime.now():
                # makes it tomorrow only if time_of_day is past
                tmp += datetime.timedelta(days=1)
            a = tmp.timestamp()
        if task.interval is not None:
            b = task.lasttime + task.interval
        task.nexttime = min(a, b)

    class AgentTask(a107.AutoClass):
        pass

    SLEEPERNAME = "__agentloop"
    __FLAG_KILL = False
