from setuptools import setup

exec(open('multivac/version.py').read())

setup(name='multivac',
      version=version,
      packages=['multivac'],
      description='Slack RTM Chatops Bot',
      author='Bradley Cicenas',
      author_email='bradley.cicenas@gmail.com',
      url='https://github.com/bcicen/multivac',
      install_requires=['slacksocket>=0.5.1'],
      license='http://opensource.org/licenses/MIT',
      classifiers=(
          'License :: OSI Approved :: MIT License ',
          'Natural Language :: English',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
      ),
      keywords='slack rtm websocket api chatops bot')
