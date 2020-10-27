from setuptools import setup, find_packages

requirements = [
    'ipyspin>=0.1.2',
    'xarray>=0.16',
    'aiohttp>=3.7',
    'aiohttp-cors>=0.7',
    'pydeck>=0.5',
    'mercantile>=1',
    'pillow>=7'
]

setup(
    author="David Brochart",
    author_email='david.brochart@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    description="An xarray extension for 3D terrain visualization",
    install_requires=requirements,
    license="MIT license",
    long_description="An xarray extension for 3D terrain visualization",
    include_package_data=True,
    keywords='xtrude',
    name='xtrude',
    packages=find_packages(include=['xtrude', 'xtrude.*']),
    setup_requires=[],
    tests_require=[],
    url='https://github.com/davidbrochart/xtrude',
    version='0.1.0',
    zip_safe=False
)
