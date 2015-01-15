# -*- coding: utf-8 -*-
import sys, getopt
from cmd import Cmd
import socket


motordriveraddress, motordriverport = "localhost", 9999


def sendcmd(data):
    # Create a socket (SOCK_STREAM means a TCP socket)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Connect to server and send data
        sock.connect((motordriveraddress, motordriverport))
        sock.sendall(data + "\n")
        # Receive data from the server and shut down
        sys.stdout.write('Response [')
        while True:
            data = sock.recv(1)
            if not data:
                break
            sys.stdout.write(data)
            sys.stdout.flush()
        sys.stdout.write("]\n")
    except:
        print "Error communicating with motors"

    finally:
        sock.close()


class CommandInterpreter(Cmd):
    def __init__(self):
        Cmd.__init__(self)
        self.prompt = "tracker> "
        self.intro = "Solar tracker controller command interface. Type help for usage"

    def emptyline(self):
        pass

    @staticmethod
    def do_send(cmd):
        """send command to tracker"""
        print "sending to tracker [%s]" % cmd
        sendcmd(cmd)

    @staticmethod
    def do_quit(cmd):
        """quit the program"""
        return True

    @staticmethod
    def do_q(cmd):
        """quit the program"""
        return True


def usage():
    print "Usage : %s [-c, --command=<command>] [--motor-driver-address=<address[:port]>]" % (sys.argv[0])
    sys.exit(1)


if __name__ == "__main__":

    linecommand = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:", ["help", "command=", "motor-driver-address="])
    except getopt.GetoptError:
        print "Error parsing argument:", sys.exc_info()[1]
        # print help information and exit:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(2)

        if o in ("-c", "--command"):
            linecommand = a

        if o == "--motor-driver-address":
            print a
            ap = a.split(":")
            if len(ap) == 1:
                motordriveraddress = ap[0]
            elif len(ap) == 2:
                motordriveraddress, motordriverport = ap
                motordriverport = int(motordriverport)
            else:
                usage()

    print ("Using server at %s:%d" % (motordriveraddress, motordriverport))
    cmdi = CommandInterpreter()
    if not linecommand:
        cmdi.cmdloop()
    else:
        cmdi.onecmd(linecommand)
