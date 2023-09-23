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
    async def fav(self, what=None):
        """Toggles favourite command and returns list

        Args:
            what: name of command to toggle

        Returns:
            ret: list of favourites
        """
        fav = self.master.fav

        if what is not None:
            what = str(what).lower()
            if what in fav:
                fav.remove(what)
            else:
                fav.append(what)
            self.master.fav = fav

        return fav

    @sl.is_command
    async def antifav(self, what=None):
        """Toggles anti-favourite command and returns list

        Args:
            what: name of command to toggle

        Returns:
            ret: list of anti-favourites
        """
        antifav = self.master.antifav

        if what is not None:
            what = str(what).lower()
            if what in antifav:
                antifav.remove(what)
            else:
                antifav.append(what)
            self.master.antifav = antifav

        return antifav
