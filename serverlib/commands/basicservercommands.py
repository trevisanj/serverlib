__all__ = ["BasicServerCommands"]

import asyncio
from colored import fg, bg, attr
from serverlib import is_command
from .commands import ServerCommands
import serverlib as sl
from .. import _api


class BasicServerCommands(ServerCommands):
    @is_command
    async def s_get_welcome(self):
        return self.master.get_welcome()

    @is_command
    async def s_poke(self):
        """Prints and returns the server subappname (useful to identify what is running in a terminal)."""
        print(f"{fg('white')}{attr('bold')}{self.master.subappname}{attr('reset')} 👈")
        return self.master.subappname

    @is_command
    async def s_help(self, what=None, flag_docstrings=False, refilter=None, fav=None, favonly=False):
        """Gets summary of available server commands or help on specific command.

        Args:
            what: specific command
            flag_docstrings: whether to include docstrings in help data
            refilter: regular expression. If passed, will filter commands containing this expression
            fav: favourites list
            favonly: flag, whether to include only favourite items

        Returns:
            serverlib.HelpData or serverlib.HelpItem
        """
        if what is None:
            helpdata = _api.make_helpdata(title=self.master.subappname,
                                          description=self.master.description,
                                          cmd=self.master.cmd,
                                          flag_protected=True,
                                          flag_docstrings=flag_docstrings,
                                          refilter=refilter,
                                          fav=fav,
                                          favonly=favonly)
            return helpdata
        else:
            if what not in self.master.metacommands:
                raise ValueError("Invalid method: '{}'".format(what))
            helpitem = _api.make_helpitem(self.master.metacommands[what], True, fav)
            return helpitem

    @is_command
    async def s_ping(self):
        """Returns "pong"."""
        return "pong"

    @is_command
    async def s_stop(self):
        """Stops server. """
        self.master.stop()
        return "As you wish."

    @is_command
    async def s_wake_up(self, sleepername=None):
        """Gently wakes up all sleepers or given sleeper."""
        self.master.wake_up(sleepername)

    # Creating sleepers from the client has no practical use. This command was created for debugging purpose.
    # Maybe clean up when this topic is definitely finished.
    # This sleepers thing started as a humorous exercise to understand task cancellation and ended up somewhat serious
    @is_command
    async def s_create_sleeper(self, seconds, name=None):
        """Creates sleeper that sleeps seconds. Just for debugging."""
        seconds = float(seconds)
        asyncio.create_task(self.master.sleep(float(seconds), name))

    @is_command
    async def s_getd_sleepers(self):
        """Reports server sleepers as a list of dicts."""
        ret = [{"name": sleeper.name, "seconds": sleeper.seconds} for sleeper in self.master.sleepers.values()]
        return ret

    @is_command
    async def s_getd_loops(self):
        """Reports server loops as a list of dicts."""
        ret = [loopdata.to_dict() for loopdata in self.master.loops]
        return ret

    @is_command
    async def s_getd_lowstate(self):
        """Returns serverlib's "lowstate" for server

        As opposed to client-side "getd_lowstate()"
        """
        return sl.lowstate.__dict__

    @is_command
    async def s_getd_cfg(self):
        return sl.cfg2dict(self.cfg)

    @is_command
    async def s_getd_all(self):
        """Returns dict containing all configurations and states"""

        cmd = list(self.master.cmd.keys())

        ret = {"serverlib.config": sl.cfg2dict(sl.config),
               "serverlib.lowstate": sl.cfg2dict(sl.lowstate),
               "cfg": await self.s_getd_cfg(),
               "loops": await self.s_getd_loops(),
               "sleepers": await self.s_getd_sleepers(),
               "cmd": cmd}
        await self.master._do_getd_all(ret)
        await self.master._on_getd_all(ret)
        return ret