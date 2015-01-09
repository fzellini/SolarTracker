#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The code in this module is adapted from algorithms provided in

"Practical Astronomy with your Calculator or Spreadsheet"
 by Peter Duffett-Smith and Jonathan Zwart
 http://www.cambridge.org/practicalastronomy

Conventions:
============
ldate: local date
gdate: Greenwich date, i.e. local date/time converted to UTC
lon_obs, lat_obs: coordinates of observer

jst: "julian siderial time", number of siderial hours since 2000-1-1 epoch
     plus siderial time at that moment. To get the normal siderial time in
     hours, take the value modulo 24.0.
     more docs on https://pythonhosted.org/timbre/astro.html
"""

from __future__ import division
import datetime as dtm
import math


def _fract(x):
    return x - int(x)


def cd_to_jd(gdate):
    """Convert Greenwich date to Julian date."""
    result = 1721424.5 + gdate.toordinal()
    try:
        return result + (gdate.hour * 3600 + gdate.minute * 60 +
                         gdate.second + gdate.microsecond * 1e-6) / 86400.0
    except AttributeError:
        # date parameter is of type 'date' instead of 'datetime'
        return result


def jd_to_cd(jd):
    """Convert Julian date to calendar date."""
    date = jd - 1721424.5
    result = dtm.datetime.fromordinal(int(date))
    result += dtm.timedelta(seconds=86400.0 * _fract(date))
    return result


def start_of_day(gdatetime):
    """Set the time part of a datetime value to zero."""
    return gdatetime.replace(hour=0, minute=0, second=0, microsecond=0)


def solar_hours(t):
    """Convert siderial hours into solar (normal) hours."""
    return t * 0.9972695663


def eccentric_anomaly(am, ec):
    """Return eccentric anomaly for given mean anomaly and eccentricity.

    am: mean anomaly
    ec: eccentricity,
    """
    m = am % (2 * math.pi)
    ae = m
    while 1:
        d = ae - (ec * math.sin(ae)) - m
        if abs(d) < 0.000001:
            break
        ae -= d / (1.0 - (ec * math.cos(ae)))
    return ae


def true_anomaly(am, ec):
    """Return true anomaly for given mean anomaly and eccentricity.

    am: mean anomaly
    ec: eccentricity,
    """
    ae = eccentric_anomaly(am, ec)
    return 2.0 * math.atan(math.sqrt((1.0 + ec) / (1.0 - ec)) * math.tan(ae * 0.5))


def sun_long(gdate):
    """Return sun longitude in degrees for given Greenwich datetime (UTC)."""

    t = (cd_to_jd(gdate) - 2415020.0) / 36525.0
    t2 = t * t

    l = 279.69668 + 0.0003025 * t2 + 360.0 * _fract(100.0021359 * t)
    m1 = 358.47583 - (0.00015 + 0.0000033 * t) * t2 + 360.0 * _fract(99.99736042 * t)
    ec = 0.01675104 - 0.0000418 * t - 0.000000126 * t2

    # sun anomaly
    at = true_anomaly(math.radians(m1), ec)

    a1 = math.radians(153.23 + 360.0 * _fract(62.55209472 * t))
    b1 = math.radians(216.57 + 360.0 * _fract(125.1041894 * t))
    c1 = math.radians(312.69 + 360.0 * _fract(91.56766028 * t))
    d1 = math.radians(350.74 - 0.00144 * t2 + 360.0 * _fract(1236.853095 * t))
    e1 = math.radians(231.19 + 20.2 * t)
    h1 = math.radians(353.4 + 360.0 * _fract(183.1353208 * t))

    d2 = (0.00134 * math.cos(a1) + 0.00154 * math.cos(b1) + 0.002 * math.cos(c1) +
          0.00179 * math.sin(d1) + 0.00178 * math.sin(e1))

    sr = (at + math.radians(l - m1 + d2)) % (2 * math.pi)
    return math.degrees(sr)

    # alternative version for sun_dist:
    # ae = eccentric_anomaly(math.radians(m1), ec)
    # d3 = (0.00000543 * math.sin(a1) + 0.00001575 * math.sin(b1) +
    #      0.00001627 * math.sin(c1) + 0.00003076 * math.cos(d1) +
    #      0.00000927 * math.sin(h1))
    # return 1.0000002 * (1.0 - ec * math.cos(ae)) + d3


def nutat_long(gdate):
    t = (cd_to_jd(gdate) - 2415020.0) / 36525.0
    t2 = t * t
    l2 = 2.0 * math.radians(279.6967 + 0.000303 * t2 + 360.0 * _fract(100.0021358 * t))
    d2 = 2.0 * math.radians(270.4342 - 0.001133 * t2 + 360.0 * _fract(1336.855231 * t))
    m1 = math.radians(358.4758 - 0.00015 * t2 + 360.0 * _fract(99.99736056 * t))
    m2 = math.radians(296.1046 + 0.009192 * t2 + 360.0 * _fract(1325.552359 * t))
    n1 = math.radians(259.1833 + 0.002078 * t2 - 360.0 * _fract(5.372616667 * t))

    dp = ((-17.2327 - 0.01737 * t) * math.sin(n1) +
          (-1.2729 - 0.00013 * t) * math.sin(l2) + 0.2088 * math.sin(2 * n1) -
          0.2037 * math.sin(d2) + (0.1261 - 0.00031 * t) * math.sin(m1) +
          0.0675 * math.sin(m2) - (0.0497 - 0.00012 * t) * math.sin(l2 + m1) -
          0.0342 * math.sin(d2 - n1) - 0.0261 * math.sin(d2 + m2) +
          0.0214 * math.sin(l2 - m1) - 0.0149 * math.sin(l2 - d2 + m2) +
          0.0124 * math.sin(l2 - n1) + 0.0114 * math.sin(d2 - m2))

    return dp / 3600.0


def nutat_obl(gdate):
    t = (cd_to_jd(gdate) - 2415020.0) / 36525.0
    t2 = t * t
    l2 = 2.0 * math.radians(279.6967 + 0.000303 * t2 + 360.0 * _fract(100.0021358 * t))
    d2 = 2.0 * math.radians(270.4342 - 0.001133 * t2 + 360.0 * _fract(1336.855231 * t))
    m1 = math.radians(358.4758 - 0.00015 * t2 + 360.0 * _fract(99.99736056 * t))
    m2 = math.radians(296.1046 + 0.009192 * t2 + 360.0 * _fract(1325.552359 * t))
    n1 = math.radians(259.1833 + 0.002078 * t2 - 360.0 * _fract(5.372616667 * t))

    ddo = ((9.21 + 0.00091 * t) * math.cos(n1) +
           (0.5522 - 0.00029 * t) * math.cos(l2) - 0.0904 * math.cos(2 * n1) +
           0.0884 * math.cos(d2) + 0.0216 * math.cos(l2 + m1) +
           0.0183 * math.cos(d2 - n1) + 0.0113 * math.cos(d2 + m2) -
           0.0093 * math.cos(l2 - m1) - 0.0066 * math.cos(l2 - n1))

    return ddo / 3600.0


def obliq(gdate):
    """Return obliquity of orbit for a given datetime."""
    c = ((cd_to_jd(gdate) - 2415020.0) / 36525.0) - 1.0
    e = (c * (46.815 + c * (0.0006 - (c * 0.00181)))) / 3600.0
    return 23.43929167 - e + nutat_obl(gdate)


def ecl_to_equ(eclon, eclat, gdate):
    """Convert ecliptic coordinates into equatorial for a given date.

    Return value is a tuple of right ascension and declination.
    """
    a = math.radians(eclon)
    b = math.radians(eclat)
    c = math.radians(obliq(gdate))
    d = math.sin(a) * math.cos(c) - math.tan(b) * math.sin(c)
    e = math.cos(a)
    ra = math.degrees(math.atan2(d, e)) % 360.0

    f = math.sin(b) * math.cos(c) + math.cos(b) * math.sin(c) * math.sin(a)
    dec = math.degrees(math.asin(f))
    return (ra, dec)


def ra_to_ha(ra, gdatetime, lon_obs):
    """Convert right ascension to hour angle."""
    return (ut_to_gst(gdatetime) - (ra - lon_obs) / 15.0) % 24.0


def equ_to_hor(ra, dec, gdatetime, lon_obs, lat_obs):
    """Convert right ascension and declination to azimuth and altitude.

    Return value is a tuple of azimuth and altitude.
    """
    dec = math.radians(dec)
    lat_obs = math.radians(lat_obs)
    ha = math.radians(ra_to_ha(ra, gdatetime, lon_obs) * 15.0)
    sinalt = math.sin(dec) * math.sin(lat_obs) + math.cos(dec) * math.cos(lat_obs) * math.cos(ha)
    a = -math.cos(dec) * math.cos(lat_obs) * math.sin(ha)
    b = math.sin(dec) - math.sin(lat_obs) * sinalt
    az = math.degrees(math.atan2(a, b)) % 360.0
    return (az, math.degrees(math.asin(sinalt)))


def ec_dec(eclon, eclat, gdate):
    """Return equatorial declination for given ecliptic coordinates and date."""
    a = math.radians(eclon)
    b = math.radians(eclat)
    c = math.radians(obliq(gdate))
    d = math.sin(b) * math.cos(c) + math.cos(b) * math.sin(c) * math.sin(a)
    return math.degrees(math.asin(d))


def ec_ra(eclon, eclat, gdate):
    """Return equatorial right ascension for given ecliptic coordinates and date."""
    a = math.radians(eclon)
    b = math.radians(eclat)
    c = math.radians(obliq(gdate))
    d = math.sin(a) * math.cos(c) - math.tan(b) * math.sin(c)
    e = math.cos(a)
    return math.degrees(math.atan2(d, e)) % 360.0


def lst_to_gst(lst, lon):
    """Convert LST value for a given longitude to GST.

    Time values are in hours, i.e. in the inverval [0, 24.0).
    """
    return (lst - (lon / 15.0)) % 24.0


def gst_to_ut(gst, gdate):
    """Convert a GST value on a given date to UTC (just the time, no date).

    Time values are in hours, i.e. in the inverval [0, 24.0).
    """
    gdate = start_of_day(gdate)
    c = (cd_to_jd(gdate) - 2451545.0) / 36525.0
    e = (6.697374558 + c * (2400.051336 + c * 0.000025862)) % 24.0
    return ((gst - e) % 24.0) * 0.9972695663


def ut_to_gst(gdatetime):
    """Calculate Greenwich siderial time for a given Greenwich datetime."""
    a = cd_to_jd(gdatetime) - 2451545.0
    d = 18.697374558 + 24.06570982439425 * a + (0.000025862 * a * a) / 1334075625
    return d % 24.0


def cd_to_jst(gdatetime):
    """Calculate number of siderial days since epoch J2000.0"""
    a = cd_to_jd(gdatetime) - 2451545.0
    return (18.697374558 + 24.06570982441908 * a) / 24.0


def jst_to_cd(jst):
    """Return calender date for a given number of siderial days (JST)."""
    a = (jst * 24.0 - 18.697374558) / 24.06570982441908
    return jd_to_cd(a + 2451545.0)


def riseset(ra, dec, vs, lat_obs):
    """Return right ascension offset from noon in degrees.

    Return value is a tuple of a boolean indicating whether the sun really
    reaches the requested angle and the corresponding datetime. If the angle
    is not reached, the datetime is either noon if the sun is always below the
    angle at that day, or midnight if it's always above.

    ra, dec: Equatorial coordinates of the sun in degrees.
    vs: Vertical shift in degrees, angular offset from the horizontal plane,
        positive below the horizon, negative above.
    lat_obs: Latitude of observer.
    """
    dec = math.radians(dec)
    vs = math.radians(vs)
    lat_obs = math.radians(lat_obs)
    f = -(math.sin(vs) + math.sin(dec) * math.sin(lat_obs)) / (math.cos(dec) * math.cos(lat_obs))

    if abs(f) < 1.0:
        return (True, math.degrees(math.acos(f)))
    else:
        # return noon if sun always below angle, or midnight if always above
        return (False, 0.0 if f > 0.0 else 180.0)


def sun_time(gdatetime, lon_obs, lat_obs, rising=True, angle=0.83333333):
    """Return UTC time of sun being at given angle below horizon.

    Return value is a tuple of a boolean indicating whether the sun really
    reaches the requested angle and the corresponding datetime. If the angle
    is not reached, the datetime is either noon if the sun is always below the
    angle at that day, or midnight if it's always above.

    gdatetime: date and time of local noon on desired day in UTC.
    lon_obs, lat_obs: Coordinates of observer.
    rising: True before noon (sunrise, morning twilight), False after noon.
    angle: Vertical angle, positive below horizon, negative above.

    Siderial times below are in the [0, 1] range instead of [0, 24].
    """
    jst = cd_to_jst(gdatetime)
    sign = -1 if rising else 1
    # solved by approximation, two iterations should be good enough
    for _ in xrange(2):
        eclon = sun_long(gdatetime) + nutat_long(gdatetime) - 0.005694
        ra, dec = ecl_to_equ(eclon, 0, gdatetime)
        # angle between noon and requested position:
        valid, delta_ra = riseset(ra, dec, angle, lat_obs)

        lst = _fract(jst)
        transit_st = _fract((ra - lon_obs) / 360.0)
        delta = 0.0
        if abs(lst - transit_st) > 1.0 / 24.0:
            # times lie on different sides of a siderial day boundary
            if transit_st > lst:
                # suppose transit_st is in the previous siderial day
                delta = -1.0
            else:
                # transit_st is in the following siderial day
                delta = 1.0
        # math.floor(jst) + delta + transit_st is the siderial time of solar noon
        gdatetime = jst_to_cd(math.floor(jst) + delta + transit_st + sign * delta_ra / 360.0)

    return (valid, gdatetime)


def local_noon(gdatetime, lon_obs):
    """Return UTC time of local noon for given date and time (also UTC)."""
    dtlocal = dtm.timedelta(hours=lon_obs / 15.0)
    gdatetime = start_of_day(gdatetime + dtlocal) + dtm.timedelta(hours=12)
    gdatetime -= dtlocal
    return gdatetime


def sun_calc(lon_obs, lat_obs):
    """Return a function that calls 'sun_time' with hard-coded coordinates.

    The resulting function expects as parameters a date and a dictionary with
    a boolean ('rising') and an angle ('angle').
    """
    return (lambda day, interval: sun_time(local_noon(day, lon_obs),
                                           lon_obs, lat_obs, interval['rising'],
                                           interval['angle'] if 'angle' in interval else 0.833333333))


def sun_az_alt(gdatetime, lon_obs, lat_obs):
    """Return azimuth and altitude of the sun."""
    eclon = sun_long(gdatetime) + nutat_long(gdatetime) - 0.005694
    ra, dec = ecl_to_equ(eclon, 0, gdatetime)
    return equ_to_hor(ra, dec, gdatetime, lon_obs, lat_obs)


if __name__ == '__main__':
    from datetime import datetime
    # tutti i tempi in UTC
    lon = 12.41
    lat = 41.9
    now = datetime.utcnow()
    az, alt = sun_az_alt(now, lon, lat)
    print "azimuth %f, elevation %f" % (az, alt)

    # crepuscolo 0.83333, crepuscolo civile 6, crepuscolo nautico 12, crepuscolo astronomico 18
    crepuscolo = 6
    a, tx = sun_time(now, lon, lat, rising=True, angle=crepuscolo)
    print tx.__str__()
    a, tx = sun_time(now, lon, lat, rising=False, angle=crepuscolo)
    print tx.__str__()



