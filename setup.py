"""
Setup script for FractalChain.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="fractalchain",
    version="1.0.0",
    author="FractalChain Team",
    description="A cryptocurrency powered by fractal mathematics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fractalchain/fractalchain",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "fractalchain=main:main",
            "fractalchain-cli=api.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
