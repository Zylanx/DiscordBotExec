import ast
import asyncio
import tokenize
import io
import sys

from contextlib import redirect_stdout


class OutputExprRewriter(ast.NodeTransformer):
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
        newnode = ast.Expr(value=call)
        ast.copy_location(newnode, node)
        ast.fix_missing_locations(newnode)
        self.generic_visit(newnode)
        return newnode
    
    def vist_Await(self, node):
        newnode = node.value
        ast.copy_location(newnode, node)
        ast.fix_missing_locations(newnode)
        self.generic_visit(newnode)
        return newnode


class FunctionAsyncRewriter(ast.NodeTransformer):
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
    def visit_Module(self, node):
        setDoneNode = ast.Expr(ast.Call(ast.Attribute(ast.Name("finishedExecSig", ast.Load()), "set_result", ast.Load()), [ast.NameConstant(None)], []))
        setExceptionNode = ast.Expr(ast.Call(ast.Attribute(ast.Name("finishedExecSig", ast.Load()), "set_exception", ast.Load()), [ast.Name("e", ast.Load())], []))
        
        mainBody = node.body + [setDoneNode]
        
        tryExceptNode = ast.ExceptHandler(ast.Name("Exception", ast.Load()), "e", [setExceptionNode])
        
        tryNode = ast.Try(mainBody, [tryExceptNode], [], [])
        
        newnode = ast.Module([tryNode])
        ast.copy_location(newnode, node)
        ast.fix_missing_locations(newnode)
        return newnode


def outputExpr(value):
    if value is not None:
        print(repr(value))


class OutputExpr:
    def __init__(self, pipe):
        self.pipe = pipe
    
    def printExpr(self, value):
        if value is not None:
            print(repr(value), file=self.pipe)


def callFuncExec(func, *args, **kwargs):
    """ WARNING: This function messes with the internal event loop in
                 ways it shouldn't. Use at your own discretion! """
    if not func:
        raise Exception("No function passed in")
    
    loop = asyncio.get_event_loop()
    if asyncio.iscoroutinefunction(func):
        fut = asyncio.ensure_future(func(*args, **kwargs))
        with redirect_stdout(sys.__stdout__):
            while not fut.done():
                loop._run_once()
        result = fut.result()
    else:
        result = func(*args, **kwargs)
    return result


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