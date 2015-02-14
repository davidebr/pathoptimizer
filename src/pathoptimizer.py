#!/usr/bin/python
import sys
import os
import getopt
import shutil
import numpy as np
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
np.set_printoptions(precision=4,suppress=True,linewidth=120)
##################################################################################
# align
##################################################################################
def alignFirstOntoSecond(r1,r2,al): 
	""" perform an optimal alignment a la plumed2 of the first argument on top of the second"""
	# normalize weights
	#al=al/al.sum()
	# com of x1	
	rr1=np.copy(r1.reshape((-1,3)))
	com1=np.array([(rr1[:,0]*al).sum(),(rr1[:,1]*al).sum(),(rr1[:,2]*al).sum()])/al.sum()
	for i in range(3): rr1[:,i]=rr1[:,i]-com1[i]
	# com of x2
	rr2=np.copy(r2.reshape((-1,3)))
	com2=np.array([(rr2[:,0]*al).sum(),(rr2[:,1]*al).sum(),(rr2[:,2]*al).sum()])/al.sum()
	for i in range(3): rr2[:,i]=rr2[:,i]-com2[i]
	rr11=0.
	rr00=0.
	rr01=np.zeros(9).reshape((3,3))
	for i in range(rr1.shape[0]):rr00+=np.dot(rr1[i,:],rr1[i,:])*al[i]
	for i in range(rr2.shape[0]):rr11+=np.dot(rr2[i,:],rr2[i,:])*al[i]
	for i in range(rr1.shape[0]):rr01+=np.outer(rr1[i,:],rr2[i,:])*al[i]
	# go back to colun ordering
	m=np.empty(16).reshape((4,4))
	m[0,0]=2.0*(-rr01[0,0]-rr01[1,1]-rr01[2,2])
	m[1,1]=2.0*(-rr01[0,0]+rr01[1,1]+rr01[2,2])
	m[2,2]=2.0*(+rr01[0,0]-rr01[1,1]+rr01[2,2])
	m[3,3]=2.0*(+rr01[0,0]+rr01[1,1]-rr01[2,2])
	m[0,1]=2.0*(-rr01[1,2]+rr01[2,1])
	m[0,2]=2.0*(+rr01[0,2]-rr01[2,0])
	m[0,3]=2.0*(-rr01[0,1]+rr01[1,0])
	m[1,2]=2.0*(-rr01[0,1]-rr01[1,0])
	m[1,3]=2.0*(-rr01[0,2]-rr01[2,0])
	m[2,3]=2.0*(-rr01[1,2]-rr01[2,1])
	m[1,0] = m[0,1]
	m[2,0] = m[0,2]
	m[2,1] = m[1,2]
	m[3,0] = m[0,3]
	m[3,1] = m[1,3]
	m[3,2] = m[2,3]
	eigenval, eigenvec = np.linalg.eig(m)
	dist=eigenval[0]+rr00+rr11
	q=eigenvec[:,0]
	#print "DISTANCE ",dist,eigenval[0]
	rotation=np.empty(9).reshape((3,3))
	rotation[0,0]=q[0]*q[0]+q[1]*q[1]-q[2]*q[2]-q[3]*q[3]
	rotation[1,1]=q[0]*q[0]-q[1]*q[1]+q[2]*q[2]-q[3]*q[3]
	rotation[2,2]=q[0]*q[0]-q[1]*q[1]-q[2]*q[2]+q[3]*q[3]
	rotation[0,1]=2*(+q[0]*q[3]+q[1]*q[2])
	rotation[0,2]=2*(-q[0]*q[2]+q[1]*q[3])
	rotation[1,2]=2*(+q[0]*q[1]+q[2]*q[3])
	rotation[1,0]=2*(-q[0]*q[3]+q[1]*q[2])
	rotation[2,0]=2*(+q[0]*q[2]+q[1]*q[3])
	rotation[2,1]=2*(-q[0]*q[1]+q[2]*q[3])
	# this in plumed2 is the matrix that aligns the reference onto the runnig, make the translate
	rotation=np.transpose(rotation)
	#print "ROTATION ",rotation
	# now rotate running frame and dump it
	# take the vector fresh
	rr1=np.copy(r1.reshape((-1,3)))
	rr1_al=np.empty(r1.size).reshape((-1,3))
        for i in range(rr1.shape[0]): rr1_al[i,:]=np.dot(rotation,rr1[i,:]-com1)+com2	
	rr1_al=rr1_al.reshape((-1))
	dd={"dist":dist,"rotation":rotation,"rotated":rr1_al}
	return dd 
	
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
#
##################################################################################
def readPlumedPrintOutput(filename):
		if os.path.isfile(filename)=="False":
			return False
		else :
			f=open(filename,"r")
			for line in f:
				if line[0:2]=="#!": # this is the header
					header=line.split()[3:] #exclude time
				else:
					data=map(float,line.split()[1:])  # I overwrite this since the average is supposed to be already calculated by plumed
			f.close()
		assert len(header)==len(data)	
		# create a dictionary, maybe simple to parse
		d={}
		for name,val in zip(header,data):
			d[name]=val	
		return d

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
			# create also numpy like object, to do easy computation
			img.pos=np.empty( len(pdb)*3 ) 
			img.occ=np.empty(len(pdb))
			img.beta=np.empty(len(pdb))
			img.pdb2ind={}
			img.ind2pdb={}
			for i in range(len(pdb)):
				img.details.append(pdb[i][0])
				img.pdb2ind[pdb[i][0].split()[1]]=i
				img.ind2pdb[i]=[pdb[i][0].split()[1]]
				img.pos[i*3+0]=pdb[i][1]
				img.pos[i*3+1]=pdb[i][2]
				img.pos[i*3+2]=pdb[i][3]
				img.occ[i]=(pdb[i][4])
				img.beta[i]=(pdb[i][5])
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
	# this is needed to translate from plumed to numpy structure 
	comp2ind={'x':0,'y':1,'z':2}
	ind2comp={0:'x',1:'y',2:'z'}
	def __init__(self):
		self.details=[]
	def parseRunOutput(self,parentString,index):
		""" retrieve the output and attach to the string according the type of calculation performed (SOMA/PCVs)"""
                if  parentString.pathtype=="SOMA" :
			print "  Retrieving SOMA statistics for image ",index
			# average_meanforces 
			a=readPlumedPrintOutput("average_meanforces")
			assert isinstance(a, (dict))  
			for i in a.keys():
				setattr(self,i.split(".")[-1],a[i])
				#print "Added ",i.split(".")[-1]," : ",getattr(self,i.split(".")[-1])	
			# average_derivatives 
			a=readPlumedPrintOutput("average_derivatives")
			# reshape in numpy array that makes sense	
			assert isinstance(a, (dict))  
			self.derivatives=np.empty(len(self.occ)*3)
			for i in a.keys():
				ind=self.pdb2ind[i.split(".")[-1].split("_")[1]]
				comp=self.comp2ind[i.split(".")[-1].split("_")[2]]
				#print "Added ",i.split(".")[-1],ind,comp
				self.derivatives[ind*3+comp]=a[i]
			#print self.derivatives
			# average_outerproduct  
			print "  derivatives are read "
			a=readPlumedPrintOutput("average_outerproduct")
			assert isinstance(a, (dict))  
			self.outerproduct=np.empty((len(self.occ)*3,len(self.occ)*3))
			for i in a.keys():
				ind1=self.pdb2ind[i.split(".")[3].split("_")[1]]
				comp1=self.comp2ind[i.split(".")[3].split("_")[2]]
				ind2=self.pdb2ind[i.split(".")[4].split("_")[1]]
				comp2=self.comp2ind[i.split(".")[4].split("_")[2]]
				#print i.split(".")[3:],ind1,comp1,ind2,comp2,a[i]
				self.outerproduct[ind1*3+comp1,ind2*3+comp2]=a[i]					
			#print self.outerproduct
			print "  outerproduct is read "
		elif parentString.pathtype=="PCV" :
			print "  Retrieving PCV statistics for image ", index
			a=readPlumedPrintOutput("average_meanforces")
			assert isinstance(a, (dict))
                        for i in a.keys():
                                setattr(self,i.split(".")[-1],a[i])
                                #print "Added ",i.split(".")[-1]," : ",getattr(self,i.split(".")[-1])
                        # average_derivatives
                        a=readPlumedPrintOutput("average_derivatives")
                        # reshape in numpy array that makes sense
                        assert isinstance(a, (dict))
			self.derivatives_s=np.empty((len(parentString.imagelist),len(self.occ)*3))
			self.derivatives_z=np.empty((len(parentString.imagelist),len(self.occ)*3))
			for i in a.keys():
				frame=i.split(".")[-1].split("_")[3]
				ind=self.pdb2ind[i.split(".")[-1].split("_")[5]]
				comp=self.comp2ind[i.split(".")[-1].split("_")[6]]
				cv=i.split(".")[-1].split("_")[0]
				#print "Added ",i.split(".")[-1],frame,ind,comp,cv	
				if cv=="sss":
					self.derivatives_s[frame,ind*3+comp]=a[i]
				elif cv=="zzz":
					self.derivatives_z[frame,ind*3+comp]=a[i]
				else:
					print "Error while reading derivatives from PCVs"
					sys.exit()
			#print  self.derivatives_s
			#print self.derivatives_z
				
			
				
##################################################################################
# the string is a collection of images plus information on how to run it
# which dir, soma/pcv , spring constant(s)
# and all the various plumed-related things
##################################################################################
class StringClass(object):
	""" this class contains the whole string and the setup on directory organization"""
	def __init__(self,inputvariables):
		""" read the string from the inputlines"""
		self.test=False
		# these are the properties required for this input: if you need any new, just plug it in here: checks are automatically performed
		needednames=["string","storedir","workdir","dumpfreq","evolstep","discard","maxrounds","optends","samplefreq"]
		print "reading input file for images"
		self.optends=False
		copyVarsToObjectByName(self,needednames,inputvariables)
		# use the variables from here
       	 	self.imagelist=readPDB(self.string)
		# type of optimization: soma or pathcvs
		self.optimizationType(inputvariables)
		# check that the samplefreq and dumpreq make sense
		if self.samplefreq>self.dumpfreq or self.dumpfreq%self.samplefreq!=0:
			print "dumpfreq must be a multiple of samplefreq"
			sys.exit(2)
       	 	self.rootdir=os.getcwd()
		# make full names out of local
		self.storedir=os.path.join(self.rootdir,self.storedir)
		self.workdir=os.path.join(self.rootdir,self.workdir)
		self.restart=False
		copyVarsToObjectByName(self,["restart","test"],inputvariables,optional=True)

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
				buf="%s%8.3f%8.3f%8.3f%6.2f%6.2f\n"%(self.imagelist[i].details[j],self.imagelist[i].pos[j*3+0],self.imagelist[i].pos[j*3+1],self.imagelist[i].pos[j*3+2],self.imagelist[i].occ[j],self.imagelist[i].beta[j]) 
				f.write(buf)
			f.write("END\n")
		f.close()

	# TODO: mechanism for skipping the initial part
	def dumpSOMAinput(self,workdir,dirname,reference):
		"""prepare the SOMA input for plumed2"""
		f=open(os.path.join(workdir,dirname,"plumed.dat"),"w")	
		filecontent="""
#
# this imposes just the bias
#
RMSD ...
  LABEL=rmsd
  REFERENCE={reference}	
  TYPE=OPTIMAL	
  SQUARED
... RMSD
wall: MOVINGRESTRAINT ARG=rmsd STEP0=0 AT0=0. KAPPA0={springconstant}
#
# this below is for a statistics on the bias
#
RMSD ...
  LABEL=rmsd_stat
  REFERENCE={reference}
  SOMA_DERIVATIVES
  TYPE=OPTIMAL
  SQUARED
... RMSD
meanforce:  MATHEVAL ARG=rmsd_stat.rmsd VAR=d  PERIODIC=NO FUNC={springconstant}*d
avg_meanforces: AVERAGE ARG=rmsd_stat.rmsd,meanforce STRIDE={samplefreq} USE_ALL_DATA
avg_derivatives: AVERAGE ARG=(rmsd_stat\.somader_.+) STRIDE={samplefreq} USE_ALL_DATA
PRINT ARG=(avg_derivatives\..+) STRIDE={dumpfreq} FILE=average_derivatives FMT=%12.8e
PRINT ARG=(avg_meanforces\..+) STRIDE={dumpfreq} FILE=average_meanforces FMT=%12.8e
#
# this is the outer product for metrics scaling
#
outer: OUTERPRODUCT ARG=(rmsd_stat\.somader_.+)
avg_outer: AVERAGE ARG=(outer\..+) STRIDE={samplefreq} USE_ALL_DATA
PRINT ARG=(avg_outer\..+) STRIDE={dumpfreq} FILE=average_outerproduct FMT=%12.8e
"""
        	context = {
        	        "reference":reference,
        	        "dumpfreq":self.dumpfreq,
        	        "samplefreq":self.samplefreq,
        	        "springconstant":self.springconstant
        	}
        	f.write(filecontent.format(**context))
		f.close()
	
	# TODO: mechanism for skipping the initial part
	def dumpPCVinput(self,workdir,dirname,reference,sval):
		"""prepare the PCV input for plumed2"""
		f=open(os.path.join(workdir,dirname,"plumed.dat"),"w")	
		filecontent="""
#
# this imposes just the bias
#
PATHMSD ...
  LABEL=path
  REFERENCE={reference}
  LAMBDA={lambdaval}
... PATHMSD
wall: MOVINGRESTRAINT ARG=path.sss,path.zzz STEP0=0 AT0={sval},0. KAPPA0={springconstant_s},{springconstant_z}
#
# this below is for a statistics on the bias
#
PATHMSD ...
  LABEL=path_stat
  REFERENCE={reference}
  LAMBDA={lambdaval}
  REFERENCE_DERIVATIVES
... PATHMSD
meanforce_s:  MATHEVAL ARG=path_stat.sss VAR=s  PERIODIC=NO FUNC={springconstant_s}*({sval}-s)
meanforce_z:  MATHEVAL ARG=path_stat.zzz VAR=z  PERIODIC=NO FUNC={springconstant_z}*z
avg_meanforces: AVERAGE ARG=path_stat.sss,path_stat.zzz,meanforce_s,meanforce_z STRIDE={samplefreq} USE_ALL_DATA
avg_derivatives: AVERAGE ARG=(path_stat\.sss_refder_.+|path_stat\.zzz_refder_.+) STRIDE={samplefreq} USE_ALL_DATA
PRINT ARG=(avg_derivatives\..+) STRIDE={dumpfreq} FILE=average_derivatives FMT=%12.8e
PRINT ARG=(avg_meanforces\..+) STRIDE={dumpfreq} FILE=average_meanforces FMT=%12.8e
"""
        	context = {
        	        "reference":reference,
        	        "dumpfreq":self.dumpfreq,
        	        "samplefreq":self.samplefreq,
        	        "springconstant_s":self.springconstant_s,
        	        "springconstant_z":self.springconstant_z,
        	        "lambdaval":self.lambdaval,
        	        "sval":str(sval+0.),
        	}
        	f.write(filecontent.format(**context))
		f.close()
        def prepareUmbrellas(self,myMDParser):
		""" prepares the umbrella sampling runs (md engine related)"""	
		if self.test: return 
                os.chdir(self.workdir)
		for i in range (0,len(self.imagelist)):
			os.chdir(self.imagelist[i].dirname)		
			########################################
			# prepare the MD input for this image
			########################################
			myMDParser.printMDInput(self.round,self.rootdir)
			########################################
			# move the coordinates in the right place
			########################################
		        myMDParser.copyStart(i,self.round,self.rootdir)
			# note that plumed-related is already there from the string handling
			os.chdir(self.workdir)		
		# now you should be in the root directory
		os.chdir(self.rootdir)		
		#sys.exit(2)	
        def runDynamics(self,myMDParser,myQueue):
		""" Just run the dynamics """
		if self.test: return 
		os.chdir(self.workdir)
		# clean the queuestack
		for i in range (0,len(self.imagelist)):
			os.chdir(self.imagelist[i].dirname)		
			myMDParser.programLauncher(self.rootdir,self.workdir,i+1,myQueue);
			os.chdir(self.workdir)
		# according to the queue system, take care of execution

		# copy/rename data if needed

		# go back home
		os.chdir(self.rootdir)		

        def parseRunOutput(self,myMDParser):
		""" Enter each dir and read the various infos """
		os.chdir(self.workdir)
		# clean the queuestack
		for i in range (0,len(self.imagelist)):
			os.chdir(self.imagelist[i].dirname)		
			# pass the string itself to get the kind of run 
			self.imagelist[i].parseRunOutput(self,i)
			os.chdir(self.workdir)
		# go back home
		os.chdir(self.rootdir)		

	def evolve(self):
		""" Evolving the frames according to the rule SOMA/PCV """
		# TODO: plug a smarter evolution like cg?
		if self.pathtype=="PCV":
	                for i in range (0,len(self.imagelist)):			
				# calculate the coupling matrix
				# evolve
				pass		
		elif self.pathtype=="SOMA":
			# sum the derivative over all the images
	                for i in range (0,len(self.imagelist)):			
				pass
			# it is a functional: should depend on the stepping?

	def freeEnergy(self):
		""" The free energy calculation for PCVs or soma """
                if self.pathtype=="PCV":
			i=0
			#d=alignFirstOntoSecond(self.imagelist[i+1].pos,self.imagelist[i].pos,self.imagelist[i+1].occ)
                        for i in range (0,len(self.imagelist)):
                                pass
                elif self.pathtype=="SOMA":
                        for i in range (0,len(self.imagelist)):
				pass

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
		if os.path.isfile(os.path.join(os.environ.get("GMXBIN"),self.preprocessor))==False:
			print "  File ",os.path.join(os.environ.get("GMXBIN"),self.preprocessor)," is not there "
			sys.exit(2)
		if os.path.isfile(os.path.join(os.environ.get("GMXBIN"),self.trjconv))==False:
			print "  File ",os.path.join(os.environ.get("GMXBIN"),self.trjconv)," is not there "
			sys.exit(2)
		# the programpath
		if os.path.isfile(os.path.join(os.environ.get("GMXBIN"),self.programpath))==False:
			print "  File ",os.path.join(os.environ.get("GMXBIN"),self.programpath)," is not there "
			sys.exit(2)
		self.programpath=os.path.join(os.environ.get("GMXBIN"),self.programpath)
		self.trjconv=os.path.join(os.environ.get("GMXBIN"),self.trjconv)
		self.preprocessor=os.path.join(os.environ.get("GMXBIN"),self.preprocessor)
	
			
	def printMDInput(self,round,rootdir):
		"""prepare the md input in cwd according to the parameters provided"""
		print "  Preparing MD input for "+self.program
		if self.program=="GROMACS":
			print "  This prepare a GROMACS input"
                        m=open("md.mdp","w") 
 		 	if os.path.isfile(self.template)==False:
				print "the template input file is not existing: " +rootdir+"/"+self.template
				sys.exit(2)	
                        f=open(self.template,"r") 

			#m.write("outputname  outcoord_"+str(round)+"\n")
			#m.write("coordinates  coord_"+str(round)+".coor \n")
 		 	if os.path.isfile(self.topology)==False:
				print "the topology file is not existing: "+self.topology
				sys.exit(2)	

 			# read the old parameter file and substitute the new one: keep the xtc for dumping 
                        m.write("nsteps = "+str(self.steps)+"\n") 
                        for line in f:
				# split into fields
				fields=line.split()	
				#for ff in fields:
                                ind1=line.find("nsteps")
				if ind1 <0  :
					m.write(line)
			m.close()	
			m=open("gromacs_paramline","w")
                        m.write(" -s topol.tpr  -x outcoord_"+str(round)+".xtc -c outcoord_"+str(round)+".gro -plumed plumed.dat ")
			m.close()	
			# do the grompp later in the real execution
		else:
			print "ERROR: the program "+self.program+" is not known "
			sys.exit() 

	def copyStart(self,index,round,rootdir):
		""" copy the start conformation prior to start (preprocess and) dynamics"""
		# if this is the round that means that the initial files should be in the root directory and 
		# not in the store directory
		if(round==1):
			print "copying from the starting points"		 
			if(self.program=="GROMACS"):
				myfile=os.path.join(rootdir,"coor_"+str(index+1)+".gro")
				if os.path.isfile(myfile)==False:
                                	print "the file "+myfile+" is not existing"
                                	sys.exit(2)	
				shutil.copy2(myfile,os.path.join(os.getcwd(),"coor_1.gro"))
				# now make the grompp
				# you need the grompp, the top, the gro  
				mycommand=self.preprocessor+" -f md.mdp  -c coor_1.gro -p "+self.topology
 				print mycommand
				proc=subprocess.Popen(mycommand,shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
				f=open("grompp.stdout","w")	
				for l in proc.stdout.readlines():
				  f.write(l)
				f.close()
				f=open("grompp.stderr","w")	
				for l in proc.stderr.readlines():
				  f.write(l)
				f.close()
			else:	
				print "PROGRAM NOT KNOWN"
				sys.exit()	

		else:
			# the file should be already in place (as restart or from the previous run which will be newly carried out) 
			if(self.program=="GROMACS"):
				file="coor_"+str(round)+".gro"
				if os.path.isfile(file)==False:
					print "Startfile not in place"
					sys.exit()	
                                # bring evthing into the box? 
				mycommand=self.preprocessor+" -f md.mdp  -c coor_"+str(round)+".gro -p "+self.structure 
 				print mycommand
				proc=subprocess.Popen(mycommand,shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
				f=open("grompp.stdout","w")	
				for l in proc.stdout.readlines():
				  f.write(l)
				f.close()
				f=open("grompp.stderr","w")	
				for l in proc.stderr.readlines():
				  f.write(l)
				f.close()
			else:	
				print "PROGRAM NOT KNOWN"
				sys.exit()	
	def programLauncher(self,rootdir,workdir,index,myQueue):
		"""takes care of launching the md program"""
		this_dir=os.getcwd()
		print "NOW I AM IN DIR: "+this_dir
		if(self.program=="GROMACS"):
     			f=open("gromacs_paramline","r")
                        for line in f:
                                command=self.preprogram+" "+self.programpath+line
                                break
                        f.close()

		if myQueue.queue == "serial" :	
			print "NOW I AM RUNNING SERIALLY: "+command
			sys.stdout.flush()
			# just run the command
                        proc=subprocess.Popen(command,shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
                        f=open("run.stdout","w")
                        for l in proc.stdout.readlines():
                          f.write(l)
                        f.close()
                        f=open("run.stderr","w")
                        for l in proc.stderr.readlines():
                          f.write(l)
                        f.close()
		elif myQueue.queue == "internal" : 
			print "NOW I AM PREPARING TO RUN WITH INTERNAL QUEUE: "+command
			sys.stdout.flush()
			print "not implemented yet"
			sys.exit()
			# prepare the script and submit it to the internal queue system
		elif myQueue.queue == "external" : 
			print "NOW I AM PREPARING TO RUN WITH EXTERNAL QUEUE SYSTEM : "+command
			sys.stdout.flush()
			print "not implemented yet"
			sys.exit()
			# prepare the script and submit it to the exernal queue system (PBS) by using the provided template


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
	if myString.restart==True or myString.test==True:
		if myString.restart==True: 
			print "This is a restart run!"
			# TODO: reload string for a restart: just check the previous round is there and infer the round number
			sys.exit()
		if myString.test==True: 
			print "This is a test run (i.e. does not run dynamics. Just uses the statistics that is already there)!"
			# assign myString.round
			myString.round=1
		myString.setDirs()
	else:
		# setup initial conditions: put the images in the directories 
		print "This run start from scratch!"
                myString.round=1
		myString.createDirs()
                myString.loadStringIntoWorkdirs()	
	#
       	# main loop
	#
	startround=myString.round
	for myString.round in range(startround,startround+myString.maxrounds): 
		print "Round ",myString.round

                print "************Preparing the umbrellas*************"	
		myString.prepareUmbrellas(myMDParser)

                print "************Running the dynamics*************"
                myString.runDynamics(myMDParser,myQueue)
		print "************Parse Outputs*************"
		# read the derivatives 
                myString.parseRunOutput(myMDParser)
		# calculate the free energy
		myString.freeEnergy()
		# evolve
		myString.evolve()
		# reparametrize 

		if myString.test==True: sys.exit()	
		# store data 
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
