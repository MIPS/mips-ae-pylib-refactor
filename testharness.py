import atlasexplorer
import tarfile
import os
import sys

# example use of AtlasExplorer library,
# this assumes that user has ran the script with the "configure" arg
# Create an instance of the class
myinst = atlasexplorer.AtlasExplorer()
# set your root target experiment folder(where the reports will land)
myinst.setRootExperimentDirectory("myexperiments")
# run an experiment with "reports" against your elf / core selelection
# retturns exp sub dir name
expdir = myinst.createExperiment("mandelbrot_rv64_O0.elf", "I8500", True)
if expdir is None:
    print("error creating experiment! Check your setup")
    sys.exit(1)

print("experiment dir: " + expdir)
