# This was made for discord.py "async".
# It should still work on discord.py "rewrite", but will just need some small edits
# It has not been tested on discord.py "rewrite"
import discord
if discord.version_info.releaselevel == "alpha":
    print('This was made for discord.py "async".\nIt should still work on discord.py "rewrite", but will just need some small edits\nIt has not been tested on discord.py "rewrite"\')

import asyncio
import eval_ast_gen

__author__ = "Zylanx"


async def commandEval(self, message: discord.Message, commandText: str):        
    commandText = commandText.strip("\n")
    
    def appendReply(env, *args, **kwargs):
        embed = None
        if "embed" in kwargs:
            embed = kwargs["embed"]
        if not args and not embed:
            raise TypeError("appendReply: No message or embed passed in")
        if not args:
            args = [""]
        eval_ast_gen.callFuncExec(self.edit_message, env["execStartMessage"], str(env["execStartMessage"].content) + "\n" + str(args[0]), embed=embed)
    
    def execAST(inputAST, env):
        # Send a message to the channel for the users code to edit if wanted
        env["execStartMessage"] = eval_ast_gen.callFuncExec(self.send_message, message.channel, "`--Eval Started--`\n")
        env["appendReply"] = partial(appendReply, env)
        
        # Actually execute the AST
        try:
            exec(compile(inputAST, "<ast>", "exec"), env)
        except Exception as e:
            env["finishedExecSig"].set_exception(e)
    
    sigDone = asyncio.Future()
    
    with io.StringIO() as outputExprPipe, io.StringIO() as evalStdout:
        outputExprInst = eval_ast_gen.OutputExpr(outputExprPipe)
        
        env = {
            'bot' : self,
            'client' : self,
            'msg' : message,
            'message' : message,
            'content' : message.content,
            'guild' : message.server,
            'channel' : message.channel,
            'me' : message.author,

            # utilities
            '_get' : discord.utils.get,
            '_find' : discord.utils.find,
            'reply' : partial(self.addToReplyQueue, message),
            'sendHere' : partial(eval_ast_gen.callFuncExec, asyncio.coroutine(partial(self.send_message, message.channel))),
            'execStartMessage' : None,
            'appendReply' : None,
            
            # Previous Executions
            'lastResult' : self.evalLastResult,
            'lastCodeText' : self.evalLastCode,
            'lastAST' : self.evalLastAST,
            
            # Exec Utils
            'outputExpr' : outputExprInst.printExpr,
            'callFuncExec' : eval_ast_gen.callFuncExec,
            'finishedExecSig' : sigDone,
            'outputExprPipe' : outputExprInst.pipe,
        }
        env.update(globals())
        
        try:
            outAST = eval_ast_gen.parseAST(commandText)
            with redirect_stdout(evalStdout):
                loop = asyncio.get_event_loop()
                handle = asyncio.events.Handle(execAST, (outAST, env), loop)
                loop._ready.insert(0, handle)
                await sigDone
        except Exception as e:
            await self.send_message(message.channel, "```py\n{}\n```".format(traceback.format_exc(limit=1)))
            return

        stdoutResult = evalStdout.getvalue()
        outputExprResult = outputExprInst.pipe.getvalue()

    await self.send_message(message.channel, "Eval Successful")

    if stdoutResult is not None:
        self.evalLastResult = stdoutResult
        
    if outAST is not None:
        self.evalLastAST = outAST
        
    self.evalLastCodeText = commandText

    formattedOut = "```py\n---Stdout---\n{}\n---Expr Vals---\n{}\n```".format(stdoutResult, outputExprResult)
    if len(formattedOut) > 2000:
        await self.send_message(message.channel, "Too long to post results")
    else:
        await self.send_message(message.channel, formattedOut)
