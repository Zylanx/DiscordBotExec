# This was made for discord.py "async".
# It should still work on discord.py "rewrite", but will just need some small edits
# It has not been tested on discord.py "rewrite"

import io
import re
from functools import partial
from contextlib import redirect_stdout
import traceback

import discord
if discord.version_info.releaselevel == "alpha":
    print('This was made for discord.py "async".\nIt should still work on discord.py "rewrite", but will just need some small edits\nIt has not been tested on discord.py "rewrite"\n')

import asyncio
import eval_ast_gen

__author__ = "Zylanx"


# Config options for the Example Bot
botToken = ""
ownerID = ""
commandPrefix = "!"


# This code is mainly meant as a demonstration. There are
#   however some parts that are _needed_. This will be
#   tagged as such ("-REQUIRED-") (This has not been done yet TODO: Mark sections as "-REQUIRED-")

# ------ The Command --------


# TODO: Finish commenting commandEval
async def commandEval(self, message: discord.Message, commandText: str):        
	"""  """
	
	commandText = commandText.strip("\n")
	
	def appendReply(env, *args, **kwargs):
		"""  """
		embed = None
		if "embed" in kwargs:
			embed = kwargs["embed"]
		if not args and not embed:
			raise TypeError("appendReply: No message or embed passed in")
		if not args:
			args = [""]
		eval_ast_gen.callFuncExec(self.edit_message, env["execStartMessage"], str(env["execStartMessage"].content) + "\n" + str(args[0]), embed=embed)
	
	def execAST(inputAST, env):
		"""  """
		
		# Send a message (synchronously) to the channel that user code has access to
		env["execStartMessage"] = eval_ast_gen.callFuncExec(self.send_message, message.channel, "`--Eval Started--`\n")
		env["appendReply"] = partial(appendReply, env)
		
		# Execute the AST
		try:
			exec(compile(inputAST, "<ast>", "exec"), env)
		except Exception as e:
			env["finishedExecSig"].set_exception(e)
	
	# Signal
	sigDone = asyncio.Future()
	
	# Setup the pipes for redirecting output
	with io.StringIO() as outputExprPipe, io.StringIO() as evalStdout:
		outputExprInst = eval_ast_gen.OutputExpr(outputExprPipe)
		
		env = {
			# Base Globals
			'bot' : self,
			'client' : self,
			'msg' : message,
			'message' : message,
			'content' : message.content,
			'guild' : message.server,
			'channel' : message.channel,
			'me' : message.author,
			'author' : message.author,
			'caller' : message.author,

			# Utilities
			'_get' : discord.utils.get,
			'_find' : discord.utils.find,
			'reply' : partial(eval_ast_gen.callFuncExec, asyncio.coroutine(partial(self.send_message, message.channel))),
			'sendHere' : partial(eval_ast_gen.callFuncExec, asyncio.coroutine(partial(self.send_message, message.channel))),
			'waitForMessage' : self.wait_for_message,
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
			# This allows the executing code's error to be printed
			# TODO: Research if the traceback can have its context set to the executed code
			await self.send_message(message.channel, "```py\n{}\n```".format(traceback.format_exc(limit=0)))
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


# ------ A Bot To Show It Off --------


# TODO: Comment ExecExampleBot
class ExecExampleBot(discord.Client):

	def __init__(self, botOwnerID=None, commandPrefix=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		if botOwnerID is None:
			botOwnerID = ""
		if commandPrefix is None:
			commandPrefix = "!"
		
		self.botOwnerID = botOwnerID
		self.commandPrefix = commandPrefix

		self.evalRegex = re.compile(r"```(?:py ?)?(.+)```", re.DOTALL)
		self.evalLastResult = None
		self.evalLastCode = None
		self.evalLastAST = None

	async def on_ready(self):
		print("!!!Bot connected and ready!!!\n")
		self.botOwner = await self.get_user_info(self.botOwnerID)

	async def on_message(self, message: discord.Message):
		if message.author.bot or (message.author == self.user): # Don't process own or other bots messages
			return

		if message.author.id == self.botOwnerID:
			if message.content.startswith(self.commandPrefix + "shutdown"):
				print("\n!!!Bot shutting down!!!")
				await self.send_message(message.channel, "Bot shutting down")
				await self.logout()
				return
			elif message.content.startswith(self.commandPrefix + "exec") or message.content.startswith(self.commandPrefix + "eval"):
				match = self.evalRegex.search(message.content)
				if match is None:
					await self.send_message(message.channel, "Eval was malformed. Please wrap code in triple-quoted code blocks.")
					return
				else:
					await self.commandEval(message, match.group(1))
					return
	
	commandEval = commandEval


if __name__ == "__main__":
	if not botToken or not ownerID:
		raise Exception("Please provide a Bot Token and your Account ID")
	print("Starting bot")
	execBot = ExecExampleBot(botOwnerID=ownerID, commandPrefix=commandPrefix)
	execBot.run(botToken)
