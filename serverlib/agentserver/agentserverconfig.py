import serverlib as sl

class AgentServerConfig(sl.DBServerConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # interval to review tasks (seconds)
        self.agentloopinterval = 15
