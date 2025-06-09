import atlasexplorer
import sys

# example use of AtlasExplorer library,
# this assumes that user has ran the script with the "configure" arg
# Create an instance of the class
myinst = atlasexplorer.AtlasExplorer()

# set your root target experiment folder(where the reports will land)
myinst.setRootExperimentDirectory("myexperiments")

# run an experiment with your elf / core selelection
# returns exp sub dir name
expdir = myinst.createExperiment("mandelbrot_rv64_O3.elf", "I8500")
if expdir is None:
    print("error creating experiment! Check your setup")
    sys.exit(1)

print("experiment dir: " + expdir)
