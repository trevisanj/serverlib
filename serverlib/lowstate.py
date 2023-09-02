class lowstate:
    """
    Low-level server state

    Values are accessible through the server command "s_getd_all".
    """

    # Number of ZMQ sockets. DO NOT CHANGE!
    numsockets = 0
    # Number of ZMQ contexts. DO NOT CHANGE!
    numcontexts = 0