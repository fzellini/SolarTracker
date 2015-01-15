# -*- coding: utf-8 -*-
# linearMotor class
#

import math
import time
import logging.handlers


def gpio_out(port, value, label=""):
    # import RPi.GPIO as GPIO
    # GPIO.output (port,value)
    log.info("%s simulate setting of GPIO %d to %d" % (label, port, value))


def deg2rad(deg):
    return deg * math.pi / 180


def rad2deg(rad):
    return 180 * rad / math.pi


class LinearMotor:
    def set_gpioout(self, gpioout):
        self.gpioOut = gpioout

    def set_gpioin(self, gpioin):
        self.gpioIn = gpioin

    def set_edgepulsecallbackfn(self, setedgecallbackfn):
        """
          edge callback function
        """
        self.setEdgeCallbackFn = setedgecallbackfn
        self.setEdgeCallbackFn(self.pulsePort, self.edgepulse, label=self.name)

    def set_cancelpulsecallbackfn(self, cancelcallback):
        self.cancelPulseCallbackFn = cancelcallback

    def __init__(self, name, dirport, powerport, pulseport, pulsestep, ab, bc, cd, d, offset, hookoffset=0, minstep=20):
        self.name = name
        self.dirPort = dirport
        self.powerPort = powerport
        self.pulsePort = pulseport
        self.pulseStep = pulsestep  # mm per pulse
        self.ab = ab  # raggio
        self.bc = bc  # distanza centro rotazione - attacco motore
        self.cd = cd  # distanza attacco motore braccio motore
        self.d = d  # spostamento dalla verticale attacco motore
        self.offset = offset  # estensione minima ( distanza attacco motore->perno)
        self.hookoffset = hookoffset
        self.hookdeg = rad2deg(math.atan2(hookoffset, ab))

        self.h = (bc ** 2 - d ** 2) ** .5

        self.b1 = rad2deg(math.atan2(d, self.h))  # angolo tra bc e  la verticale

        self.step = 1
        self.pos = 0
        self.wait = .2
        self.power = 0
        self.minstep = minstep

        self.gpioOut = None
        self.gpioIn = None
        self.setEdgeCallbackFn = None
        self.cancelPulseCallbackFn = None

        self.minAngle = None
        self.maxAngle = None

        log.info("LinearMotor %s created" % name)

    def setanglerange(self, minangle, maxangle):
        """
        set angle range for this motor
        """
        self.minAngle = minangle
        self.maxAngle = maxangle

    def setinitialpos(self, pos):
        """
          set initial position
        """
        self.pos = pos

    def setdir(self, direction):
        """
          switch diretion relay
          -1 = backwards
           1  = forwards ( extension )
        """
        log.info("%s issued setDir %d" % (self.name, direction))
        self.step = direction
        pval = 1
        if direction == -1:
            pval = 0

        self.gpioOut(self.dirPort, pval, label=self.name)  # dir
        time.sleep(self.wait)

    def setpower(self, power):
        """
          switch power relay
           0  = off
           1  = on
        """
        # glitch management
        log.info("%s issued setPower %d" % (self.name, power))

        self.gpioOut(self.powerPort, power, label=self.name)
        # time.sleep (0.2)
        self.power = power

    def backward(self):
        self.setdir(-1)

    def forward(self):
        self.setdir(1)

    def on(self):
        self.setpower(1)

    def off(self):
        self.setpower(0)

    def gopos(self, newpos):
        """
          goto position
        """
        log.info("%s going to pos %d" % (self.name, newpos))
        if newpos < 0:
            newpos = 0
            log.info("%s newpos forced to 0" % self.name)

        if abs(newpos - self.pos) < self.minstep:
            return
        if newpos > self.pos:
            self.forward()
        else:
            self.backward()

        self.on()

        opp = -999
        tx = time.time()
        while True:
            ty = time.time()
            if ty - tx > .5:
                tx = ty
                if opp == self.pos:
                    break
                opp = self.pos

            # log.info( "%s pos %d" % (self.name,self.pos))
            if self.step > 0:
                # forward
                if self.pos > newpos - 2:
                    break
            else:
                # backward
                if self.pos < newpos + 2:
                    break

            time.sleep(.1)

        log.info("%s pos %d" % (self.name, self.pos))

        self.off()

    def angle2pos(self, angle):
        anglein = angle
        angle += 90

        beta = angle - self.b1
        beta -= self.hookdeg
        # log.info ( "%s angle %f b1 %f hook %f offset-ed angle %f" % (self.name,angle,self.b1,self.hookdeg,beta))

        teta = 90
        beta = deg2rad(beta)
        teta = deg2rad(teta)
        ac = (self.ab ** 2 + self.bc ** 2 - 2 * self.ab * self.bc * math.cos(beta)) ** .5
        y2 = math.asin((self.ab * math.sin(beta)) / ac)
        a2 = deg2rad(180) - (beta + y2)
        a1 = math.asin((self.cd * math.sin(teta)) / ac)
        a = a1 + a2
        y = deg2rad(360) - (a + beta + teta)
        y1 = y - y2
        ad = (ac * math.sin(y1)) / math.sin(teta)
        px = ad - self.offset

        # log.info( "%s lato incognito %d (offset-ed %d), angolo su a %f, angolo su c %f" % (self.name,ad,px,rad2deg(a),rad2deg(y)))

        position = px / self.pulseStep
        # log.info ( "%s for %f degree LX is %f (%f inches)" % (self.name,angle,px,px/25.4))
        log.debug("%s - angle2pos - angle %f -> position: %f" % (self.name, anglein, position))
        return position

    def fixangle(self, angle):
        if self.minAngle is not None and angle < self.minAngle:
            angle = self.minAngle
            log.warn("%s angle too low: clipped to %f" % (self.name, angle))
        if self.maxAngle is not None and angle > self.maxAngle:
            angle = self.maxAngle
            log.warn("%s angle too high: clipped to %f" % (self.name, angle))
        return angle

    def goangle(self, angle):
        log.info("%s going to angle %f" % (self.name, angle))
        angle = self.fixangle(angle)
        position = self.angle2pos(angle)
        self.gopos(position)

    def edgepulse(self, gpio=None, level=None, tick=None):

        # if not self.power:
        #  return                          # glitch ?
        if level is None:
            level = self.gpioIn(self.pulsePort)

        # rising edge on forward = ++
        # falling edge on backward = --
        if level:
            if self.step > 0:
                self.pos += 1
        else:
            if self.step < 0:
                self.pos -= 1

    def calibrate(self):
        """
          goto "0" position
        """
        log.info("%s calibration" % (self.name))
        self.backward()
        self.on()
        opp = -999

        endtime = time.time() + 120  # max seconds for calibration
        while opp != self.pos and time.time() < endtime:
            log.info("%s pos %d" % (self.name, self.pos))
            opp = self.pos
            time.sleep(.4)

        self.off()
        time.sleep(.4)
        self.pos = 0


if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger("linearmotor")
    log.setLevel(logging.INFO)

    # 755

    pitch = LinearMotor("[pitch]", dirport=21, powerport=19, pulseport=3, pulsestep=0.522, ab=225, bc=355, cd=40, d=-5,
                        offset=136, hookoffset=34)
    pitch.set_gpioout(gpio_out)

    roll = LinearMotor("[roll]", dirport=16, powerport=15, pulseport=5, pulsestep=0.522, ab=225, bc=708, cd=40, d=75,
                       offset=503)
    roll.set_gpioout(gpio_out)

    roll.goangle(70)
    #  roll.calibrate()
    pitch.goangle(70)

