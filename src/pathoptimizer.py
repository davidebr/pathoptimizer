#!/usr/bin/python
import sys
import os
import getopt
import numpy
import time
import subprocess
import string
import re
import copy
import string
import tarfile
#
# numpy printoptions
#
numpy.set_printoptions(precision=4,suppress=True,linewidth=120)
##################################################################################
##################################################################################
class StringClass:
	
	def optimizationType(self,inputlines):
		""" scan the inputlines and see if you have Soma or Pathcvs: then parse the correct arguments """
                for line in self.inputlines:		
			m=line.split()	
			if m[0]=="pathtype": pathtype=m[1]
                try:
                        stringinputstring
                except NameError:
                        print("ERROR: string not set")
                        sys.exit(2)	
	
	
	
##################################################################################
# PathOptimizer object
##################################################################################
class PathOptimizer(object):
	restart=False
	maxstep=1000000.

	def __init__(self, argv):	
		""" initialize the object  just reading filename and evtl if restart """
		print "Initializing path optimizer ",argv
	        try:
	                opts, args = getopt.getopt(argv, "rf:")
	        except getopt.GetoptError, err:
	                print str(err)
	                self.usage()
	                sys.exit()
		if len(argv)==0:
	                self.usage()
	                sys.exit()
	        for o, a in opts:
			print "O ",o,a
	                if o == "-f":
	                        print "found input file: "+a
	                        self.inputfile=a
	                if o == "-r":
	                        print "restarting the string "
	                        self.restart=True
		# check if the filename exists
	        try:
	                self.inputfile
	        except NameError:
	                print("ERROR: filename not set. Use -f filename for input")
	                sys.exit(2)
		# just parse the string now in pythonic input 
		import imp
		self.inputvariables = imp.load_source("",self.inputfile)

	@staticmethod
	def usage():
		""" describe how to initialize a class in general """
        	print "requires an input file -f"
        	print "e.g.  -f input.dat"
        	print "it eventually accepts a -r restart option"
        	sys.exit(0)

	def initString(self):
		""" read the string from the inputlines"""
		print "reading input file for images"
       	 	# parse input
       	 	optends=False
       	 	for line in self.inputlines:
       	 	        	#print line, # note with "," do not print the newline!
       	 	   	m=line.split()	
       	 	        if m[0]=="string":
       	 			inputstring=m[1] 
       	 	        if m[0]=="storedir":
       	 			storedir=m[1] 
       	 	        if m[0]=="workdir":
       	 			workdir=m[1] 
       	 	        if m[0]=="dumpfreq":
       	 			dumpfreq=m[1] 
       	 	        if m[0]=="evolstep":
       	 			evolstep=float(m[1]) 
       	 	        if m[0]=="discard":
       	 			discard=m[1] 
       	 	 	if m[0]=="maxrounds":
       	 			maxrounds=m[1] 
       	 	 	if m[0]=="optends":
       	 			optends=True 
       	 	# do some checks on output
       	 	#		sys.exit(2)
       	 	try:
       	 	 	inputstring	
       	 	except NameError:
       	 		print("ERROR: string not set")
       	 		sys.exit(2)
       	 	try:
       	 		storedir 
       	 	except NameError:
       	 		print("ERROR: storedir not set")
       	 		sys.exit(2)
       	 	try:
       	 		workdir 
       	 	except NameError:
       	 		print("ERROR: workdir not set")
       	 		sys.exit(2)
       	 	try:
       	 		dumpfreq 
       	 	except NameError:
       	 		print("ERROR: dumpfreq not set")
       	 		sys.exit(2)
       	 	try:
       	 		evolstep 
       	 	except NameError:
       	 		print("ERROR: evolstep not set")
       	 		sys.exit(2)
       	 	try:
       	 		discard	
       	 	except NameError:
       	 		print("ERROR: discard value not set ")
       	 		sys.exit(2)
       	 	try:
       	 		maxrounds	
       	 	except NameError:
       	 		print("ERROR: maxrounds value not set ")
       	 		sys.exit(2)
       	 	#
       	 	# creating the string
       	 	#
       	 	myString=StringClass()
		# the string itself
       	 	myString.imagelist=readPDB(inputstring)
		# type of optimization: soma or pathcvs
		myString.optimizationType(self.inputlines)
		# the directories
       	 	myString.storedir=storedir 
       	 	myString.workdir=workdir 
       	 	myString.rootdir=os.getcwd()
       	 	myString.dumpfreq=dumpfreq 
       	 	myString.evolstep=evolstep 
       	 	myString.discard=float(discard)
       	 	myString.maxrounds=int(maxrounds)
       	 	myString.optends=optends
       	 	return myString

##################################################################################
#  main routine
##################################################################################
def doOptimization(argv):
        print "String method/Path CV optimizer starting point"
	# embed everything in a object to keep everything clean
	po=PathOptimizer(argv)	
       	# initial loop
        print "************ INITIAL STRING PARSING       *************"
        sys.exit()

##################################################################################
# this is the main command executed
##################################################################################
doOptimization(sys.argv[1:])
