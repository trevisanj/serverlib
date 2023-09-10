__all__ = ["make_help", "make_helpdata", "HelpData", "HelpGroup", "HelpItem", "make_text", "format_method",
           "make_groups", "make_helpitem"]

from dataclasses import dataclass
from typing import *
from colored import fg, bg, attr
import inspect, re, ansiwrap, math, shutil
from . import _misc


# ➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰
# Text-rendering configuration

# Styles
STYLE_TITLE = fg("white")+attr("bold")      # help title
STYLE_DESCRIPTION = fg("yellow")            # help description
STYLE_GROUPTITLE = fg("light_yellow")       # group title
STYLE_NAME = attr("bold")+fg("light_gray")  # method name

# How to distinguish between stared and non-stared methods
FAVSTAR = attr("blink")+attr("bold")+fg("white")+"✺"+attr("reset")
# FAVSTAR = "🌟"
NOTFAV = " "

# ➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰
# Data classes

@dataclass
class HelpItem:
    name: str
    oneliner: str
    signature: inspect.Signature= None
    docstring: str = None
    flag_fav: bool = False


@dataclass
class HelpGroup:
    title: str
    items: List[HelpItem]

    def __len__(self):
        return len(self.items)


@dataclass
class HelpData:
    title: str
    description: str
    groups: List[HelpGroup]


# ➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰
# Actions


def favthing(helpitem):
    """Returns text identifying method as favourite of else empty space(s) of same length."""
    return NOTFAV if not helpitem.flag_fav else FAVSTAR


def make_groups(cmd, flag_protected=True, flag_docstrings=False, refilter=None, fav=None, favonly=False):
    if fav is None: fav = []
    groups = []
    for commands in cmd.values():
        items = []
        meta = _misc.get_metacommands(commands, flag_protected)
        for metacommand in meta:
            # re filter
            if refilter is not None and not re.search(refilter, metacommand.name): continue

            flag_fav = metacommand.name.lower() in fav

            if favonly and not flag_fav: continue

            items.append(make_helpitem(metacommand, flag_docstrings, fav))
        if items: groups.append(HelpGroup(commands.title, items))
    return groups


def make_helpitem(metacommand, flag_docstrings, fav):
    flag_fav = metacommand.name.lower() in fav
    return HelpItem(metacommand.name,
                    metacommand.oneliner,
                    inspect.signature(metacommand.method),
                    docstring=None if not flag_docstrings else metacommand.method.__doc__,
                    flag_fav=flag_fav)


def make_helpdata(title, description, cmd, flag_protected, flag_docstrings=False, refilter=None, fav=None,
                  favonly=False):
    """Assembles HelpData object from Server or Client instance.

    Args:
        title: help title
        description: help description
        cmd: {name: Commands, ...}  (name not used)
        flag_protected: whether to include protected methods in help
        flag_docstrings: whether to include docstrings in help data
        refilter: regular expression. If passed, will filter commands containing this expression
        fav: list of favourites (command names)
        favonly: flag, whether to include only favourite items

    Returns: a HelpData instance

    """
    groups = make_groups(cmd, flag_protected, flag_docstrings, refilter, fav, favonly)
    ret = HelpData(title, description, groups)
    return ret


def make_help(title, description, cmd, flag_protected=True, refilter=None, fav=None):
    """Makes help text from Server or Client instance.

    See make_helpdata() for description on parameters
    """
    helpdata = make_helpdata(title, description, cmd, flag_protected, refilter, fav)
    text = make_text(helpdata)
    return text


def make_text(helpdata, numcolumns=None, preferredcolumnwidth=90, spacer=" | "):
    """
    Creates help text (string)

    Args:
        helpdata: HelpData object
        numcolumns: if not specified, automatic
        preferredcolumnwidth:
        spacer: column spacer
    """
    def format_title(helpdata):
        return [f"{STYLE_TITLE}{helpdata.title}",
                "="*len(helpdata.title)+attr("reset")]
    def format_description(s):
        # Returns as list to make it easier to implement text wrapping, if necessary.
        return [f"{STYLE_DESCRIPTION}{s}{attr('reset')}"]

    def format_grouptitle(group):
        return f"{STYLE_GROUPTITLE}{group.title}{attr('reset')}"

    def format_oneliner(helpitem):
        return f"{favthing(helpitem)}{STYLE_NAME}{helpitem.name:>{methodlen}}{attr('reset')} -- {helpitem.oneliner}"

    terminalwidth = shutil.get_terminal_size()[0]
    if numcolumns is None:
        s = len(spacer)
        ROUNDBREAK = 2  # will make 2.6 round to 2, not to 3 etc.
        numcolumns = max(1, int(round((terminalwidth+s)/(preferredcolumnwidth+s)*ROUNDBREAK)/ROUNDBREAK))
    columnwidth = int((terminalwidth+s*(1-numcolumns))/numcolumns)

    methodlen = max([max([len(item.name) for item in helpgroup.items]+[0]) for helpgroup in helpdata.groups if len(helpgroup) > 0]+[0])

    lines = format_title(helpdata)
    if helpdata.description: lines.extend(format_description(helpdata.description))
    lines.append("")

    for helpgroup in helpdata.groups:
        if len(helpgroup) == 0: continue
        lines.append(format_grouptitle(helpgroup))
        for helpitem in helpgroup.items:
            lines.append(format_oneliner(helpitem))

    if numcolumns == 1:
        return "\n".join(lines)

    lines_ = []
    for line in lines:
        wrapped = ansiwrap.wrap(line, columnwidth)
        for wrappedline in wrapped:
            lines_.append(wrappedline+" "*(columnwidth-ansiwrap.ansilen(wrappedline)))
    n = len(lines_)
    numrows = math.ceil(n/numcolumns)
    i = 0
    _ret = [""]*numrows
    icol = 0
    while i <= n-1:
        spacer_ = spacer if icol > 0 else ""
        for j in range(numrows):
            _ret[j] += spacer_+lines_[i]
            i += 1
            if i >= n: break
        icol += 1

    return "\n".join(_ret)


def format_method(helpitem):
    """Command-specific help."""
    sig = str(helpitem.signature).replace("(", "").replace(")", "").replace(",", "")
    return "{}{}{} {}{}\n\n{}".format(
        favthing(helpitem),
        STYLE_NAME, helpitem.name, sig, attr("reset"),
        helpitem.docstring)
