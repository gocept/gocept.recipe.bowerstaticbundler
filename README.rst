================================
gocept.recipe.bowerstaticbundler
================================

Bundling and minifying components included via bowerstatic_.

This recipe imports you bowerstatic components, which you must specify in the
recipes config (see below for details). It then retrieves your local components,
calculates the import order and minifies and bundles JS and CSS files. The
bundles are saved to your ``bower_components`` folder (or whatever folder you
specified) as a new component called ``bowerstatic_bundle``.

In your application you can then switch between bundled or non-bundled versions
with an include helper function::

    def bower_include(environ, name):
        if not os.environ.get('BOWERSTATIC_DEBUG'):
            name = 'bowerstatic_bundle'
        include = components.includer(environ)
        include(name)

In your view, where you normally get the includer and include your libraries,
you now call::

    bower_include(self.request.environ, '<you_library_name>')

This package uses rcssmin_ and rjsmin_ to minify CSS and JS files.


Configuration
=============

Here is an example configuration for ``bowerstaticbundler``::

    [buildout]
    parts += bundle

    [bundle]
    recipe = gocept.recipe.bowerstaticbundler
    eggs = mypackage
           myotherpackage
    modules = mypackage.browser.resource
              myotherpackage.browser.resource
    bower = mypackage.bower
    target_dir = ${config:bower_components}
    environment = bundle-config

    [bundle-config]
    BOWER_COMPONENTS_DIR = ${config:bower_components}

You need to specify the location of your local components via the ``eggs`` and
``modules`` options. Eggs is needed to import your modules, where the components
live, while modules specify the path to import them directly. This is needed as
bower calculates the components and resources during import time, so we need to
trigger them in the build step.

You also must provide the location of you bower singleton via the ``bower``
option.

``target_dir`` specifies the directory, where the bundled component will be
placed. It is recommended to point this to your `bower_components` folder, where
your bower packages live, as bowerstatic_ will have to import the bundles as
well in order to be able to include them into your Application.

With the ``environment`` option you can specify environment variables. In the
example above we specify one environment variable called
``BOWER_COMPONENTS_DIR``, which is the variable bower is looking for in the
environment to get the installed bower packages. This might be different in your
setup.

.. _bowerstatic: http://bowerstatic.readthedocs.org/
.. _rcssmin: http://opensource.perlig.de/rcssmin/
.. _rjsmin: http://opensource.perlig.de/rjsmin/
