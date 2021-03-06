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
        self._target_dir = options['target_dir']
        self._current_component_name = ''
        links = buildout['buildout'].get('find-links', ())
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

    @property
    def target_dir(self):
        return os.path.join(self._target_dir, self._current_component_name)

    def write_bower_json(self, dict):
        with open(os.path.join(self.target_dir, '.bower.json'), 'w') as bjson:
            bjson.write(json.dumps(dict, indent=2, separators=(',', ': ')))

    def assure_target_dir(self):
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

    def install(self):
        self.update()

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
        for bower_components_name, collection in (
                bower._component_collections.items()):
            if collection.fallback_collection is None:
                # This is not a local collection
                # XXX What if no local collection is found?!
                continue
            for component_name, component in collection._components.items():
                # Build a bundle for each local component_name
                self._current_component_name = (
                    BUNDLE_DIR_NAME + '_' + component_name.replace('.', '_'))
                self.assure_target_dir()
                environ = {}
                includer = collection.includer(environ)
                includer(component_name)

                resources_by_type = self.get_resources_by_type(bower, environ)
                resources = self.copy_resources_by_type(resources_by_type)
                version, bundles = self.create_bundles_by_type(
                    resources_by_type)

                # Write .bower.json file
                self.write_bower_json({
                    'name': self._current_component_name,
                    'main': resources + bundles,
                    'version': version})

    def get_resources_by_type(self, bower, environ):
        """Return file paths to assets separated by type, i.e. CSS, JS etc.

        Example structure of the returned dict:

        {'.js': [
            {'package': jquery', 'path': /path/to/jquery.js'},
            {'package': gocept.jsform', 'path': /path/to/jsform.js'}
        ]}

        """
        inclusions = environ.get('bowerstatic.inclusions')
        if inclusions is None:
            return {}

        import bowerstatic.toposort
        inclusions = bowerstatic.toposort.topological_sort(
            inclusions._inclusions,
            lambda inclusion: inclusion.dependencies())

        resources_by_type = {}
        for inclusion in inclusions:
            resource = inclusion.resource
            component = resource.component
            collection = component.component_collection

            ext = resource.ext
            path = bower.get_filename(
                collection.name, component.name,
                component.version, resource.file_path)
            resources_by_type.setdefault(ext, []).append({
                'package': component.name,
                'path': path
            })
        return resources_by_type

    def create_bundles_by_type(self, resources_by_type):
        """Get file content, minify it and bundle by type, i.e. JS, CSS etc.

        Will calculate a version number by generating the hash for the combined
        content of all bundles.

        Will only bundle files whose extension is present in BUNDLE_EXTENSIONS.

        """
        m = md5.new()
        bundle_names = []
        for ext, resources in resources_by_type.items():
            if ext not in BUNDLE_EXTENSIONS:
                continue
            bundle_name = 'bundle%s' % ext
            with open(os.path.join(
                    self.target_dir, bundle_name), 'w') as bundle:
                for resource in resources:
                    with open(resource['path']) as file_:
                        content = file_.read()
                        if ext == '.css':
                            content = self.copy_linked_resources(
                                content, resource['path'])
                        if ext in MINIFIERS:
                            content = MINIFIERS[ext](content)
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
            target = os.path.join(
                self.target_dir, os.path.basename(filename)).encode('utf-8')
            if os.path.lexists(target):
                os.unlink(target)
            os.symlink(os.path.join(os.path.dirname(path), filename), target)
            content = content.replace(filename, os.path.basename(target), 1)
        return content

    def copy_resources_by_type(self, resources_by_type):
        """Copy static resources like images or templates into the bundle dir.

        Will only copy resources whose extension is in RESOURCE_EXTENSIONS.

        XXX: Name clashes are ignored, the last file wins right now.

        """
        copied_resources = []
        for ext, resources in resources_by_type.items():
            if ext not in RESOURCE_EXTENSIONS:
                continue
            for resource in resources:
                # create namespace directory for package
                target_dir = os.path.join(self.target_dir, resource['package'])
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                # copy file into namespace directory inside the bundle dir
                filename = os.path.basename(resource['path'])
                destination = os.path.join(target_dir, filename)
                shutil.copyfile(resource['path'], destination)

                # add relative file path to copied resources
                copied_resources.append(os.path.join(
                    resource['package'], filename))

        return copied_resources

    def _sanitize_filename(self, filename):
        if filename.startswith('"') or filename.startswith("'"):
            filename = filename[1:-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        if '#' in filename:
            filename = filename.split('#')[0]
        return filename
