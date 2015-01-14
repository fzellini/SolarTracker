# -*- coding: utf-8 -*-
import sys, logging, getopt, re
import logging.handlers
import time
import os
import pickle
import math
from sun import sun_az_alt, sun_time
import datetime
import socket
# sudo apt-get install python-tz
import pytz


formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
logName = os.environ['HOME'] + "/logs/tracker2.log"
log = logging.getLogger("tracker2")
log.setLevel(logging.DEBUG)
fh = logging.handlers.TimedRotatingFileHandler(filename=logName, when="midnight", interval=1, backupCount=5)
fh.setLevel(logging.DEBUG)
# fh.setFormatter (formatter)
log.addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# ch.setFormatter (formatter)
log.addHandler(ch)


def usage():
    print "Usage : %s [--latitude=<latitude> ] [--longitude=<longitude>] [--timezone=<timezone, default CET>] " \
          "[-s,--step=<step[s|m]>] [--motor-driver-address=<address[:port]>] [--timewarp=<factor>] [--simulate] " \
          "[--startfrom=<dd/mm/YYYY-HH:MM>]" % (sys.argv[0])
    sys.exit(1)


def sendcmd2motor(data):
    global simulate
    # Create a socket (SOCK_STREAM means a TCP socket)
    if simulate:
        log.info("simulating send [%s] to motor" % (data))
        return

    log.info("Attempt to send [%s] to motor" % (data))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Connect to server and send data
        sock.connect((motordriveraddress, motordriverport))
        sock.sendall(data + "\n")
        # Receive data from the server and shut down
        r = 'Response ['
        sys.stdout.write(r)
        while True:
            data = sock.recv(1)
            if not data: break
            r = r + data
            sys.stdout.write(data)
            sys.stdout.flush()
        sys.stdout.write("]\n")
        r += "]"
        log.info(r)
    except:
        log.error("Error communicating with motors")

    finally:
        sock.close()


# time warp factor ( 0 = disabled )
timeWarp = 0
startUTime = 0
startUTC = False

# time routines


def sleep(tempo):
    global timeWarp
    tempo = float(tempo)
    if not timeWarp:
        time.sleep(tempo)
    else:
        time.sleep(tempo / timeWarp)


def unixtime():
    global startUTime, timeWarp

    tempo = time.time()
    if not startUTime:
        startUTime = tempo
    if not timeWarp:
        return tempo
    else:
        return (tempo - startUTime) * timeWarp


def utcnow():
    global startUTC, timeWarp, startFROM
    dt = datetime.datetime.utcnow()
    if not startUTC:
        if startFROM:
            startUTC = startFROM
            startFROM = dt - startFROM
        else:
            startUTC = dt
    if not timeWarp:
        return dt
    else:
        if startFROM:
            dt = dt - startFROM
        tdelta = (dt - startUTC) * timeWarp
        return startUTC + tdelta


def getlocaltime(dt):
    return dt + utcoffset


def time2str(dt):
    return "%s (%s UTC)" % (getlocaltime(dt), dt)


if __name__ == "__main__":

    step = 60
    latitude = 42.021
    longitude = 12.468817
    motordriveraddress = "localhost"
    motordriverport = 9999
    simulate = False
    startFROM = False
    timeZone = "CET"

    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:",
                                   ["help", "latitude=", "longitude=", "motor-driver-address=", "step=", "timewarp=",
                                    "simulate", "startfrom=", "timezone="])
    except getopt.GetoptError:
        # print help information and exit:
        print "Error parsing argument:", sys.exc_info()[1]
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(2)
        if o == "--simulate":
            simulate = True

        if o in ("-s", "--step"):
            mul = 1
            if a[-1] == 's':
                a = a[:-1]
            if a[-1] == 'm':
                a = a[:-1]
                mul = 60
            step = float(a) * mul

        if o == "--startfrom":
            startFROM = datetime.datetime.strptime(a, "%d/%m/%Y-%H:%M")
            log.info("startFROM %s" % startFROM)

        if o == "--latitude":
            latitude = float(a)
        if o == "--longitude":
            longitude = float(a)
        if o == "--motor-driver-address":
            ap = a.split(":")
            if ap.len() == 1:
                motordriveraddress = ap[0]
            elif ap.len() == 2:
                motordriveraddress, motordriverport = ap
            else:
                usage()
        if o == "--timewarp":
            timeWarp = int(a)
        if o == "--timezone":
            timeZone = a

    log.info("Tracker location [%f,%f], timezone %s" % (latitude, longitude, timeZone))
    log.info("Step is %f seconds" % step)
    log.info("motor driver server address [%s:%d]" % (motordriveraddress, motordriverport))

    if timeWarp:
        log.warn("simulation mode: timeWarp %d" % timeWarp)

    # td=datetime.timedelta(minutes=10)

    # timediff from UTC
    loc_dt = pytz.timezone(timeZone)

    if startFROM and timeWarp:
        # timediff from UTC of startFROMP
        a = loc_dt.localize(startFROM)
    else:
        a = loc_dt.localize(datetime.datetime.now())

    utcoffset = a.tzinfo.utcoffset(a)
    if startFROM and timeWarp:
        startFROM = startFROM - utcoffset  # startFROM as local time

    log.info("utc diff %s" % utcoffset)

    twilight_angle = 6  # crepuscolo civile
    tracking_angle = -6  # traccia fino a questa altezza del sole, poi smette

    now = utcnow()
    levt = now

    # giorno o notte ?
    ok, trise = sun_time(now, longitude, latitude, rising=True, angle=twilight_angle)
    ok, tset = sun_time(now, longitude, latitude, rising=False, angle=twilight_angle)
    trise = trise.replace(year=now.year, month=now.month, day=now.day)
    tset = tset.replace(year=now.year, month=now.month, day=now.day)

    ok, tstart = sun_time(now, longitude, latitude, rising=True, angle=tracking_angle)
    ok, tend = sun_time(now, longitude, latitude, rising=False, angle=tracking_angle)
    tstart = tstart.replace(year=now.year, month=now.month, day=now.day)
    tend = tend.replace(year=now.year, month=now.month, day=now.day)

    day = False
    track = False
    if now > trise and now < tset:
        day = True
    if now > tstart and now < tend:
        track = True

    if not day:
        trise = trise + datetime.timedelta(days=1)
        tset = tset + datetime.timedelta(days=1)
        tstart = tstart + datetime.timedelta(days=1)
        tend = tend + datetime.timedelta(days=1)

    log.info("Day: %s" % day)
    log.info("Track: %s" % track)

    log.info("morning twilight at %s" % (time2str(trise)))
    log.info("tracking start at %s" % (time2str(tstart)))

    log.info("tracking end at %s" % (time2str(tend)))
    log.info("evening twilight at %s" % (time2str(tset)))

    t = unixtime()
    tevt = t

    while True:
        t = unixtime()
        # event generation
        #   "time"  timer elapsed
        #   "night" day->night transition
        #   "day"   night->day transition
        #
        event = False
        if t >= tevt:
            event = "time"
            tevt += step
            now = utcnow()
            if levt < tset and now > tset:
                event = "night"
            if levt < trise and now > trise:
                event = "day"

            if levt < tend and now > tend:
                event = "endtrack"
            if levt < tstart and now > tstart:
                event = "track"

            levt = now

        if event:
            log.info("%s - event [%s]" % (time2str(now), event))
        else:
            continue

        if event == "track":
            track = True
        if event == "endtrack":
            track = False

        if event == "time" and track:
            az, alt = sun_az_alt(now, longitude, latitude)
            log.info("  azimuth %f, elevation %f" % (az, alt))
            # convert az,alt to pitch and roll and send to motor controller
            sendcmd2motor("ae %f,%f" % (az, alt))

        if event == "night":
            # recompute set & rise

            ok, trise = sun_time(now, longitude, latitude, rising=True, angle=twilight_angle)
            trise = trise.replace(year=now.year, month=now.month, day=now.day)
            trise = trise + datetime.timedelta(days=1)

            ok, tset = sun_time(now, longitude, latitude, rising=False, angle=twilight_angle)
            tset = tset.replace(year=now.year, month=now.month, day=now.day)
            tset = tset + datetime.timedelta(days=1)

            ok, tstart = sun_time(now, longitude, latitude, rising=True, angle=tracking_angle)
            tstart = tstart.replace(year=now.year, month=now.month, day=now.day)
            tstart = tstart + datetime.timedelta(days=1)

            ok, tend = sun_time(now, longitude, latitude, rising=False, angle=tracking_angle)
            tend = tend.replace(year=now.year, month=now.month, day=now.day)
            tend = tend + datetime.timedelta(days=1)

            log.info("morning twilight at %s" % (time2str(trise)))
            log.info("tracking start at %s" % (time2str(tstart)))

            log.info("tracking end at %s" % (time2str(tend)))
            log.info("evening twilight at %s" % (time2str(tset)))

            day = False
            # calibrate motors
            sendcmd2motor("roll calibrate")
            sendcmd2motor("pitch calibrate")
            #
            az, alt = sun_az_alt(tstart, longitude, latitude)
            log.info("  for next day azimuth %f, elevation %f" % (az, alt))
            # sendCmdToMotor ("ae %f,%f" % (az,alt))
            sendcmd2motor("pitchroll a 0,0")  # upside position at night

        if event == "day":
            # position tracker to morning position
            az, alt = sun_az_alt(tstart, longitude, latitude)
            log.info("  aurora positioning %f, elevation %f" % (az, alt))
            sendcmd2motor("ae %f,%f" % (az, alt))

            day = True

        sleep(step)

    sys.exit(0)
