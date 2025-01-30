import atlasexplorer


# # end class def
# Create an instance of the class
myinst = atlasexplorer.AtlasExplorer()

myinst.setRootExperimentDirectory("./myexperiments")

myinst.setGWbyChannelRegion()

myinst.createExperiment("mandelbrot_O0.elf", "shogun")
