from setuptools import setup

exec(open('multivac/version.py').read())

requirements = [ 'slacksocket>=0.6.0',
                 'Flask>=0.10.1',
                 'Flask-RESTful>=0.3.2',
                 'gevent>=1.1b1',
                 'redis>=2.10.3',
                 'names>=0.3.0',
                 'PyYAML>=3.11',
                 'termcolor>=1.1.0' ]

setup(
    name='multivac-bot',
    version=version,
    packages=['multivac'],
    description='Extensible ChatOps framework with built-in support for Slack',
    author='Bradley Cicenas',
    author_email='bradley@vektor.nyc',
    url='https://github.com/vektorlab/multivac',
    install_requires=requirements,
    package_data={ 'multivac': ['templates/*', 'static/*'] },
    include_package_data=True,
    license='http://opensource.org/licenses/MIT',
    classifiers=(
        'License :: OSI Approved :: MIT License ',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 5 - Production/Stable',
    ),
    keywords='slack rtm websocket api chatops bot',
    entry_points={ 'console_scripts': ['multivac = multivac.cli:main'] }
)
