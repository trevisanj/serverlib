import zmq, zmq.asyncio, pickle, a107, serverlib as sl

__all__ = ["Client"]

TIMEOUT = 30000  # miliseconds to wait until server replies

class Client(sl.Console):
    """Client class."""

    @property
    def socket(self):
        if self.__ctx is None:
            self.__make_context()
        if self.__socket is None:
            self.__make_socket()
        return self.__socket

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__ctx, self.__socket = None, None

    # INTERFACE

    async def connect(self):
        await self._assure_initialized()
        _ = self.socket

    async def execute_client(self, statement, *args, **kwargs):
        """Executes statement; tries special, then client-side."""
        await self._assure_initialized()
        self._parse_statement(statement, args, kwargs)
        return await sl.Console._do_execute(self)

    async def execute_server(self, statement, *args, **kwargs):
        """Executes statement directly on the server."""
        assert isinstance(statement, str)
        await self._assure_initialized()
        self._parse_statement(statement, args, kwargs)
        return await self.__execute_server()
    
    async def execute_bytes(self, bst):
        """Sents statement to server, receives reply, unpickles and returns.

        Args:
            bst: bytes in the form "<command> <data>".

        Returns:
            ret: either result or exception raised on the server (does not raise)
        """

        def process_result(b):
            ret = pickle.loads(b)
            if isinstance(ret, Exception):
                ret.from_server = True
                raise ret
            return ret

        await self._assure_initialized()
        try:
            await self.socket.send(bst)
            b = await self.socket.recv()
        except zmq.Again as e:
            # Will re-create socket in case of timeout
            # https://stackoverflow.com/questions/41009900/python-zmq-operation-cannot-be-accomplished-in-current-state

            # TODO this doesn't seem right: it is just zmq.Again, man
            self.__del_socket()
            raise sl.Retry(a107.str_exc(e))
        ret = process_result(b)
        return ret

    # OVERRIDEN

    async def _get_prompt(self):
        if self.cfg.flag_ownidentity:
            return await super()._get_prompt()
        return await self.execute_server("_get_prompt")

    async def _get_welcome(self):
        if self.cfg.flag_ownidentity:
            return await super()._get_welcome()
        return await self.execute_server("_get_welcome")

    async def _do_close(self):
        if self.__socket is not None:
            self.__del_socket()
            self.__ctx.destroy()
            sl.lowstate.numcontexts -= 1

    async def _do_execute(self):
        flag_try_server = False
        try:
            ret = await super()._do_execute()
        except sl.NotAClientCommand:
            # Note: I don't want to raise another exception inside here; that's why I use this flag instead
            flag_try_server = True
        if flag_try_server:
            ret = await self.__execute_server()
        return ret

    async def _do_help(self, refilter=None):
        helpdata_server = await self.execute_server("_help", refilter=refilter)
        cfg = self.cfg
        helpdata = sl.make_helpdata(title=cfg.subappname,
                                    description=cfg.description,
                                    cmd=self.cmd,
                                    flag_protected=True,
                                    refilter=refilter)
        specialgroup = await self._get_help_specialgroup()
        helpdata.groups = [specialgroup]+helpdata.groups+helpdata_server.groups
        if not self.cfg.flag_ownidentity:
            helpdata.title = helpdata_server.title
            helpdata.description = helpdata_server.description
        text = sl.make_text(helpdata)
        return text


    async def _do_help_what(self, commandname):
        try:
            return await super()._do_help_what(commandname)
        except sl.NotAClientCommand:
            return await self.execute_server("_help", commandname)

    # PRIVATE

    def __make_socket(self):
        self.__del_socket()
        self.__socket = self.__ctx.socket(zmq.REQ)
        sl.lowstate.numsockets += 1
        self.__socket.setsockopt(zmq.SNDTIMEO, TIMEOUT)
        self.__socket.setsockopt(zmq.RCVTIMEO, TIMEOUT)
        print(f"Connecting {self.name}, ``{self.cfg.subappname}(client)'', to {self.cfg.url} ...")
        self.__socket.connect(self.cfg.url)

    def __make_context(self):
        self.__ctx = zmq.asyncio.Context()
        sl.lowstate.numcontexts += 1

    async def __execute_server(self):
        data = self._statementdata
        bst = data.commandname.encode()+b" "+pickle.dumps([data.args, data.kwargs])
        return await self.execute_bytes(bst)

    def __del_socket(self):
        if self.__socket is not None:
            try:
                self.__socket.setsockopt(zmq.LINGER, 0)
                self.__socket.close()
                sl.lowstate.numsockets -= 1
            except zmq.ZMQError as e:
                raise
            self.__socket = None
