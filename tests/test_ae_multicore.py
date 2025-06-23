import atlasexplorer
import locale


def test_multicore():
    locale.setlocale(locale.LC_ALL, "")
    # example use of AtlasExplorer library,
    # this assumes that user has ran the script with the "configure" arg
    # Create an instance of the class
    aeinst = atlasexplorer.AtlasExplorer(verbose=True)
    # create a new experiment
    experiment = atlasexplorer.Experiment("myexperiments", aeinst, verbose=True)
    # add a workload to the experiment
    experiment.addWorkload("resources/mandelbrot_rv64_O0.elf")
    experiment.addWorkload("resources/memcpy_rv64.elf")
    # set the core type for the experiment
    experiment.setCore("shogun_2t")
    # run an experiment
    experiment.run()

    total_cycles = experiment.getSummary().getTotalCycles()
    assert total_cycles == 256757, "Total Cycles should be 256757"
