
import inspect, sys, re

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'


def textColor(color, txt):
	return color + txt + bcolors.ENDC


class Verbose:

	verboseLevel = 10
	enablePrintArguments = True
	trimText = 134

	customColors = {'Train.py':        '\033[31m',
	                'TrainedModel.py': '\033[32m',
	                'Model.py':        '\033[33m'}
	# 34, 35, 36


	callFileJustifySize = 20
	callFnctJustifySize = 25


	@staticmethod
	def __processText(text):
		text = str(text)
		if len(text) > Verbose.trimText:
			return text[0:Verbose.trimText-3] + "…"
		else:
			return text

	@staticmethod
	def __getColor(callFile):
		if callFile in Verbose.customColors:
			return Verbose.customColors[callFile]
		else:
			return '\033[90m'

	@staticmethod
	def __getPrefix():
		callFile = inspect.stack()[2][1].split('/')[-1]
		callFnct = inspect.stack()[2][3]
		return textColor(Verbose.__getColor(callFile), callFile.ljust(Verbose.callFileJustifySize) + callFnct.ljust(Verbose.callFnctJustifySize))

	@staticmethod
	def __formatFunctionArguments(argsDict):
		argsStr = "("
		sep = ""
		for k in argsDict:
			argsStr += sep + k
			if k != "self": # just because it is not pretty
				argsStr += "=" + str(argsDict[k])
			sep = ", "
		return argsStr + ")"

	@staticmethod
	def __Colorize_OK_ERROR(txt):
		txt = re.sub("(\\[[ ]*OK[ ]*\\])",      textColor(bcolors.OKGREEN, "\\1"), txt)
		txt = re.sub("(\\[[ ]*ERROR[ ]*\\])",   textColor(bcolors.FAIL,    "\\1"), txt)
		txt = re.sub("(\\[[ ]*WARNING[ ]*\\])", textColor(bcolors.WARNING, "\\1"), txt)
		txt = re.sub("(\\[[ ]*INFO[ ]*\\])",    textColor(bcolors.OKBLUE,  "\\1"), txt)
		return txt


	@staticmethod
	def print_arguments():
		if Verbose.enablePrintArguments:
			callFile = inspect.stack()[1][1].split('/')[-1]
			callFnct = inspect.stack()[1][3]
			argsDict = inspect.getargvalues(inspect.stack()[1][0])[3]
			print(textColor(Verbose.__getColor(callFile), callFile.ljust(Verbose.callFileJustifySize) + callFnct + Verbose.__processText(Verbose.__formatFunctionArguments(argsDict))))


	@classmethod
	def print_text(cls, lvl, text, returnToLineBeginningAfter=False):
		if lvl <= Verbose.verboseLevel:
			print(Verbose.__getPrefix() + ": " + cls.__Colorize_OK_ERROR(Verbose.__processText(text)))
			if returnToLineBeginningAfter:
				sys.stdout.write("\033[F")
