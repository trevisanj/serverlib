__all__ = ["AgentServerCommands"]

import serverlib as sl, a107
from . import agentserver

class AgentServerCommands(sl.DBServerCommands):
    @sl.is_command
    async def get_agentnames(self):
        """Returns names of alive agents"""

        return list(self.master.agents.keys())

    @sl.is_command
    async def suspend_all(self):
        """Kills all agents and suspends all tasks."""

        await self.master.kill_agents()

        db = self.dbfile
        db.execute("update task set state = ?", (sl.TaskState.suspended,))
        db.commit()


    @sl.is_command
    async def run_asap(self, task):
        """
        Configures task(s) to be executed as soon as possible.

        Args:
            task: <task id>|"all"|"idle"|"suspended"|"inactive"

        Notes:
            1. tasks "in_progress" won't be touched in no situation
            2. tasks "inactive" will be set to "idle" only if task=="inactive" explicitly
        """

        flag_single = False
        try:
            task = int(task)
            flag_single = True
        except ValueError:
            if task == "all":
                pass
            elif task == sl.TaskState.in_progress:
                raise ValueError(f"Tasks '{task} won't be touched")
            elif task not in (sl.TaskState.idle, sl.TaskState.suspended, sl.TaskState.inactive):
                raise ValueError(f"Invalid value for task: '{task}'")

        db = self.dbfile

        where = "where "+(f"id={task}" if isinstance(task, int)
                          else f"state <> '{sl.TaskState.in_progress}' "
                               f"and state <> '{sl.TaskState.inactive}'" if task == "all"
                          else f"state = '{task}'")

        agentnames = set(db.get_singlecolumn(f"select agentname from task {where}"))

        db.execute(f"update task set state=?, nexttime=0 {where}", (sl.TaskState.idle,))
        self.dbfile.commit()

        try:
            # Tries to wake up specific agents involved
            for agentname in agentnames:
                self.logger.debug(f"Trying to take up agent '{agentname}'")
                self.server.wake_up(agentname, flag_raise=True)
        except KeyError:
            # If any agent is not found, better to review agents
            self.server.review_agents()

    @sl.is_command
    async def getd_tasks(self, where=""):
        """Returns list-of-dicts containing all task table columns."""
        if where: where = " where "+where
        ret = self.dbfile.get_lod(f"select * from task{where}")
        return ret

    @sl.is_command
    async def insert_task(self, agentname, command, time_of_day=None, interval=None, flag_commit=True, **kwargs):
        """
        Inserts task

        Args:
            agentname:
            command:
            time_of_day:
            interval:
            flag_commit:
            kwargs:

        returns:
            None
        """
        flag_commit = a107.to_bool(flag_commit)
        taskcommands = self.master.get_new_taskcommands()
        if not hasattr(taskcommands, command) or not hasattr(getattr(taskcommands, command), "__call__"):
            raise ValueError(f"Invalid command '{command}'")
        if time_of_day is None and interval is None:
            raise ValueError(f"Please specify at least one of the following: time_of_day, interval")

        cols_values = {"command": command, "agentname": agentname, "time_of_day": time_of_day, "interval": interval,}
        cols_values.update(kwargs)
        if "state" not in cols_values:
            cols_values["state"] = sl.TaskState.idle

        await sl.insert_row(db=self.dbfile,
                            tablename="task",
                            cols_values=cols_values)
        if flag_commit:
            self.dbfile.commit()

    @sl.is_command
    async def update_task(self, taskid, **cols_values):
        """Updates columns for identified task"""
        db = self.dbfile
        try:
            await sl.update_row(db=db,
                                tablename="task",
                                id_=taskid,
                                cols_values=cols_values,
                                columnnames=None)

            task = self.master.AgentTask(**self.dbfile.get_singlerow("select * from task where id=?", (taskid,)))
            self.master.calculate_nexttime(task)

            db.execute("update task set nexttime=? where id=?", (task.nexttime, task.id))
            db.commit()
        except:
            db.rollback()

    @sl.is_command
    async def delete_task(self, taskid):
        """Deletes task identified by taskid"""

        db = self.dbfile
        db.execute("delete from task where id=?", (taskid,))
        db.commit()
