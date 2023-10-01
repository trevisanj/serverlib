__all__ = ["App", "LocalApp"]

import serverlib as sl
from .._api import WithCfg, WithClosers


class App(WithCfg, WithClosers):
    """Creates object to be used as master when required."""

    def __init__(self, cfg=None, appname=None, logginglevel=None, flag_log_console=None, flag_log_file=None,
                 **kwargs):
        WithClosers.__init__(self)

        if cfg is None:
            class cfg(sl.BaseCfg):
                pass

        vv = locals()
        for name in ["appname", "logginglevel", "flag_log_file", "flag_log_console"]:
            value = vv[name]
            if value:
                setattr(cfg, name, value)

        WithCfg.__init__(self, cfg, **kwargs)

    async def run(self, method, *args, **kwargs):
        """Initializes, calls await method(self, *args, **kwargs) and closes"""
        await self._initialize_closers()
        try:
            await method(self, *args, **kwargs)
        finally:
            await self.close()


class LocalApp(App):
    """Creates object to be used as master when required, using local directory as datadir."""

    def __init__(self, *args, autodir=".", **kwargs):
        super().__init__(*args, autodir=autodir, **kwargs)
