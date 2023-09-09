# serverlib

Client-server skeleton in Python using 0MQ

## Examples

Run ```fortuneserver.py``` and ```fortuneclient.py```

## About Servers

## ```AgentServer```

One task commandds instance will be created for each agent.
So, each task commands object is an isolated environment for its respective agent.
todo (2023-09-04) There is no clear reason for this, so to be revisited.

Each agent executes its task sequentially.

## Naming conventions

  - **variable representing table id** examples: ```taskid```, ```questionid```, ```agentid``` 

## References

ASCII art letters made with http://patorjk.com/software/taag/#p=display&f=Calvin%20S&t=use%20me

```
┌─┐┌┐ ┌─┐┌┬┐┌─┐┌─┐┌─┐┬ ┬┬ ┬┬┌─┬  ┌┬┐┌┐┌┌─┐┌─┐┌─┐ ┬─┐┌─┐┌┬┐┬ ┬┬  ┬┬ ┬─┐ ┬┬ ┬┌─┐
├─┤├┴┐│   ││├┤ ├┤ │ ┬├─┤│ │├┴┐│  │││││││ │├─┘│─┼┐├┬┘└─┐ │ │ │└┐┌┘│││┌┴┬┘└┬┘┌─┘
┴ ┴└─┘└─┘─┴┘└─┘└  └─┘┴ ┴┴└┘┴ ┴┴─┘┴ ┴┘└┘└─┘┴  └─┘└┴└─└─┘ ┴ └─┘ └┘ └┴┘┴ └─ ┴ └─┘
```
