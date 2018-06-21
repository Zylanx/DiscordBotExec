import ast
import asyncio
import tokenize
import io
import sys

from contextlib import redirect_stdout

__author__ = "Zylanx"


class OutputExprRewriter(ast.NodeTransformer):
    """
        OutputExprRewriter: This transformer runs through every top level statement and wraps them in
                            so they send their result to the function "outputExpr".
                            This is the basis for the "Interactive Interpreter" style of return value display
                            It also removes "await" statements, just leaving the
                            expression afterwards (which it proceeds to process)
    """
    
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return node
        
    def visit_AsyncFunctionDef(self, node):
        return node

    def visit_Expr(self, node):
        if not isinstance(node.value, list):
            if not node.value:
                args = []
            else:
                args = [node.value]
        else:
            args = node.value
        
        call = ast.Call(ast.Name("outputExpr", ast.Load()), args, [])
        newNode = ast.Expr(value=call)
        ast.copy_location(newNode, node)
        ast.fix_missing_locations(newNode)
        self.generic_visit(newNode)
        return newNode
    
    def visit_Await(self, node):
        newNode = node.value
        ast.copy_location(newNode, node)
        ast.fix_missing_locations(newNode)
        self.generic_visit(newNode)
        return newNode


class FunctionAsyncRewriter(ast.NodeTransformer):
    """
        FunctionAsyncRewriter: This transformer runs through the AST and redirects all function calls
                               to be wrapped by the "callFuncExec" function
    """
    
    def visit_Call(self, node):
        if not isinstance(node.args, list):
            if not node.args:
                args = []
            else:
                args = [node.args]
        else:
            args = node.args
        
        args.insert(0, node.func)
        call = ast.Call(ast.Name("callFuncExec", ast.Load()), args, node.keywords)
        ast.copy_location(call, node)
        ast.fix_missing_locations(call)
        self.generic_visit(call)
        return call


class FinishedSigWrapper(ast.NodeTransformer):
    """
        FinishedSigWrapper: This transformer wraps the modified code in some extra code to deal with communicating
                            the execution to the outside world and signaling to the future that it is now done
                            and the command has completed, or if there is a failure, that an exception has
                            occurred
    """
    
    def visit_Module(self, node):
        setDoneNode = ast.Expr(ast.Call(ast.Attribute(ast.Name("finishedExecSig", ast.Load()), "set_result", ast.Load()), [ast.NameConstant(None)], []))
        setExceptionNode = ast.Expr(ast.Call(ast.Attribute(ast.Name("finishedExecSig", ast.Load()), "set_exception", ast.Load()), [ast.Name("e", ast.Load())], []))
        
        mainBody = node.body + [setDoneNode]
        
        tryExceptNode = ast.ExceptHandler(ast.Name("Exception", ast.Load()), "e", [setExceptionNode])
        
        tryNode = ast.Try(mainBody, [tryExceptNode], [], [])
        
        newNode = ast.Module([tryNode])
        ast.copy_location(newNode, node)
        ast.fix_missing_locations(newNode)
        return newNode


# TODO: Comment outputExpr
def outputExpr(value):
    """
        outputExpr: Top level expressions are wrapped by a call to this function.
                    This function simply prints the repr of the result of the wrapped expression.
    """
    if value is not None:
        print(repr(value))


# TODO: Comment OutputExpr
# COMMENT: OutputExpr is just left over from before the stdout was smart piped like it is now
class OutputExpr:
    def __init__(self, pipe):
        self.pipe = pipe
    
    def printExpr(self, value):
        if value is not None:
            print(repr(value), file=self.pipe)


#  WARNING: This function messes with the internal asyncio 
#	        event loop in ways it shouldn't. Use at your own discretion! 
def callFuncExec(func, *args, **kwargs):
    """
        callFuncExec: This function does most of the heavy lifting for the library
                      It takes in a function and depending on whether it is a normal function
                      or a coroutine, either execute it normally, or otherwise take
                      control of the asyncio event loop and run it synchronously.
    """
    
    # If nothing passed in, then there is a fatal error and it needs to exit
    if not func:
        raise Exception("No function passed in")
    
    # If the function is a coroutine, add the function to the event
    # loop then step through the loop until the future has completed
    if asyncio.iscoroutinefunction(func):
        loop = asyncio.get_event_loop()
        fut = asyncio.ensure_future(func(*args, **kwargs)) # Adds the func as a future to the loop 
        
        # Leaving our managed code so redirect stdout back to system
        with redirect_stdout(sys.__stdout__):
            while not fut.done(): # loop until the future is ready
                loop._run_once()
        result = fut.result()
    else: # Normal function. Just execute as normal
        result = func(*args, **kwargs)
    return result


# TODO: Comment fixASTAwaitError
# TODO: Strip awaits from even more places
def fixASTAwaitError(text, offset):
    tokenList = list(tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline))
    
    def flattenList():
        returnList = []
        for token in tokenList:
            returnList.append((token.type, token.string))
        return returnList

    def findTokenAtOffset(offset):
        for index, token in enumerate(tokenList):
            if token.start[1] <= offset and offset < token.end[1]:
                return index
        return None
            
    def tokenMatchType(index, tokenType):
        if tokenList[index].exact_type == tokenType:
            return True
        else:
            return False
            
    def tokenMatchValue(index, value):
        if tokenList[index].string == value:
            return True
        else:
            return False
    
    def tokenMatch(index, tokenType, value):
        token = tokenList[index]
        if token.exact_type == tokenType and token.string == value:
            return True
        else:
            return False
    
    index = findTokenAtOffset(offset)
    if index is None:
        index = findTokenAtOffset(offset+1)
        if index is None:
            return None
        else:
            if not (tokenMatchType(index, tokenize.DOT) or tokenMatchType(index, tokenize.LPAR)):
                return None
    if tokenMatchType(index, tokenize.LPAR):
        # It is at a function (possibly)
        if tokenMatchType(index-1, tokenize.NAME):
            # Very likely in a function
            if tokenMatch(index-2, tokenize.NAME, "await"):
                # Found an await I know I can deal with
                del tokenList[index-2]
                tokenList = flattenList()
                return tokenize.untokenize(tokenList).decode("utf-8")
    elif tokenMatchType(index, tokenize.DOT):
        # Possibly an attribute call
        if tokenMatchType(index+1, tokenize.NAME):
            if tokenMatchType(index-1, tokenize.NAME):
                if tokenMatch(index-2, tokenize.NAME, "await"):
                    del tokenList[index-2]
                    tokenList = flattenList()
                    return tokenize.untokenize(tokenList).decode("utf-8")
    return None


# TODO: Comment parseAST
def parseAST(inputText):
    for _ in range(50):
        try:
            outAST = ast.parse(inputText)
            break
        except SyntaxError as e:
            lineno = e.lineno
            offset = e.offset
            text = e.text.rstrip("\n")
            if text[0] != "\n":
                text = "\n" + text
        
            fixedLine = fixASTAwaitError(text, offset)
            
            if fixedLine is None:
                raise
            else:
                fixedLine = fixedLine.lstrip("\n")
                inputText = inputText.splitlines()
                inputText[lineno-1] = fixedLine
                inputText = "\n".join(inputText)
    
    outAST = FunctionAsyncRewriter().visit(outAST)
    outAST = OutputExprRewriter().visit(outAST)
    outAST = FinishedSigWrapper().visit(outAST)
    return outAST