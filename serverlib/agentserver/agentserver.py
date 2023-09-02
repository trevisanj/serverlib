__all__ = ["AgentServer"]

import asyncio, a107, traceback, time, inspect, serverlib as sl
from .taskcodes import *

class AgentServer(sl.DBServer):
    """Agent Server base class

    Args:
        taskclass: class of the task object. If not specified, defaults to a107.AutoClass
#        dbclientgetter: (not optional) callable that must return a db client (this is a callable (and not a simple
#                        class) to introduce flexibility in initializing this object)
        taskcommandsgetter: (not optional) callable that must return an instance of an Intelligence descendant
                            containing methods whose name match the contents of the column `task.command`
                            in the database, and these methods must have a signature of either ```(self)````or
                            ```(self, task)```.
    """

    @property
    def agents(self):
        return self.__agents

    @property
    def sleepername(self):
        return self.__sleepername

    def __init__(self, *args, taskcommandsgetter, taskclass=None, **kwargs):
    # def __init__(self, *args, dbclientgetter, taskcommandsgetter, taskclass=None, **kwargs):

        from ._agentservercommands import AgentServerCommands

        super().__init__(*args, **kwargs)

        if not isinstance(self.cfg, sl.AgentServerConfig):
            raise TypeError(f"cfg must be a serverlib.AgentServerConfig, not {self.cfg.__class__.__name__}")

        if taskclass is None: taskclass = a107.AutoClass
        # self.__dbclientgetter = dbclientgetter
        self.__taskcommandsgetter = taskcommandsgetter

        self.__taskclass = taskclass
        self.__sleepername = "agentserver-agentloop"
        self.__agents = {}  # {agentname: (self.__agentlo_op() made task), ...}
        self._attach_cmd(AgentServerCommands())

    # INTERFACE ZONE ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱

    # def get_dbclient(self):
    #     """Calls the dbclient getter passed to the constructor. This is supposed to create a new dbclient."""
    #     return self.__dbclientgetter()

    # PRIVATE ZONE ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱

    @sl.is_loop
    async def __agentloop(self):
        # This is the loop which spawns/kills agents

        my_debug = lambda s: self.logger.debug(f"🕵🕵🕵 {s}'")

        async def review_agents():
            existingnames = list(self.__agents.keys())
            sql = f"select agentname from task where state!= '{TaskState.SUSPENDED}' group by agentname"
            # newnames = await dbclient.execute_server("s_get_singlecolumn", sql)
            newnames = self.dbfile.get_singlecolumn(sql)
            for name in existingnames:
                if name not in newnames:
                    my_debug(f"Killing agent '{name}'")
                    try: self.__agents[name].cancel()
                    except KeyError: my_debug(f"Agent '{name}' is already dead")
            for newname in newnames:
                if newname not in existingnames:
                    my_debug(f"Spawning agent '{newname}'")
                    self.__agents[newname] = asyncio.create_task(self.__agentlife(newname))

        # dbclient = self.get_dbclient()



        try:
            while True:
                try: await review_agents()
                except sl.Retry as e: await self.sleep(e, self.__sleepername)
                else: await self.sleep(self.cfg.agentloopinterval, self.__sleepername)
        finally:
            my_debug(f"{self.__class__.__name__}.__agentloop() on its 'finally:' BEGIN")



            # await dbclient.close()


            agents = list(self.__agents.values())
            for agent in agents: agent.cancel()
            my_debug(f"{self.__class__.__name__}.__agentloop() on its 'finally:' END")

    # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

    async def __agentlife(self, agentname):
        """
        Each agent lives inside one call to this method
        """

        A = f"🕵 {agentname}"
        my_debug = lambda s: self.logger.debug(f"{A} {s}")
        my_info = lambda s: self.logger.info(f"{A} {s}")

        # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

        async def get_tasks():
            st = f"select * from task where agentname='{agentname}' and state!='{TaskState.SUSPENDED}'"
            return [self.__taskclass(**row) for row in self.dbfile.execute(st)]
            # return [self.__taskclass(**row) for row in await dbclient.execute_server("s_execute", st)]

        # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

        async def run_tasks_sequential(tasks, taskcommands, agentname):
            # async def run_tasks_sequential(self, tasks, dbclient, taskcommands, agentname):

            """Tasks are executed sequentially.

            Returns: (waittime, minnexttime)
                waittime: time to wait until this method should be called again (seconds); or if preferred,
                minnexttime: the timestamp representing the next time this method should be called."""
            # assert isinstance(dbclient, sl.Client)
            assert isinstance(taskcommands, sl.Intelligence)

            for task in tasks:
                if task.nexttime < time.time():
                    # chillouttime = await self.__run_task(task, dbclient, taskcommands)

                    chillouttime = await run_task(task, taskcommands)
                    if chillouttime > 0:
                        await self.sleep(chillouttime, agentname)

            minnexttime = min(task.nexttime for task in tasks)
            waittime = max(0, minnexttime - time.time())
            return waittime, minnexttime

        # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

        # async def __run_task(self, task, dbclient, taskcommands):
        async def run_task(task, taskcommands):
            """Exception handling center. Returns eventual chillout time"""
            chillouttime = 0.

            async def es():
                sql = "update task set lasttime=?, nexttime=?, lasterror=?, state=?, result=? where id=?"
                # await dbclient.execute_server("s_execute", sql,
                #       (task.lasttime, task.nexttime, task.lasterror, task.state, task.result, task.id),
                #       flag_commit=True)
                self.dbfile.execute(sql,
                                    (task.lasttime, task.nexttime, task.lasterror, task.state, task.result, task.id))
                self.dbfile.commit()

            # These act_on_*() are supposed to update the task table in the database

            # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

            async def act_on_error(e):
                # Will always find exception because last item is the completely generic Exception

                try:
                    for item in errormap:
                        if isinstance(e, item.ecls):
                            break

                    task.lasterror = a107.str_exc(e)
                    task.result = TaskResult.FAIL

                    waittime = 0
                    if item.action == TaskAction.RETRY:
                        task.state = TaskState.IDLE
                        assert isinstance(e, sl.Retry)
                        waittime = e.waittime
                        task.nexttime = time.time() + waittime
                    elif item.action == TaskAction.SUSPEND:
                        task.state = TaskState.SUSPENDED
                        task.nexttime = 0.
                    else:
                        raise NotImplementedError(f"Action '{item.action}' not implemented")

                    self.logger.info(f"Error executing {task}: {task.lasterror} (action: {item.action})")

                    await es()

                except BaseException as e:
                    # This is to facilitate debugging should the code above have any error: reports error, suspends task
                    # and crashes

                    task.lasterror = f"Error inside act_on_error(): {a107.str_exc(e)}"
                    task.result = TaskResult.FAIL
                    task.state = TaskState.SUSPENDED
                    task.nexttime = 0.

                    raise

                return item.flag_raise, waittime

            # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

            async def act_on_success():
                task.lasterror = ""
                task.result = TaskResult.SUCCESS
                task.state = TaskState.IDLE
                task.nexttime = t + task.interval
                await es()

            # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

            async def act_on_start():
                task.lasterror = ""
                task.result = TaskResult.NONE
                task.state = TaskState.IN_PROGRESS
                task.lasttime = time.time()
                await es()

            # ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

            # === BEGIN task execution

            my_debug(f"taking task {task} at {a107.now_str()}")

            t = time.time()
            await act_on_start()
            try:
                method = getattr(taskcommands, task.command)
                signature = inspect.signature(method)
                if len(signature.parameters) == 0:
                    await method()  # task does not care about the task object
                elif len(signature.parameters) == 1:
                    await method(task)
                else:
                    msg = f"Method {taskcommands.__class__.__name__}.{method.__name__}() has wrong number of arguments " \
                          f"(signature possibilities are: `()` or `(task)`, not `{str(signature)}`)"
                    raise AssertionError(msg)
            except asyncio.CancelledError:
                raise
            except BaseException as e:
                flag_raise, chillouttime = await act_on_error(e)
                if flag_raise:
                    raise  # will cause the agent to crash because it is a bug anyway
            else:
                await act_on_success()
            return chillouttime

            # === END task execution

        # === BEGIN agent life

        try:
            # dbclient = self.get_dbclient()
            taskcommands = self.__taskcommandsgetter(self)
            await taskcommands.initialize()
            try:
                while True:
                    try:
                        tasks = await get_tasks()
                        if not tasks:
                            # 🕵 says: Probably all tasks were suspended, or even deleted, after I was spawned.
                            #          If this no-task situation persists, the server will soon kill me.
                            my_debug(f"Got no tasks to run, so sleeping for a bit ...")

                            await self.sleep(sl.config.retry_waittime, agentname)
                            continue

                        else:
                            my_debug(f"Got {len(tasks)} tasks to run")

                        waittime, _ = await run_tasks_sequential(tasks, taskcommands, agentname)

                        if waittime > 0:
                            await self.sleep(waittime, agentname)

                    except sl.Retry as e:
                        self.logger.info(f"{A} Error: {a107.str_exc(e)} (will retry)")
                        await self.sleep(e, agentname)
                        continue

            finally:
                my_debug(f"on its 'finally:'")
                await sl.retry_on_cancelled(taskcommands.close(), logger=self.logger)
                # await sl.retry_on_cancelled(dbclient.close(), logger=self.logger)
                my_debug(f"succeeded on its 'finally:'")
        except asyncio.CancelledError:
            # I know one could say I should raise this, not no, this is agent logic: agent loop does not raise
            pass
        except BaseException as e:
            my_debug(f"️💀️ crashed with: '{a107.str_exc(e)}'")
            if not isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
                traceback.print_exc()
        finally:
            del self.__agents[agentname]

        # END agent life


# ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲

