__all__ = ["AgentServerCommands"]

import serverlib as sl

class AgentServerCommands(sl.ServerCommands):
    async def _on_initialize(self):
        self.dbclient = self._append_closers(self.server.get_dbclient())

    @sl.is_command
    async def s_agentnames(self):
        return list(self.master.agents.keys())

    @sl.is_command
    async def s_run_task_asap(self, idtask):
        """Configures task to be executed as soon as possible and tries to wake up corresponding agent."""
        agentname = await self.dbclient.execute("s_get_scalar", f"select agentname from task where id={idtask}")
        await self.dbclient.execute("s_execute", f"update task set state=0, nexttime=0 where id={idtask}", flag_commit=True)
        # Tries to wake up the agent; if it fails, wakes up the server to span agent
        try:
            self.server.wake_up(agentname)
        except KeyError:
            # failed waking agent up, wakes up server instead
            self.server.wake_up(self.server.mastersleepername)

    @sl.is_command
    async def s_run_all_tasks_asap(self):
        """Configures all idle tasks (state==0) to be executed as soon as possible and tries to wake up everybody."""
        await self.dbclient.execute("s_execute", f"update task set state=0, nexttime=0 where state=0", flag_commit=True)
        self.server.wake_up()

