__all__ = ["WithCommands"]

import serverlib as sl, asyncio

class WithCommands:
    """This class enters as an ancestor for the Client and Server class in a multiple-inheritance composition."""

    def __init__(self):
        # {name: Command, ...}
        self.cmd = {}
        # {commandname: Command, ...}, synthesized from all self.cmd
        self.metacommands = {}

    async def _initialize_cmd(self):
        await asyncio.gather(*[cmd.initialize() for cmd in self.cmd.values()])

    def _attach_cmd(self, cmd):
        """Attaches one or more Commands instances.

        Args:
            cmd: Command or [Command0, Command1, ..]

        This method is not async because it was designed to be called from __init__().
        """
        if not isinstance(cmd, (list, tuple)): cmd = [cmd]
        for _ in cmd:
            if not isinstance(_, sl.Commands): raise TypeError(f"Invalid commands type: {_.__class__.__name__}")
        for _ in cmd:
            _.master = self
            self.cmd[_.name] = _
            for metacommand in _.__get_meta__(flag_protected=True):
                self.metacommands[metacommand.name] = metacommand
