from setuptools import setup, find_packages

setup(
    name="atlasexplorer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "cryptography>=45.0.3",
        "inquirerpy>=0.3.4",
        "pycryptodome>=3.23.0",
        "pyelftools>=0.32",
        "requests>=2.32.4",
        "python-dotenv",
    ],
)
