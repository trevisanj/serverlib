# TODO this could be a package in itself, with option to configure the "power tabulate map"

__all__ = ["print_result"]

import tabulate, a107, serverlib as sl, textwrap, re, pl3
from serverlib.consts import *
from colored import fg, bg, attr


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


def _powertabulate(rows, header, logger=None, *args, **kwargs):
    def get_logger():
        return logger if logger is not None else a107.get_python_logger()

    mymap = [[[i for i, h in enumerate(header) if h in row["fieldnames"]], row["converter"]] for row in
             _powertabulatemap]
    mymap = [row for row in mymap if row[0]]
    if mymap:
        for row in rows:
            for indexes, converter in mymap:
                for i in indexes:
                    try:
                        if row[i] is not None: row[i] = converter(row[i])
                    except Exception as e:
                        get_logger().info(
                            f"Error '{a107.str_exc(e)}' while trying to apply convertion to field '{header[i]}' with value {repr(row[i])}")
                        raise

    return tabulate.tabulate(rows, header, *args, floatfmt="f", **kwargs)


def _detect_girafales(s):
    lines = s.split("\n")
    return any(line.startswith("-") and line.count("-") > len(line)/2 for line in lines)


def print_result(ret, logger=None, flag_colors=True):
    print_tabulated = a107.print_girafales if flag_colors else print

    def print_header(k, level):
        print(attr('bold')+COLOR_HEADER+"\n".join(a107.format_h(level+1, k))+attr("reset"))

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

    def handle_dict(arg, level=0):
        if len(arg) > 0:
            first = next(iter(arg.values()))
            if isinstance(first, dict):
                # dict of dicts: converts key to column
                rows = [[k, *v.values()] for k, v in arg.items()]
                header = ["key", *first.keys()]
                print_tabulated(_powertabulate(rows, header, logger=logger))
            elif isinstance(first, (tuple, list)):
                # dict of lists: prints keys as titles and processes lists
                for i, (k, v) in enumerate(arg.items()):
                    if i > 0: print()
                    print_header(k, level)
                    handle_list(v)
            elif isinstance(first, str) and "\n" in first:
                # dict of strings with more than one line: prints keys as titles and prints strings
                for i, (k, v) in enumerate(arg.items()):
                    if i > 0: print()
                    print_header(k, level)
                    print(v)
            else:
                # "simple dict": 2-column (key, value) tabloe
                rows = [(k, v) for k, v in arg.items()]
                header = ["key", "value"]
                print_tabulated(_powertabulate(rows, header, logger=logger))

        else:
            handle_default(arg)

    def handle_helpdata(arg):
        text = sl.make_text(arg)
        print(text)

    def handle_status(arg):
        print(f"{COLOR_HEADER}Status:{RESET} {a107.fancilyquoted(arg.msg)}")

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
    elif isinstance(ret, sl.HelpData):
        handle_helpdata(ret)
    elif isinstance(ret, sl.Status):
        handle_status(ret)
    else:
        handle_default(ret)
