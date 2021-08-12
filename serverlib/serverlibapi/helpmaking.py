__all__ = ["make_help", "make_helpdata", "HelpData", "HelpGroup", "HelpItem", "make_text", "format_method",
           "make_groups"]

from dataclasses import dataclass
from typing import *
from colored import fg, bg, attr
import inspect, re
from .metacommand import *


# Styles
STYLE_TITLE = fg("white")+attr("bold")      # help title
STYLE_DESCRIPTION = fg("yellow")            # help description
STYLE_GROUPTITLE = fg("light_yellow")       # group title
STYLE_NAME = attr("bold")+fg("light_gray")  # method name


@dataclass
class HelpItem:
    name: str
    oneliner: str
    signature: inspect.Signature = None
    docstring: str = None


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


def make_groups(cmd, flag_protected=True, flag_docstrings=False, refilter=None):
    groups = []
    for commands in cmd.values():
        items = []
        meta = commands.get_meta(flag_protected)
        for metacommand in meta:
            # re filter
            if refilter is not None and not re.search(refilter, metacommand.name): continue

            items.append(HelpItem(metacommand.name,
                                  metacommand.oneliner,
                                  inspect.signature(metacommand.method),
                                  docstring=None if not flag_docstrings else metacommand.method.__doc__))
        if items: groups.append(HelpGroup(commands.title, items))
    return groups


def make_helpdata(title, description, cmd, flag_protected, flag_docstrings=False, refilter=None):
    """Assembles HelpData object from Server or Client instance.

    Args:
        title: help title
        description: help description
        cmd: {name: Commands, ...}  (name not used)
        flag_protected: whether to include protected methods in help
        flag_docstrings: whether to include docstrings in help data
        refilter: regular expression. If passed, will filter commands containing this expression

    Returns: a HelpData instance

    """
    groups = make_groups(cmd, flag_protected, flag_docstrings, refilter)
    ret = HelpData(title, description, groups)
    return ret


def make_help(title, description, cmd, flag_protected=True, refilter=None):
    """Makes help text from Server or Client instance.

    See make_helpdata() for description on parameters
    """
    helpdata = make_helpdata(title, description, cmd, flag_protected, refilter)
    text = make_text(helpdata)
    return text


def make_text(helpdata):
    def format_title(helpdata):
        return [f"{STYLE_TITLE}{helpdata.title}",
                "="*len(helpdata.title)+attr("reset")]
    def format_description(s):
        # Returns as list to make it easier to implement text wrapping, if necessary.
        return [f"{STYLE_DESCRIPTION}{s}{attr('reset')}"]

    def format_grouptitle(group):
        return f"{STYLE_GROUPTITLE}{group.title}{attr('reset')}"

    def format_oneliner(helpitem):
        return f"{STYLE_NAME}{helpitem.name:>{methodlen}}{attr('reset')} -- {helpitem.oneliner}"

    methodlen = max([max([len(item.name) for item in helpgroup.items]) for helpgroup in helpdata.groups if len(helpgroup) > 0])

    lines = format_title(helpdata)
    if helpdata.description: lines.extend(format_description(helpdata.description))
    lines.append("")

    for helpgroup in helpdata.groups:
        if len(helpgroup) == 0: continue
        lines.append(format_grouptitle(helpgroup))
        for helpitem in helpgroup.items:
            lines.append(format_oneliner(helpitem))

    return "\n".join(lines)


def format_method(method):
    """Command-specific help."""
    sig = str(inspect.signature(method)).replace("(", "").replace(")", "").replace(",", "")
    return "{}{} {}{}\n\n{}".format(STYLE_NAME, method.__name__, sig, attr("reset"), method.__doc__)
