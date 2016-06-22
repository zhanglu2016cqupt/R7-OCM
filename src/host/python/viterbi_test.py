import numpy as np

import gsmlib.splibs as sp
import matplotlib.pyplot as plt

def readfile(fn):
	f = open(fn)
	l = []
	for line in f.readlines():
		line = line.replace("+-","-")
		a = complex(line)
		l.append(a)
	return np.array(l)
mafi = readfile("../../../data/mafi")
training = readfile("../../../data/training")
rhh = readfile("../../../data/rhh")

def toState(t,r_i):
	"""
	1  -> 1
	-1 -> 0
	"""
	s = 0
	for x in t:
		s *= 2
		if r_i == 1:
			if x.real>0:
				s+=1
		else:
			if x.imag>0:
				s+=1
		r_i = 1 -r_i
	return s

def s2s(s,r_i):
	"""
	inverse order
	rf = 1
	if = 0
	"""
	ret = np.zeros(5,dtype=complex)
	if r_i==1:
		inc = 1
	else:
		inc = 0
	for i in range(5):
		if (s&1)==1:
			ret[i] = 1.+0j
		else:
			ret[i] = -1.+0j
		s >>=1
		if (i+inc)%2 == 0:
			ret[i] *= 1.j
	print r_i,s,ret
	return ret


def table(r):
	t = np.zeros((2,32),dtype=complex)
	for r_i in range(2):
		for s in range(32):
			t[r_i][s]=np.dot(s2s(s,r_i),r)
	return t

def forward(t,m,start,r_i,l):
	(i,sn) = t.shape
	sn /= 2
	metrics = np.zeros((sn,l+1))
	tracback = np.zeros((sn,l),dtype=int)
	for i in range(sn):
		metrics[i,0]=-1e100
	metrics[start,0]=0
	for i in range(l):
		for s in range(sn/2):
			# shift in 0
			m00 = metrics[s,i]+(m[i]*t[r_i,s*2]).real
			m08 = metrics[s+sn/2,i]+(m[i]*t[r_i,s*2+sn]).real
			if m00>m08:
				metrics[s*2,i+1]=m00
				tracback[s*2,i]=0
			else:
				metrics[s*2,i+1]=m08
				tracback[s*2,i]=1
			# shift in 0
			m10 = metrics[s,i]+(m[i]*t[r_i,s*2+1]).real
			m18 = metrics[s+sn/2,i]+(m[i]*t[r_i,s*2+sn+1]).real
			if m10>m18:
				metrics[s*2+1,i+1]=m10
				tracback[s*2+1,i]=0
			else:
				metrics[s*2+1,i+1]=m18
				tracback[s*2+1,i]=1

		r_i = 1 - r_i
	end = metrics[:,l]
	ends = end.argmax()
	print "end state",ends
	ret = []
	es = ends
	for i in range(5):
		ret.append(es&1)
		es >>= 1

	for i in range(l-1,0,-1):
		b = tracback[ends,i]
		ret.append(b)
		ends /=2
		ends += b*sn/2

	return ret[::-1]

t = table(rhh)
fout = np.zeros(64,dtype=complex)
for i in range(64-5):
	ss = toState(training[i:i+5],i%2)
	r_i = i%2
	print "%4d"%ss,t[r_i][ss],mafi[42+2+i]
	fout[i]=t[r_i][ss]

x = forward(t,mafi[42+64-2:],2,1,len(mafi[42+64-2:]))
