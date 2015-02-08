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
#
# basic queue class: this is a simple test for queue class
#
# myqueue=hbd.Queue(4)
# for ii in range(10): 
#         f=open("tt_"+str(ii),'w')
#    	f.write(" sleep "+str(random.randint(1, 20)) )
#    	f.close()
# 	myqueue.push_in_queue("tt_"+str(ii))	
# myqueue.waitforall()
#
##################################################################################
class Queue(object):
        def __init__(self,nproc):
		""" a simple queue class that is useful to submit processes one after the other in a workstation exploiting all the processors """
		# consider to use a set for queue and running
                self.queue=set()
                self.done=set()
                self.rundirs={}
                self.executables={}
                self.running=set()
                self.inqueue=set()
		self.nproc=nproc
        def push_in_queue(self,executable):
		# embed the executable (should be a script) in another script so to assign a specific number to the stopfile
		# if there are enough processors it will run otherwise will set this into queue
		# should return a code so to explicit chain jobs
		mycode=str(random.randint(1, 2000000))
                self.queue.add(mycode)
		self.rundirs[mycode]=os.getcwd()
		self.executables[mycode]=executable
	        f=open("queue_"+mycode,'w')
                f.write("cd "+os.getcwd()+" ; sh "+executable+" 1>queuerr_"+mycode+" 2>queueout_"+mycode+" ; touch queuestop_"+mycode  )
                f.close()
		# first check if something is running
		running=copy.deepcopy(self.running)		
		for run in running :
			# find the dir
			if run not in self.done:
				if  os.path.exists(self.rundirs[run]+"/queuestop_"+run) :	
					self.running.remove(run)				
					self.done.add(run)
					print run," IS FINISHED. EXEC ",self.executables[run]," DIR ",self.rundirs[run]
	
		if len(self.running) < self.nproc :
			print "LAUNCHING ",mycode
			os.system("sh ./queue_"+mycode+" &")
			self.running.add(mycode)
		else:
			print "QUEUE FULL FOR  ",mycode
			self.inqueue.add(mycode)
		return mycode 
	def waitforall(self):
		print "NOW WAITFORALL TO BE OVER..."
		# this should finalize all the jobs waiting for something to happen
		while len(self.done)!=len(self.queue) :	
			# loop over all the running and see which stopfile has been created
			running=copy.deepcopy(self.running)		
			for run in running :
				# find the dir
				if run not in self.done:
					if  os.path.exists(self.rundirs[run]+"/queuestop_"+run) :	
						self.running.remove(run)				
						self.done.add(run)
						print run," IS FINISHED. EXEC ",self.executables[run]," DIR ",self.rundirs[run]
			# now send all the calcs that I can send
			if len(self.inqueue) >0:	
				while  len(self.running)<self.nproc :
					if len(self.inqueue) >0:	
						mycode=self.inqueue.pop()	
						mydir=self.rundirs[mycode]
						os.system("sh "+mydir+"/queue_"+mycode+" &")
						self.running.add(mycode)
						print mycode," IS LAUNCHED"
					else:
						break
			#time.sleep(1)
		print "ALL DONE!"
		return
	def killall(self):
		"""
			kill all the processes in the queue
		"""	
		#for i in queue:
	#		os.system("ps aux | grep queue_"+i+" | awk '{if($2==)}' )
		pass

##################################################################################
# convenience function : just paste variables names and content from an environment 
# to another: useful to parse a pythonic input and spread the content into
# the various objects
##################################################################################
def copyVarsToObjectByName(sinkobject,listvars,sourceobject,optional=False):
	""" copy variables from an object to the next based on a list of argument names """
	for var in listvars:
		acquire=True	
  		try:
       	               getattr(sinkobject, var)
		except AttributeError:
			pass
		else:	
			print "Name \""+var+"\" already assigned to object  :  ",getattr(sinkobject, var)
		try:
			getattr(sourceobject, var)
		except AttributeError:
			if optional==False:	
				print "Name \""+var+"\" not stated in input and this is needed"	
				sys.exit(2)
			else: 
                                print "Name \""+var+"\" not stated in input but is optional, so who cares? "	
			      
				acquire=False	
		if acquire==True:	
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
class ImageClass(object):
	""" A simple image class which is meant to keep the data from a pdb"""
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
class StringClass(object):
	""" this class contains the whole string and the setup on directory organization"""
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
# MDParserClass 
##################################################################################
class MDParserClass(object):
	def __init__(self,inputvariables):
		""" Initialize the object that takes care of the MD parameters and programs handling """
		print "reading input file for MDParser"
		# decide which program is to be used 
		copyVarsToObjectByName(self,["program","programpath","template","steps"],inputvariables)
		# preprogram: something like "mpirun -np 4" or mpiexec?
		self.preprogram=""
		copyVarsToObjectByName(self,["preprogram"],inputvariables,optional=True)
		#
		# program-dependent customization
		# i.e. gromacs requires preprocessing stage, while namd requires parameter files and psf
		#
	        if self.program=="GROMACS":
			self.lookupGROMACSArgs(inputvariables)
		elif self.program=="NAMD":
			print "NAMD is not yet implemented! "
			exit(2)
		elif self.program=="AMBER":
			print "AMBER is not yet implemented! "
			exit(2)
		else :
			print "The program "+self.program+" is not yet implemented! "
			exit(2)
	def lookupGROMACSArgs(self,inputvariables):
		""" define specific GROMACS junk """
		# this must be specified
		copyVarsToObjectByName(self,["topology","preprocessor","trjconv","gmxdir"],inputvariables)
		# set the environment variables
                os.environ["GMXDIR"]=self.gmxdir
                os.environ["GMXBIN"]=self.gmxdir+"/bin"
                os.environ["GMXLDLIB"]=self.gmxdir+"/lib"
                os.environ["GMXDATA"]=self.gmxdir+"/share"

#	def createDirs(self):
#		""" this should prepare and create the dirs"""	
#		# check if the working dir exist 
#		if os.path.exists(self.storedir)==False :
#			print "the storedir does not yet exit"	 
#		        os.mkdir(self.storedir)	
#		os.chdir(self.storedir)
#		# transform into absolute path	
#		self.storedir=os.getcwd()
#		os.chdir(self.rootdir)
#		if os.path.exists(self.workdir)==False :
#			print "the workdir does not yet exit"	 
#		        os.mkdir(self.workdir)	
#                os.chdir(self.workdir)
#		# transform into absolute path	
#		self.workdir=os.getcwd()
#		for i in range (0,len(self.imagelist)):
#			dirname="dir_"+str(i+1)	
#                        self.imagelist[i].dirname=dirname
#			if os.path.exists(dirname)==False :
#				print "the dir "+dirname+" does not yet exit"	 
#			        os.mkdir(dirname)	
#			os.chdir(dirname)		
#                        os.system("rm -rf *") #clean up a bit 
#			os.chdir("../")		
#		# now you should be in the root directory
#		os.chdir(self.workdir)		

##################################################################################
# QueueParser : choose the option for the queueing 
##################################################################################
class QueueParser(object):
	def __init__(self,inputvariables):
		""" initialize the various queue related stuff """
		# if no queue is defined, then it is a serial run and any 	
		# parallel improvement can be obtained via preprogram that can
		# handle the mpi parallelism 
		# "serial" : do the jobs one after the other
		# "internal" : use the internal driver
		# "external" : use a pbs to distribute the jobs 
		# "distributed" : a large bunch of processes is reserved and the nodes are assigned internally 
		self.queue="serial"
                copyVarsToObjectByName(self,["queue"],inputvariables,optional=True)		
		if self.queue=="external":
                	copyVarsToObjectByName(self,["queuetemplate"],inputvariables)		
		if self.queue=="internal":
                	copyVarsToObjectByName(self,["nmaxprocs"],inputvariables)		
	
##################################################################################
# PathOptimizer object
##################################################################################
class PathOptimizer(object):
	restart=False

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
	# various information about the string type and how to run it
        print "************ INITIAL STRING PARSING       *************"
	myString= StringClass(po.inputvariables)		
        print "************ MD PARAMETERS  PARSING       *************"
	myMDParser= MDParserClass(po.inputvariables)
        print "************ QUEUE  PARSING               *************"
	myQueue=QueueParser(po.inputvariables)
       	# initial loop
        sys.exit()

##################################################################################
# this is the main command executed
##################################################################################
doOptimization(sys.argv[1:])
