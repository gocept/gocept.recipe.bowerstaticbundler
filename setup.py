import os
from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name='gocept.recipe.bowerstaticbundler',
    version='0.1.0.dev0',
    url='https://vcs.verdi4you.de/gocept.recipe.bowerstaticbundler',
    license='GPL',
    description='XXX',
    author='union.cms developers',
    author_email='dev@unioncms.org',
    long_description=(read('README.rst')
                      + '\n\n' +
                      'Detailed Documentation\n'
                      '**********************'
                      + '\n\n' +
                      read('CHANGES.rst')
                      ),
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Zope2',
        'Framework :: Zope3',
        'License :: OSI Approved :: Gnu public license',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='union.cms zope zope2 zope3',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['gocept'],
    include_package_data=True,
    install_requires=[
        'setuptools',
    ],
    zip_safe=False,
)
