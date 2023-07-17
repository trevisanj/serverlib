__all__ = ["AgentServerCommands"]

import serverlib as sl

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
        agentname = self.dbfile.get_scalar(f"select agentname from task where id={idtask}")
        self.dbfile.execute(f"update task set state=0, nexttime=0 where id={idtask}")
        self.dbfile.commit()
        # Tries to wake up the agent; if it fails, wakes up the server to span agent
        try:
            self.server.wake_up(agentname)
        except KeyError:
            # failed waking agent up, wakes up server instead
            self.server.wake_up(self.server.sleepername)

    @sl.is_command
    async def s_run_all_tasks_asap(self):
        """Configures all idle tasks (state==0) to be executed as soon as possible and tries to wake up everybody."""
        self.dbfile.execute(f"update task set state=0, nexttime=0 where state=0")
        self.dbfile.commit()
        self.server.wake_up()

