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
# convenience function : just paste variables names and content from an environment 
# to another: useful to parse a pythonic input and spread the content into
# the various objects
##################################################################################
def copyVarsToObjectByName(sinkobject,listvars,sourceobject):
	""" copy variables from an object to the next based on a list of argument names """
	for var in listvars:
		try:
			getattr(sourceobject, var)
		except NameError:
			print "Name ",var," not stated in input and this is needed"	
			sys.exit(2)
		setattr(sinkobject,var,getattr(sourceobject, var))
		print "  Variable \""+var+"\" acquired from input: ",getattr(sinkobject,var)
##################################################################################
# convenience pdb reader
##################################################################################
def readPDB(filename):
	""" a simple pdb reader in terms of images """
	#create an image for each pdb
	print "Opening file: ",filename
	f=open(filename,"r")
	images=[]
	pdb=[]
	for line in f:
		m=line.split()
		if  m[0]=="END" or m[0]=="TER":
			# push the pdb into the image
			#print pdb
			img=ImageClass()			
			for i in range(len(pdb)):
				img.details.append(pdb[i][0])
				img.x.append(pdb[i][1])
				img.y.append(pdb[i][2])
				img.z.append(pdb[i][3])
				img.occ.append(pdb[i][4])
				img.beta.append(pdb[i][5])
			images.append(img)
			pdb=[]
		else:
			if line.startswith('ATOM') or line.startswith('HETATM'):
				pdb.append( [line[0:30],float(line[31:38]),float(line[39:46]),float(line[47:54]),float(line[54:59]),float(line[60:66])] )	
	f.close()
	print "File read! Found ",len(images)," images ! "
	return images

##################################################################################
# simple image class
##################################################################################
class ImageClass:
	fake=0
	x=[]
	y=[]
	z=[]
	occ=[]
	beta=[]
	details=[]
##################################################################################
# the string is a collection of images plus information on how to run it
# which dir, soma/pcv , spring constant(s)
# and all the various plumed-related things
##################################################################################
class StringClass:

	def __init__(self,inputvariables):
		""" read the string from the inputlines"""

		# these are the properties required for this input: if you need any new, just plug it in here: checks are automatically performed
		needednames=["string","storedir","workdir","dumpfreq","evolstep","discard","maxrounds","optends"]

		print "reading input file for images"
		self.optends=False
		copyVarsToObjectByName(self,needednames,inputvariables)
		# use the variables from here
       	 	self.imagelist=readPDB(self.string)
		# type of optimization: soma or pathcvs
		self.optimizationType(inputvariables)
       	 	self.rootdir=os.getcwd()

	def optimizationType(self,inputvariables):
		""" scan the inputlines and see if you have Soma or Pathcvs: then parse the correct arguments """
		copyVarsToObjectByName(self,["pathtype"],inputvariables)		
		if  getattr(self,"pathtype").upper()=="SOMA" : 
			print "This is a SOMA run: need a single spring constant "	
	                copyVarsToObjectByName(self,["springconstant"],inputvariables)
		elif  getattr(self,"pathtype").upper()=="PCV" :
                        print "This is a PCV run "
	                copyVarsToObjectByName(self,["springconstant_s"],inputvariables)
	                copyVarsToObjectByName(self,["springconstant_z"],inputvariables)
		else:
			print "There is no such pathtype !!! ",getattr(self,"pathtype")
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

##################################################################################
#  main routine
##################################################################################
def doOptimization(argv):
        print "String method/Path CV optimizer starting point"
	# embed everything in a object to keep everything clean
	po=PathOptimizer(argv)	
	myString= StringClass(po.inputvariables)		
       	# initial loop
        print "************ INITIAL STRING PARSING       *************"
        sys.exit()

##################################################################################
# this is the main command executed
##################################################################################
doOptimization(sys.argv[1:])
