import numpy as np
from Burst import *
import splibs
import viterbi_detector

class SBMessage(item):
	length = 39

class SBM0(SBMessage):
	pass

class SBM1(SBMessage):
	pass

class SBTraining(item):
	length = 64
	bits = [
		1,0,1,1,1,0,0,1,
		0,1,1,0,0,0,1,0,
		0,0,0,0,0,1,0,0,
		0,0,0,0,1,1,1,1,
		0,0,1,0,1,1,0,1,
		0,1,0,0,0,1,0,1,
		0,1,1,1,0,1,1,0,
		0,0,0,1,1,0,1,1]
	unmodulated = np.array(bits)*2 - 1
	modulated = item.gmsk_mapper(bits,complex(0.,-1.))
		
class SB(Burst):

	__field__ = [TB,SBM0,SBTraining,SBM1,TB,NGP]
	__name__ = "SB"
	__viterbi_cut = 2	
	__viterbi_f = TB.length+SBM0.length+SBTraining.length - __viterbi_cut
	def __init__(self):
		Burst.__init__(self)
		self.viterbi = viterbi_detector.viterbi_detector(5,156,SBTraining.modulated)
		
	def peekL(self):
		f = self.mapLData()
		return np.abs(self.channelEst(f,SBTraining.modulated))
	
	def peekS(self):
		self.chn = self.channelEst(self.recv,SBTraining.modulated)
		return np.abs(self.chn)
	
	def setChEst(self):
		#print len(self.chn),len(self.chn[Burst.trainingPos-32:Burst.trainingPos+32]),Burst.trainingPos
		self.cut_chn,self.cut_pos = splibs.maxwin(self.chn[Burst.trainingPos-32:Burst.trainingPos+32],Burst.chn_len)
		self.cut_pos += Burst.trainingPos-32
		self.bs = self.cut_pos-int(TB.length+SBM0.length)*Burst.fosr #maybe wrony
		self.ibs = int(self.bs)
		self.timing = self.bs-self.ibs
		self.be = self.ibs+int(Burst.length*Burst.fosr+Burst.chn_len+1)
		rhh = splibs.matchFilter( 
			  self.chn[self.cut_pos:self.cut_pos+Burst.chnMatchLength]
			, self.cut_chn
			, Burst.fosr
			, 0. )/float(SBTraining.length)

		self.rhh = np.zeros(len(rhh)*2-1,dtype=complex)
		self.rhh[:len(rhh)]=np.conj(rhh[::-1])
		self.rhh[len(rhh):]=rhh[1:]

		self.mafi = splibs.matchFilter(self.recv[self.ibs:self.be],self.cut_chn,Burst.fosr,self.timing)
		self.viterbi.table(self.rhh)
		msg = self.viterbi.forward(self.mafi)
		msg = self.viterbi.dediff(msg)
		self.sbm0 = msg[4:43]
		self.sbm1 = msg[43+64:43+64+39]
		
	def tofile(self,p):
		self.save = { 'rhh':self.rhh
					, 'mafi':self.mafi
					, 'training':SBTraining.modulated
				}
		for f in self.save:
			np.savetxt(p+f,self.save[f])
	
	def fromfile(self,p):
		for f in self.save:
			self.save[f]=np.savetxt(p+f)
	

	@staticmethod
	def overheadL():
		return TB.length+SBM0.length+Burst.large_overlap
	@staticmethod
	def overheadS():
		return TB.length+SBM0.length+Burst.small_overlap

def main():
	a = SB()
	a.dump()
	print a.getLen()
	print len(SBTraining.modulated)

if __name__ == '__main__':
	main()

