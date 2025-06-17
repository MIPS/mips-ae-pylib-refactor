import pytest
import atlasexplorer
import sys
import locale

def test_exp():
    # example use of AtlasExplorer library,
    # this assumes that user has ran the script with the "configure" arg
    # Create an instance of the class
    myinst = atlasexplorer.AtlasExplorer(verbose=True)

    # set your root target experiment folder(where the reports will land)
    myinst.setRootExperimentDirectory("myexperiments")

    # run an experiment with your elf / core selelection
    # returns exp sub dir name
    experiment = myinst.createExperiment("mandelbrot_rv64_O3.elf", "I8500")
    assert experiment.getRoot() is not None, "Error creating experiment! Check your setup"


