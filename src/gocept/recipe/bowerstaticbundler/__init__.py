import importlib
import json
import os
import pkg_resources
import sys
import zc.buildout.easy_install
import md5
import rcssmin
import rjsmin

BUNDLE_DIR_NAME = 'bowerstatic_bundle'
BOWER_JSON = {
    "name": BUNDLE_DIR_NAME,
    "version": "0.1",
}
MINIFIERS = {
    '.js': rjsmin.jsmin,
    '.css': rcssmin.cssmin,
}


class Recipe(object):

    def __init__(self, buildout, name, options):
        self.name, self.options = name, options
        self.modules = self.options.get('modules', '').splitlines()
        self.eggs = self.options.get('eggs', '').splitlines()
        self.bower = self.options['bower']
        self.eggs_directory = buildout['buildout']['eggs-directory']
        links = buildout['buildout'].get('find-links', ())
        self.target_dir = os.path.join(options['target_dir'], BUNDLE_DIR_NAME)
        if links:
            links = links.split()
        self.links = links
        self.index = buildout['buildout'].get('index')
        self.newest = buildout['buildout'].get('newest') == 'true'
        self.executable = buildout['buildout']['executable']
        self.develop_eggs_directory = (
            buildout['buildout']['develop-eggs-directory'])
        environment_name = self.options.get('environment')
        self.environment = {}
        if environment_name is not None:
            self.environment = buildout[environment_name]

    def write_bower_json(self, dict):
        with open(os.path.join(self.target_dir, '.bower.json'), 'w') as bjson:
            bjson.write(json.dumps(dict))

    def install(self):
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)
        # Write an "empty" .bower.json file as bowerstatic expects that
        self.write_bower_json(BOWER_JSON)
        self.update()
        return self.target_dir

    def update(self):
        # Setup paths end environment
        for key, value in self.environment.items():
            os.environ[key] = value
        ws = zc.buildout.easy_install.install(
            self.eggs, self.eggs_directory,
            links=self.links,
            index=self.index,
            executable=self.executable,
            path=[self.develop_eggs_directory],
            newest=self.newest)
        sys.path[0:0] = ws.entries
        for entry in ws.entries:
            pkg_resources.working_set.add_entry(entry)
        # Import bowerstatic to calculate resources and their dependencies
        for package in self.modules:
            importlib.import_module(package)
        bower_module, bower_attr = self.bower.split(':')
        bower = getattr(importlib.import_module(bower_module), bower_attr)
        environ = {}
        for bower_components_name, collection in (
                bower._component_collections.items()):
            if collection.fallback_collection is None:
                # This is not a local collection
                # XXX What if no local collection is found?!
                continue
            includer = collection.includer(environ)
            for component_name, component in collection._components.items():
                includer(component_name)
        inclusions = environ['bowerstatic.inclusions']
        topological_sort = importlib.import_module(
            'bowerstatic.toposort').topological_sort
        inclusions = topological_sort(
            inclusions._inclusions,
            lambda inclusion: inclusion.dependencies())
        paths_by_type = {}
        bundle_names = []
        for inclusion in inclusions:
            resource = inclusion.resource
            component = resource.component
            collection = component.component_collection

            ext = resource.ext
            paths_by_type.setdefault(ext, []).append(
                bower.get_filename(collection.name, component.name,
                                   component.version, resource.file_path))
        # Get file contents, minify it and bundle all together
        m = md5.new()
        for type_, paths in paths_by_type.items():
            bundle_name = 'bundle%s' % type_
            with open(os.path.join(
                    self.target_dir, bundle_name), 'w') as bundle:
                for path in paths:
                    with open(path) as file_:
                        content = file_.read()
                        if type_ in MINIFIERS:
                            content = MINIFIERS[type_](content)
                        m.update(content)
                        bundle.write(content)
                        bundle.write('\n')
            bundle_names.append(bundle_name)
        # Write .bower.json file
        version = m.hexdigest()
        bjson = BOWER_JSON.copy()
        bjson['main'] = bundle_names
        bjson['version'] = version
        self.write_bower_json(bjson)
