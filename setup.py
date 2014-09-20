import os
from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name='gocept.recipe.bowerstaticbundler',
    version='0.1.0.dev0',
    url='https://vcs.verdi4you.de/gocept.recipe.bowerstaticbundler',
    license='GPL',
    description='Minifies and bundles JS and CSS files included with '
                'bowerstatic.',
    author='gocept gmbh & co. kg',
    author_email='mail@gocept.org',
    long_description=(read('README.rst')
                      + '\n\n' +
                      read('CHANGES.rst')
                      ),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Framework :: Buildout',
        'Framework :: Buildout :: Recipe',
        'Intended Audience :: Developers',
        'License :: OSI Approved',
        'License :: OSI Approved :: Zope Public License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Build Tools',
    ],
    keywords='bower bowerstatic minify bundle css js javascript buildout '
             'recipe',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['gocept', 'gocept.recipe'],
    include_package_data=True,
    install_requires=[
        'setuptools',
        'zc.buildout',
        'rcssmin',
        'rjsmin',
    ],
    entry_points="""
      [zc.buildout]
      default = gocept.recipe.bowerstaticbundler:Recipe
      """,
    zip_safe=False,
)
