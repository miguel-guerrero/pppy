#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# MIT License
#
# Copyright (c) 2018-Present, Miguel A. Guerrero
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Please send bugs and suggestions to: miguel.a.guerrero@gmail.com
# -------------------------------------------------------------------------------
import json
import os
import pickle
import re
import sys
import traceback


# -------------------------------------------------------------------------------
# Given a line replace code in between delimLeft and delimRight into { and }
# that can be easilly evaluated as an f'string. If any single { or } is found
# quote it as {{ and }} as it was inteded to be sent as-is to the output
# -------------------------------------------------------------------------------
class UnexpectedDelimException(Exception):
    def __init__(self, col, line, delim):
        self.col = col
        self.line = line
        self.delim = delim

    def __str__(self):
        return (
            f"ERROR unexpected delimiter {self.delim} at column "
            + f"{self.col+1}\n"
            + f"LINE: {self.line}\n      "
            + "-" * (self.col - 1)
            + "^"
        )


class UnterminatedExprException(Exception):
    def __init__(self, line):
        self.line = line

    def __str__(self):
        return f"ERROR unterminated expression LINE: {self.line}"


def quote(line, delimLeft, delimRight):
    lenL = len(delimLeft)
    lenR = len(delimRight)
    newLine = ""
    insideExpr = False
    skip = 0
    for i, currChar in enumerate(line):
        if skip > 0:
            skip -= 1
        else:
            if not insideExpr:
                if line[i : i + lenL] == delimLeft:
                    insideExpr = True
                    newLine += "{"
                    skip = lenL - 1
                else:
                    if currChar in "{}":
                        newLine += currChar * 2  # quote it by duplication
                    elif currChar in "'":
                        newLine += "\\" + currChar  # quote it with \
                    else:
                        newLine += currChar  # copy it
            else:
                if line[i : i + lenR] == delimRight:
                    insideExpr = False
                    newLine += "}"
                    skip = lenR - 1
                elif line[i : i + lenL] == delimLeft:
                    raise UnexpectedDelimException(i + 1, line, delimLeft)
                else:
                    newLine += currChar
    if insideExpr:
        raise UnterminatedExprException(line)
    return newLine


# -------------------------------------------------------------------------------
# Generate the intermediate python code that when executed will generate the
# redered template
# -------------------------------------------------------------------------------
def genPython(
    lines,
    paramFile=None,
    ppio={},
    leading="% ",
    leftExprDelim="${",
    rightExprDelim="}",
    leftBlkDelim="<%",
    rightBlkDelim="%>",
    lineOffset=0,
    scriptPath=".",
):

    modName = "pp"
    prevPrefix = prefix = ""
    buf = []
    out = []
    needIndent = False
    indent = 4 * " "

    def lineLoc(line, lineNum, lineLim):
        pad = max(100 - len(line), 0)
        if lineNum <= 0 or lineNum >= lineLim:
            return line
        return line + " " * pad + f" # user line {lineNum}"

    def indentList(lst, ind):
        return [ind + line for line in lst]

    def flushBuffer():
        if needIndent:
            if len(prefix) > len(prevPrefix):
                newBuf = indentList(buf, prefix)
            elif len(prefix) < len(prevPrefix):
                newBuf = indentList(buf, prevPrefix + indent)
            else:
                newBuf = indentList(buf, prefix + indent)
        else:
            newBuf = indentList(buf, prevPrefix)
        return out + newBuf, []

    # serialize ppio dictionary and let the generated code load it
    ppioSer = pickle.dumps(ppio)
    out.append(f"import sys, pickle")
    out.append(f"sys.path.insert(0,'{scriptPath}')")
    out.append(f'sys.path.insert(0, "./")')
    out.append(f"import {modName}")
    out.append(f"ppio = pickle.loads({ppioSer})")
    out.append(f"# ppio = {ppio} # for debug")
    # param struct will contain parameters from file with potential
    # overrides from the ppio dictionary
    out.append(f'paramDict = {modName}.jsonToDict("{paramFile}")')
    out.append(f"# override json contents with ppio dictionary")
    out.append(f"{modName}.addToDict(paramDict, ppio)")
    out.append(f"param = {modName}.Struct(**paramDict)")
    out.append("end = endfor = endif = None")
    out.append("emitLines = []")
    out.append("def emit(s): emitLines.append(s)")
    out.append(f"# --- {modName} payload code begins ---")

    inPythonMode = False
    lines.append(leading)  # this will force a final flush
    for i, line in enumerate(lines):
        line = line.rstrip("\n")  # remove \n
        if inPythonMode:
            if re.match(rightBlkDelim + "$", line):
                inPythonMode = False
                out.append("# python end")
            else:
                out.append(line)
        else:
            if re.match(leftBlkDelim + "$", line):
                inPythonMode = True
                out, buf = flushBuffer()
                out.append("# python start")
            else:
                if re.match(leading, line):
                    line = line[len(leading) :]  # skip leading marker
                    # find indentation (allows spaces and dots) and clean dots
                    indentMatch = re.match(r"[ \.]*", line)
                    if indentMatch:
                        prevPrefix = prefix
                        prefix = " " * len(indentMatch.group())
                        line = re.sub(r"^[ \.]+", prefix, line)
                    # flush buffered lines (we needed to see indent of next)
                    if buf:
                        out, buf = flushBuffer()
                    out.append(line)
                    needIndent = re.search(r":\s*$", line) is not None
                elif re.match(leading.rstrip(), line):
                    raise ValueError(
                        f"input python must start with '{leading}', "
                        + f"found '{line}' on user line {i+1}"
                    )
                else:
                    line = quote(line, leftExprDelim, rightExprDelim)
                    buf.append(f"emit(f'{line}')")

    lineCnt = len(out)
    lineOffset += lineCnt - len(lines)
    out.append((f"# --- {modName} payload code ends ---"))
    out.append(('_render = "\\n".join(emitLines)'))
    out.append((f"{modName}.addToDict(ppio, param.getDict())"))
    return [
        lineLoc(line, i - lineOffset + 1, lineCnt - lineOffset)
        for i, line in enumerate(out)
    ]


# -------------------------------------------------------------------------------
# Used by the generated python prefix code
# -------------------------------------------------------------------------------
def jsonToDict(filename):
    if filename == "":
        return {}
    with open(filename) as fjson:
        s = fjson.read()
    return json.loads(s)


def addToDict(dst, src):
    for k, v in src.items():
        dst[k] = v


# a structure that returns None for not-defined fields
# and can be used as a dict too
class Struct:
    def __init__(self, **kwargs):
        self.argDict = kwargs

    def setDict(self, argDict):
        self.argDict = argDict

    def getDict(self):
        return self.argDict

    def __getattr__(self, key):
        if key in self.argDict.keys():
            return self.argDict[key]
        return None

    def __setattr__(self, key, val):
        if key != "argDict":
            self.argDict[key] = val
        else:
            object.__setattr__(self, key, val)

    __getitem__ = __getattr__
    __setitem__ = __setattr__

    def __repr__(self):
        return (
            "Struct("
            + ", ".join(f"{k}={v!r}" for k, v in self.argDict.items())
            + ")"
        )


# -------------------------------------------------------------------------------
# Given a python string, execute it and return the content of its _render
# variable. In our case we use _render to hold all emitted lines after
# executing the preprocessing step
# -------------------------------------------------------------------------------
def execScript(program, ppio):
    _render = None
    loc = locals()
    exec(program, loc)
    return loc["_render"], loc["ppio"]


# -------------------------------------------------------------------------------
# Render a template string. if there is an error create an itermediate script
# to help debugging
# -------------------------------------------------------------------------------
def genIntermPython(program, intermFile):
    with open(intermFile, "w") as f:
        f.write(f'{program}\nprint(_render, end="") # for debug')


def render(
    templateStr,
    paramFile="",
    ppio={},
    keepPython=False,
    intermFile="__from_string__.debug.py",
    lineOffset=0,
    scriptPath=".",
):

    inputLst = templateStr.split("\n")
    pythonCodeLst = genPython(
        inputLst,
        paramFile,
        ppio,
        lineOffset=lineOffset,
        scriptPath=scriptPath,
    )

    program = "\n".join(pythonCodeLst)

    out = rc = None
    try:
        out, rc = execScript(program, ppio)
        if keepPython:
            genIntermPython(program, intermFile)
    except Exception:
        # if there is an error, generate code for debug
        excMsg = re.sub("<string>", intermFile, traceback.format_exc(0))
        print(
            f"An ERROR occurred, run 'python3 {intermFile}' to debug",
            file=sys.stderr,
        )
        print(excMsg, file=sys.stderr)
        genIntermPython(program, intermFile)
        raise
    return out, rc


# -------------------------------------------------------------------------------
# Wrapper for render when the template is in a file
# -------------------------------------------------------------------------------
def renderFile(
    templateFile,
    paramFile="",
    ppio={},
    keepPython=False,
    lineOffset=0,
    scriptPath=".",
):
    with open(templateFile) as f:
        templateStr = f.read().rstrip()
    return render(
        templateStr,
        paramFile,
        ppio,
        keepPython,
        intermFile=templateFile + ".debug.py",
        lineOffset=lineOffset,
        scriptPath=scriptPath,
    )


# -------------------------------------------------------------------------------
#                                   MAIN
# -------------------------------------------------------------------------------
if __name__ == "__main__":
    from argparse import ArgumentParser, FileType

    def numberOrStr(s):
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s

    def mainCmdParser(parser):
        parser.add_argument(
            "templateFile", help="template file to be expanded", type=str
        )
        parser.add_argument(
            "--paramFile", "-p", help="parameter file", type=str, default=""
        )
        parser.add_argument(
            "--outFile",
            "-o",
            help="output file, defaults to stdout",
            type=FileType("w"),
            default="-",
        )
        parser.add_argument(
            "--keyValues", "-k", help="key=value pairs", nargs="+", default=[]
        )
        parser.add_argument(
            "--keepPython",
            help="keep intermediate python script",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--verbose",
            "-v",
            help="print output ppio on stderr",
            action="store_true",
            default=False,
        )
        args = parser.parse_args()
        args.keyValues = dict(kv.split("=") for kv in args.keyValues)
        args.keyValues = {
            k: numberOrStr(v) for k, v in args.keyValues.items()
        }
        return args

    args = mainCmdParser(ArgumentParser())
    scriptPath = os.path.realpath(os.path.dirname(__file__))

    out, rc = renderFile(
        args.templateFile,
        args.paramFile,
        ppio=args.keyValues,
        keepPython=args.keepPython,
        scriptPath=scriptPath,
    )
    args.outFile.write(out)
    if args.verbose:
        print(f"{rc}", file=sys.stderr)

