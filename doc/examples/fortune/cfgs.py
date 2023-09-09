import serverlib as sl

@sl.is_app
class server(sl.ServerCfg):
    _appname = "fortune"
    port = 6666

@sl.is_client(server)
class client(sl.ClientCfg):
    pass