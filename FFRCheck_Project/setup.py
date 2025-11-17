from setuptools import setup, find_packages

setup(
    name="ffrcheck",
    version="1.0.0",
    description="FFR Check - Enhanced version with ITF parsing integration and memory optimization",
    author="nabdghan",
    packages=find_packages(),
    install_requires=[
        "lxml>=4.9.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "ffrcheck=src.main:main",
        ],
    },
)
