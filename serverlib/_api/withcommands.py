__all__ = ["WithCommands"]

import serverlib as sl, asyncio, a107

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
            if not isinstance(cmd, (list, tuple)): cmd = [cmd]
            for _ in cmd:
                if not isinstance(_, sl.Intelligence):
                    raise TypeError(f"Invalid commands type: {_.__class__.__name__} (must be an Intelligence)")
            for _ in cmd:
                _.master = self
                self.cmd[_.title] = _
                for metacommand in _.get_meta(flag_protected=True):
                    name = metacommand.name
                    # WARNING: #gambiarra ahead
                    if name in self.metacommands and name not in ["getd_cfg"]:
                        print(a107.format_warning(f"Repeated command: '{name}'"))  # TODO let's see, maybe we let commands override each other
                    self.metacommands[name] = metacommand
