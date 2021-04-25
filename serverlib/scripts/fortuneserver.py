#!/usr/bin/env python
import serverlib, a107, argparse, random as ra, textwrap, asyncio
__doc__ = """Random Utilities Server

This server will provide you some words of wisdom + some stupid bonus features."""


class FortuneCommands(serverlib.ServerCommands):
    name = "fortune"
    async def random_name(self):
        """Generates a random human name."""
        return a107.random_name()

    async def fortune(self):
        """Fortune teller for the codependent."""
        return "\n".join(textwrap.wrap(ra.choice(FORTUNE), 70))

    async def random(self):
        return ra.random()

    random.__doc__ = ra.random.__doc__

    async def randint(self, a, b):
        return ra.randint(int(a), int(b))

    randint.__doc__ = ra.randint.__doc__

    async def choice(self, bargs):
        """Returns one of the arguments passed randomly chosen."""

        return ra.choice(self.to_list(bargs))


def main(args):
    cfg = serverlib.ServerConfig()
    cfg.host = args.host
    cfg.port = args.port
    cfg.flag_log_console = True
    cfg.applicationname = "fortune"
    cfg.description = __doc__
    server = serverlib.Server(cfg, cmd=FortuneCommands())
    asyncio.run(server.run())


FORTUNE = ["Reluctance to say no and establish firm boundaries triggers your feeling overwhelmed.",
           "Sometimes it is easier to leave people without a reply rather than saying no and feeling guilty.",
           "Most people struggle with a fear of missing out (FOMO) at different times.",
           "Social medial like Facebook seems to play a role in exacerbating fear of missing out (FOMO) and anxiety.",
           "Disable all notifications from all apps on your phone now.",
           "For impulsivity, it is usually recommended to project into the future the feelings you WILL have once the consequences of poor decision-making have come home to roost.",
           "We tend to filter our disadvantages and risks in favor of the potential benefits of our actions.",
           "Fast forward the DVD of your life and probable scenarios.",
           "The idea is to be able to learn communication tactics well enough so you can apply them in the heat of the moment as things come up.",
           "For Obsessive-Compulsive disorder (OCD), Exposure and Response Prevention (ERP) is the gold standard.",
           "People sometimes don't realize that anger is a way by which anxiety or fear is expressed.",
           "Identifying what the primary emotion is and what triggers that is a big part of recovery.",
           "Modern brain science tells is that there are 3 common responses to threat that both humans and animals display.",
           "People who have full blown panic attacks are actually experiencing this fight or flight response more or less at random.",
           "In the long term, avoidance becomes the fuel for anxiety, because then you are living much more in your head and becoming attached to all sorts of thoughts and worries of the imagination.",
           "Exposure to the things we fear the most is a critical part of treatment.",
           "You can stand in the side of a pool all day wiring and imagining how cold it is going to be, but only by getting in and splashing around do you realize that the coldness was mostly relative.",
           "Codependency is a complicated concept in mental health having to do with boundaries.",
           "Codependents tend to \"take on\" the emotions of others and focus a bit too heavily on pleasing people.",
           ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, help="host", default=None)
    parser.add_argument('port', type=int, help='port', nargs="?", default=6666)

    args = parser.parse_args()
    main(args)
