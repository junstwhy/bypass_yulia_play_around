import logging
logging.basicConfig(filename='logs.log',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)
logging.info("let's get it started")
import numpy as np
from neuron import h
import h5py as hdf5
h.load_file('nrngui.hoc')

#paralleling NEURON stuff
pc = h.ParallelContext()
rank = int(pc.id())
nhost = int(pc.nhost())

modes = ['PLT', 'STR', 'AIR', 'TOE', 'QPZ', 'QUAD']
mode = 'PLT'
logging.info(mode)

#param
speed = 50 # duration of layer 25 = 21 cm/s; 50 = 15 cm/s; 125 = 6 cm/s
#TODO update freq
bs_fr = 100 #40 # frequency of brainstem inputs
versions = 1
step_number = 20 # number of steps
layers =  2 # 5  # 5 is default

CV_number = 6
extra_layers = 0 # 1 + layers
nMN = 21 # 210
nAff = 12 # 120
nInt = 19 # 196
N = 5 #50
k = 0.017
CV_0_len = 12 # 125

if mode == 'AIR':
    k = 0.001
    speed = 25

if mode == 'TOE':
    k = 0.01

if mode == 'QUAD':
    CV_0_len = 175
    k = 0.003

one_step_time = int((6 * speed + CV_0_len) / (int(1000 / bs_fr))) * (int(1000 / bs_fr))
time_sim = 25 + one_step_time * step_number

exnclist = []
inhnclist = []
exstdpnclist = []
inhstdpnclist = []
eesnclist = []
stimnclist = []

from interneuron import interneuron
from motoneuron import motoneuron
from bioaffrat import bioaffrat
from muscle import muscle

import random

'''
network topology https://github.com/max-talanov/bypass/blob/main/figs/CPG_feedback_loops.png
'''
class CPG:
    def __init__(self, speed, bs_fr, inh_p, step_number, layers, extra_layers, N):

        self.interneurons = []
        self.motoneurons = []
        self.afferents = []
        self.stims = []
        self.ncell = N
        self.groups = []
        self.motogroups = []
        self.affgroups = []
        self.RG_E = []
        self.RG_F = []
        self.V3F = []

        for layer in range(layers):
            #TODO OMs --
            self.dict_0 = {layer: 'OM{}_0'.format(layer + 1)}
            self.dict_1 = {layer: 'OM{}_1'.format(layer + 1)}
            self.dict_2E = {layer: 'OM{}_2E'.format(layer + 1)}
            self.dict_2F = {layer: 'OM{}_2F'.format(layer + 1)}
            self.dict_3 = {layer: 'OM{}_3'.format(layer + 1)}
            self.dict_C = {layer: 'C{}'.format(layer + 1)}

        for layer in range(CV_number):
            '''cut and muscle feedback'''
            self.dict_CV = {layer: 'CV{}'.format(layer + 1)}
            self.dict_CV_1 = {layer: 'CV{}_1'.format(layer + 1)}
            # TODO -> RG
            self.dict_RG_E = {layer: 'RG{}_E'.format(layer + 1)}
            self.dict_RG_F = {layer: 'RG{}_F'.format(layer + 1)}
            self.dict_V3F = {layer: 'V3{}_F'.format(layer + 1)}


        for layer in range(layers, extra_layers):
            #TODO OMs for extra layers --
            self.dict_0 = {layer: 'OM{}_0'.format(layer + 1)}
            self.dict_1 = {layer: 'OM{}_1'.format(layer + 1)}
            self.dict_2E = {layer: 'OM{}_2E'.format(layer + 1)}
            self.dict_2F = {layer: 'OM{}_2F'.format(layer + 1)}
            self.dict_3 = {layer: 'OM{}_3'.format(layer + 1)}
            self.dict_C = {layer: 'C{}'.format(layer + 1)}

        if mode == 'QPZ':
            #TODO --
            self.OM1_0E = self.addpool(self.ncell, "OM1_0E", "delay")
            self.OM1_0F = self.addpool(self.ncell, "OM1_0F", "delay")
        else:
            self.OM1_0E = self.addpool(self.ncell, "OM1_0E", "int")
            self.OM1_0F = self.addpool(self.ncell, "OM1_0F", "int")

        '''add pool'''
        for layer in range(layers):
            if mode == 'QPZ':
                #TODO --
                self.dict_0[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_0", "delay")
            else:
                # TODO OM0 -> E:RG
                self.dict_0[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_0", "int")
            # TODO --
            self.dict_1[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_1", "int")
            self.dict_2E[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2E", "int")
            self.dict_2F[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2F", "int")
            self.dict_3[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_3", "int")

        for layer in range(CV_number):
            '''Cutaneous pools'''
            self.dict_CV[layer] = self.addpool(self.ncell, "CV" + str(layer + 1), "aff")
            self.dict_CV_1[layer] = self.addpool(self.ncell, "CV" + str(layer + 1) + "_1", "aff")

            '''interneuronal pool'''
            # TODO -> RG
            self.dict_RG_E[layer] = self.addpool(self.ncell, "IP" + str(layer + 1) + "_E", "int")
            self.dict_RG_F[layer] = self.addpool(self.ncell, "IP" + str(layer + 1) + "_F", "int")
            self.RG_E.append(self.dict_RG_E[layer])
            self.RG_F.append(self.dict_RG_F[layer])



        for layer in range(layers, extra_layers):
            # TODO OM0 -> E:RG
            self.dict_0[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_0", "int")
            # TODO --
            self.dict_1[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_1", "int")
            self.dict_2E[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2E", "int")
            self.dict_2F[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_2F", "int")
            self.dict_3[layer] = self.addpool(self.ncell, "OM" + str(layer + 1) + "_3", "int")

        '''RG'''
        self.RG_E = sum(self.RG_E, [])
        self.RG_F = sum(self.RG_F, [])

        '''sensory and muscle afferents and brainstem and V3F'''
        self.sens_aff = self.addpool(nAff, "sens_aff", "aff")
        self.Ia_aff_E = self.addpool(nAff, "Ia_aff_E", "aff")
        self.Ia_aff_F = self.addpool(nAff, "Ia_aff_F", "aff")
        self.BS_aff_E = self.addpool(nAff, "BS_aff_E", "aff")
        self.BS_aff_F = self.addpool(nAff, "BS_aff_F", "aff")
        self.V3F      = self.addpool(nAff, "V3F", "int")

        '''moto neuron pools'''
        self.mns_E = self.addpool(nMN, "mns_E", "moto")
        self.mns_F = self.addpool(nMN, "mns_F", "moto")

        '''muscles'''
        self.muscle_E = self.addpool(nMN*30, "muscle_E", "muscle")
        self.muscle_F = self.addpool(nMN*20, "muscle_F", "muscle")

        '''reflex arc'''
        self.Ia_E = self.addpool(nInt, "Ia_E", "int")
        self.InE = self.addpool(nInt, "iIP_E", "int")
        self.R_E = self.addpool(nInt, "R_E", "int")

        self.Ia_F = self.addpool(nInt, "Ia_F", "int")
        self.InF = self.addpool(nInt, "iIP_F", "int")
        self.R_F = self.addpool(nInt, "R_F", "int")
        # self.Iagener_E = []
        # self.Iagener_F = []

        '''BS'''
        #TODO BS -> periodic stimulation
        self.E_bs = self.addgener(0, bs_fr, 10000, False)
        self.F_bs = self.addgener(0, bs_fr, 10000, False)

        '''muscle afferents generators'''
        self.Iagener_E = self.addIagener(self.muscle_E, self.muscle_E, 10)
        self.Iagener_F = self.addIagener(self.muscle_F, self.muscle_F, speed*6)

        '''cutaneous inputs'''
        cfr = 200
        c_int = 1000 / cfr
        '''cutaneous inputs generators'''
        for layer in range(CV_number):
            self.dict_C[layer] = []
            for i in range(step_number):
                self.dict_C[layer].append(self.addgener(25 + speed * layer + i * (speed * CV_number + CV_0_len),
                                                        random.gauss(cfr, cfr/10), (speed / c_int + 1)))

        # TODO  --
        for layer in range(layers, extra_layers):
            self.dict_C[layer] = []
            for i in range(step_number):
                self.dict_C[layer].append(self.addgener(25 + speed * (layer - 4) + i * (speed * CV_number + CV_0_len),
                                                        random.gauss(cfr, cfr/10), (speed / c_int + 1)))

        self.C_1 = []
        self.C_0 = []
        self.V0v = []
        # for i in range(step_number):
        #     self.Iagener_E.append(self.addIagener((1 + i * (speed * 6 + 125)), self.ncell, speed))
        # for i in range(step_number):
        #     self.Iagener_F.append(self.addIagener((speed * 6 + i * (speed * 6 + 125)), self.ncell, 25))
        for i in range(step_number):
            self.C_0.append(self.addgener(25 + speed * 6 + i * (speed * 6 + CV_0_len), cfr, CV_0_len/c_int, False))
            self.V0v.append(self.addgener(40 + speed * 6 + i * (speed * 6 + CV_0_len), cfr, 100/c_int, False))
            ## TODO add BS here


        # self.C_0.append(self.addgener(0, cfr, (speed / c_int)))

        for layer in range(CV_number):
            self.C_1.append(self.dict_CV_1[layer])
        self.C_1 = sum(self.C_1, [])

        # self.C_0 = sum(self.C_0, [])

        # self.Iagener_E = sum(self.Iagener_E, [])
        # self.Iagener_F = sum(self.Iagener_F, [])

        '''generators'''
        # TODO --
        createmotif(self.OM1_0E, self.dict_1[0], self.dict_2E[0], self.dict_3[0])
        for layer in range(1, layers):
            createmotif(self.dict_0[layer], self.dict_1[layer], self.dict_2E[layer], self.dict_3[layer])

        for layer in range(layers, extra_layers):
            createmotif(self.dict_0[layer], self.dict_1[layer], self.dict_2E[layer], self.dict_3[layer])

        '''extra flexor connections'''
        createmotif(self.OM1_0F, self.dict_1[0], self.dict_2F[0], self.dict_3[0])
        #
        for layer in range(1, layers):
            createmotif(self.dict_0[layer], self.dict_1[layer], self.dict_2F[layer], self.dict_3[layer])

        # TODO --
        for layer in range(1, layers):
            connectcells(self.dict_2F[layer - 1], self.dict_2F[layer], 2.5, 2)

        # TODO --
        for layer in range(layers, extra_layers):
            connectcells(self.dict_2F[layer - 1], self.dict_2F[layer], 0.45, 2)

        # connectcells(self.dict_CV[0], self.OM1_0F, 0.0005, 3)
        # connectcells(self.V0v, self.dict_2F[0], 0.75, 1)

        #TODO OM0 -> RG
        connectcells(self.dict_CV[0], self.OM1_0F, 0.00075, 3)
        connectcells(self.V0v, self.OM1_0F, 3.75, 3)
        # connectcells(self.V0v, self.dict_2F[0], 3.5, 3)

        '''between delays via excitatory pools'''
        '''extensor'''
        for layer in range(1, layers):
            connectcells(self.dict_CV[layer - 1], self.dict_CV[layer], 0.75, 3)

        #TODO OM0->RG
        connectcells(self.dict_CV[0], self.OM1_0E, 0.00047, 2)
        for layer in range(1, layers):
            connectcells(self.dict_CV[layer], self.dict_0[layer], 0.00048, 2)

        '''inhibitory projections'''
        '''extensor'''
        #TODO OM1->RG
        for layer in range(2, layers+1):
            if layer > 3:
                for i in range(0, (layer - 2)):
                    connectcells(self.dict_C[layer], self.dict_3[i], 1.95, 1)
                    # connectcells(self.dict_C[layer], self.dict_2E[i], 1.75, 1, True)
            else:
                for i in range(0, (layer - 1)):
                    connectcells(self.dict_C[layer], self.dict_3[i], 1.95, 1)
                    # connectcells(self.dict_C[layer], self.dict_2E[i], 1.75, 1, True)
        for layer in range(layers, extra_layers):
            connectcells(self.dict_C[layer-3], self.dict_3[layer], 1.95, 1)

        ''' BS '''
        #genconnect(self.E_bs, self.Ia_aff_E, 1.5, 1)
        #genconnect(self.E_bs, self.Ia_aff_F, 1.5, 1)
        #genconnect(self.E_bs, self.dict_CV[0], 1.5, 2)
        genconnect(self.E_bs, self.BS_aff_E, 1.5, 1)
        genconnect(self.F_bs, self.BS_aff_F, 1.5, 1)

        connectcells(self.BS_aff_F, self.V3F, 1.5, 1)

        '''generators of Ia aff'''
        genconnect(self.Iagener_E, self.Ia_aff_E, 0.00005, 1, False, 5)
        genconnect(self.Iagener_F, self.Ia_aff_F, 0.0001, 1, False, 15)
        '''Ia2motor'''
        connectcells(self.Ia_aff_E, self.mns_E, 1.55, 1.5)
        connectcells(self.Ia_aff_F, self.mns_F, 0.5, 1.5)
        '''motor2muscles'''
        connectcells(self.mns_E, self.muscle_E, 15.5, 2, False, 45)
        connectcells(self.mns_F, self.muscle_F, 15.5, 2, False, 45)

        # '''IP'''
        # for layer in range(1, 4):
        #     connectcells(self.dict_IP_E[layer-1], self.dict_IP_E[layer+1], 0.45*layer, 2)
        #     connectcells(self.dict_IP_F[layer-1], self.dict_IP_F[layer+1], 0.45*layer, 2)

        for layer in range(layers):
            '''Extensor'''
            connectinsidenucleus(self.dict_RG_F[layer])
            # connectinsidenucleus(self.dict_1[layer])
            #TODO look into dict_2E, dict_2F
            connectinsidenucleus(self.dict_2E[layer])
            connectinsidenucleus(self.dict_2F[layer])
            # connectcells(self.dict_1[layer], self.dict_IP_E[layer], 0.75, 2)
            #TODO --
            connectcells(self.dict_2E[layer], self.dict_RG_E[layer], 1.75, 3)
            '''RG2Motor'''
            connectcells(self.dict_RG_E[layer], self.mns_E, 2.75, 3)

            if layer > 3:
                #TODO --
                connectcells(self.dict_RG_E[layer], self.Ia_aff_E, layer * 0.0002, 1, True)
            else:
                '''RG2Ia'''
                connectcells(self.dict_RG_E[layer], self.Ia_aff_E, 0.0001, 1, True)
            '''Flexor'''
            # connectcells(self.dict_1[layer], self.dict_IP_F[layer], 0.75, 2)
            connectcells(self.dict_2F[layer], self.dict_RG_F[layer], 2.85, 2)
            '''RG2Motor RG2Ia'''
            connectcells(self.dict_RG_F[layer], self.mns_F, 3.75, 2)
            #TODO check this
            connectcells(self.dict_RG_F[layer], self.Ia_aff_F, 0.95, 1, True)

        for layer in range(CV_number):
            '''cutaneous inputs'''
            connectcells(self.dict_C[layer], self.dict_CV_1[layer], 0.15*k*speed, 2)

        # connectcells(self.IP_F, self.Ia_aff_F, 0.0015, 2, True)
        # connectcells(self.IP_E, self.Ia_aff_E, 0.0015, 2, True)

        '''C'''
        #TODO OM0 -> E:RG
        if layers > 0:
            '''C1'''
            connectcells(self.dict_CV_1[0], self.OM1_0E, 0.00075*k*speed, 2)
        if layers > 1:
            connectcells(self.dict_CV_1[0], self.dict_0[1], 0.00001*k*speed, 3)
            '''C2'''
            connectcells(self.dict_CV_1[1], self.OM1_0E, 0.0005*k*speed, 2)
            connectcells(self.dict_CV_1[1], self.dict_0[1], 0.00045*k*speed, 3)
        if layers > 2:
            connectcells(self.dict_CV_1[0], self.dict_0[2], 0.00001*k*speed, 3)
            '''C2'''
            connectcells(self.dict_CV_1[1], self.dict_0[2], 0.00025*k*speed, 3)
            '''C3'''
            # connectcells(self.dict_CV_1[2], self.OM1_0E, 0.00001*k*speed, 2)
            connectcells(self.dict_CV_1[2], self.dict_0[1], 0.0004*k*speed, 2)
            connectcells(self.dict_CV_1[2], self.dict_0[2], 0.00035*k*speed, 3)
        if layers > 3:
            connectcells(self.dict_CV_1[2], self.dict_0[3], 0.0002*k*speed, 3)
            '''C4'''
            connectcells(self.dict_CV_1[3], self.dict_0[2], 0.00035*k*speed, 3)
            connectcells(self.dict_CV_1[3], self.dict_0[3], 0.00035*k*speed, 3)
            connectcells(self.dict_CV_1[4], self.dict_0[2], 0.00035*k*speed, 3)
            connectcells(self.dict_CV_1[4], self.dict_0[3], 0.00035*k*speed, 3)
        if layers > 4:
            connectcells(self.dict_CV_1[3], self.dict_0[4], 0.0001*k*speed, 3)
            connectcells(self.dict_CV_1[4], self.dict_0[4], 0.0001*k*speed, 3)
            #
            '''C5'''
            connectcells(self.dict_CV_1[5], self.dict_0[4], 0.00025*k*speed, 3)
            connectcells(self.dict_CV_1[5], self.dict_0[3], 0.0001*k*speed, 3)

        '''C=1 Extensor'''
        connectcells(self.RG_E, self.InE, 0.001, 1)

        for layer in range(layers+1):
            connectcells(self.dict_CV_1[layer], self.InE, 1.8, 1)
            connectcells(self.dict_C[layer], self.InE, 1.8, 1)

        connectcells(self.InE, self.OM1_0F, 1.9, 1, True)

        #TODO look into dict_2F and dict_2E
        for layer in range(layers):
            connectcells(self.InE, self.dict_2F[layer], 1.8, 2, True)
            connectcells(self.InF, self.dict_2E[layer], 0.5, 2, True)

        '''Ia2RG, RG2Motor'''
        connectcells(self.InE, self.RG_F, 0.5, 1, True)
        ## TODO STDP weight
        connectcells(self.Ia_aff_F, self.RG_F, 0.5, 1, stdptype=True)

        connectcells(self.InE, self.Ia_aff_F, 1.2, 1, True)
        connectcells(self.InE, self.mns_F, 0.8, 1, True)

        '''C=0 Flexor'''
        connectcells(self.RG_F, self.InF, 0.0001, 1)
        connectcells(self.InF, self.RG_E, 0.8, 1, True)
        ## TODO STDP weight
        connectcells(self.Ia_aff_E, self.RG_E, 0.5, 1)

        connectcells(self.InF, self.InE, 0.5, 1, True)
        connectcells(self.InF, self.Ia_aff_E, 0.5, 1, True)
        connectcells(self.InF, self.mns_E, 0.4, 1, True)
        connectcells(self.C_0, self.InF, 0.8, 1)

        '''reflex arc'''
        connectcells(self.InE, self.Ia_E, 0.001, 1)
        connectcells(self.Ia_aff_E, self.Ia_E, 0.008, 1)
        connectcells(self.mns_E, self.R_E, 0.00015, 1)
        connectcells(self.Ia_E, self.mns_F, 0.08, 1, True)
        connectcells(self.R_E, self.mns_E, 0.00015, 1, True)
        connectcells(self.R_E, self.Ia_E, 0.001, 1, True)

        connectcells(self.InF, self.Ia_F, 0.001, 1)
        connectcells(self.Ia_aff_F, self.Ia_F, 0.008, 1)
        connectcells(self.mns_F, self.R_F, 0.00015, 1)
        connectcells(self.Ia_F, self.mns_E, 0.08, 1, True)
        connectcells(self.R_F, self.mns_F, 0.00015, 1, True)
        connectcells(self.R_F, self.Ia_F, 0.001, 1, True)

        connectcells(self.R_E, self.R_F, 0.04, 1, True)
        connectcells(self.R_F, self.R_E, 0.04, 1, True)
        connectcells(self.Ia_E, self.Ia_F, 0.08, 1, True)
        connectcells(self.Ia_F, self.Ia_E, 0.08, 1, True)
        connectcells(self.InE, self.InF, 0.04, 1, True)
        connectcells(self.InF, self.InE, 0.04, 1, True)


    def addpool(self, num, name="test", neurontype="int"):
        '''
        Creates interneuronal pool and returns gids of pool
        Parameters
        ----------
        num: int
            neurons number in pool
        neurontype: string
            int: interneuron
            delay: interneuron with 5ht
            moto: motoneuron
            aff: afferent
        Returns
        -------
        gids: list
            the list of neurons gids
        '''
        gids = []
        gid = 0
        if neurontype.lower() == "delay":
            delaytype = True
        else:
            delaytype = False
        if neurontype.lower() == "moto":
            diams = motodiams(num)
        for i in range(rank, num, nhost):
            if neurontype.lower() == "moto":
                cell = motoneuron(diams[i])
                self.motoneurons.append(cell)
            elif neurontype.lower() == "aff":
                cell = bioaffrat()
                self.afferents.append(cell)
            elif neurontype.lower() == "muscle":
                cell = muscle()
                self.motoneurons.append(cell)
            else:
                cell = interneuron(delaytype)
                self.interneurons.append(cell)
            while pc.gid_exists(gid) != 0:
                gid += 1
            gids.append(gid)
            pc.set_gid2node(gid, rank)
            nc = cell.connect2target(None)
            pc.cell(gid, nc)

        # ToDo remove me (Alex code) - NO
        if neurontype.lower() == "moto" or neurontype.lower() == "muscle":
            self.motogroups.append((gids, name))
        elif neurontype.lower() == "aff":
            self.affgroups.append((gids, name))
        else:
            self.groups.append((gids, name))

        return gids

    def addgener(self, start, freq, nums, noise=True):
        '''
        Creates generator and returns generator gid

        Parameters
        ----------
        start: int
            generator start up
        freq: int
            generator frequency
        nums: int
            signals number
        noise: bool
            generates noizy output
        Returns
        -------
        gid: int
            generator gid
        '''
        gid = 0
        stim = h.NetStim()
        stim.number = nums
        if noise:
            stim.start = random.uniform(start - 3, start + 3)
            stim.noise = 0.05
        else:
            stim.start = start
        stim.interval = int(1000 / freq)
        #skinstim.noise = 0.1
        self.stims.append(stim)
        while pc.gid_exists(gid) != 0:
            gid += 1
        pc.set_gid2node(gid, rank)
        ncstim = h.NetCon(stim, None)
        pc.cell(gid, ncstim)
        return gid

    def addIagener(self, mn, mn2, start):
        '''
        Creates self.Ia generators and returns generator gids
        Parameters
        ----------
        start: int
            generator start up
        num: int
            number in pool
        Returns
        -------
        gids: list
            generators gids
        '''
        gid = 0
        moto = pc.gid2cell(random.randint(mn[0], mn[-1]))
        moto2 = pc.gid2cell(random.randint(mn2[0], mn2[-1]))
        stim = h.IaGenerator(0.5)
        stim.start = start
        h.setpointer(moto.muscle_unit(0.5)._ref_F_fHill, 'fhill', stim)
        h.setpointer(moto2.muscle_unit(0.5)._ref_F_fHill, 'fhill2', stim)
        self.stims.append(stim)
        while pc.gid_exists(gid) != 0:
            gid += 1
        pc.set_gid2node(gid, rank)
        ncstim = h.NetCon(stim, None)
        pc.cell(gid, ncstim)

        return gid

def connectcells(pre, post, weight, delay = 1, inhtype = False, N = 50, stdptype = False, threshold = 10):
    ''' Connects with excitatory synapses
      Parameters
      ----------
      pre: list
          list of presynase neurons gids
      post: list
          list of postsynapse neurons gids
      weight: float
          weight of synapse
          used with Gaussself.Ian distribution
      delay: int
          synaptic delay
          used with Gaussself.Ian distribution
      nsyn: int
          numder of synapses
      inhtype: bool
          is this connection inhibitory?
      N: int
          number of synapses
      stdptype: bool
           is connection stdp?
      threshold: int
            voltage thershold
    '''
    nsyn = random.randint(N-15, N)
    for post_gid in post:
        if pc.gid_exists(post_gid):
            for j in range(nsyn):
                src_gid = random.randint(pre[0], pre[-1])
                target = pc.gid2cell(post_gid)
                if stdptype:
                    if inhtype:
                        syn = target.synlistinhstdp[j]
                        nc = pc.gid_connect(src_gid, syn)
                        nc.delay = delay
                        pc.threshold(src_gid, threshold)
                        """Create STDP synapses"""
                        dummy = h.Section()  # Create a dummy section to put the point processes in
                        stdpmech = h.STDP(0, sec=dummy)  # Create the STDP mechanism
                        # TODO check target, threshold,
                        presyn = pc.gid_connect(src_gid,
                                                stdpmech)  # threshold, delay, 1)  # Feed presynaptic spikes to the STDP mechanism -- must have weight >0
                        presyn.delay = delay
                        presyn.weight = 1
                        pstsyn = pc.gid_connect(post_gid,
                                                stdpmech)  # threshold, delay, -1)  # Feed postsynaptic spikes to the STDP mechanism -- must have weight <0
                        pstsyn.delay = delay
                        pstsyn.weight = -1
                        pc.threshold(post_gid, threshold)
                        h.setpointer(nc._ref_weight[0], 'synweight',
                                     stdpmech)  # Point the STDP mechanism to the connection weight
                        inhstdpnclist.append(nc)
                    else:
                        syn = target.synlistex[j]
                        nc = pc.gid_connect(src_gid, syn)
                        nc.delay = delay
                        pc.threshold(src_gid, threshold)
                        """Create STDP synapses"""
                        dummy = h.Section()  # Create a dummy section to put the point processes in
                        stdpmech = h.STDP(0, sec=dummy)  # Create the STDP mechanism
                        # TODO check target, threshold,
                        presyn = pc.gid_connect(src_gid,
                                                stdpmech)  # threshold, delay, 1)  # Feed presynaptic spikes to the STDP mechanism -- must have weight >0
                        presyn.delay = delay
                        presyn.weight[0] = 1
                        pstsyn = pc.gid_connect(post_gid,
                                                stdpmech)  # threshold, delay, -1)  # Feed postsynaptic spikes to the STDP mechanism -- must have weight <0
                        pstsyn.delay = delay
                        pstsyn.weight[0] = -1
                        pc.threshold(post_gid, threshold)
                        h.setpointer(nc._ref_weight[0], 'synweight',
                                     stdpmech)  # Point the STDP mechanism to the connection weight
                        exstdpnclist.append(nc)
                        # nc.weight[0] = random.gauss(weight, weight / 6) # str

                else:
                    if inhtype:
                        syn = target.synlistinh[j]
                        nc = pc.gid_connect(src_gid, syn)
                        inhnclist.append(nc)
                    else:
                        syn = target.synlistex[j]
                        nc = pc.gid_connect(src_gid, syn)
                        exnclist.append(nc)
                        # nc.weight[0] = random.gauss(weight, weight / 6) # str

                if mode == 'STR':
                    nc.weight[0] = 0 # str
                else:
                    nc.weight[0] = random.gauss(weight, weight / 5)
                nc.delay = random.gauss(delay, delay / 5)



def genconnect(gen_gid, afferents_gids, weight, delay, inhtype = False, N = 50):
    ''' Connects with generator
      Parameters
      ----------
      afferents_gids: list
          list of presynase neurons gids
      gen_gid: int
          generator gid
      weight: float
          weight of synapse
          used with Gaussian distribution
      delay: int
          synaptic delay
          used with Gaussian distribution
      nsyn: int
          numder of synapses
      inhtype: bool
          is this connection inhibitory?
    '''
    nsyn = random.randint(N, N+5)
    for i in afferents_gids:
        if pc.gid_exists(i):
            for j in range(nsyn):
                target = pc.gid2cell(i)
                if inhtype:
                    syn = target.synlistinh[j]
                    # nc = pc.gid_connect(gen_gid, syn)
                    # stimnclist.append(nc)
                    # nc.delay = random.gauss(delay, delay / 6)
                    # nc.weight[0] = 0
                else:
                    syn = target.synlistees[j]
                    # nc = pc.gid_connect(gen_gid, syn)
                    # stimnclist.append(nc)
                    # nc.delay = random.gauss(delay, delay / 6)
                    # nc.weight[0] = random.gauss(weight, weight / 6)
                nc = pc.gid_connect(gen_gid, syn)
                stimnclist.append(nc)
                nc.delay = random.gauss(delay, delay / 5)
                nc.weight[0] = random.gauss(weight, weight / 6)

def createmotif(OM0, OM1, OM2, OM3):
    ''' Connects motif module
      see https://github.cself.OM/research-team/memristive-spinal-cord/blob/master/doc/dself.Iagram/cpg_generatoself.R_FE_paper.png
      Parameters
      ----------
      self.OM0: list
          list of self.OM0 pool gids
      self.OM1: list
          list of self.OM1 pool gids
      self.OM2: list
          list of self.OM2 pool gids
      self.OM3: list
          list of self.OM3 pool gids
    '''
    connectcells(OM0, OM1, 2.85, 3)
    connectcells(OM1, OM2, 2.85, 3)
    connectcells(OM2, OM1, 1.95, 3)
    connectcells(OM2, OM3, 0.001, 3)
    connectcells(OM1, OM3, 0.00005, 3)
    connectcells(OM3, OM2, 4.5, 1, True)
    connectcells(OM3, OM1, 4.5, 1, True)

def connectinsidenucleus(nucleus):
    connectcells(nucleus, nucleus, 0.25, 0.5)

def spike_record(pool, extra = False):
    ''' Records spikes from gids
      Parameters
      ----------
      pool: list
        list of neurons gids
      extra: bool
          extracellular or intracellular voltages to record
      Returns
      -------
      v_vec: list of h.Vector()
          recorded voltages
    '''
    v_vec = []

    for i in pool:
        cell = pc.gid2cell(i)
        vec = h.Vector(np.zeros(int(time_sim/0.025 + 1), dtype=np.float32))
        if extra:
            vec.record(cell.soma(0.5)._ref_vext[0])
        else:
            vec.record(cell.soma(0.5)._ref_v)
        v_vec.append(vec)
    return v_vec

def motodiams(number):
    nrn_number = number
    standby_percent = 70
    active_percent = 100 - standby_percent

    standby_size = int(nrn_number * standby_percent / 100)
    active_size = nrn_number - standby_size

    loc_active, scale_active = 27, 3
    loc_stanby, scale_stanby = 44, 4

    x2 = np.concatenate([np.random.normal(loc=loc_active, scale=scale_active, size=active_size),
                     np.random.normal(loc=loc_stanby, scale=scale_stanby, size=standby_size)])

    return x2

def spikeout(pool, name, version, v_vec):
    ''' Reports simulation results
      Parameters
      ----------
      pool: list
        list of neurons gids
      name: string
        pool name
      version: int
          test number
      v_vec: list of h.Vector()
          recorded voltage
    '''
    global rank
    pc.barrier()
    vec = h.Vector()
    for i in range(nhost):
        if i == rank:
            outavg = []
            for j in range(len(pool)):
                outavg.append(list(v_vec[j]))
            outavg = np.mean(np.array(outavg), axis = 0, dtype=np.float32)
            vec = vec.from_python(outavg)
        pc.barrier()
    pc.barrier()
    result = pc.py_gather(vec, 0)
    if rank == 0:
        logging.info("start recording")
        result = np.mean(np.array(result), axis = 0, dtype=np.float32)
        with hdf5.File('./res/new_rat4_{}_speed_{}_layers_{}1_eeshz_{}.hdf5'.format(name, speed, layers, bs_fr), 'w') as file:
            for i in range(step_number):
                sl = slice((int(1000 / bs_fr) * 40 + i * one_step_time * 40), (int(1000 / bs_fr) * 40 + (i + 1) * one_step_time * 40))
                file.create_dataset('#0_step_{}'.format(i), data=np.array(result)[sl], compression="gzip")
    else:
        logging.info(rank)


def prun(speed, step_number):
    ''' simulation control
    Parameters
    ----------
    speed: int
      duration of each layer
    '''
    pc.timeout(0)
    tstop = time_sim#25 + (6 * speed + 125) * step_number
    pc.set_maxstep(10)
    h.stdinit()
    pc.psolve(tstop)


def finish():
    ''' proper exit '''
    pc.runworker()
    pc.done()
    # print("hi after finish")
    h.quit()

if __name__ == '__main__':
    '''
    cpg_ex: cpg
        topology of central pattern generation + reflex arc
    '''
    k_nrns = 0
    k_name = 1

    for i in range(versions):
        cpg_ex = CPG(speed, bs_fr, 100, step_number, layers, extra_layers, N)
        logging.info("created")
        motorecorders = []
        motorecorders_mem = []
        for group in cpg_ex.motogroups:
            motorecorders.append(spike_record(group[k_nrns], True))

        for group in cpg_ex.motogroups:
            motorecorders_mem.append(spike_record(group[k_nrns]))
        affrecorders = []
        for group in cpg_ex.affgroups:
          affrecorders.append(spike_record(group[k_nrns], i))
        recorders = []
        for group in cpg_ex.groups:
          recorders.append(spike_record(group[k_nrns], i))
        logging.info("added recorders")

        print("- " * 10, "\nstart")
        prun(speed, step_number)
        print("- " * 10, "\nend")

        logging.info("done")

        for group, recorder in zip(cpg_ex.motogroups, motorecorders):
            spikeout(group[k_nrns], group[k_name], i, recorder)

        for group, recorder in zip(cpg_ex.motogroups, motorecorders_mem):
            spikeout(group[k_nrns], 'mem_{}'.format(group[k_name]), i, recorder)
        for group, recorder in zip(cpg_ex.affgroups, affrecorders):
          spikeout(group[k_nrns], group[k_name], i, recorder)
        for group, recorder in zip(cpg_ex.groups, recorders):
          spikeout(group[k_nrns], group[k_name], i, recorder)
        logging.info("recorded")

    finish()
