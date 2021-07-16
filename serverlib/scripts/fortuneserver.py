#!/usr/bin/env python
"""A fucked-up fortune teller with sentences based on my online therapy sessions at BetterHelp."""
import serverlib, a107, argparse, random as ra, textwrap, asyncio


class FortuneCommands(serverlib.ServerCommands):
    def __init__(self, *args, **kwargs):

        def genericcommand(topic):
            async def about_topic(self):
                return "\n".join(textwrap.wrap(ra.choice(FORTUNES[topic]), 80))

            about_topic.__doc__ = f"Tells fortune on '{topic}' topic."
            about_topic.__name__ = topic
            bound_method = about_topic.__get__(self, self.__class__)
            ret = bound_method
            return ret


        for topic in FORTUNES.keys():
            method = genericcommand(topic)
            setattr(self, topic, method)

        super().__init__(*args, **kwargs)


def main(args):
    cfg = serverlib.ServerConfig(appname="fortune",
                                 host=args.host,
                                 port=args.port,
                                 flag_log_console=True,
                                 description=__doc__)
    server = serverlib.Server(cfg, cmd=FortuneCommands())
    asyncio.run(server.run())


FORTUNES = {
"counselling": [
    "Reluctance to say **NO** and establish firm boundaries triggers your feeling overwhelmed. So, fucking learn how to say fucking **NO**.",
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
    ],
"programming": [
    "Are you having fun?",
    "Write user code first, as if the API already existed.",
],
"dark": [
    "Just kill yourself, will you?",
    "Did you kill yourself already?",
    "All effort is pointless, since in the end you will just die hitting the curb with your head",
],
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, help="host", default=None)
    parser.add_argument('port', type=int, help='port', nargs="?", default=6666)

    args = parser.parse_args()
    main(args)
