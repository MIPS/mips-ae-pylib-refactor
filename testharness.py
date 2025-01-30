import atlasexplorer
import tarfile
import os

# example use of AtlasExplorer library,
# this assumes that user has ran the script with the "configure" arg
# Create an instance of the class
myinst = atlasexplorer.AtlasExplorer()

# set your root target experiment folder(where the reports will land)
myinst.setRootExperimentDirectory("./myexperiments")

# run an experiment with "reports" against your elf / core selelection
# retturns exp sub dir name
expdir = myinst.createExperiment("mandelbrot_O0.elf", "shogun")
print("exp dir: " + expdir)
# todo:  parse result reports

print("unpacking summary report")
reporttar = os.path.join("myexperiments", expdir, "summary", "report_results.tar.gz")

destdir = os.path.join("myexperiments", expdir, "summary")
with tarfile.open(reporttar, "r:gz") as tar:
    tar.extractall(destdir)
    tar.close()
