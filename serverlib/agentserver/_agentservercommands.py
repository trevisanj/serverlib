__all__ = ["AgentServerCommands"]

import serverlib as sl, a107
from . import agenttask

class AgentServerCommands(sl.DBServerCommands):
    async def _on_initialize(self):
        pass
        # self.dbclient = self._append_closers(self.server.get_dbclient())

    @sl.is_command
    async def s_get_agentnames(self):
        return list(self.master.agents.keys())

    @sl.is_command
    async def s_run_task_asap(self, idtask):
        """Configures task to be executed as soon as possible and tries to wake up corresponding agent."""
        agentname = self.dbfile.get_scalar("select agentname from task where id=?", (idtask,))
        self.dbfile.execute("update task set state=?, nexttime=0 where id=?", (sl.TaskState.IDLE, idtask))
        self.dbfile.commit()
        # Tries to wake up the agent; if it fails, wakes up the server to span agent
        try:
            self.server.wake_up(agentname)
        except KeyError:
            # failed waking agent up, wakes up server instead
            self.server.wake_up(self.server.sleepername)

    @sl.is_command
    async def s_run_idle_tasks_asap(self):
        """Configures all idle tasks (state==serverlib.TaskState.IDLE) to be executed as soon as possible and tries to wake up everybody."""
        self.dbfile.execute(f"update task set nexttime=0 where state=?", (sl.TaskState.IDLE))
        self.dbfile.commit()
        self.server.wake_up()

    @sl.is_command
    async def s_getd_tasks(self, where=""):
        """Returns list-of-dicts containing all task table columns."""
        if where: where = " where "+where
        ret = [dict(row) for row in self.dbfile.execute(f"select * from task{where}")]
        return ret

    @sl.is_command
    async def s_insert_task(self, command, agentname, time_of_day, interval, **kwargs):
        taskcommands = self.master.get_new_taskcommands()
        if not hasattr(taskcommands, command) or not hasattr(getattr(taskcommands, command), "__call__"):
            raise ValueError(f"Invalid command '{command}'")

        cols_values = {"command": command, "agentname": agentname, "time_of_day": time_of_day, "interval": interval,}
        cols_values.update(kwargs)

        await sl.insert_row(db=self.dbfile,
                            tablename="task",
                            cols_values=cols_values)

    @sl.is_command
    async def s_update_task(self, idtask, *cols_values):
        """Updates columns for identified task.

        Args:
            idtask: existing value for task's 'id' field
            *cols_values: pairs of arguments: (columnname0, value0, columnname1, value1, ...)
        """
        db = self.dbfile
        await sl.update_row(db=db,
                            tablename="task",
                            id_=idtask,
                            cols_values=cols_values,
                            columnnames=None)

        task = agenttask.AgentTask(**self.dbfile.get_singlerow("select * from task where id=?", (idtask,)))
        task.calculate_nexttime()

        db.execute("update task set nexttime=? where id=?", (task.nexttime, task.id))
        db.commit()
