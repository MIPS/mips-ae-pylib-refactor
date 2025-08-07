from atlasexplorer.atlasexplorer import AtlasExplorer, Experiment
import locale


def test_singlecore():
    locale.setlocale(locale.LC_ALL, "")
    # example use of AtlasExplorer library,
    # this assumes that user has ran the script with the "configure" arg
    # Create an instance of the class using MIPS_ATLAS_CONFIG env variable
    import os
    config_str = os.environ.get("MIPS_ATLAS_CONFIG", "")
    try:
        apikey, channel, region = config_str.split(":")
    except ValueError:
        raise RuntimeError("MIPS_ATLAS_CONFIG environment variable must be set as 'apikey:channel:region'")
    aeinst = AtlasExplorer(
        apikey,
        channel,
        region,
        verbose=True,
    )
    # create a new experiment in 'myexperiments' directory
    experiment = Experiment("myexperiments", aeinst, verbose=True)
    # add a workload to the experiment
    experiment.addWorkload("resources/mandelbrot_rv64_O0.elf")
    # experiment.addWorkload("resources/memcpy_rv64.elf")
    # set the core type for the experiment
    experiment.setCore("I8500_(1_thread)")
    # run an experiment
    experiment.run()
    
    total_cycles = experiment.getSummary().getTotalCycles()
    assert total_cycles == 253629, "Total Cycles should be 253629"
