__all__ = ["make_help", "make_helpdata", "HelpData", "HelpGroup", "HelpItem", "make_text", "format_method",
           "make_groups", "make_helpitem"]

from dataclasses import dataclass
from typing import *
from colored import fg, bg, attr
import inspect, re, ansiwrap, math, shutil, a107
from . import _misc


# ➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰
# Text-rendering configuration

# Styles
STYLE_TITLE = fg("white")+attr("bold")      # help title
STYLE_DESCRIPTION = fg("yellow")            # help description
STYLE_GROUPTITLE = fg("light_yellow")       # group title
STYLE_NAME = attr("bold")+fg("light_gray")  # method name

# How to distinguish between stared and non-stared methods
# Note: adjuts NOTFAV accordingly depending on the number of columns the FAVSTAR will take to render

# FAVSTAR = attr("blink")+attr("bold")+fg("yellow")+"✺"+attr("reset")
# FAVSTAR = "🌟"
FAVSTAR = "🌊"
ANTIFAV = "❌"
NOTFAV = "  "

# ➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰➰
# Data classes

@dataclass
class HelpItem:
    name: str
    oneliner: str
    signature: inspect.Signature= None
    docstring: str = None
    flag_fav: bool = False
    flag_antifav: bool = False


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
    return (NOTFAV if not helpitem.flag_fav else FAVSTAR)+(NOTFAV if not helpitem.flag_antifav else ANTIFAV)



def make_groups(cmd, flag_protected=True, flag_docstrings=False, refilter=None, fav=None, favonly=False, antifav=None):
    if fav is None:
        fav = []
    if antifav is None:
        antifav = []
    groups = []
    for commands in cmd.values():
        items = []
        meta = _misc.get_metacommands(commands, flag_protected)
        for metacommand in meta:
            # re filter
            if refilter is not None and not re.search(refilter, metacommand.name): continue

            flag_fav = metacommand.name.lower() in fav

            if favonly and not flag_fav:
                continue

            items.append(make_helpitem(metacommand, flag_docstrings, fav, antifav))
        if items:
            groups.append(HelpGroup(commands.title, items))
    return groups


def make_helpitem(metacommand, flag_docstrings, fav, antifav):
    flag_fav = metacommand.name.lower() in fav
    flag_antifav = metacommand.name.lower() in antifav
    return HelpItem(metacommand.name,
                    metacommand.oneliner,
                    inspect.signature(metacommand.method),
                    docstring=None if not flag_docstrings else metacommand.method.__doc__,
                    flag_fav=flag_fav,
                    flag_antifav=flag_antifav)


def make_helpdata(title, description, cmd, flag_protected, flag_docstrings=False, refilter=None, fav=None,
                  favonly=False, antifav=None):
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
        antifav: list of antifavourites (command names)

    Returns: a HelpData instance

    """
    groups = make_groups(cmd, flag_protected, flag_docstrings, refilter, fav, favonly, antifav)
    ret = HelpData(title, description, groups)
    return ret


def make_help(title, description, cmd, flag_protected=True, refilter=None, fav=None, antifav=None):
    """Makes help text from Server or Client instance.

    See make_helpdata() for description on parameters
    """
    helpdata = make_helpdata(title, description, cmd, flag_protected, refilter, fav, antifav)
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

    def _format_description(s):
        return f"{STYLE_DESCRIPTION}{s}{attr('reset')}"

    def format_description(s):
        # Returns as list to make it easier to implement text wrapping, if necessary.
        return [_format_description(s)]

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
    if helpdata.description:
        kebab = a107.kebab(helpdata.description, columnwidth, "  ")
        lines.extend([_format_description(line) for line in kebab.split("\n")])
    lines.append("")

    for helpgroup in helpdata.groups:
        if len(helpgroup) == 0: continue
        lines.append(format_grouptitle(helpgroup))
        for helpitem in helpgroup.items:
            lines.append(format_oneliner(helpitem))

    numcolumns = 2

    if numcolumns == 1:
        return "\n".join(lines)

    lines_ = []
    for line in lines:
        wrapped = ansiwrap.wrap(line, columnwidth)
        for wrappedline in wrapped:
            # favourite star discount using length of NOTFAV as reference
            favd = len(NOTFAV)-1 if FAVSTAR in wrappedline else 0
            antifavd = len(NOTFAV)-1 if ANTIFAV in wrappedline else 0
            spaces = " "*(columnwidth-ansiwrap.ansilen(wrappedline)-favd-antifavd)
            lines_.append(wrappedline+spaces)
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
            if i >= n:
                break
        icol += 1

    return "\n".join(_ret)


def format_method(helpitem):
    """Command-specific help."""
    sig = str(helpitem.signature).replace("(", "").replace(")", "").replace(",", "")
    return "{}{}{} {}{}\n\n{}".format(
        favthing(helpitem),
        STYLE_NAME, helpitem.name, sig, attr("reset"),
        helpitem.docstring)
