# DiscordBotExec
A cool, but likely finicky, exec command for a discord.py-based bot  

## Table of Contents
  [DiscordBotExec](#discordbotexec)  
  - [Features](#features)  
  - [Feature Details](#feature-details)  
    - [Implicit Awaits](#implicit-awaits)  
    - [Interactive Value Display](#interactive-value-display)  
    - [Synch Code Calling Asynch](#synch-code-calling-asynch)  
  - [Command Usage](#command-usage)  
  - [Examples](#examples)  
    - [Basic Call](#basic-call)  
    - [Interactive Interpreter Style Expression Printing](#interactive-interpreter-style-expression-printing)  
    - [Sending A Message Without Await](#sending-a-message-without-await)  
    - [Async Call As Value For Function Argument](#async-call-as-value-for-function-argument)  
  - [Project Layout](#project-layout)  
  - [How To Add To Your Bot](#how-to-add-to-your-bot)  
  - [Bugs](#bugs)  
    - [Exec's](#execs)  
      - [Multiple Execs Block Each Other](#multiple-execs-block-each-other)  
  - [Random Info](#random-info)  
    - ["Why did you do this! Are you some kind of maniac?!"](#why-did-you-do-this-are-you-some-kind-of-maniac)  
    - [Why do awaits cause so much trouble?](#why-do-awaits-cause-so-much-trouble)  
    - ["Is this unique?"](#is-this-unique)  
  
  
## Features
- No need use awaits in your code! ([Example 1](#sending-a-message-without-await), [Example 2](#async-call-as-value-for-function-argument))  
- Displays expression values just like an interactive interpretter! ([Example](#interactive-interpreter-style-expression-printing))  
- Can call async code in synchronous code!!! ([Example](#async-call-as-value-for-function-argument))  
- Barely tested code that uses asyncio internals in ways they never should!  
- BUGS!!! (hopefully not, but who knows)  

## Feature Details
### Implicit Awaits
> Note: This is not accurate when it comes to code in `async def` functions.  
> They will still need awaits in their function body  

This command effectively causes async and sync functions to be treated the same in the passed in code.  
asynchronous code is executed asynchronously so as not to block the rest of the bot, but in such a way that to the passed in code it appears as if it is just another synchronous call.  
This means that you don't have to worry about mixing async and synchronous code. They can both be executed from each other and mixed to your hearts desire.  

### Interactive Value Display
Just like how the Python Interactive Interpreter will display values of expressions and return values that aren't being assigned  
So too will this function.  
Debugging has never been easier! (And with this command, you will likely be doing a lot of it)  

### Synch Code Calling Asynch
I'm sure you have had the struggle where you are trying to interop your bot with a synchronous library and how difficult that is.  
Having that brought over to quick use commands that will likely be used for debugging is annoying and frustrating.  
This command avoids that.  
(To this command, _EVERYTHING_ is synchronous)

## Command Usage
There are a few little things and definitions that are important to know for the commands operation  
- Definitions
    > "Top level": Top level refer to anything that is not wrapped in a function or class definition  
    >     i.e. it is being executed in the global scope  
    > ```py
    > # Top level
    > print("I'm top level!")
    > try:
    >     print("Me too!")
    >
    > # Not top level
    > def func():
    >     print("I am not top level")
    > ```

- Awaits
    > This command simplifies calling async code. It removes the need to be in an async function to call async code.  
    > It also removes the need to use "await" when calling async functions.  
    > And even if you do use "await", it will still work! (If it doesn't, just get rid of the "await" and it probably will. Nobody likes awaits, not even this command)  
    > 
    > You can even use await on non-async functions due to the way this command modifies function calls in the passed in source code. It doesn't care if it is an async or sync function, they are both called the same way!  
    > 
    > This also adds an interesting, and very useful side-effect. Because both async and sync are treated as sync (it is slightly more complex than that), you can do things you wouldn't normally be able such as using an async function call as an argument to a function ([Async Call As Value For Function Argument](#async-call-as-value-for-function-argument))  
    > **Important: At this point in time, none of this applies inside async function definitions in the passed in code. That remains unmodified and still needs awaits**  

- Interactive Interpreter Style Expression Printing
    > The command will print all top level statements just like the python interactive interpreter would.  
    > Internally this works by wrapping expressions in a function call that prints out the value, skipping over None.  
    > Expressions by Pythons definition are function calls or expressions that aren't part of an assignment ([Example](#interactive-interpreter-style-expression-printing))  

Those are the only real important things to remember as compared to a normal exec command.

## Examples
### Basic Call
Just pass in any normal python code. Nothing special

### Interactive Interpreter Style Expression Printing
Here are some examples showing what it will print.  
```py
1 + 1
"Hello World"
bot.send_message(channel, "hello").content
=== Output ===
2
Hello World
hello
```

### Sending A Message Without Await
```py
bot.send_message(channel, text)
```
Yes, it is that simple

### Async Call As Value For Function Argument
This will wait until the specified user posts a message in the given channel.  
It will then send another message that contains what the user just sent.  
**This is not possible (so easily at least) in normal exec commands. This command is different**
```py
bot.send_message(channel, bot.wait_for_message(channel=channel, author=User).content)
```

## Project Layout
- eval_ast_gen.py  
This contains all of the functions for generating and modifying the AST of the passed in code.  
It is where almost all of the action is going on.  

- exec_command.py
This contains the implementation of the exec command.  
It is a slightly edited version of the one that my bot is currently using.  

All of the code is pretty much uncommented. It should be at least partially possible to understand the code without them.  

## How To Add To Your Bot
The file "exec_command.py" contains the command  
Do note that it is not in a form that you can just "load a cog"  
You will need to edit it so that your bot is able to call and use the command  
> Do note that this was designed for the d.py "async" branch  
> I have not yet tested it on d.py "rewrite"

## Bugs
### Exec's
#### Multiple Execs Block Each Other
While the exec's wont block other bot functions, they will block each other.  
If you run one exec that waits for a message, then run another. The new exec will block the old one until it exits.  
This is due to the execs being synchronous. This means that in order to get values out of coroutines, the synchronous code has to take manual control of the event loop.  
In short: They nest  

## Random Info
### "Why did you do this! Are you some kind of maniac?!"
While I can't say for sure that I am not (I mean, seriously. Just look at the code!), I didn't do it for that reason.  
I did it for fun and to see if I could.  
Asyncio really does not like synchronous code and if you ever need to use some you will end up either doing some very strange things or, in the case of synchronous code that needs to use async code, just forget about doing it at all.  
The easy way would have been to use threads or multiple processes (or even to just turn it into an async function). But I get annoyed with people always saying how "great" and "good" async is and how _terrible_ threads are and so I thought I would twist that in and make an exec function that uses no extra threads to do synchronous code.  
> There is at least one thing I am "crazy" for doing, and that is not wrapping the users code in  
an async def.  
> It wouldn't matter if I just stripped away the async def at the end, it would just make things far better. And if I left it there, it would mean that I would not need to do any of this needless "Sync calling Async" rubbish.  
> But... That wouldn't be any fun!

### Why do awaits cause so much trouble?
The way python parses "await" is pretty hacky as-is. I didn't want to modify the user passed in code by wrapping it in an async func def just to strip it away after. Instead I am tokenizing and modifying each syntax error until there are none left (or unless it hits more than 10).  
It is _very_ hacky and repeated tokenization, modification, and then retokenisation eventually ends up messing with the line of source it is modifying.
> May change to just wrap in an async func def then strip away after ast generation. May not strip
> At which point this will likely go away

### "Is this unique?"
Best answer: "I hope so, because this is a pretty terrible way of doing things"  
Maybe, maybe not. I have no idea and I can't be bothered looking.  
Likely someone else has tried something similar.  
