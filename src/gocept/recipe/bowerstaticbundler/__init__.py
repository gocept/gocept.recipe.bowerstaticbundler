import importlib
import json
import md5
import os
import pkg_resources
import rcssmin
import re
import rjsmin
import shutil
import sys
import zc.buildout.easy_install

BUNDLE_DIR_NAME = 'bowerstatic_bundle'
BOWER_JSON = {
    "name": BUNDLE_DIR_NAME,
    "version": "0.1",
}
CSS_URL_REGEXP = re.compile("url\((.*?)\)")
MINIFIERS = {
    '.js': rjsmin.jsmin,
    '.css': rcssmin.cssmin,
}
BUNDLE_EXTENSIONS = ['.js', '.css']
RESOURCE_EXTENSIONS = ['.pt', '.ico', '.gif', '.png', '.jpg']


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

    def assure_target_dir(self):
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

    def install(self):
        self.assure_target_dir()
        # Write an "empty" .bower.json file as bowerstatic expects that
        self.write_bower_json(BOWER_JSON)
        self.update()
        return self.target_dir

    def update(self):
        self.assure_target_dir()
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

        paths_by_type = self.get_paths_by_type(bower, environ)
        resources = self.copy_resources_by_type(paths_by_type)
        version, bundles = self.create_bundles_by_type(paths_by_type)

        # Write .bower.json file
        bjson = BOWER_JSON.copy()
        bjson['main'] = resources + bundles
        bjson['version'] = version
        self.write_bower_json(bjson)

    def get_paths_by_type(self, bower, environ):
        """Return file paths to assets separated by type, i.e. CSS, JS etc."""
        inclusions = environ.get('bowerstatic.inclusions')
        if inclusions is None:
            return {}

        import bowerstatic.toposort
        inclusions = bowerstatic.toposort.topological_sort(
            inclusions._inclusions,
            lambda inclusion: inclusion.dependencies())

        paths_by_type = {}
        for inclusion in inclusions:
            resource = inclusion.resource
            component = resource.component
            collection = component.component_collection

            ext = resource.ext
            paths_by_type.setdefault(ext, []).append(
                bower.get_filename(collection.name, component.name,
                                   component.version, resource.file_path))
        return paths_by_type

    def create_bundles_by_type(self, paths_by_type):
        """Get file content, minify it and bundle by type, i.e. JS, CSS etc.

        Will calculate a version number by generating the hash for the combined
        content of all bundles.

        Will only bundle files whose extension is present in BUNDLE_EXTENSIONS.

        """
        m = md5.new()
        bundle_names = []
        for type_, paths in paths_by_type.items():
            if type_ not in BUNDLE_EXTENSIONS:
                continue
            bundle_name = 'bundle%s' % type_
            with open(os.path.join(
                    self.target_dir, bundle_name), 'w') as bundle:
                for path in paths:
                    with open(path) as file_:
                        content = file_.read()
                        if type_ == '.css':
                            content = self.copy_linked_resources(content, path)
                        if type_ in MINIFIERS:
                            content = MINIFIERS[type_](content)
                        m.update(content)  # to generate version number
                        bundle.write(content)
                        bundle.write('\n')
            bundle_names.append(bundle_name)
        return m.hexdigest(), bundle_names

    def copy_linked_resources(self, content, path):
        """Make sure that resources linked in the contents of CSS files are
           accessable in the bundle.

           XXX: Name clashes are ignored, the last file wins right now.
           """
        additional_files = CSS_URL_REGEXP.findall(content)
        for filename in additional_files:
            filename = self._sanitize_filename(filename)
            target = os.path.join(self.target_dir, os.path.basename(filename))
            if os.path.lexists(target):
                os.unlink(target)
            os.symlink(os.path.join(os.path.dirname(path), filename), target)
            content = content.replace(filename, os.path.basename(target), 1)
        return content

    def copy_resources_by_type(self, paths_by_type):
        """Copy static resources like images or templates into the bundle dir.

        Will only copy resources whose extension is in RESOURCE_EXTENSIONS.

        XXX: Name clashes are ignored, the last file wins right now.

        """
        resources = []
        for type_, paths in paths_by_type.items():
            if type_ not in RESOURCE_EXTENSIONS:
                continue
            for path in paths:
                filename = os.path.basename(path)
                destination = os.path.join(self.target_dir, filename)
                shutil.copyfile(path, destination)
                resources.append(filename)
        return resources

    def _sanitize_filename(self, filename):
        if filename.startswith('"') or filename.startswith("'"):
            filename = filename[1:-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        if '#' in filename:
            filename = filename.split('#')[0]
        return filename
