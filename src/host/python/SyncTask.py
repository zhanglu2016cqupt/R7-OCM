import gsmlib.GSMC0 as C0
import matplotlib.pyplot as plt

import Q7Mem

import numpy as np
import gsmlib.splibs as sp
import gsmlib.Burst as Burst
rx = Q7Mem.rx()
c0 = C0.GSMC0()
c0.setRx(rx)
c0.initSCH()
c0.initBCCH()
#c0.initCCCH(range(2,3))
#Burst.Burst.log = open("../../../temp/log","wb")
#c0.state.bcch_log = open("../../../data/bcch","wt")
r = c0.run()
if Burst.Burst.log!= None:
	Burst.Burst.log.close()
if c0.state.bcch_log!=None:
	c0.state.bcch_log.close() 
#plt.plot(r)

#plt.show()

#sb = c0.C0.frame[1][0]
#ret = sp.filter(sb.__class__.__field__[2].modulated,sb.rhh)
