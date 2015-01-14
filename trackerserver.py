# -*- coding: utf-8 -*-
# controller motori
# 

import sys, logging, getopt
import logging.handlers
import time
import os
import re
import SocketServer
import linearmotor
import trackerdriver
import ConfigParser

cback = {}
broadCom = {19: 10, 21: 9, 22: 25, 15: 22, 16: 23, 18: 24}
motorCmd = re.compile("(roll|pitch) +((calibrate)|(a) ([-+]?[\d.]+)|(p) ([\d.]+))")
prCmd = re.compile("(pitchroll) +((a) ([-+]?[\d.]+),([-+]?[\d.]+)|(p) ([\d.]+),([\d.]+))")
aeCmd = re.compile("(ae) +(([\d.]+),([\d.]+))")
lockCmd = re.compile("(lock) +(on|off|@a ([-+]?[\d.]+),([-+]?[\d.]+))")

locked = False


def domotor(axis, cmd, match):
    global pitchMotor, rollMotor

    if axis == "pitch":
        motor = pitchMotor
    elif axis == "roll":
        motor = rollMotor
    else:
        log.warn("invalid axis [%s]" % axis)
        return

    if cmd == "calibrate":
        motor.calibrate()
        tDriver.savestate()
    else:
        if match.group(4):
            angle = float(match.group(5))
            motor.goangle(angle)
            tDriver.savestate()
        if match.group(6):
            pos = int(match.group(7))
            motor.gopos(pos)
            tDriver.savestate()

    time.sleep(1)



class MyTCPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        global rollCmd, prCmd, RPCV, locked

        h = self.request.makefile()
        data = h.readline().strip()
        log.debug("{} wrote:".format(self.client_address[0]))
        log.debug("[%s]" % (data))
        #
        # commands: roll <calibrate|step>
        #

        cmd = False

        match = motorCmd.match(data)
        if match:
            axis = match.group(1)
            cmd = match.group(2)
            if not locked:
                log.info("executing [%s %s]" % (axis, cmd))
                h.write("executing [%s %s]" % (axis, cmd))
                domotor(axis, cmd, match)
            else:
                log.info("locked: ignoring executing [%s %s]" % (axis, cmd))
                h.write("locked: ignoring executing [%s %s]" % (axis, cmd))

        match = prCmd.match(data)
        if match:
            cmd = "pr"
            if not locked:
                log.info("executing [%s %s]" % (match.group(1), match.group(2)))
                h.write("executing [%s %s]" % (match.group(1), match.group(2)))
                p = match.group(6)
                a = match.group(3)
                if a:
                    tDriver.gotopitchrollangle(float(match.group(4)), float(match.group(5)))
                    time.sleep(1)
                if p:
                    tDriver.gotopitchrollpos(int(match.group(7)), int(match.group(8)))
                    time.sleep(1)
            else:
                log.info("locked: ignoring executing [%s %s]" % (match.group(1), match.group(2)))
                h.write("locked: ignoring executing [%s %s]" % (match.group(1), match.group(2)))

        match = aeCmd.match(data)
        if match:
            cmd = "ae"
            if not locked:
                log.info("executing [%s %s]" % (match.group(1), match.group(2)))
                h.write("executing [%s %s]" % (match.group(1), match.group(2)))
                tDriver.gotoaziele(float(match.group(3)), float(match.group(4)))
                time.sleep(1)
            else:
                log.info("locked: ignoring executing [%s %s]" % (match.group(1), match.group(2)))
                h.write("locked: ignoring executing [%s %s]" % (match.group(1), match.group(2)))

        match = lockCmd.match(data)
        if match:
            cmd = "lock"
            secure = match.group(2)
            if secure == "on":
                locked = True
                log.info("Tracker locked")
                h.write("Tracker locked")
            elif secure == "off":
                locked = False
                log.info("Tracker unlocked")
                h.write("Tracker unlocked")
            elif secure.startswith("@a"):
                locked = True
                lockpitch = match.group(3)
                lockroll = match.group(4)
                lockpitch = float(lockpitch)
                lockroll = float(lockroll)
                tDriver.gotopitchrollangle(lockpitch, lockroll)
                log.info("Tracker locked at position %f,%f" % (lockpitch, lockroll))
                h.write("Tracker locked at position %f,%f" % (lockpitch, lockroll))

            else:
                cmd = None  # trigger error

        if not cmd:
            log.info("Unknown command")
            h.write("Unknown command")

        h.flush()


def setup_gpio():
    global pi1
    global simulation
    global config
    if simulation:
        return

    if iolib == "GPIO":
        # use P1 header pin numbering convention
        GPIO.setmode(GPIO.BOARD)

        # pitch
        GPIO.setup(config.getint("pitch", "powerport"), GPIO.OUT)  # pitch power
        GPIO.setup(config.getint("pitch", "dirport"), GPIO.OUT)  # pitch dir
        GPIO.setup(config.getint("pitch", "pulseport"), GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pitch sensor

        # roll
        GPIO.setup(config.getint("roll", "powerport"), GPIO.OUT)  # roll power
        GPIO.setup(config.getint("roll", "dirport"), GPIO.OUT)  # roll dir
        GPIO.setup(config.getint("roll", "pulseport"), GPIO.IN, pull_up_down=GPIO.PUD_UP)  # roll sensor

    elif iolib == "pigpio":
        pi1 = pigpio.pi()
        # pitch
        pi1.set_mode(broadCom[config.getint("pitch", "powerport")], pigpio.OUTPUT)
        pi1.set_mode(broadCom[config.getint("pitch", "dirport")], pigpio.OUTPUT)
        pi1.set_mode(broadCom[config.getint("pitch", "pulseport")], pigpio.INPUT)
        pi1.set_pull_up_down(broadCom[config.getint("pitch", "pulseport")], pigpio.PUD_UP)

        # roll
        pi1.set_mode(broadCom[config.getint("roll", "powerport")], pigpio.OUTPUT)
        pi1.set_mode(broadCom[config.getint("roll", "dirport")], pigpio.OUTPUT)
        pi1.set_mode(broadCom[config.getint("roll", "pulseport")], pigpio.INPUT)
        pi1.set_pull_up_down(broadCom[config.getint("roll", "pulseport")], pigpio.PUD_UP)

    else:
        pass


def cleanup_gpio():
    global config
    global pi1
    if simulation:
        return
    if iolib == "GPIO":
        GPIO.output(config.getint("pitch", "powerport"), 0)
        GPIO.output(config.getint("roll", "powerport"), 0)
        GPIO.cleanup()
    elif iolib == "pigpio":
        pi1.stop()
    else:
        pass


def usage():
    print "Usage : %s [-s,--simulate] [-c,--config=<configuration file>] [-h,--help]" % (sys.argv[0])
    sys.exit(1)


if __name__ == "__main__":

    statefile = "motor.dat"
    simulation = False
    pitchrolldatafile = "pr.dat"
    HOST, PORT = "localhost", 9999
    angleOffset = 0
    iolib = "pigpio"
    configFile = "tracker.ini"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hsc:", ["help", "simulate", "config="])
    except getopt.GetoptError:
        print "Error parsing argument:", sys.exc_info()[1]
        # print help information and exit:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(2)

        if o in ("-s", "--simulate"):
            simulation = True

        if o in ("-c", "--config"):
            configFile = a

    # read and parse config file

    config = ConfigParser.SafeConfigParser()
    config.read(configFile)

    HOST = config.get("globals", "host")
    PORT = config.getint("globals", "port")
    angleOffset = config.getfloat("globals", "angleOffset")
    statefile = config.get("globals", "statefile")
    log = config.get("globals", "log")
    iolib = config.get("globals", "iolib")

    # log stuffs

    logName = os.environ['HOME'] + "/logs/" + log
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s')
    fh = logging.handlers.TimedRotatingFileHandler(filename=logName, when="midnight", interval=1, backupCount=5)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    log = logging.getLogger("trackerserver")
    log.setLevel(logging.DEBUG)
    log.addHandler(fh)
    log.addHandler(ch)

    logt = logging.getLogger("trackerdriver")
    logt.setLevel(logging.DEBUG)
    logt.addHandler(fh)
    logt.addHandler(ch)
    trackerdriver.log = logt

    logm = logging.getLogger("linearmotor")
    logm.setLevel(logging.DEBUG)
    logm.addHandler(fh)
    logm.addHandler(ch)
    linearmotor.log = logm

    if iolib not in ("GPIO", "pigpio"):
        log.error("invalid iolib [%s]: must be GPIO or pigpio" % (iolib))

    log.info("using iolib [%s]" % (iolib))
    if angleOffset != 0:
        log.info("angle-offset [%f]" % (angleOffset))

    log.info("statefile [%s]" % (statefile))

    # selective imports
    if not simulation:
        if iolib == "pigpio":
            import pigpio

        if iolib == "GPIO":
            import RPi.GPIO as GPIO

    setup_gpio()

    log.info("Starting server on port [%d], simulation [%s]" % (PORT, simulation))

    if not simulation:

        if iolib == "GPIO":
            # define functions for GPIO library

            def gpio_out(port, value, label=""):
                GPIO.output(port, value)
                log.info("%s setted GPIO %d to %d" % (label, port, value))

            def gpio_in(port):
                return GPIO.input(port)

            # set edgeCallBack function
            def set_edgecallbackfn(port, fn, label=""):
                log.info("%s set edge callback on port # %d" % (label, port))
                GPIO.add_event_detect(port, GPIO.BOTH, callback=fn, bouncetime=2)

            def cancelcallback(port, label=""):
                log.info("%s cancel callback fn for port : # %d" % (label, port))
                GPIO.remove_event_detect(port)

        elif iolib == "pigpio":
            def gpio_out(port, value, label=""):
                # ALL gpios are identified by their Broadcom number
                pi1.write(broadCom[port], value)

            def gpio_in(port):
                return pi1.read(broadCom[port])

            def set_edgecallbackfn(port, fn, label=""):
                global cback
                log.info("%s set edge callback fn for port # %d" % (label, port))
                if port in cback.keys():
                    cback[port].cancel()
                cback[port] = pi1.callback(broadCom[port], pigpio.EITHER_EDGE, fn)

            def cancelcallback(port, label=""):
                global cback
                log.info("%s cancel callback on port # %d" % (label, port))
                if port in cback.keys():
                    cback[port].cancel()

        else:
            pass
    else:

        def gpio_out(port, value, label=""):
            # import RPi.GPIO as GPIO
            # GPIO.output (port,value)
            log.info("%s simulate setting GPIO %d to %d" % (label, port, value))

        def gpio_in(port):
            log.info("simulated read GPIO # %d" % (port))

        def set_edgecallbackfn(port, fn, label=""):
            log.info("%s simulated set edge callback fn on port # %d" % (label, port))

        def cancelcallback(port, label=""):
            log.info("%s simulated cancel callback for port # %d" % (label, port))

    pitchMotor = linearmotor.LinearMotor(
        "[pitch]",
        dirport=config.getint("pitch", "dirport"),
        powerport=config.getint("pitch", "powerport"),
        pulseport=config.getint("pitch", "pulseport"),
        pulsestep=config.getfloat("pitch", "pulsestep"),
        ab=config.getfloat("pitch", "ab"),
        bc=config.getfloat("pitch", "bc"),
        cd=config.getfloat("pitch", "cd"),
        d=config.getfloat("pitch", "d"),
        offset=config.getfloat("pitch", "offset"),
        hookoffset=config.getfloat("pitch", "hookoffset"),
        minstep=config.getint("pitch", "minstep"))

    pitchMotor.set_gpioout(gpio_out)
    pitchMotor.set_gpioin(gpio_in)
    pitchMotor.set_edgepulsecallbackfn(set_edgecallbackfn)
    pitchMotor.set_cancelpulsecallbackfn(cancelcallback)

    rollMotor = linearmotor.LinearMotor(
        "[roll]",
        dirport=config.getint("roll", "dirport"),
        powerport=config.getint("roll", "powerport"),
        pulseport=config.getint("roll", "pulseport"),
        pulsestep=config.getfloat("roll", "pulsestep"),
        ab=config.getfloat("roll", "ab"),
        bc=config.getfloat("roll", "bc"),
        cd=config.getfloat("roll", "cd"),
        d=config.getfloat("roll", "d"),
        offset=config.getfloat("roll", "offset"),
        hookoffset=config.getfloat("roll", "hookoffset"),
        minstep=config.getint("roll", "minstep"))

    rollMotor.set_gpioout(gpio_out)
    rollMotor.set_gpioin(gpio_in)
    rollMotor.set_edgepulsecallbackfn(set_edgecallbackfn)
    rollMotor.set_cancelpulsecallbackfn(cancelcallback)

    tDriver = trackerdriver.TrackerDriver(pitchMotor, rollMotor, angleOffset, statefile=statefile)
    # if statefile and os.path.isfile(statefile):
    #    tDriver.restoreState (statefile)

    server = False
    try:
        # Create the server, binding to localhost on port 9999
        server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)

        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
    except:

        print sys.exc_info()
        if server:
            print "Shutting down server"
            server.shutdown()
        cleanup_gpio()

    cleanup_gpio()
