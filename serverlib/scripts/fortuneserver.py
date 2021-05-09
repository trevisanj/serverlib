#!/usr/bin/env python
import serverlib, a107, argparse, random as ra, textwrap, asyncio
__doc__ = """A fucked-up fortune teller with sentences based on my online therapy sessions at BetterHelp."""


class FortuneCommands(serverlib.ServerCommands):
    async def random_name(self):
        """Generates a random human name."""
        return a107.random_name()

    async def fortune(self):
        """Fucked-up fortune teller."""
        return "\n".join(textwrap.wrap(ra.choice(FORTUNE), 70))

    async def random(self):
        return ra.random()

    random.__doc__ = ra.random.__doc__

    async def randint(self, a, b):
        return ra.randint(int(a), int(b))

    randint.__doc__ = ra.randint.__doc__

    async def choice(self, *args):
        """Returns one of the arguments passed randomly chosen."""
        return ra.choice(args)


def main(args):
    cfg = serverlib.ServerConfig()
    cfg.host = args.host
    cfg.port = args.port
    cfg.flag_log_console = True
    cfg.applicationname = "fortune"
    cfg.description = __doc__
    server = serverlib.Server(cfg, cmd=FortuneCommands())
    asyncio.run(server.run())


FORTUNE = ["Reluctance to say **NO** and establish firm boundaries triggers your feeling overwhelmed. So, fucking learn how to say fucking **NO**.",
           "Sometimes it is easier to leave people without a reply rather than saying **NO** and feeling guilty. Therefore, get your fucking shit together and fucking say **NO** if that's what you want to say. But don't leave people waiting. Don't be a coward. Say what you have to say. Nicely. Gently. Don't be a pussy.",
           "Most people struggle with a fear of missing out (FOMO) at different times. Therefore, take some time to figure out what the fuck you want from your fucking life and do not fucking waste your time fucking praying for good things to happen nor crying because they didn't happen. Just go for what you want.",
           "Social medial like Facebook, Instagram, Twitter, Tinder, Reddit, Snapchat, Tiktok, Youtube, Facebook, Doctoralia, Tinder, Instagram, and others seem to play a role in exacerbating fear of missing out (FOMO) and anxiety. It is worth to delete all your accounts and risk not seeing any other human being ever again rather whan waking up at 3am to check whether your crush has already replied to your filthy and patetic message.",
           "Disable all notifications from all apps on your phone now. Just do it.",
           "Project into the future the feelings you WILL have once the consequences of poor decision-making have come home to roost.",
           "We tend to filter our disadvantages and risks in favor of the potential benefits of our actions. Put the rationality googles on.",
           "Fast forward the DVD of your life and probable scenarios. Take your time.",
           "The idea is to be able to learn communication tactics well enough so you can apply them in the heat of the moment as things come up. Yeah baby, do some low-stakes training if necessary. Actually forget all about training. Just figure out what you really want.",
           "For Obsessive-Compulsive disorder (OCD), Exposure and Response Prevention (ERP) is the gold standard.",
           "People sometimes don't realize that anger is a way by which anxiety or fear is expressed. If you are experiencing anger management problems, apply for a 1-year monastery internship.",
           "Modern brain science tells is that there are 3 common responses to threat that both humans and animals display: fight, fright and social media swiping.",
           "People who have full blown panic attacks are actually experiencing fight or flight responses more or less at random. Thinking of this inspires us to learn how to see the brain as a machine and build up the ways by which this machine will function in our favour despite our screwed-up past, emotional wounds, childhood neglect, abandonment and abuse.",
           "In the long term, avoidance becomes the fuel for anxiety, because then you are living much more in your head and becoming attached to all sorts of thoughts and worries of the imagination. Exposure to the things we fear the most is a critical part of treatment.",
           "You can stand in the side of a pool all day wiring and imagining how cold it is going to be, but only by getting in and splashing around do you realize that the coldness was mostly relative.",
           "Codependency is a complicated concept in mental health having to do with boundaries. Codependents tend to \"take on\" the emotions of others and focus a bit too heavily on pleasing people.",
           ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, help="host", default=None)
    parser.add_argument('port', type=int, help='port', nargs="?", default=6666)

    args = parser.parse_args()
    main(args)
