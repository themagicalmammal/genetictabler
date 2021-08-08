import codecs
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = "1.0.3"
DESCRIPTION = "Time Table scheduling using Genetic Algorithm."
LONG_DESCRIPTION = "Time Table scheduling using Genetic Algorithm which is tailored to work such that resource utilization is reduced in accordance with the genes that are being generated."

# Setting up
setup(
    name="genetictabler",
    version=VERSION,
    author="Dipan Nanda and Ashish Shah",
    author_email="d19cyber@gmail.com",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=[],
    keywords=[
        "python",
        "geneticalgorithm",
        "genetics",
        "genes",
        "chromosomes",
        "timetable",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
