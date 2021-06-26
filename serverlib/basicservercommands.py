import serverlib as sl, asyncio
__all__ = ["BasicServerCommands"]


class BasicServerCommands(sl.ServerCommands):
    async def _help(self, what=None):
        """Gets summary of available server commands or help on specific command.

        This command was made protected to make the point that "?" is the preferred way to get help at the client side.
        """
        if what is None:
            cfg = self.master.cfg
            # text = sl.make_help(title=cfg.prefix,
            #                     description=cfg.description,
            #                     cmd=self.master.cmd, flag_protected=True)
            # return text
            helpdata = sl.make_helpdata(title=cfg.prefix,
                                        description=cfg.description,
                                        cmd=self.master.cmd, flag_protected=True)
            return helpdata
        else:
            if what not in self.master.metacommands:
                raise ValueError("Invalid method: '{}'".format(what))
            return sl.format_method(self.master.metacommands[what].method)

    async def ping(self):
        """Returns "pong"."""
        return "pong"

    async def _stop(self):
        """Stops server. """
        self.master.stop()
        return "As you wish."

    async def _get_configuration(self):
        """Returns dict containing configuration information.

        Returns:
            {script_name0: filepath0, ...}
        """
        return await self.master.get_configuration()

    async def _wake_up(self, sleepername=None):
        """Gently wakes up all sleepers or given sleeper."""
        self.master.wake_up(sleepername)

    async def _sleepers(self):
        """Reports server sleepers as a list of dicts."""
        ret = [{"name": sleeper.name, "seconds": sleeper.seconds} for sleeper in self.master.sleepers.values()]
        return ret

    # Creating sleepers from the client has no practical use. This command was created for debugging purpose.
    # Maybe clean up when this topic is definitely finished.
    # This sleepers thing started as a humorous exercise to understand task cancellation and ended up somewhat serious
    async def _create_sleeper(self, seconds, name=None):
        """Creates sleeper that sleeps seconds. Just for debugging."""
        seconds = float(seconds)
        asyncio.create_task(self.master.sleep(float(seconds), name))

    async def _loops(self):
        """Reports server loops as a list of dicts."""
        ret = []
        for name, task in self.master.lo_ops.items():
            ret.append({"name": name,
                        "status": "pending" if not task.done() else "cancelled" if task.cancelled() else "finished",
                        "marked": task.marked,
                        "errormessage": task.errormessage,
                        })
        return ret
