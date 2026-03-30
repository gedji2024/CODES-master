from setuptools import setup
import re
import os

def find_version(*file_paths):
    with open(os.path.join(os.path.dirname(__file__), *file_paths), 'r') as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    name="gym_examples",
    version=find_version("gym_examples", "__init__.py"),
    author="Georges Djimefo",
    author_email="djimefo@gmail.com",
    description="WSN routing environment with Monotonic Attention-based reward scalarization.",
    url="https://github.com/gedji/CODES.git",
    install_requires=[
        "numpy",
        "gym==0.21.0",
        "scipy",
        "msgpack_numpy",
        "tqdm",
        "msgpack",
        "torch",
    ],
)