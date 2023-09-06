# TODO this could be a package in itself, with option to configure the "power tabulate map"

__all__ = ["print_result", "result2str"]

import tabulate, a107, textwrap, re, pl3, io
from serverlib.config import *
from colored import fg, bg, attr
from contextlib import redirect_stdout
import serverlib as sl


def print_result(ret, logger, flag_colors=True):
    from ._api import helpmaking

    print_tabulated = a107.print_girafales if flag_colors else print

    def handle_all(ret, level=0):

        def print_header(k):
            print(format_header(k))

        def format_header(k):
            return ((attr("bold") + config.colors.header if flag_colors else "") +
                    "\n".join(a107.format_h(level + 1, k)) +
                    (attr("reset") if flag_colors else ""))

        def handle_list(arg):
            if len(arg) > 0:
                if isinstance(arg[0], dict):
                    excluded = ("info",)
                    header = [k for k in arg[0].keys() if k not in excluded]
                    rows = [[v for k, v in row.items() if k not in excluded] for row in arg]
                    print_tabulated(_powertabulate(rows, header))
                else:
                    print("\n".join([str(x) for x in arg]))  # Experimental: join list elements with "\n"
            else:
                handle_default(arg)

        def handle_dict(arg):
            if len(arg) > 0:
                # 20230827 Limiting recursive resolution to first level
                if level == 0 and any(isinstance(x, (tuple, list, dict)) for x in arg.values()):
                    # complex values: prints keys as titles and processes values
                    for i, (k, v) in enumerate(arg.items()):
                        if i > 0:
                            print()
                        print_header(k)
                        handle_all(v, level+1)
                else:
                    first = next(iter(arg.values()))
                    if isinstance(first, str) and "\n" in first:
                        # dict of strings with more than one line: prints keys as titles and prints strings
                        for i, (k, v) in enumerate(arg.items()):
                            if i > 0:
                                print()
                            print_header(k)
                            print(v)
                    else:
                        # "simple dict": 2-column (key, value) table
                        rows = [(k, v) for k, v in arg.items()]
                        header = ["key", "value"]
                        print_tabulated(_powertabulate(rows, header, logger=logger))

            else:
                handle_default(arg)

        def handle_helpdata(arg):
            text = helpmaking.make_text(arg)
            print(text)

        def handle_status(arg):
            msg = arg.msg if not isinstance(arg.msg, (list, tuple)) else "\n".join(arg.msg)
            if msg:
                print(f"{format_header('Status:')} {a107.fancilyquoted(msg)}")
            handle_all(arg.ret, level+1)

        def handle_default(arg):
            if not isinstance(arg, str): arg = str(arg)
            if "\n" in arg:
                if _detect_girafales(arg):
                    print_tabulated(arg)
                else:
                    print(arg)
            else:
                arg = re.sub(r'\s+', ' ', arg)
                print("\n".join(textwrap.wrap(arg, 80)))

        if isinstance(ret, str):
            print(ret)

        elif isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[0], list) and isinstance(ret[1], list):
            # Tries to detect "tabulate-like" (rows, headers) arguments
            print_tabulated(_powertabulate(*ret))
        elif isinstance(ret, list):
            handle_list(ret)
        elif isinstance(ret, dict):
            handle_dict(ret)
        elif isinstance(ret, helpmaking.HelpData):
            handle_helpdata(ret)
        elif isinstance(ret, sl.Status):
            handle_status(ret)
        else:
            handle_default(ret)

    handle_all(ret, 0)


def result2str(ret, logger, flag_colors=True):
    """Captures print_result() output to redirect it to a string.

    See print_results() for arguments.

    References:
        [1] https://stackoverflow.com/questions/1218933/can-i-redirect-the-stdout-into-some-sort-of-string-buffer
    """
    with io.StringIO() as buf, redirect_stdout(buf):
        print_result(ret, logger, flag_colors)
        output = buf.getvalue()
    return output


_powertabulatemap = [
    {"fieldnames": ("whenthis", "ts", "ts0", "ts1", "lasttime", "nexttime", "whenthisenter", "whenthisexit"),
     "converter": lambda x: a107.dt2str(a107.to_datetime(x)), },
    # "converter": lambda x: a107.ts2str(x, tz=a107.utc)},
    {"fieldnames": ("period",),
     "converter": pl3.QP.to_str},
    {"fieldnames": ("error", "lasterror",),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 50))},
    {"fieldnames": ("narration",),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 50))},
]


def _powertabulate(rows, header, logger, *args, **kwargs):

    mymap = [[[i for i, h in enumerate(header) if h in row["fieldnames"]], row["converter"]] for row in
             _powertabulatemap]
    mymap = [row for row in mymap if row[0]]
    if mymap:
        for row in rows:
            for indexes, converter in mymap:
                for i in indexes:
                    try:
                        if row[i] is not None: row[i] = converter(row[i])
                    except BaseException as e:
                        logger().error(f"Error '{a107.str_exc(e)}' while trying to apply convertion to field "
                                      f"'{header[i]}' with value {repr(row[i])}")
                        raise

    return tabulate.tabulate(rows, header, *args, floatfmt="f", **kwargs)


def _detect_girafales(s):
    lines = s.split("\n")
    return any(line.startswith("-") and line.count("-") > len(line)/2 for line in lines)
