#!/usr/bin/env python

# This file is part of Openplotter.
# Copyright (C) 2015 by sailoog <https://github.com/sailoog/openplotter>
#
# Openplotter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# any later version.
# Openplotter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Openplotter. If not, see <http://www.gnu.org/licenses/>.

import sys, ConfigParser, os, socket, time, pynmea2, geomag, datetime, RTIMU, math, threading

pathname = os.path.dirname(sys.argv[0])
currentpath = os.path.abspath(pathname)

data_conf = ConfigParser.SafeConfigParser()
data_conf.read(currentpath+'/openplotter.conf')


#global variables
global position
position=['','','','']
global date
date=datetime.date.today()
global mag_var
mag_var=['','']
global heading
heading=''

def thread_frecuency():
	SETTINGS_FILE = "RTIMULib"
	s = RTIMU.Settings(SETTINGS_FILE)
	imu = RTIMU.RTIMU(s)
	imu.IMUInit()

 	global mag_var
 	global heading

	tick=time.time()

 	while True:
 		tick2=time.time()
		if tick2-tick > float(data_conf.get('STARTUP', 'nmea_rate')):
			tick=time.time()
# mag_var
			mag_var=[]
			if position[0] and position[2]:
				lat=lat_DM_to_DD(position[0])
				if position[1]=='S': lat = lat * -1
				lon=lon_DM_to_DD(position[2])
				if position[3]=='W': lon = lon * -1
				now = date
				var=float(geomag.declination(lat, lon, 0, now))
				var=round(var,1)
				if var >= 0.0:
					mag_var=[var,'E']
				if var < 0.0:
					mag_var=[var*-1,'W']
			else:
				mag_var=['','']

# hdg
			if data_conf.get('STARTUP', 'nmea_hdg')=='1':
				if imu.IMURead():
					data = imu.getIMUData()
					fusionPose = data["fusionPose"]
					heading=math.degrees(fusionPose[2])
					if heading<0:
						heading=360+heading
					heading=round(heading,1)
				hdg = pynmea2.HDG('OP', 'HDG', (str(heading),'','',str(mag_var[0]),mag_var[1]))
				hdg1=str(hdg)
				hdg2=repr(hdg1)+"\r\n"
				hdg3=hdg2.replace("'", "")
				sock.sendto(hdg3, ('localhost', 10110))
				print hdg3


def lat_DM_to_DD(DM):
	degrees=float(DM[0:2])
	minutes=float(DM[2:len(DM)])
	minutes=minutes/60
	DD=degrees+minutes
	return DD

def lon_DM_to_DD(DM):
	degrees=float(DM[0:3])
	minutes=float(DM[3:len(DM)])
	minutes=minutes/60
	DD=degrees+minutes
	return DD


def create_rmc(msg):
	msgstr=str(msg)
	items=msgstr.split(',')
	last_item=items[12].split('*')
	if mag_var[0]: mag_var[0]=str(mag_var[0])
	rmc = pynmea2.RMC('OP', 'RMC', (items[1],items[2],items[3],items[4],items[5],items[6],items[7],items[8],items[9],mag_var[0],mag_var[1],last_item[0]))
	rmc1=str(rmc)
	rmc2=repr(rmc1)+"\r\n"
	rmc3=rmc2.replace("'", "")
	sock.sendto(rmc3, ('localhost', 10110))
	print rmc3


def check_nmea():
	global position
	global date
	while True:
		frase_nmea =''
		try:
			frase_nmea = sock_in.recv(512)
		except socket.error, error_msg:
			print 'Failed to connect with localhost:10110.'
			print 'Error: '+ str(error_msg[0])
			break
		else:
			if frase_nmea:
				try:
					msg = pynmea2.parse(frase_nmea)

					#position
					if msg.sentence_type == 'RMC' or msg.sentence_type =='GGA' or msg.sentence_type =='GNS' or msg.sentence_type =='GLL':
						position=[msg.lat, msg.lat_dir, msg.lon, msg.lon_dir]

					#date
					if msg.sentence_type == 'RMC':
						date=msg.datestamp

					#$OPRMC
					if msg.talker != 'OP' and msg.sentence_type == 'RMC' and data_conf.get('STARTUP', 'nmea_rmc')=='1':
						create_rmc(msg)

				#except Exception,e: print str(e)
				except: pass
			else:
				break


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

hilo=threading.Thread(target=thread_frecuency)
hilo.setDaemon(1)
hilo.start()

while True:
	try:
		sock_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock_in.settimeout(10)
		sock_in.connect(('localhost', 10110))
	except socket.error, error_msg:
		print 'Failed to connect with localhost:10110.'
		print 'Error: '+ str(error_msg[0])
	else: 
		check_nmea()

	print 'No data, trying to reconnect...'
	time.sleep(7)