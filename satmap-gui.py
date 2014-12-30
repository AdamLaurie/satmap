#!/usr/bin/python

#  satmap-gui.py - python tool for mapping satellite coverage (GUI component)
# -*- coding: iso-8859-15 -*-
#
#  Adam Laurie <adam@algroup.co.uk> aka Major Malfunction <majormal@pirate-radio.org>
#
#  http://rfidiot.org/ 
#  http://alcrypto.co.uk
#
#  This code is copyright (c) Adam Laurie, 2010, All rights reserved.
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

# note: you will need to install the fluendo version of gstreamer0.10-plugins-bad: gstreamer0.10-fluendo-mpegdemux
#       *** then re-install gstreamer0.10-plugins-bad

version= '0.1i'

import os
from Tkinter import *
from operator import *
import tkFileDialog
import gtk
import pygst
pygst.require("0.10")
import gst
import utils

MASTER_PIDS= "0:16:17:18"
pid_table= {}
current_pids= ''
current_program= None
available_programs= {}
menu_options= []
Video_PAD= None
Audio_PAD= None

widget_master= Tk()
widget_master.title('satmap GUI (%s)' % version)

width= 800

# polarity colours
COLOURS={
	'V':'#00%02x00',
	'H':'#%02x0000',
	'-':'#0000%02x',
	}

WINDOW_WIDTH= 600
WINDOW_HEIGHT= 675
WINDOW_MARGIN= 20
TEXT_OFFSET= 7
X_OFFSET= 100

#
# gstreamer functions
#

def start_stop(event):
        global current_pids
        global menu_program
	global menu_options
	global available_programs
	global program

        if button_transponder_tune_state.get() == "Tune":
                button_transponder_tune_state.set("Stop")
		pol= transponder_polarity.get()
                freq= int(field_transponder_freq.get())
                current_pids= MASTER_PIDS
                symrate= int(field_transponder_symbol.get()) / 1000
                source.set_property("polarity", pol)
                source.set_property("frequency", freq)
                source.set_property("symbol-rate", symrate)
                source.set_property("pids",current_pids)
                program.set('')
		menu_options= []
                player.set_state(gst.STATE_PLAYING)
        else:
                button_transponder_tune_state.set("Tune")
                player.set_state(gst.STATE_NULL)

def on_message(bus, message):
	print 'got message:', message.structure.get_name()
	t = message.type
	if t == gst.MESSAGE_EOS:
		player.set_state(gst.STATE_NULL)
	elif t == gst.MESSAGE_ERROR:
		player.set_state(gst.STATE_NULL)
		err, debug = message.parse_error()
		print "Error: %s" % err, debug
	return True

def demuxer_callback(demuxer, pad):
	global Video_PAD
	global Audio_PAD

	print 'demuxer callback', pad.get_property("template").name_template
	if pad.get_property("template").name_template == "video_%04x":
		print 'video sink added'
		qv_pad = queuev.get_pad("sink")
		if Video_PAD:
			print 'removing stale Video PAD'
			Video_PAD[0].unlink(Video_PAD[1])
		pad.link(qv_pad)
		Video_PAD= (pad,qv_pad)
	elif pad.get_property("template").name_template == "audio_%04x":
		print 'audio sink added'
		qa_pad = queuea.get_pad("sink")
		if Audio_PAD:
			print 'removing stale Audio PAD'
			Audio_PAD[0].unlink(Audio_PAD[1])
		pad.link(qa_pad)
		Audio_PAD= (pad,qa_pad)
	return True

def on_sync_message(bus, message):
	global available_programs
	global current_program

	if message.structure is None:
		print 'got empty sync message'
		return True
	message_name = message.structure.get_name()
	if message_name == "nit":
		network_provider.set('Network: ' + message.structure['network-name'])
		return True
	if message_name == "sdt":
		s = message.structure
		services = s["services"]
		tsid = s["transport-stream-id"]
		actual = s["actual-transport-stream"]
		for service in services:
			name = service.get_name()
			sid = int(name[8:])
			name= provider= scrambled= running_status= "Unknown"
			if service.has_field("name"):
				name = service["name"]
			if service.has_field("provider-name"):
				provider=  service["provider-name"]	
			if service.has_field("scrambled"):
				scrambled= service["scrambled"]
				if scrambled:
					scrambled= "scrambled"
				else:
					scrambled= "free to air"
			if service.has_field("running-status"):
				running_status= service["running-status"]
			if not available_programs.has_key(sid):
				available_programs.update({sid:''})
			# update if entry is blank
			if available_programs[sid] == '':
				available_programs[sid]= '%s:%s:%s:%s' % (name, provider, scrambled, running_status)
				# actual is set if we are on the right transponder for this program
				if actual:
					# descriptions for current menu have been updated, so update menu
					update_program_menu_names()
					print '***',
				#print 'program %d: %s, is brought to you by %s, is %s, and is %s' % (sid, name, provider, scrambled, running_status)
				if current_program == sid:
					update_video_title(sid)
		return True
	if message_name == "prepare-xwindow-id":
		imagesink = message.src
		imagesink.set_property("force-aspect-ratio", True)
		imagesink.set_property("draw-borders", True)
		# comment out the next line to have video pop up in it's own window
		imagesink.set_xwindow_id(field_video.winfo_id())
		print 'streaming...'
		return True
	if message_name == "eit":
		# need to do something with this!
		return True
	print 'got sync message:', message_name
	for key in message.structure.keys():
		print '  ', key, message.structure[key]
	return True

def set_program(event):
	global current_pids
	global available_programs
	global program

	prog= program.get()
	# split program number and description
	prog= prog.split(':')[0]
	progno= int(prog)
	update_video_title(progno)
	demuxer.set_property("program-number", progno)
	current_pids= '%s:%s' % (MASTER_PIDS, pid_table[prog])
	source.set_property("pids", current_pids)
	player.set_state(gst.STATE_NULL)
	player.set_state(gst.STATE_PLAYING)

def pat_info_changed_callback(demux, param):
	global menu_options
	global available_programs

	print("PAT info has changed")
	pi = demux.get_property("pat-info")
	menu_options=  []
	for prog in pi:
		print("PAT: Program %d on PID 0x%04x" % (prog.props.program_number, prog.props.pid))
		# create structure for program description
		if not available_programs.has_key(int(prog.props.program_number)):
			available_programs.update({int(prog.props.program_number):''})
		pid_table.update({'%d' % prog.props.program_number:'%d' % prog.props.pid})
		menu_options.append('%i:%s' % (int(prog.props.program_number), available_programs[int(prog.props.program_number)]))
	update_program_menu(menu_options)

# update program names for all items in menu
# (call this if available_programs[] has new info in it)
def update_program_menu_names():
	global menu_options
	global available_programs

	new_menu_options= []
	for prog in menu_options:
		progno= int(prog.split(':')[0])
		new_menu_options.append('%i:%s' % (progno,  available_programs[progno]))
	update_program_menu(new_menu_options)

# populate drop-down menu for program selection
def update_program_menu(menu):
	global menu_program
	global menu_options
	global available_programs
	global program

	# create menu for program selection
	menu_options= sorted(menu)
	menu_program.destroy()
	menu_program= OptionMenu(frame_transponder, program, *menu_options, command= set_program)
	menu_program.grid(row= 2, column= 2, sticky= W)
	if program.get() == '':
		program.set(menu_options[0])

def pmt_info_changed_callback(demux, param):
	global current_pids

	pi = demux.get_property("pmt-info")
	print("PMT info for program %s has changed" % pi.props.program_number)
	print("PMT: PCR pid is 0x%04x" % pi.props.pcr_pid)
	current_pids= '%s:%s:%s' % (MASTER_PIDS,pi.props.pcr_pid,pid_table['%d' % pi.props.program_number])
	for s in pi.props.stream_info:
		print("PMT: Stream on pid 0x%04x" % s.props.pid)
		current_pids += ':%s' % s.props.pid
	source.set_property("pids", current_pids)
	return True

#
# widget functions
#

def update(field, data):
	field.delete(0,END)
	field.insert(0,data)

def select_blob(event):
	canvas= event.widget
	x = event.x
	y = event.y
	closest= canvas.find_closest(x,y)
	position, start_frequency, end_frequency, symbol_rate, polarity= (canvas.gettags(closest)[0]).split(',')
	position= int(position)
	start_frequency= int(start_frequency)
	end_frequency= int(end_frequency)
	symbol_rate= int(symbol_rate)
	center= ((end_frequency - start_frequency) / 2) + start_frequency
	update(field_transponder_freq, center)
	transponder_polarity.set(polarity)
	update(field_transponder_symbol, symbol_rate)

def update_video_title(progno):
	global current_program

	frame_video.config(text= ' Video Stream - %s' % available_programs[progno])
	current_program= progno

#
# file frame
#
frame_file= LabelFrame(widget_master, text= " File ")
frame_file.grid(sticky= NW)
field_file= Entry(frame_file, width= 64)
field_file.grid()
def select_file(): get_file()
button_select= Button(frame_file, text= 'Select File', command=select_file)
button_select.grid(pady= 8)

#
# selected transponder frame
#
frame_transponder= LabelFrame(widget_master, text= " Transponder ")
frame_transponder.grid(sticky= NE+W)
# row 0
label_transponder_freq= Label(frame_transponder, text= "Frequency")
label_transponder_freq.grid(row= 0, column= 0, sticky= W, padx=  8)
label_transponder_polarity= Label(frame_transponder, text= "Polarity")
label_transponder_polarity.grid(row= 0, column= 1, sticky= W)
label_transponder_symbol= Label(frame_transponder, text= "Symbol Rate")
label_transponder_symbol.grid(row= 0, column= 2, sticky= W)
# row 1
field_transponder_freq= Entry(frame_transponder, width= 16)
field_transponder_freq.grid(row= 1, column= 0, padx= 8)
transponder_polarity= StringVar()
transponder_polarity.set('-')
menu_transponder_polarity= OptionMenu(frame_transponder, transponder_polarity, '-','H','V')
menu_transponder_polarity.grid(row= 1, column= 1)
field_transponder_symbol= Entry(frame_transponder, width= 16)
field_transponder_symbol.grid(row= 1, column= 2)
# row 2
def do_start_stop(arg= None): start_stop(arg)
button_transponder_tune_state= StringVar()
button_transponder_tune_state.set("Tune")
button_transponder_tune= Button(frame_transponder, textvariable=button_transponder_tune_state, command= do_start_stop)
button_transponder_tune.grid(row= 2, column= 0, pady= 8)
label_program= Label(frame_transponder, text= "Select Program:")
label_program.grid(row= 2, column= 1, sticky= E)
program= StringVar()
menu_program= OptionMenu(frame_transponder, program, '')
menu_program.grid(row= 2, column= 2)
# row 3
network_provider= StringVar()
network_provider.set('Network: None')
label_network_provider= Label(frame_transponder, textvariable= network_provider)
label_network_provider.grid(row= 3, column= 0, sticky= W, padx= 8)

#
# video frame
#
frame_video= LabelFrame(widget_master, text= ' Video Stream ')
frame_video.grid(sticky= NW)
field_video= Canvas(frame_video, width= 512, height= 384, bg= 'black')
field_video.grid()

#
# map frame
#
frame_map= LabelFrame(widget_master, text= " Map - click on blob to select transponder")
frame_map.grid(row= 0, column= 1, rowspan= 3, sticky= NW)
field_map= Canvas(frame_map, width= 600, height= 100, bg= 'black')
field_map.grid(row= 1) 
field_map.bind("<ButtonRelease-1>",select_blob)

def get_file():
	global frame_map
	global widget_master

	file = tkFileDialog.askopenfilename(parent=widget_master,title='Choose a file')
	field_file.delete(0,999)
	field_file.insert(0,file)

	handle= open(file,'r',0)
	handle.readline()
	start_freq, end_freq,  step= ((handle.readline()).strip()).split(',')
	start_freq= int(start_freq)
	end_freq= int(end_freq)
	step= int(step)
	height= (end_freq - start_freq) / step
	yscalefactor= float(height) / float(WINDOW_HEIGHT)
	field_map.config(height= (height / yscalefactor) + (WINDOW_MARGIN * 2))
	# draw scale
	for freq in range(start_freq,end_freq,step * 45):
		field_map.create_text(WINDOW_MARGIN,((height - ((freq - start_freq) / step)) / yscalefactor) + WINDOW_MARGIN + TEXT_OFFSET,fill= 'white', text= freq, anchor=SW)


	handle.readline()
	# get signal strength range
	strength_min= 999999
	strength_max= 0
	for data in handle.readline().strip():
		try:
			position, frequency, symbol_rate, polarity, strength= data.split(',')
			if int(strength) < strength_min:
				strength_min= int(strength)
			if int(strength) > strength_max:
				strength_max= int(strength)
		except:
			break
	# reset data
	handle.seek(0)
	for x in range(4):
		handle.readline()
	# read data one line at a time. one line == one pixel
	y_bot= height - 1
	y_top= y_bot
	current_polarity= '-'
	regions= 0
	start_frequency= 0
	while True:
		data= (handle.readline()).strip()
		if not data == '':
			position, frequency, symbol_rate, polarity, strength= data.split(',')
			x= int(position) + X_OFFSET
			if start_frequency == 0:
				start_frequency= frequency
			if not polarity == current_polarity:
				#if not current_polarity == '-':
					#field_map.create_line(x,(y_bot / yscalefactor) + WINDOW_MARGIN,x,(y_top / yscalefactor) + WINDOW_MARGIN, fill=COLOURS[current_polarity], tag='%s,%s,%s,%s,%s' % (position, start_frequency, end_frequency, symbol_rate, current_polarity))
				field_map.create_line(x,(y_bot / yscalefactor) + WINDOW_MARGIN,x,(y_top / yscalefactor) + WINDOW_MARGIN, fill=COLOURS[current_polarity] % utils.scale(int(strength), strength_min, strength_max, 0xff), tag='%s,%s,%s,%s,%s' % (position, start_frequency, end_frequency, symbol_rate, current_polarity))
				current_polarity= polarity
				y_bot= y_top
				regions += 1
				start_frequency= frequency
			end_frequency= frequency
			y_top -= 1
		else:
			break
	print '%d regions' % regions

#
# gstreamer setup
#
player = gst.Pipeline("player")
source = gst.element_factory_make("dvbsrc", "dvb-source")
parser = gst.element_factory_make("mpegtsparse","parser")
demuxer = gst.element_factory_make("mpegtsdemux", "demuxer")
demuxer.connect("pad-added", demuxer_callback)
demuxer.connect("notify::pat-info", pat_info_changed_callback)
demuxer.connect("notify::pmt-info", pmt_info_changed_callback)
video_decoder = gst.element_factory_make("mpeg2dec", "video-decoder")
audio_decoder = gst.element_factory_make("mad", "audio-decoder")
audioconv = gst.element_factory_make("audioconvert", "converter")
audiosink = gst.element_factory_make("alsasink", "audio-output")
videosink = gst.element_factory_make("xvimagesink", "video-output")
queuea = gst.element_factory_make("queue", "queuea")
queuea.set_property("max-size-buffers", 0)
queuea.set_property("max-size-time", 0)
queuev = gst.element_factory_make("queue", "queuev")
queuev.set_property("max-size-buffers", 0)
queuev.set_property("max-size-time", 0)
colorspace = gst.element_factory_make("ffmpegcolorspace", "colorspace")

#
# connect pipeline
#
player.add(source, parser, demuxer, video_decoder, audio_decoder, audioconv, audiosink, videosink, queuea, queuev, colorspace)
gst.element_link_many(source, parser, demuxer)
# demuxer will connect to output section via dynamic pad upon sync event
gst.element_link_many(queuev, video_decoder, colorspace, videosink)
gst.element_link_many(queuea, audio_decoder, audioconv, audiosink)

bus = player.get_bus()
bus.add_signal_watch()
bus.connect("message", on_message)
bus.enable_sync_message_emission()
bus.connect("sync-message::element", on_sync_message)

#
# let's roll
#
gtk.gdk.threads_init()
widget_master.mainloop()
