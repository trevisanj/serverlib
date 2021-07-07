__all__ = ["hopo2url", "cfg2str", "cfg2dict", "parse_statement"]

import a107


def hopo2url(hopo, fallbackhost="127.0.0.1"):
    """Resolves (host, port) tuple into URL string."""
    if isinstance(hopo, str):
        # Verifies if it is the case of a port specified as str
        try: hopo = int(hopo)
        except ValueError: pass

    if isinstance(hopo, int):
        # Only port was specified
        host = fallbackhost
        port = hopo
    elif isinstance(hopo, str):
        host = hopo
        port = None
    else:
        host = hopo[0]
        port = int(hopo[1])
    if host is None:
        host = fallbackhost
    h = f"tcp://{host}" if "/" not in host else host
    return h if port is None else f"{h}:{port}"


def cfg2str(cfg, flag_clean=True):
    """Converts config object to string.

    Args:
        cfg:
        flag_clean: if True, skips attributes that do not render nicely, such as "<object object at 0x7f93a4aa6160>"
    """
    l = []
    for attrname in dir(cfg):
        if not attrname.startswith("_"):
            attr = getattr(cfg, attrname)
            s = repr(attr)
            if flag_clean and "object at" in s:
                continue
            if len(s) > 150:
                s = s[:75]+" ... "+s[-75:]

            l.append(f"{attrname}={s}")
    return "\n".join(l)


def cfg2dict(cfg, flag_clean=True):
    """Converts config object to dict.

        Args:
            cfg:
            flag_clean: if True, skips attributes that do not render nicely, such as "<object object at 0x7f93a4aa6160>"
        """
    ret = {}
    for attrname in dir(cfg):
        if not attrname.startswith("_"):
            attr = getattr(cfg, attrname)
            s = repr(attr)
            if flag_clean and s[0] == "<":
                continue
            ret[attrname] = attr

    return ret


def parse_statement(statement, *args_, **kwargs_):
    """Parses statement and returns (commandname, args, kwargs, outputfilename)"""
    outputfilename = None
    try:
        index = statement.index(" ")
    except ValueError:
        commandname, args, kwargs = statement, [], {}
    else:
        commandname = statement[:index]
        args, kwargs = a107.str2args(statement[index+1:])
    if args_: args.extend(args_)
    if kwargs_: kwargs.update(kwargs_)
    if args:
        if isinstance(args[-1], str) and args[-1].startswith(">>>"):
            outputfilename = args.pop()[3:]
    return commandname, args, kwargs, outputfilename