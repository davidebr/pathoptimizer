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
			alreadyassigned=False
			pass
		else:	
			print "  Name \""+var+"\" already assigned to object  :  ",getattr(sinkobject, var)
			alreadyassigned=True
		try:
			getattr(sourceobject, var)
		except AttributeError:
			if optional==False:	
				print "  Name \""+var+"\" not stated in input and this is needed"	
				sys.exit(2)
			else: 
				if alreadyassigned==True:
                               	 	print "  Name \""+var+"\" not stated in input but is already assigned "	
				else:
                                	print "  Name \""+var+"\" not stated in input but is optional, so who cares? "	
				acquire=False	
		else:
			if alreadyassigned==True: print "Reassigning the variable..." 
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
	def __init__(self):
		self.x=[]
		self.y=[]
		self.z=[]
		self.occ=[]
		self.beta=[]
		self.details=[]
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
		# make full names out of local
		self.storedir=os.path.join(self.rootdir,self.storedir)
		self.workdir=os.path.join(self.rootdir,self.workdir)
		self.restart=False
		copyVarsToObjectByName(self,["restart"],inputvariables,optional=True)

	def optimizationType(self,inputvariables):
		""" scan the inputlines and see if you have Soma or Pathcvs: then parse the correct arguments """
		copyVarsToObjectByName(self,["pathtype"],inputvariables)		
		if  getattr(self,"pathtype").upper()=="SOMA" : 
			print "This is a SOMA run: need a single spring constant "	
			self.pathtype="SOMA"
	                copyVarsToObjectByName(self,["springconstant"],inputvariables)
		elif  getattr(self,"pathtype").upper()=="PCV" :
                        print "This is a PCV run "
			self.pathtype="PCV"
	                copyVarsToObjectByName(self,["springconstant_s"],inputvariables)
	                copyVarsToObjectByName(self,["springconstant_z"],inputvariables)
	                copyVarsToObjectByName(self,["lambdaval"],inputvariables)
		else:
			print "There is no such pathtype !!! ",getattr(self,"pathtype")
			sys.exit(2)
	def createDirs(self):
		""" this should prepare and create the dirs"""	
		# check if the working dir exist 
		if os.path.exists(self.storedir)==False :
			print "  The storedir does not yet exit : making it!"	 
		        os.mkdir(self.storedir)	
		if os.path.exists(self.workdir)==False :
			print "  The workdir does not yet exist: making it!"	 
		        os.mkdir(self.workdir)	
		os.chdir(self.workdir)
		for i in range (0,len(self.imagelist)):
			dirname="dir_"+str(i+1)	
                        self.imagelist[i].dirname=dirname
			if os.path.exists(os.path.join(self.workdir,dirname))==False :
				print "the dir "+dirname+" does not yet exit"	 
			        os.mkdir(os.path.join(self.workdir,dirname))	
			os.chdir(os.path.join(self.workdir,dirname))		
                        os.system("rm -rf *") #clean up a bit 
		os.chdir(self.rootdir)		
	def setDirs(self):
		""" this should only set the dirs for a restart"""	
		# check if the working dir exist 
		if os.path.exists(self.workdir)==False :
			print "the workdir does not yet exist: looks like it is not a restart"	 
			sys.exit()
                os.chdir(self.workdir)
		for i in range (0,len(self.imagelist)):
			dirname="dir_"+str(i+1)	
                        self.imagelist[i].dirname=dirname
			if os.path.exists(os.path.join(self.workdir,dirname))==False :
				print "the dir "+dirname+" does not yet exist: this is a rather bizarre restart "	 
				sys.exit()

		if os.path.exists(self.storedir)==False :
			print "the workdir does not yet exist: looks like it is not a restart"	 
			sys.exit()
        def loadStringIntoWorkdirs(self):
		""" Loads the frames in each workdir according soma/pcv optimization """
		os.chdir(self.workdir)
                for i in range (0,len(self.imagelist)):
			# if soma: put the all images	
			if self.pathtype=="PCV": # in pcvs all images are loaded 
				self.imagelist[i].filename=os.path.join(self.workdir,self.imagelist[i].dirname,"iter_"+str(self.round)+".dat")
				self.dumpImages(self.imagelist[i].filename,range(0,len(self.imagelist)))
				self.dumpPCVinput(self.workdir,self.imagelist[i].dirname,self.imagelist[i].filename,i+1)	
			elif self.pathtype=="SOMA": # soma must be splitted per image
				self.imagelist[i].filename=os.path.join(self.workdir,self.imagelist[i].dirname,"iter_"+str(self.round)+"_"+str(i+1)+".dat")
				self.dumpImages(self.imagelist[i].filename,[i])
				self.dumpSOMAinput(self.workdir,self.imagelist[i].dirname,self.imagelist[i].filename)	

	def dumpImages(self,filename,mylist):
		"""Dump a pdb on the filename with all the images on the list""" 
		f=open(filename,"w")			
		for i in mylist:
			for j in range(len(self.imagelist[i].details)):					
				buf="%s%8.3f%8.3f%8.3f%6.2f%6.2f\n"%(self.imagelist[i].details[j],self.imagelist[i].x[j],self.imagelist[i].y[j],self.imagelist[i].z[j],self.imagelist[i].occ[j],self.imagelist[i].beta[j]) 
				f.write(buf)
			f.write("END\n")
		f.close()

	def dumpSOMAinput(self,workdir,dirname,reference):
		"""prepare the SOMA input for plumed2"""
		f=open(os.path.join(workdir,dirname,"plumed.dat"),"w")	
		f.write("RMSD ...\n")
		f.write("  LABEL=rmsd \n")
		f.write("  REFERENCE "+reference+"\n")
		f.write("  TYPE=OPTIMAL\n")	
		f.write("...RMSD \n");
		f.write("uwall: UPPER_WALLS ARG=rmsd AT=0 KAPPA="+str(self.springconstant)+" EXP=2 \n")	
		f.write("PRINT ARG=rmsd_restraint,uwall.* STRIDE="+str(self.dumpfreq)+" FILE=colvar FMT=%12.8f\n")
                f.write("#\n# THIS BELOW IS THE STATISTICS PART FOR THE SPRING CALCULATION\n#\n")	
		f.write("avg_spring: AVERAGE ARG=rmsd_restraint,uwall.* STRIDE="+str(self.dumpfreq)+" USE_ALL_DATA\n")
		f.write("PRINT ARG=(avg_spring\.+) STRIDE="+str(self.dumpfreq)+" 100 FILE=colvar FMT=%12.8f\n")
		f.write("#\n# THIS BELOW IS THE STATISTICS PART FOR THE DERIVATIVES #\n#\n")
		f.write("RMSD ...\n")
		f.write("  LABEL=rmsd_stat \n")
		f.write("  REFERENCE "+reference+"\n")
		f.write("  SOMA_DERIVATIVES\n")	
		f.write("  TYPE=OPTIMAL\n")	
		f.write("...RMSD \n");
		f.write("avg: AVERAGE ARG=(rmsd_stat\.somader_.+) STRIDE="+str(self.dumpfreq)+" USE_ALL_DATA\n")
		f.write("PRINT ARG=(avg\..+) STRIDE="+str(self.dumpfreq)+" FILE=derivatives_averaged FMT=%12.8f")
		f.close()
	def dumpPCVinput(self,workdir,dirname,reference,sval):
		"""prepare the PCV input for plumed2"""
		f=open(os.path.join(workdir,dirname,"plumed.dat"),"w")	
		f.write("PATHMSD ...\n")
		f.write(" LABEL=path \n") 
		f.write(" REFERENCE="+reference+" \n")
		f.write(" LAMBDA="+str(self.lambdaval+0.)+"\n")
		f.write("... PATHMSD\n")
		f.write("uwall: UPPER_WALLS ARG=path.sss,path.zzz AT="+str(sval+0.)+",0 KAPPA="+str(self.springconstant_s+0.)+","+str(self.springconstant_z+0.)+" EXP=2 \n")	
                f.write("PRINT ARG=rmsd_restraint,uwall.* STRIDE="+str(self.dumpfreq)+" FILE=colvar FMT=%12.8f\n")
		f.write("#\n# THIS BELOW IS THE STATISTICS PART \n#\n")
		f.write("PATHMSD ...\n")
		f.write(" LABEL=path_stat \n") 
		f.write(" REFERENCE="+reference+" \n")
		f.write(" REFERENCE_DERIVATIVES\n ")
		f.write(" LAMBDA="+str(self.lambdaval+0.)+"\n")
		f.write("... PATHMSD\n")
		f.write("avg: AVERAGE ARG=(path_stat\.sss_refder_.+) STRIDE="+str(self.dumpfreq)+" USE_ALL_DATA\n")
		f.write("PRINT ARG=(avg\..+) STRIDE="+str(self.dumpfreq)+" FILE=derivatives_averaged FMT=%12.8f")
		f.close()

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
		self.template=os.path.join(os.getcwd(),self.template)
		if os.path.isfile(self.template)=="False":
			print "  File ",self.template," is not there"
			sys.exit(2)
		else:
			print "  File template : ",self.template
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
		# now check they exist for sure
		# topology must be local
		if os.path.isfile(os.path.join(os.getcwd(),self.topology))==False:	
			print "  File ",os.path.join(os.getcwd(),self.topology)," is not there "			
			sys.exit(2)
		else: #reassign the full path
			self.topology=os.path.join(os.getcwd(),self.topology)
		# set the environment variables
                os.environ["GMXDIR"]=self.gmxdir
                os.environ["GMXBIN"]=os.path.join(self.gmxdir,"bin")
                os.environ["GMXLDLIB"]=os.path.join(self.gmxdir,"lib")
                os.environ["GMXDATA"]=os.path.join(self.gmxdir+"share")
		# programs must have path that refers to the 	
		if os.path.isfile(os.path.join(os.path.join,"/bin",self.preprocessor))==False:
			print "  File ",os.path.join(os.getcwd(),self.preprocessor)," is not there "
			sys.exit(2)
		if os.path.isfile(os.path.join(os.path.join,"/bin",self.trjconv))==False:
			print "  File ",os.path.join(os.getcwd(),self.trjconv)," is not there "
			sys.exit(2)
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
	                if os.path.isfile(os.path.join(os.getcwd(),self.queuetemplate))==False:
	                        print "  File ",os.path.join(os.getcwd(),self.queuetemplate)," is not there "
       		                sys.exit(2)
                	else: #reassign the full path
                        	self.topology=os.path.join(os.getcwd(),self.queuetemplate)	
		if self.queue=="internal":
                	copyVarsToObjectByName(self,["nmaxprocs"],inputvariables)		
	
##################################################################################
# PathOptimizer object
##################################################################################
class PathOptimizer(object):
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
	#
       	# initialize data structure 
	# 
	# TODO is restart? structure should be already there, just check it
	# 
	if myString.restart==True:
		print "This is a restart run!"
		myString.setDirs()
		# TODO: reload string for a restart: just check the previous round is there and infer the round number
		sys.exit()
		pass
	else:
		# setup initial conditions: put the images in the directories 
		print "This run start from scratch!"
                myString.round=1
		myString.createDirs()
                myString.loadStringIntoWorkdirs()	
	#
       	# main loop
	#
	for i in range(myString.round,myString.round+myString.maxrounds): 
		print "Round ",i
		# prepare input for md
                print "************Preparing the umbrellas*************"	

		# just run 
		# read the derivatives 
		# calculate the mean forces
		# evolve
		# reparametrize


		# reinitialize
	
                # old ORAC trick: check if a "STOP" file is there
                if os.path.isfile("STOP")==True:
                        print "************FOUND STOP FILE: Game Over! *************"
                        sys.exit()
        sys.exit()


##################################################################################
# this is the main command executed
##################################################################################
doOptimization(sys.argv[1:])
