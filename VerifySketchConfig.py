#!/usr/bin/env python
#
# A script to verify all example sketches using the Arduino
# command line --verify option.
#
# Also has support for the W&L sketch reconfiguration system.
# This allows us to have multiple ways to run a sketch, like with
# a Bricktronics Shield, Bricktronics Megashield, and a breakout board.
#
# Conceptually, there are multiple config sets numbered 1 - N. Each config set
# can be one or more blocks within the code. Each config block looks like:
# // Config 1 - arduino:avr:uno
# // Code that is commented-out
# // More lines of commented-out code
# // Config end
# (Ignore the leading "# " on the four lines above.)
# This script will parse the sketch file and determine how many config sets
# are present in the file. Then it will iterate through each config set,
# make modifications to the file (remove leading spaces and "// " on lines in
# the current config set's block(s) ), and then verify with Arduino.
# Text after the hyphen is interpreted as arguments to Arduino's --board param:
# https://github.com/arduino/Arduino/blob/ide-1.5.x/build/shared/manpage.adoc
#
# If there are no configs detected, it will just use the file as-is with Uno.
#
# We read in the specified ino file, make modification, and write it back out,
# to the same file. This avoid issues with relative paths and stuff like that.
#
# Usage: VerifySketchConfig.py
# Iterates through ./examples/* to build them all, so call it from your
# Arduino library's top-level directory. It looks in ./examples/*
#
# Written by Matthew Beckler and Adam Wolf, for Wayne and Layne, LLC.
# Released under terms of the GPL version 2.
# Contact us if you want to discuss alternate licenses.
# http://wayneandlayne.com/

import sys
import os
import subprocess
import re

# Update this variable to point to your Arduino binary
ARDUINO = "/home/matthew/bin/arduino"

def RunAllConfigs( ino ):

    RE_CONFIG = "^// Config (\d+) - (.*)$"

    print "*" * 80
    print "Reading file '%s'" % ino

    def EnableConfigSet( original, ii ):
        InsideDesiredConfigBlock = False
        modified = []
        board = ""

        for line in original:
            if InsideDesiredConfigBlock:
                if line.strip() == "// Config end":
                    InsideDesiredConfigBlock = False
                    modified.append(line)
                else:
                    # remove leading //
                    modified.append(line.strip().strip("//") + "\n")
            else:
                # If we are not in an active config block, always use line unchanged
                modified.append(line)
                # check if we are starting a new config block
                x = re.search(RE_CONFIG, line.strip())
                if x:
                    config_set = int(x.group(1))
                    if config_set == ii:
                        # This is the config set we want, enable it
                        InsideDesiredConfigBlock = True
                        board = x.group(2)

        return modified, board

    def VerifyWithArduino(board, ino):
        args = [ARDUINO, "--verify", "--board", board, ino]
        print " ".join(args)
        retcode = subprocess.call(args)
        if retcode != 0:
            print "Error while running Arduino, exiting"
            sys.exit(1)


    # Read in original sketch file
    with open(ino, "r") as fid:
        original = fid.readlines()

    num_config_sets = 0
    for line in original:
        x = re.search(RE_CONFIG, line.strip())
        if x:
            config_set = int(x.group(1))
            #print "%d, '%s'" % (config_set, line.strip())
            num_config_sets = max(num_config_sets, config_set)
    print "Found %d config sets" % num_config_sets

    if num_config_sets == 0:
        # No config sets detected, use file as-is with Arduino Uno
        # TODO add support for a "Config default: arduino:avr:uno" line
        #   that would let us specify on a per-file basis how to run it.
        x = "===== Processing file as-is for arduino:avr:uno "
        x += "=" * (80 - len(x))
        print x
        VerifyWithArduino("arduino:avr:uno", ino)
    else:
        # We really, really don't want to mess up the original file on disc
        try:
            for ii in range(1, num_config_sets + 1):
                x = "===== Processing config set %d " % ii
                x += "=" * (80 - len(x))
                print x
                modified, board = EnableConfigSet( original, ii )
                with open(ino, "w") as fid:
                    fid.write("".join(modified))
                VerifyWithArduino(board, ino)
        finally:
            # restore the original file
            print "Restoring original sketch file"
            with open(ino, "w") as fid:
                fid.write("".join(original))


# TODO make this only iterate over files in examples/*/ that end in .ino
for subdir, dirs, files in os.walk("examples"):
    for f in files:
        RunAllConfigs( os.path.join(subdir, f) )

# Return good status if we don't exit(1) early
sys.exit(0)

