import zmq, zmq.asyncio, pickle, a107, serverlib as sl, asyncio
from . import _api

__all__ = ["Client"]


class Client(sl.Console):
    """Client class.

    Args:
        timeout: time to wait for server response (seconds)
    """

    whatami = "client"

    @property
    def url(self):
        return sl.hopo2url((self.cfg.host, self.cfg.port))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Temporary timeout (seconds) to be used only once when server command is executed
        # It is reset by any of the execute*() methods
        self.temporarytimeout = None

        self.__ctx, self.__socket = None, None

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTERFACE

    # async def connect(self):
    #     await self._assure_initialized()
    #     self.__assure_socket()

    async def execute(self, *args, **kwargs):
        try:
            return await super().execute(*args, **kwargs)
        finally:
            self.temporarytimeout = None

    async def execute_client(self, statement, *args, **kwargs):
        """Executes statement; tries special, then client-side."""
        try:
            await self._assure_initialized()
            self._parse_statement(statement, args, kwargs)
            return await self._execute_console()
        finally:
            self.temporarytimeout = None

    async def execute_server(self, statement, *args, **kwargs):
        """Executes statement directly on the server."""
        if not isinstance(statement, str):
            raise TypeError(f"I need str, not {statement.__class__.__name__}")
        try:
            await self._assure_initialized()
            self._parse_statement(statement, args, kwargs)
            return await self.__execute_server()

        finally:
            self.temporarytimeout = None

    async def execute_bytes(self, bst):
        """Sents statement to server, receives reply, unpickles and returns.

        Args:
            bst: bytes in the form "<command> <data>".

        Returns:
            ret: either result or exception raised on the server (does not raise)
        """
        try:
            await self._assure_initialized()
            return await self.__execute_bytes(bst)
        finally:
            self.temporarytimeout = None

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # OVERRIDEN

    async def _initialize_client(self):
        self.__assure_socket()
        server_subappname = await self._get_server_subappname()

        # client and server subappname must match
        if self.subappname != server_subappname:
            raise sl.MismatchError(f'Client x Server subappname mismatch '
                                   f'(\'{self.subappname}\' x \'{server_subappname}\')')

    async def _get_server_subappname(self):
        srvcfg = await self.__execute_server_no_init("getd_cfg")
        ret = srvcfg["_subappname"]
        if ret is None:
            ret = srvcfg["_appname"]
        return ret

    async def _get_prompt(self):
        return await self._get_server_subappname()

    async def _get_welcome(self):
        return await self.execute_server("get_welcome")

    async def _do_close(self):
        if self.__socket is not None:
            self.__del_socket()
            self.__ctx.destroy()
            sl.lowstate.numcontexts -= 1

    async def _do_execute(self):
        flag_try_server = False
        try:
            ret = await super()._do_execute()
        except sl.NotAConsoleCommand:
            # Note: I don't want to raise another exception inside here; that's why I use this flag instead
            flag_try_server = True
        if flag_try_server:
            ret = await self.__execute_server()
        return ret

    async def _do_help(self, refilter=None, fav=None, favonly=None):
        helpdata_server = await self.execute_server("s_help", refilter=refilter, fav=fav, favonly=favonly)
        helpdata = _api.make_helpdata(title=self.subappname,
                                      description=self.description,
                                      cmd=self.cmd,
                                      flag_protected=True,
                                      refilter=refilter,
                                      fav=fav,
                                      favonly=favonly)
        helpdata.groups = helpdata.groups+helpdata_server.groups
        if not refilter and not favonly:
            specialgroup = await self._get_help_specialgroup()
            helpdata.groups = [specialgroup]+helpdata.groups
        helpdata.title = helpdata_server.title
        helpdata.description = helpdata_server.description
        text = _api.make_text(helpdata)
        return text


    async def _do_help_what(self, commandname):
        try:
            return await super()._do_help_what(commandname)
        except sl.NotAConsoleCommand:
            # Note: it is not the best way to send the list of favourites to the server ... but whatever
            return _api.format_method(await self.execute_server("s_help", commandname, fav=self.fav))

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PRIVATE

    def __make_socket(self):
        self.__del_socket()
        self.__socket = self.__ctx.socket(zmq.REQ)
        sl.lowstate.numsockets += 1
        self.__set_timeout(self.cfg.timeout)
        self.logger.info(f"Connecting {self.name}, ``{self.subappname}(client)'', to {self.url} ...")
        self.__socket.connect(self.url)

    def __set_timeout(self, timeout):
        zmqtimeout = int(timeout*1000)  # ZMQ needs timeout in milliseconds
        self.__assure_socket()
        self.__socket.setsockopt(zmq.SNDTIMEO, zmqtimeout)
        self.__socket.setsockopt(zmq.RCVTIMEO, zmqtimeout)

    def __make_context(self):
        self.__ctx = zmq.asyncio.Context()
        sl.lowstate.numcontexts += 1

    def __assure_socket(self):
        if self.__ctx is None:
            self.__make_context()
        if self.__socket is None:
            self.__make_socket()

    async def __execute_server_no_init(self, statement, *args, **kwargs):
        """Executes command on server without initialization check."""
        self._parse_statement(statement, args, kwargs)
        return await self.__execute_server()

    async def __execute_server(self):
        data = self._statementdata
        bst = data.commandname.encode()+b" "+pickle.dumps([data.args, data.kwargs])
        i = 0
        while True:
            try:
                return await self.__execute_bytes(bst)
            except sl.Retry as e:
                i += 1
                if i == self.cfg.maxtries:
                    raise

                waittime = e.waittime if e.waittime is not None else self.cfg.waittime_retry_command
                self.logger.error(f"Error executing statement '{data.commandname}': {a107.str_exc(e)} "
                                  f"(attempt {i}/{self.cfg.maxtries}) (will retry in {waittime} seconds)")
                await asyncio.sleep(waittime)

    async def __execute_bytes(self, bst):
        def process_result(b):
            ret = pickle.loads(b)
            if isinstance(ret, BaseException):
                ret.from_server = True
                raise ret
            return ret

        flag_temporarytimeout = self.temporarytimeout is not None
        try:
            if flag_temporarytimeout:
                self.__set_timeout(self.temporarytimeout)
            socket = self.__get_socket()
            await socket.send(bst)
            b = await socket.recv()
        except zmq.Again as e:
            raise sl.Retry(a107.str_exc(e))
        except zmq.ZMQError as e:
            # 20210912 This makes more sense, i.e., deleting the socket only after ruling out less serious situations
            self.__del_socket()
            raise sl.Retry(a107.str_exc(e))
        finally:
            if flag_temporarytimeout:
                self.__set_timeout(self.cfg.timeout)

        ret = process_result(b)
        return ret

    def __del_socket(self):
        if self.__socket is not None:
            try:
                self.__socket.setsockopt(zmq.LINGER, 0)
                self.__socket.close()
                sl.lowstate.numsockets -= 1
            except zmq.ZMQError as e:
                raise
            except:
                raise
            self.__socket = None

    def __get_socket(self):
        self.__assure_socket()
        return self.__socket
