=======
CHANGES
=======

1.2.1 (unreleased)
==================

- Also copy images into the bundle dir, which will be rendered as the fav icon.


1.2.0 (2015-01-13)
==================

- Copy all template files into the bundle dir, rather building one huge
  bundle.pt template


1.1.1 (2015-01-12)
==================

- Prevent error on update if `bowerstatic_bundle` directory is missing.


1.1 (2015-01-12)
================

- Symlink additional resources references in CSS files (images, fonts, …) into
  the bundle and point minified CSS to these symlinks.


1.0.2 (2015-01-08)
==================

- Fixed handling of the ``pkg_resources`` working set when collecting
  resources from eggs.

- Make sure recipe does not brake when there are no resources to bundle.


1.0.1 (2014-09-20)
==================

- Repair homepage url in setup.py.


1.0.0 (2014-09-20)
==================

- Initial release.
