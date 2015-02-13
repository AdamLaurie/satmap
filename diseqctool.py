#!/usr/bin/python

#  diseqctool.py - command line tool for satellite steering & tuning
# -*- coding: iso-8859-15 -*-
#
#  Adam Laurie <adam@algroup.co.uk> aka Major Malfunction <majormal@pirate-radio.org>
#
#  http://rfidiot.org/ 
#  http://alcrypto.co.uk
#
#  This code is copyright (c) Adam Laurie, 2010-2014 All rights reserved.
#  For non-commercial use only, the following terms apply - for all other
#  uses, please contact the author:
#
#    This code is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import dvb
import time
from utils import *

version= "1.0a"

Polarity= 'H'
FrontEnd_fd= None
FrontEnd_poll= None
FrontEnd= None
Frequency= 10700000
SymbolRate= 22000000
Step= 0

Audio_fd= None
Video_fd= None
Teletext_fd= None

# local devices
DVB_FE_Device= dvb.frontend()
DVB_DEMUX_Device= dvb.demux()

def init_frontend(reinit):
	global FrontEnd_fd
	global FrontEnd_poll
	global FrontEnd
	global DVB_FE_Device
	global Frequency
	global Step

	if not reinit and FrontEnd_fd != None:
		return FrontEnd_fd, FrontEnd_poll, FrontEnd

	if FrontEnd_fd != None:
		FrontEnd_fd.close()

	FrontEnd_fd, FrontEnd_poll, FrontEnd = dvb.open_fe(DVB_FE_Device)
	if not FrontEnd_fd:
		print 'Fail! No DVB frontend device detected!'
		print FrontEnd
		exit(True)
	if Frequency < FrontEnd.frequency_min + dvb.LOW_OFFSET:
		Frequency= FrontEnd.frequency_min + dvb.LOW_OFFSET
	if Frequency > FrontEnd.frequency_max + dvb.HIGH_OFFSET:
		Frequency= FrontEnd.frequency_max + dvb.HIGH_OFFSET
	Step= FrontEnd.frequency_stepsize
	return FrontEnd_fd, FrontEnd_poll, FrontEnd

# reset card
def reset_frontend():
	if not dvb.dvb_tune(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate):
		print 'Fail! No DVB frontend device detected!'
		exit(True)
	
def init_demux(reinit):	
	global Audio_fd
	global Video_fd
	global Teletext_fd
	global DVB_DEMUX_Device

	if not reinit and Audio_fd != None:
		return Audio_fd, Video_fd, Teletext_fd

	if Audio_fd != None:
		Audio_fd.close()
		Video_fd.close()
		Teletext_fd.close()

	Audio_fd, Video_fd, Teletext_fd = dvb.open_demux(DVB_DEMUX_Device)
	if not Audio_fd:
		print 'Fail! No DVB demux device detected!'
		exit(True)
	return Audio_fd, Video_fd, Teletext_fd

if len(sys.argv) == 1:
	print
	print 'Usage: %s <COMMAND> [ARG(s)] ... [<COMMAND> [ARG(s)] ... ]' % sys.argv[0]
	print
	print '  Commands:'
	print
	print '     ADAPTER <#>                                      Set DVB adapter no (Default is 0)'
	print "     DEMUX <DEVICE>                                   Set DVB Demux device (default is '%s')" % DVB_DEMUX_Device
	print "     EAST <'STEP'|'TIME'> <#>                         Drive EAST for up to 128 steps or seconds (TIME 0 drives to end stop)"
	print "     FE <DEVICE>                                      Set DVB Front End device (default is '%s')" % DVB_FE_Device
	print "     FIND <FREQ> <'H'|'V'> <RATE> <'EAST'|'WEST'>     Find and centre on active signal"
	print '     FREQ <FREQ>                                      Set Frequency in Hz (default is %d)' % Frequency
	print '     FSCAN <STEP>                                     Perform frequency only scan'
	print '     GOTO <#>                                         Goto stored satellite position #'
	print '     INFO                                             Show Front End device info'
	print "     LIMIT <'EAST'|'WEST'>                            Set EAST or WEST motor drive end stops"
	print "     POLARITY <'H'|'V'>                               Set Horizonal or Vertical polarity (default is '%s')" % Polarity
	print '     POWER <#>                                        Power up positioner motor for # seconds'
	print "     SCAN <TYPE> <'EAST'|'WEST'> <STEPS> <LOGFILE>    Perform frequency scan and log results"
	print '     SIGNAL                                           Show current status of receiver'
	print '     STATUS                                           Show current status of positioner motor'
	print "     STEER <DEGREES> <'EAST'|'WEST'>                  Steer to angle - e.g. 13.0 EAST for HotBird"
	print '     STOP                                             Stop positioner motor'
	print '     STORE <#>                                        Store current position as satellite #'
	print '     SYMBOL <RATE>                                    Set Symbol Rate (default is %d)' % SymbolRate
	print '     TUNE                                             Tune DVB Receiver (default is %d Hz, %s, Symbolrate %d)' % (Frequency, dvb.POLARITIES[Polarity], SymbolRate)
	print "     WEST <'STEP'|'TIME'> <#>                         Drive WEST for up to 128 steps or seconds (TIME 0 drives to end stop)"
	print
	print '  Commands will be executed sequentially and must be combined as appropriate.'
	print
	print '  Note that not all cards provide power all the time, so you may need to bracket'
	print '  steering commands with POWER to enable motor - e.g.'
	print
	print '    %s power 5 west step 50 power 30' % sys.argv[0]
	print
	print '  Timings will vary with equipment, but as there is no way for Diseqc 1.x compliant'
	print '  hardware to tell when a positioning command has finished, you must ensure that'
	print '  power is made available for the maximum possible duration of any movement.'
	print
	exit(True)

current= 1

while current < len(sys.argv):
	command= sys.argv[current].upper()
	if command == 'ADAPTER':
		current += 1
		dvb.DVB_Adapter= int(sys.argv[current])
		print
		print '  Setting adapter to %d (%s):' % (dvb.DVB_Adapter, dvb.adapter())
		DVB_FE_Device= dvb.frontend()
		DVB_DEMUX_Device= dvb.demux()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		dvb.display_fe_device(DVB_FE_Device,FrontEnd)
		print 
		current += 1
		continue
	if command == 'DEMUX':
		current += 1
		DVB_DEMUX_Device= sys.argv[current]
		print
		print '  Setting DEMUX to', DVB_DEMUX_Device, '-',
		sys.stdout.flush()
		Audio_fd, Video_fd, Teletext_fd = init_demux(True)
		print 'OK'
		current += 1
		continue
	if command == 'EAST' or command == 'WEST':
		current += 1
		type= sys.argv[current].upper()
		current += 1
		steps= int(sys.argv[current])
		if command == 'EAST':
			diseqc_command= dvb.DISEQC_DRIVE_E
		else:
			diseqc_command= dvb.DISEQC_DRIVE_W
		print
		print '  Driving %s %d -' % (command, steps),
		sys.stdout.flush()
		if steps > 128:
			print 'Max steps is 128!'
			exit(True)
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		status, error= dvb.diseqc_drive(FrontEnd_fd, FrontEnd_poll, diseqc_command, type, steps, steps)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'FE':
		current += 1
		DVB_FE_Device= sys.argv[current]
		print
		print '  Setting FE to', DVB_FE_Device, '-',
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(True)
		print 'OK'
		current += 1
		continue
	if command == 'FIND':
		current += 1
		print
		Frequency= int(sys.argv[current])
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		if Frequency < Front_End.frequency_min + dvb.LOW_OFFSET:
			print 'value below minimum of %d:' % (Front_End.frequency_min + dvb.LOW_OFFSET),
		if Frequency > Front_End.frequency_max + dvb.HIGH_OFFSET:
			print 'value above maximum of %d:' % (Front_End.frequency_max + dvb.HIGH_OFFSET),
		current += 1
		Polarity= sys.argv[current].upper()
		current += 1
		SymbolRate= int(sys.argv[current])
		current += 1
		print '  Finding transponder %d/%s/%d' % (Frequency, Polarity, SymbolRate), 
		if sys.argv[current].upper() == 'EAST':
			print 'EASTwards'
			diseqc_command= dvb.DISEQC_DRIVE_E
		else:
			print 'WESTwards'
			diseqc_command= dvb.DISEQC_DRIVE_W
		found= 0
		steps= 0
		strengths= []
		finished= False
		while not found or (found and not finished):
			# find an active signal
			dvb.dvb_tune(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate)
			status, ber, snr, strength, params = dvb.dvb_fe_status(FrontEnd_fd)
			if status.status & dvb.FE_HAS_LOCK and snr > 0 and ber == 0:
				# filter out random crap by checking again
				time.sleep(1)
				status, ber, snr, strength, params = dvb.dvb_fe_status(FrontEnd_fd)
				if status.status & dvb.FE_HAS_LOCK and snr > 0 and ber == 0:
					if not found:
						print '   Found after %d steps' % steps
					found += 1
					# expect signal strength to rise steadily after the first couple of 
					# erroneous 'edge' signals
					strengths.append(strength)
			else:
				if found:
					finished= True
			status, error= dvb.diseqc_drive(FrontEnd_fd, FrontEnd_poll, diseqc_command, 'STEP', 1, 1)
			steps += 1
			if status:
				print '   step: %d BER: %d SNR: %d Signal Strength: %d' % (steps, ber, snr, strength)
				sys.stdout.flush()
			else:
				print 'Failed!', error
				exit(True)
		# ignore the first and last erroneous 'edge' signals
		x= strengths[3:-3]
		x.sort()
		print '      strongest signal was', x[-1]
		print '      seeking back to that level...'
		if diseqc_command == dvb.DISEQC_DRIVE_W:
			diseqc_command= dvb.DISEQC_DRIVE_E
		else:
			diseqc_command= dvb.DISEQC_DRIVE_W
		while strength != x[-1]:
			status, error= dvb.diseqc_drive(FrontEnd_fd, FrontEnd_poll, diseqc_command, 'STEP', 1, 1)
			dvb.dvb_tune(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate)
			time.sleep(1)
			status, ber, snr, strength, params = dvb.dvb_fe_status(FrontEnd_fd)
			print '        signal strength:', strength
			steps -= 1
		if x.count(x[-1]) > 1:
			print '          stepping another %d steps to centre' % (x.count(x[-1]) / 2)
			dvb.diseqc_drive(FrontEnd_fd, FrontEnd_poll, diseqc_command, 'STEP', x.count(x[-1]) / 2, x.count(x[-1]) / 2)
			steps -= x.count(x[-1]) / 2
		print '          total steps from starting position:', steps
		current += 1
		continue
	if command == 'FREQ':
		current += 1
		print
		print '  Setting Frequency to',
		Frequency= int(sys.argv[current])
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		if Frequency < Front_End.frequency_min + dvb.LOW_OFFSET:
			print 'value below minimum of %d:' % (Front_End.frequency_min + dvb.LOW_OFFSET),
		if Frequency > Front_End.frequency_max + dvb.HIGH_OFFSET:
			print 'value above maximum of %d:' % (Front_End.frequency_max + dvb.HIGH_OFFSET),
		print '%d' % Frequency, '-',
		sys.stdout.flush()
		if not dvb.dvb_tune(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate):
			print 'Failed!'
		else:
			print 'OK'
		current += 1
		continue
	if command == 'FSCAN':
		current += 1
		step= int(sys.argv[current])
		print
		print '  Performing frequency scan in steps of %d (%d steps):' % (step, ((FrontEnd.frequency_max + dvb.HIGH_OFFSET) - (FrontEnd.frequency_min + dvb.LOW_OFFSET)) / step)
		sys.stdout.flush()
		init_frontend(False)
		reset_frontend()
		# wait for settle
		time.sleep(1)
		Frequency= FrontEnd.frequency_min + dvb.LOW_OFFSET
		while Frequency <= FrontEnd.frequency_max + dvb.HIGH_OFFSET:
			for Polarity in 'H', 'V':
				dvb.set_polarity(FrontEnd_fd, Polarity)
				status, strength= dvb.detect_signal_strength(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate)
				if status:
					print '    %d/%s: %d' % (Frequency, Polarity, strength),
				else:
					print '  Failed!'
					exit(True)
			print
			Frequency += step
		current += 1
		continue
	if command == 'GOTO':
		current += 1
		pos= int(sys.argv[current])
		print
		print '  Going to satellite no. %d -' % pos,
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		status, error= dvb.diseqc_goto_store(FrontEnd_fd, FrontEnd_poll, pos)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'INFO':
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		dvb.display_fe_device(DVB_FE_Device,FrontEnd)
		current += 1
		continue
	if command == 'LIMIT':
		current += 1
		compass= sys.argv[current].upper()
		print
		print '  Setting %s limit -' % compass,
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		if compass != 'EAST' and compass != 'WEST':
			print 'Failed! Invalid end stop!'
			exit(True)
		status, error= diseqc_set_limit(FrontEnd_fd, FrontEnd_poll, compass)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'POLARITY':
		current += 1
		Polarity= sys.argv[current].upper()
		print
		print '  Setting Polarity to', dvb.POLARITIES[Polarity], '-',
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		if not dvb.set_polarity(FrontEnd_fd, Polarity):
			print 'Failed!'
		else:
			print 'OK'
		current += 1
		continue
	if command == 'POWER':
		current += 1
		seconds= int(sys.argv[current])
		count= seconds
		start= int(time.time())
		print
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		while seconds > 0:
			print '  Powering motor for %d seconds -          \r' % seconds,
			sys.stdout.flush()
			dvb.diseqc_power_on(FrontEnd_fd, FrontEnd_poll)
			now= int(time.time())
			if now != start:
				seconds -= 1
				start= now
		print '  Powering motor for %d seconds - OK' % count
		current += 1
		continue
	if command == 'SCAN':
		print
		print '  Performing',
		current += 1
		type= sys.argv[current].upper()
		if type == 'STRENGTH':
			print type, 'scan -',
		sys.stdout.flush()
		init_frontend(False)
		reset_frontend()
		# wait for settle
		time.sleep(1)
		steps= 0
		while steps < 100:
			Frequency= FrontEnd.frequency_min + dvb.LOW_OFFSET
			while Frequency <= FrontEnd.frequency_max + dvb.HIGH_OFFSET:
				status, strength= dvb.detect_signal_strength(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate)
				if status:
					print '%d,%d,%d' % (steps, Frequency, strength)
				else:
					print '  Failed!'
					exit(True)
				Frequency += Step
			steps += 1
			dvb.diseqc_drive(FrontEnd_fd, FrontEnd_poll, DISEQC_DRIVE_E, 'STEP', 1, 1)
		current += 1
		continue
	if command == 'SIGNAL':
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		status, ber, snr, strength, params = dvb.dvb_fe_status(FrontEnd_fd)
		dvb.display_fe_status(status, ber, snr, strength)
		if params:
			dvb.display_fe_params(params)
		current += 1
		continue
	if command == 'STATUS':
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		print
		print '  Getting positioner status -',
		sys.stdout.flush()
		status, error= display_diseqc_status(FrontEnd_fd, FrontEnd_poll)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'STEER':
		current += 1
		degrees= float(sys.argv[current])
		current += 1
		compass= sys.argv[current].upper()
		print 
		print '  Steering to %0.2f %s -' % (degrees, compass),
		if compass != 'EAST' and compass != 'WEST':
			print 'Failed! Invalid direction!'
			exit(True)
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		status, error= dvb.diseqc_steer(FrontEnd_fd, FrontEnd_poll, degrees, compass)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'STOP':
		print
		print '  Stopping motor -',
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		status, error= dvb.diseqc_halt(FrontEnd_fd, FrontEnd_poll)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'STORE':
		current += 1
		satno= int(sys.argv[current])
		print
		print '  Storing position as satellite no. %d -' % satno,
		sys.stdout.flush()
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		status, error= dvb.diseqc_store(FrontEnd_fd, FrontEnd_poll,satno)
		if status:
			print 'OK'
		else:
			print 'Failed!', error
			exit(True)
		current += 1
		continue
	if command == 'SYMBOL':
		current += 1
		SymbolRate= int(sys.argv[current])
		print
		print '  Setting Symbol Rate to',
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		if SymbolRate < Front_End.symbol_rate_min:
			print 'value below minimum of %d:' % (Front_End.symbol_rate_min),
		if SymbolRate > Front_End.symbol_rate_max:
			print 'value above maximum of %d:' % (Front_End.symbol_rate_max),
		print SymbolRate, '-',
		sys.stdout.flush()
		if not dvb.dvb_tune(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate):
			print 'Failed!'
		else:
			print 'OK'
		current += 1
		continue
	if command == 'TUNE':
		print
		print '  Tuning receiver to %d Hz, %s, Symbolrate %d -' % (Frequency, dvb.POLARITIES[Polarity], SymbolRate),
		FrontEnd_fd, FrontEnd_poll, Front_End = init_frontend(False)
		reset_frontend()
		sys.stdout.flush()
		if not dvb.dvb_tune(FrontEnd_fd, FrontEnd_poll, Frequency, Polarity, SymbolRate):
			print 'Failed!'
		else:
			print 'OK'
		current += 1
		continue
	print
	print 'Unrecognised command:', sys.argv[current]
	exit(True)
print
exit(False)
