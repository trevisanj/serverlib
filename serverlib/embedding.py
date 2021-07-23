"""Allows embedding an IPython inside the program as a working console or client.

This code is based on a107.console and replaces it.
"""

__all__ = ["embed_ipython"]

import a107, signal, inspect, serverlib as sl


async def embed_ipython(console, globalsdict, colors="linux", flag_close=True):
    """
    Extracts commands to globalsdict and Embeds Ipython
    Args:
        console: serverlib.Console instance
        globalsdict: dictionary obtained (probably in main module) using globals()
        colors: embed() suppresses colors by default, so I implemented this control with a default value
        flag_close: whether to close the console upon exit

    Actions performed:

        - modifies globalsdict to have all commands + a "print_help()" method
        - supresses Ctrl+Z. **You will have to type "exit"**. Don't worry, Yoda will tell you
    """

    from IPython import embed

    async def print_help(command=None):
        """Prints help"""
        print(await console.metacommands["help"].method(command))

    def servercommandfactory(client, methodname, docstring, signature):
        """Returns new callable that can call a server method"""

        # parameters separated by commas for the call inside
        parslist = []
        for name, param in signature.parameters.items():
            if param.kind == inspect._VAR_POSITIONAL:
                name = '*'+name
            elif param.kind == inspect._VAR_KEYWORD:
                name = '**'+name
            else:
                name = f"{name}={name}"
            parslist.append(name)
        commaed = ", ".join(parslist)
        # parameters with default values for the "def" line
        with_defaults = str(signature)[1:-1]  #", ".join([name+("" if param.default == inspect._empty else f"={repr(param.default)}") for name, param in signature.parameters.items()])

        scode = f"""
async def {methodname}({with_defaults}):
    \"\"\"{docstring}\"\"\"
    return await client.execute_server("{methodname}", {commaed})
    """
        code = compile(scode, "mandioca", "exec")
        fakeglobals = {}
        eval(code, {"client": client}, fakeglobals)
        method = fakeglobals[methodname]
        return method

    for metacommand in console.metacommands.values():
        globalsdict[metacommand.name] = metacommand.method

    if isinstance(console, sl.Client):
        serverhelpdata = await console.execute_server("_help", flag_docstrings=True)
        for group in serverhelpdata.groups:
            for item in group.items:
                globalsdict[item.name] = servercommandfactory(console,
                                                              item.name,
                                                              item.oneliner if not item.docstring else item.docstring,
                                                              item.signature)

    def _ctrl_z_handler(signum, frame):
        # this will trigger _atexit()
        print(a107.format_yoda('Press Ctrl+Z do not, type "exit" you must'))

        # atexit.register(on_exit)  # _atexit)
    signal.signal(signal.SIGTSTP, _ctrl_z_handler)

    locals().update(globalsdict)

    del metacommand, globalsdict, servercommandfactory

    # I inspected the source code for embed() and saw that "autoawait" (which I want to be true) is conditioned to
    # the "using" kwarg, which I found to require a module name ar value, so I just did using="asyncio" and now
    # I can call "await xxxxx"
    #
    # The use of nest_asyncio was suggested in https://stackoverflow.com/questions/56415470/calling-ipython-embed-in-asynchronous-code-specifying-the-event-loop
    # This allows me to "await on" before embedding IPython, i.e., can create "async def main(...)", do whatever asynchronous initialization, then embed.
    import nest_asyncio
    nest_asyncio.apply()
    try:
        embed(header=await console._get_welcome(), colors=colors, using="asyncio")
    finally:
        if flag_close:
            await console.close()
