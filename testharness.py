import atlasexplorer
import tarfile
import os
import sys

# example use of AtlasExplorer library,
# this assumes that user has ran the script with the "configure" arg
# Create an instance of the class
myinst = atlasexplorer.AtlasExplorer()

# set your root target experiment folder(where the reports will land)
myinst.setRootExperimentDirectory("./myexperiments")

# run an experiment with "reports" against your elf / core selelection
# retturns exp sub dir name
expdir = myinst.createExperiment("mandelbrot_O0.elf", "shogun")
if expdir is None:
    print("error creating experiment! Check your setup")
    sys.exit(1)

print("experiment dir: " + expdir)
# todo:  parse result reports

reportnames = ["summary", "inst_counts", "inst_trace"]

for report in reportnames:
    print("unpacking report: " + report)
    reporttar = os.path.join("myexperiments", expdir, report, "report_results.tar.gz")
    if os.path.exists(reporttar):
        destdir = os.path.join("myexperiments", expdir, report)
        with tarfile.open(reporttar, "r:gz") as tar:
            tar.extractall(destdir)
            tar.close()
    else:
        print("report does not exist!!, skipped " + report)
