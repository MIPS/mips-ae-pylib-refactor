import atlasexplorer

  
# # end class def
# Create an instance of the class
myinst = atlasexplorer.AtlasExplorer("de627017-532c-4cef-adff-5c9c444440df")


myinst.setRootExperimentDirectory("./myexperiments")

myinst.setGWbyChannelRegion()

myinst.createExperiment('mandelbrot_O0.elf', "shogun")