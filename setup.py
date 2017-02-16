"""
pyCasual
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="pycasual",
    version="0.0.3",
    url="http://github.com/izacht13/pyCasual/",
    license="MIT",
    author="Isaac Torbett",
    author_email="izacht13@gmail.com",
    description="An interpreter for Casual Markup Language.",
    py_modules=["pycasual"],
    scripts=["pycasual.py"],
    keywords=["web html markup"],
    platforms="any",
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Intended Audience :: Developers",
        'Topic :: Software Development',
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
		"Programming Language :: Python :: 3.6"
    ]
)