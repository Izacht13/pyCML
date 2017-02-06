from setuptools import setup, find_packages

setup(
    name='pycasual',
    version="0.0.1",
    url='http://github.com/izacht13/pyCasual/',
    license='MIT',
    author='Isaac Torbett',
    author_email='izacht13@gmail.com',
    description='An interpreter for Casual Markup Language.',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    keywords=['web html markup'],
    platforms='linux',
    install_requires=[],
    entry_points={},
    classifiers=[
        'Development Status :: 1 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: 3.6'
    ]
)