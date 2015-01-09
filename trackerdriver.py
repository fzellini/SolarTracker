# -*- coding: utf-8 -*-
# TrackerDriver class
# a TrackerDriver is composed of two linearmotors, have an orientation
#
import math
import time
import logging.handlers
import linearmotor
import pickle
import os
from Vec3d import Vec3d


def getpitchroll(azi, ele):
    vz = math.sin(math.radians(ele))
    vx = -math.cos(math.radians(azi)) * math.cos(math.radians(ele))
    vy = math.sin(math.radians(azi)) * math.cos(math.radians(ele))
    v = Vec3d(vy, vx, vz)
    pitch = v.get_angle_around_x() - 90
    v.rotate_around_x(-pitch)
    roll = v.get_angle_around_y()

    return pitch, roll


class TrackerDriver:
    def __init__(self, pitchmotor, rollmotor, azioffset, statefile="motor.dat"):
        self.pitchMotor = pitchmotor
        self.rollMotor = rollmotor
        self.aziOffset = azioffset
        self.statefile = statefile
        self.restorestate()

    def gotopitchposition(self, pos):
        self.pitchMotor.gopos(pos)
        self.savestate()

    def gotopitchangle(self, angle):
        self.pitchMotor.goangle(angle)
        self.savestate()

    def gotorollposition(self, pos):
        self.rollMotor.gopos(pos)
        self.savestate()

    def gotorollangle(self, angle):
        self.rollMotor.goangle(angle)
        self.savestate()

    def gotopitchrollpos(self, pitchpos, rollpos):
        """
          move both axis together
        :param pitchpos: pitch position in reed steps
        :param rollpos: roll position in reed steps
        """
        log.info("going to pos [pitch %d, roll %d]" % (pitchpos, rollpos))

        # todo: check also for max values
        if pitchpos < 0:
            pitchpos = 0
            log.info("pitchpos forced to 0")
        if rollpos < 0:
            rollpos = 0
            log.info("roll forced to 0")

        self.rollMotor.wait = 0
        self.pitchMotor.wait = 0

        #
        pitch = False
        if abs(pitchpos - self.pitchMotor.pos >= self.pitchMotor.minstep):
            if pitchpos > self.pitchMotor.pos:
                self.pitchMotor.forward()
            else:
                self.pitchMotor.backward()
            pitch = True

        roll = False
        if abs(rollpos - self.rollMotor.pos >= self.rollMotor.minstep):
            if rollpos > self.rollMotor.pos:
                self.rollMotor.forward()
            else:
                self.rollMotor.backward()
            roll = True

        if pitch or roll:
            time.sleep(.2)  # wait direction relais set-up
        if pitch:
            self.pitchMotor.on()
        if roll:
            self.rollMotor.on()

        oroll = -999
        opitch = -999
        txr = time.time()
        txp = txr

        while pitch or roll:
            # log.info( "pitch pos %d, roll pos %d" % (self.pitchMotor.pos,self.rollMotor.pos))
            ty = time.time()
            if pitch:
                if ty - txp > .5:
                    txp = ty
                    if self.pitchMotor.pos == opitch:
                        pitch = False
                    opitch = self.pitchMotor.pos
                if self.pitchMotor.step > 0:
                    # forward
                    if self.pitchMotor.pos > pitchpos - 2:
                        pitch = False
                else:
                    # backward
                    if self.pitchMotor.pos < pitchpos + 2:
                        pitch = False
                if not pitch:
                    self.pitchMotor.off()

            if roll:
                if ty - txr > .5:
                    txr = ty
                    if self.rollMotor.pos == oroll:
                        roll = False
                    oroll = self.rollMotor.pos

                if self.rollMotor.step > 0:
                    # forward
                    if self.rollMotor.pos > rollpos - 2:
                        roll = False
                else:
                    # backward
                    if self.rollMotor.pos < rollpos + 2:
                        roll = False
                if not roll:
                    self.rollMotor.off()

            time.sleep(.1)

        log.info("pitch pos %d, roll pos %d" % (self.pitchMotor.pos, self.rollMotor.pos))

        self.rollMotor.wait = .2
        self.pitchMotor.wait = .2
        self.savestate()

    def gotopitchrollangle(self, pitchangle, rollangle):
        """
          move tracker at specified pitch and roll angle
          positive values for pitch points north, for roll points east
          both pitch and roll == 0 means  horizontal position
        :param pitchangle:  pitch angle
        :param rollangle:   roll angle
        """
        log.info("going to pitchangle %f, rollangle %f" % (pitchangle, rollangle))
        pitchpos = self.pitchMotor.angle2pos(pitchangle)
        rollpos = self.rollMotor.angle2pos(rollangle)
        self.gotopitchrollpos(pitchpos, rollpos)

    def gotoaziele(self, az, alt):
        """
          goto specific azi, ele, applying azioffset
        """
        log.info("going to azi %f, ele %f" % (az, alt))
        if self.aziOffset != 0:
            az = az + self.aziOffset
            az %= 360.0

            log.info("correcting azi to %f due to offset of %f" % (az, self.aziOffset))

        pr = getpitchroll(az, alt)
        log.info("  pitch [%f], roll [%f]" % (pr[0], pr[1]))
        self.gotopitchrollangle(pr[0], pr[1])

    def savestate(self):
        """
          save tracker state (motor position)
        """
        state = (self.pitchMotor.pos, self.rollMotor.pos)
        output = open(self.statefile, 'wb')
        # Pickle dictionary using protocol 0.
        pickle.dump(state, output)
        output.close()
        log.info("position saved [%s, pitch=%d roll=%d]" % (self.statefile, self.pitchMotor.pos, self.rollMotor.pos))

    def restorestate(self):
        """
          save tracker state (motor position)
        """
        if os.path.exists(self.statefile):
            inputhandle = open(self.statefile, 'rb')
            # Pickle dictionary using protocol 0.
            state = pickle.load(inputhandle)
            inputhandle.close()

            self.pitchMotor.pos, self.rollMotor.pos = state
            log.info("restored position from [%s pitch=%d roll=%d]" % (self.statefile,
                                                                       self.pitchMotor.pos,
                                                                       self.rollMotor.pos))

        else:
            self.savestate()


def gpio_out(port, value, label=""):
    # import RPi.GPIO as GPIO
    # GPIO.output (port,value)
    log.info("%s simulate setting of GPIO %d to %d" % (label, port, value))


# main test
if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger("trackerdriver")
    log.setLevel(logging.INFO)

    logm = logging.getLogger("linearmotor")
    logm.setLevel(logging.INFO)

    linearmotor.log = logm

    pitchM = linearmotor.LinearMotor("[pitch]", dirport=21, powerport=19, pulseport=3, pulsestep=0.522, ab=225, bc=355,
                                    cd=40, d=-5, offset=136, hookoffset=34)
    pitchM.set_gpioout(gpio_out)

    rollM = linearmotor.LinearMotor("[roll]", dirport=16, powerport=15, pulseport=5, pulsestep=0.522, ab=225, bc=708,
                                   cd=40, d=75, offset=503)
    rollM.set_gpioout(gpio_out)

    td = TrackerDriver(pitchM, rollM, 0)
    # td.gotoPitchRollAngle(0,0)

    td.gotoaziele(150, 45)


