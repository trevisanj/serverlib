"""
Basic conversion routines
"""

__all__ = ["hopo2url", "cfg2dict"]


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


def cfg2dict(cfg, flag_clean=True):
    """Converts config object to dict.

        Args:
            cfg:
            flag_clean: if True, skips attributes that do not render nicely, such as "<object object at 0x7f93a4aa6160>"
        """
    ret = {}
    for attrname in dir(cfg):
        if not attrname.startswith("__"):
            attr = getattr(cfg, attrname)
            s = repr(attr)
            if flag_clean and s[0] == "<":
                continue
            ret[attrname] = attr
    return ret
