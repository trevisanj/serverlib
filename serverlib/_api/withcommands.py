__all__ = ["WithCommands"]

import serverlib as sl, asyncio, a107
from . import _misc


class WithCommands:
    """This class enters as an ancestor for the Client and Server class in a multiple-inheritance composition."""

    def __init__(self, cmd=None):
        # {name: Command, ...}
        self.cmd = {}
        # {commandname: Command, ...}, synthesized from all self.cmd
        self.metacommands = {}
        # All command methods to be called easier
        self.methods = _Methods()

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

        def wrap_init_exec(method):
            async def wrap_init_exec_(*args, **kwargs):
                await self._assure_initialized()
                return await method(*args, **kwargs)

            return wrap_init_exec_

        def process_one_cmd(one_cmd):
            one_cmd.master = self
            self.cmd[one_cmd.title] = one_cmd
            for metacommand in _misc.get_metacommands(one_cmd, flag_protected=True):
                name = metacommand.name

                # WARNING: #gambiarra ahead
                if name in self.metacommands:
                    tmp = self.metacommands[name]
                    raise RuntimeError(f"Attaching {one_cmd.__class__.__name__}.{name}() to {self.__class__.__name__}: "
                                       f"class {tmp.method.__self__.__class__.__name__}.{name}() came first")

                self.metacommands[name] = metacommand
                setattr(self.methods, name, wrap_init_exec(metacommand.method))

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


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class _Methods:
    pass