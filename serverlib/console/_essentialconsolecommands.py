__all__ = ["EssentialConsoleCommands"]

import serverlib as sl


class EssentialConsoleCommands(sl.ConsoleCommands):
    @sl.is_command
    async def help(self, what=None, favonly=False):
        """Gets general help or help on specific command."""
        return await self.master.help(what, favonly)

    @sl.is_command
    async def favhelp(self, what=None, favonly=False):
        """Equivalent to "help favonly=True"."""
        return await self.help(favonly=True)

    @sl.is_command
    async def fav(self, what):
        """Toggles favourite command."""
        fav = self.master.cfg.fav
        what= str(what).lower()
        if what in fav:
            fav.remove(what)
        else:
            fav.append(what)
        self.master.cfg.set("fav", fav)

    @sl.is_command
    async def get_fav(self):
        """Return list of favourite commands."""
        return self.master.cfg.fav

    @sl.is_command
    async def getd_lowstate(self):
        return sl.lowstate.__dict__

