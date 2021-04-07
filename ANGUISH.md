#20200402
I am not saying the model is bad, but it is so confusing
Why do I need client commands and server commands?
It is because server commands accept any data, not only strings; and client commands are ones that can be typed at the command prompt, that's why.
It is resourceful. If you don't like server commands, just ignore them and implement a client commands layer for each singl server command.
No. If it is not obvious, it is bad. I gotta modify this, turn this into something that can be understood.

commands.send_image --> client.send_message_with_attachments --> servercommands.

I am going to see through this!
This is really important

I am going to build this lib, but pañña is going to be an exception.
I already had this deal with myself, that I would not touch pañña, that it wouldn't use
a lib, OK? OK. It is what it is. It works, why should I break it?
Why do I always struggle between different ways to do things? The great is the enemy of the good 

#20210405
OK, I think I got this working.