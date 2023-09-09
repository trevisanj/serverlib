__all__ = ["WithCommands"]

import serverlib as sl, asyncio, a107
from . import _basicapi

class WithCommands:
    """This class enters as an ancestor for the Client and Server class in a multiple-inheritance composition."""

    def __init__(self, cmd=None):
        # {name: Command, ...}
        self.cmd = {}
        # {commandname: Command, ...}, synthesized from all self.cmd
        self.metacommands = {}

        if cmd is not None:
            self._attach_cmd(cmd)

    async def _initialize_cmd(self):
        await asyncio.gather(*[cmd.initialize() for cmd in self.cmd.values()])

    def _attach_cmd(self, *cmds):
        """Attaches one or more Commands instances.

        Args:
            cmds: iterates recursively processing all Command objects found

        **Note** This method may be called from __init__().
        """

        def process_one_cmd(one_cmd):
            one_cmd.master = self
            self.cmd[one_cmd.title] = one_cmd
            for metacommand in _basicapi.get_metacommands(one_cmd, flag_protected=True):
                name = metacommand.name

                # WARNING: #gambiarra ahead
                if name in self.metacommands:
                    # TODO let's see, maybe we let commands override each other without warning
                    self.logger.warming(f"Repeated command: '{name}'")

                self.metacommands[name] = metacommand

        def process_many(list_of_cmds):
            for cmd in list_of_cmds:
                if isinstance(cmd, (list, tuple)):
                    process_many(cmd)
                elif cmd is None:
                    continue
                else:
                    if not isinstance(cmd, sl.Intelligence):
                        raise TypeError(f"Invalid command type: `{cmd.__class__.__name__}` "
                                        f"(must be a `serverlib.Intelligence`)")

                    process_one_cmd(cmd)

        process_many(cmds)
