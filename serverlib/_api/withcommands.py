__all__ = ["WithCommands"]

import serverlib as sl, asyncio, a107
from . import _basicapi

class WithCommands:
    """This class enters as an ancestor for the Client and Server class in a multiple-inheritance composition."""

    def __init__(self):
        # {name: Command, ...}
        self.cmd = {}
        # {commandname: Command, ...}, synthesized from all self.cmd
        self.metacommands = {}

    async def _initialize_cmd(self):
        await asyncio.gather(*[cmd.initialize() for cmd in self.cmd.values()])

    def _attach_cmd(self, *cmds):
        """Attaches one or more Commands instances.

        Args:
            cmds: each element may be a Commands or [Commands0, Commands1, ..]

        **Note** This method may be called from __init__().
        """
        for cmd in cmds:
            if not isinstance(cmd, (list, tuple)):
                cmd = [cmd]

            for cmd_ in cmd:
                if not isinstance(cmd_, sl.Intelligence):
                    raise TypeError(f"Invalid commands type: {cmd_.__class__.__name__} (must be an Intelligence)")

            for cmd_ in cmd:
                cmd_.master = self
                self.cmd[cmd_.title] = cmd_
                for metacommand in _basicapi.get_metacommands(cmd_, flag_protected=True):
                    name = metacommand.name

                    # WARNING: #gambiarra ahead
                    if name in self.metacommands:
                        # TODO let's see, maybe we let commands override each other without warning
                        self.logger.warming(f"Repeated command: '{name}'")

                    self.metacommands[name] = metacommand
