from atlasexplorer import atlasexplorer
import locale
import os


def test_multicore():
    locale.setlocale(locale.LC_ALL, "")
    # example use of AtlasExplorer library,
    # this assumes that user has ran the script with the "configure" arg
    # Create an instance of the class
    aeinst = atlasexplorer.AtlasExplorer(
        "de627017-532c-4cef-adff-5c9c444440df",
        "I8500_(2_threads)",
        "us-west-2",
        verbose=True,
    )
    # create a new experiment
    experiment = atlasexplorer.Experiment("myexperiments", aeinst, verbose=True)
    # add workloads to the experiment using absolute paths
    mandelbrot_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "resources", "mandelbrot_rv64_O0.elf"
        )
    )
    memcpy_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "resources", "memcpy_rv64.elf")
    )
    experiment.addWorkload(mandelbrot_path)
    experiment.addWorkload(memcpy_path)
    # set the core type for the experiment
    experiment.setCore("I8500_(2_threads)")
    # run an experiment
    experiment.run()

    total_cycles = experiment.getSummary().getTotalCycles()
    print(f"Total Cycles: {total_cycles}")
    assert total_cycles == 257577, "Total Cycles should be 257577"
