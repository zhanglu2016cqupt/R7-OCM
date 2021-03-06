import reg_define as reg
from const import *
import time
import sys
if c_system=='Linux':
	import dev_mem
import math
import axi2s_c
import ad9361PLL

class AD9361_c:
	def __init__(self):
		if c_system=='Linux':
			self.dev = dev_mem.dev_mem(AD9361_SPI_BASE,AD9361_SPI_SIZE)
			self.ref = 25e6
		self.api = {
			  'arreg':self.apiread
			, 'awreg':self.apiwrite
		}
		self.webapi = {
			"tx":{  "set":{"freq":self.Set_Tx_freq,"gain":self.Set_Tx_Gain}
						, "get":{"freq":self.Get_Tx_freq,"gain":self.Get_Tx_Gain}
						}
		,	"rx":{  "set":{"freq":self.Set_Rx_freq,"gain":self.Set_Rx_Gain}
						, "get":{"freq":self.Get_Rx_freq,"gain":self.Get_Rx_Gain}
						}
		};

		self.order = {
			  'SPIWrite'     : self.API_SPIWrite
			, 'SPIRead'      : self.API_SPIRead
			, 'RESET_DUT'    : self.API_RESET_DUT
			, 'WAIT'         : self.API_WAIT
			, 'WAIT_CALDONE' : self.API_WAIT_CALDONE
			}



		"""
		Reg 0x16
    D7   D6   D5     D4     D3     D2        D1   D0
    RXBB TXBB RXQuad TXQuad RXGain TXMonitor RFDC Baseband

		WAIT_CALDONE	BBPLL,2000	// Wait for BBPLL to lock, Timeout 2sec, Max BBPLL VCO Cal Time: 552.960 us (Done when 0x05E[7]==1)
		WAIT_CALDONE	RXCP,100	// Wait for CP cal to complete, Max RXCP Cal time: 737.280 (us)(Done when 0x244[7]==1)
		WAIT_CALDONE	TXCP,100	// Wait for CP cal to complete, Max TXCP Cal time: 737.280 (us)(Done when 0x284[7]==1)
		WAIT_CALDONE	RXFILTER,2000	// Wait for RX filter to tune, Max Cal Time: 89.355 us (Done when 0x016[7]==0)
		WAIT_CALDONE	TXFILTER,2000	// Wait for TX filter to tune, Max Cal Time: 45.502 us (Done when 0x016[6]==0)
		WAIT_CALDONE	BBDC,2000	// BBDC Max Cal Time: 40400.000 us. Cal done when 0x016[0]==0
		WAIT_CALDONE	RFDC,2000	// RFDC Max Cal Time: 549654.000 us Cal done when 0x016[1]==0
		WAIT_CALDONE	TXQUAD,2000	// Wait for cal to complete (Done when 0x016[4]==0)
		"""
		self.cal_db = {
			'BBPLL'		  :{'reg':0x05e,'mask':0x80,'done':0x80},
			'RXCP' 		  :{'reg':0x244,'mask':0x80,'done':0x80},
			'TXCP' 		  :{'reg':0x284,'mask':0x80,'done':0x80},
			'RXFILTER'  :{'reg':0x016,'mask':0x80,'done':0x00},
			'TXFILTER'  :{'reg':0x016,'mask':0x40,'done':0x00},
			'RXQUAD'    :{'reg':0x016,'mask':0x20,'done':0x00},
			'TXQUAD'    :{'reg':0x016,'mask':0x10,'done':0x00},
			'RXGAIN'    :{'reg':0x016,'mask':0x08,'done':0x00},
			'TXMON'     :{'reg':0x016,'mask':0x04,'done':0x00},
			'RFDC'      :{'reg':0x016,'mask':0x02,'done':0x00},
			'BBDC'      :{'reg':0x016,'mask':0x01,'done':0x00}
		}
		self.ensm_db = ['SLEEP/WAIT','CALIBRATION','CALIBRATION', 'CALIBRATION', 'WAIT to ALERT delay', 'ALERT', 'TX', 'TX FLUSH', 'RX', 'RX FLUSH', 'FDD', 'FDD FLUSH']
		self.cntr = axi2s_c.axi2s_c()
		self.pll = ad9361PLL.ad9361PLL(25e6)

	def apiread(self,argv):
		if 'reg' in argv:
			return {'ret':'ok','data':hex(self.readByte(int(argv.reg,16)))}
		else:
			return {'ret':'err','res':'reg not given'}

	def apiwrite(self,argv):
		if 'reg' in argv and 'value' in argv:
			self.writeByte(int(argv.reg,16),int(argv.value,16))
			return {'ret':'ok'}
		else:
			return {'ret':'err','res':'reg or value not given'}


	def cntrWrite(self,addr,d):
		self.cntr.write(addr,d)

	def init(self):
		pass
	def deinit(self):
		self.dev.deinit()

	def readreg(self,regname):
		if c_system=='Linux':
			r = self.dev.ioread(reg.addr[regname])
		else:
			r = 0
			print 'R:',regname, hex(r)
		return r
	
	def writereg(self,regname,data):
		if c_system=='Linux':
			self.dev.iowrite(reg.addr[regname],data)
		else:
			print 'W:',regname, hex(data)

	def spi_op(self,addr,data,wop):
		H8 = addr>>8
		H8 = H8 & 0x3
		b = len(data)
		l = (b-1)&0x7
		H8 = H8 | (l<<4)
		if wop==1:
			H8 = H8 | 0x80
		HL = addr & 0xff
		self.writereg('SPI_Config',0x4015)
		self.writereg('SPI_Tx_data',H8)
		self.writereg('SPI_Tx_data',HL)
		for i in range(b):
			self.writereg('SPI_Tx_data',data[i])
		r = 0
		#while(r==0):
		r = self.readreg('SPI_Intr_status')&0x2
		#	print "Tx FIFO underflow:",r
		self.writereg('SPI_Config',0x7c15)
		RH = self.readreg('SPI_Rx_data')
		RL = self.readreg('SPI_Rx_data')
		for i in range(b):
			data[i] = self.readreg('SPI_Rx_data')
		#print "Read:",RH,RL,data[:]
		return data
		
	def readByte(self,addr):
		data=[0xff]
		data = self.spi_op(addr,data,0)
		print "R: [0x%04x]:0x%02x"%(addr,data[0])
		return data[0]

	def writeByte(self,addr,d):
		data = [d]
		data = self.spi_op(addr,data,1)
		print "W: [0x%04x]:0x%02x"%(addr,d)

	def RESET_FPGA(self):
		pass

	def API_RESET_DUT(self,args):
		self.cntrWrite('AD9361_RST',0)
		self.cntrWrite('AD9361_RST',1)

	def BlockWrite(self):
		pass

	def SPIWrite(self,addr,data):
		self.writeByte(addr,data)

	def SPIRead(self,addr):
		return self.readByte(addr)
	
	def ReadPartNumber(self):
		pass

	def WAIT_CALDONE(self,module,timeout):
		time.sleep(float(timeout)/1000.)

	def API_SPIWrite(self,args):
		self.SPIWrite(int(args[0],16),int(args[1],16))
	
	def API_SPIRead(self,args):
		self.SPIRead(int(args[0],16))

	def API_WAIT(self,args):
		t = float(args[0])
		time.sleep(t/1000.)

	def API_WAIT_CALDONE(self,args):
		m = args[0]
		t = int(args[1])
		if m in self.cal_db:
			while(t>0):
				modu = self.cal_db[m]
				r = self.SPIRead(modu['reg']) & modu['mask']
				if r==modu['done']:
					break
				time.sleep(0.01)
				t -= 10

	def RFFreqCalc(self,f):
		VCO_Divider = math.floor(math.log(12e9/f)/math.log(2.))
		F_RFPLL = (2**VCO_Divider)*f
		n = F_RFPLL/(self.ref*2)
		N_integer = int(math.floor(n))
		N_fractional = int(round(8388593.*(n-N_integer)))
		return (int(VCO_Divider)-1,N_integer,N_fractional)

	def RFWord2Freq(self,VCO_Divider,F):
		VCO_Divider += 1
		N_F = F[4]*65536+F[3]*256+F[2]
		N_I = F[1]*256+F[0]
		n = float(N_I)+float(N_F)/8388593.
		f = (n*self.ref*2.)/float(2**VCO_Divider) 
		return f

	def Get_freq(self,Base=0x271):
		div = self.readByte(0x5)
		if Base==0x271:
			div = (div>>4)&0xf
		else:
			div = div&0xf
		F = []
		for i in range(5):
			F.append(self.readByte(Base))
			Base += 1
		return self.RFWord2Freq(div,F)
	
	def Set_freq(self,f,Base=0x271):
		self.cntrWrite('AD9361_EN',0)
		(D,I,F)=self.RFFreqCalc(f)
		div = self.readByte(0x5)
		div &= 0xf
		div |= D<<4
		W = []
		W.append(I&0xff)
		W.append((I>>8)&0x3)
		W.append(F&0xff)
		F >>= 8
		W.append(F&0xff)
		F >>= 8
		W.append(F&0x7f)
		for i in range(5):
			self.writeByte(Base,W[i])
			Base += 1
		self.writeByte(5,div)
	def disable_FDD(self):
		r = self.ENSM(1)
		timeout = 10
		while r!=0x5:
			self.cntrWrite('AD9361_EN',1)
			time.sleep(0.001)
			self.cntrWrite('AD9361_EN',0)
			time.sleep(0.001)
			r = self.ENSM(1)
			timeout -= 1
			if timeout<0:
				break

	def Check_FDD(self):
		r = self.ENSM(1)
		timeout = 10
		while r!=0xa:
			self.cntrWrite('AD9361_EN',0)
			time.sleep(0.001)
			self.cntrWrite('AD9361_EN',1)
			time.sleep(0.001)
			r = self.ENSM(1)
			timeout -= 1
			if timeout<0:
				break

	def Set_Tx_freq(self,f):
		
		#self.disable_FDD()
		D,reg = self.pll.Set_freq(f)
		reg = self.pll.rx2tx(reg)
		oldD = self.readByte(5)
		oldD &= 0xf
		oldD |= D<<4
		self.writeByte(0x27d,0)
		for (r,v) in reg:
			self.writeByte(r,v)
		self.writeByte(5,oldD)
		#self.API_WAIT_CALDONE(["TXCP","100"])
		#self.Check_FDD()

	
	def Set_Rx_freq(self,f):
		#self.disable_FDD()
		
		self.writeByte(0x23d,0)
		D,reg = self.pll.Set_freq(f)
		oldD = self.readByte(5)
		oldD &= 0xf0
		oldD |= D&0xf
		for (r,v) in reg:
			self.writeByte(r,v)
		self.writeByte(5,oldD)
		#self.API_WAIT_CALDONE(["RXCP","100"])
		#self.Check_FDD()
		
	def Get_Tx_freq(self):
		return self.Get_freq(0x271)

	def Get_Rx_freq(self):
		return self.Get_freq(0x231)
	
	def Set_Tx_Gain(self,g,p):
		d = int(round(0-g*4.))
		if d>=0 and d<360:
			if p==1:
				Base = 0x73
			else:
				Base = 0x75
			self.writeByte(Base,d&0xff)
			self.writeByte(Base+1,(d>>8)&1)

	def Get_Tx_Gain(self,p):
		if p==1:
			Base = 0x73
		else:
			Base = 0x75
		d =	self.readByte(Base+1)&1
		d *= 256
 		d += self.readByte(Base)&0xff
 		g = 0.-float(d)/4.
 		return g

	def Set_Rx_Gain(self,g,p):
		d = int(g)
		if d>=0 and d<=0x4c:
			if p==1:
				Base = 0x109
			else:
				Base = 0x10c
			self.writeByte(Base,d)

	def Get_Rx_Gain(self,p):
		if p==1:
			Base = 0x109
		else:
			Base = 0x10c
		return self.readByte(Base)

	def ENSM(self,p=None):
		r = self.readByte(0x17)&0xf
		if p and r<12:
			print 'ENSM:',r,self.ensm_db[r]
		return r

	def CalRXQUAD(self):
		"""
		1) Refer to the AD9361 Evaluation Software generated script for setup values for registers 0x186, 0x187, 0x168, 0x16F
		2) Move the AD9361 into the ALERT state
		3) Ensure both RF synthesizers are enabled (FDD mode). 0x013=0x01(ENSM FDD) and 0x015[2] (Dual synth mode) is set.
		4) Set 0x169=0xC0 //Verify free run mode is disabled in 0x169[3].
		5) Set 0x057=0x33 //Power down TX mixer. This improves the calibration result.
		6) Set TX LO frequency to the RX LO frequency + BBBW/2. This places the TX LO in the passband of the RX spectrum. If the
		TX LO integer frequency word was written, allow time for the TX VCO calibration to complete.
		7) Set 0x016=0x20 //Start the RX Quadrature Calibration
		8) Wait for calibration to complete (when 0x016 = 0x00).
		9) Set TX LO back to its original frequency.
		10) Set 0x057=0x30 //Re-enable TX mixer for normal operation.
		11) Return to TDD operation if desired by setting register 0x013=0x00 and clear 0x015[2] (Dual synth mode).
		"""
		pass
		
def main():
	uut = AD9361_c()
	
	if len(sys.argv)>1:
		if sys.argv[1]=='S':
			if len(sys.argv)==3:
				print hex(uut.readreg(sys.argv[2]))
			elif len(sys.argv)==4:
				uut.writereg(sys.argv[2],int(sys.argv[3],16))
		elif sys.argv[1]=='R':
			if len(sys.argv)==3:
				uut.readByte(int(sys.argv[2],16))
			elif len(sys.argv)==4:
				uut.writeByte(int(sys.argv[2],16),int(sys.argv[3],16))
	else:
		uut.readreg('SPI_Config')
		(D,I,F) = uut.RFFreqCalc(25e6,835e6)
		print D,hex(I),hex(F)

if __name__ == '__main__':
	main()