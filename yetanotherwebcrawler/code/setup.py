#!/usr/bin/env python

from distutils.core import setup

setup(name='YetAnotherWebCrawler',
      description='Yet another very simple webcrawler.',
      long_description='Yet another very simple webcrawler that goes where no crawler has gone before.',
      author='Serrano M.',
      author_email='serrano.miser[at]@gmail.com',
      version='0.1',
      license='GPLv3',
      scripts=['yetanotherwebcrawler.py'],
      requires=[
          'requests',
          'lxml',
          ],
      )
