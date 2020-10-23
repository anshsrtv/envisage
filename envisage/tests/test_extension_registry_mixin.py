# (C) Copyright 2007-2020 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in LICENSE.txt and may be redistributed only under
# the conditions described in the aforementioned license. The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#
# Thanks for using Enthought open source!
"""
Base set of tests for extension registry and its subclasses wrapped in a
mixin class.
"""

# Enthought library imports.
from envisage.api import ExtensionPoint
from envisage.api import UnknownExtensionPoint
from traits.api import List


class ExtensionRegistryTestMixin:
    """ Base set of tests for extension registry and its subclasses.

    Note that tests from this mixin has a limited coverage: It must not depend
    on the functionality of ``IExtensionPointRegistry.set_extensions``.

    See ``SettableExtensionRegistryTestMixin`` for the other tests that
    depend on ``IExtensionPointRegistry.set_extensions``.

    Test cases inheriting from this mixin should define a setUp method that
    defines self.registry as an instance of ExtensionPointRegistry.
    """

    def test_empty_registry(self):
        """ empty registry """

        registry = self.registry

        # Make sure there are no extensions.
        extensions = registry.get_extensions("my.ep")
        self.assertEqual(0, len(extensions))

        # Make sure there are no extension points.
        extension_points = registry.get_extension_points()
        self.assertEqual(0, len(extension_points))

    def test_add_extension_point(self):
        """ add extension point """

        registry = self.registry

        # Add an extension *point*.
        registry.add_extension_point(self.create_extension_point("my.ep"))

        # Make sure there's NO extensions.
        extensions = registry.get_extensions("my.ep")
        self.assertEqual(0, len(extensions))

        # Make sure there's one and only one extension point.
        extension_points = registry.get_extension_points()
        self.assertEqual(1, len(extension_points))
        self.assertEqual("my.ep", extension_points[0].id)

    def test_get_extension_point(self):
        """ get extension point """

        registry = self.registry

        # Add an extension *point*.
        registry.add_extension_point(self.create_extension_point("my.ep"))

        # Make sure we can get it.
        extension_point = registry.get_extension_point("my.ep")
        self.assertNotEqual(None, extension_point)
        self.assertEqual("my.ep", extension_point.id)

    def test_remove_empty_extension_point(self):
        """ remove empty_extension point """

        registry = self.registry

        # Add an extension point...
        registry.add_extension_point(self.create_extension_point("my.ep"))

        # ...and remove it!
        registry.remove_extension_point("my.ep")

        # Make sure there are no extension points.
        extension_points = registry.get_extension_points()
        self.assertEqual(0, len(extension_points))

    def test_remove_non_existent_extension_point(self):
        """ remove non existent extension point """

        registry = self.registry

        with self.assertRaises(UnknownExtensionPoint):
            registry.remove_extension_point("my.ep")

    def test_remove_non_existent_listener(self):
        """ remove non existent listener """

        registry = self.registry

        def listener(registry, extension_point, added, removed, index):
            """ Called when an extension point has changed. """

            self.listener_called = (registry, extension_point, added, removed)

        with self.assertRaises(ValueError):
            registry.remove_extension_point_listener(listener)

    def create_extension_point(self, id, trait_type=List, desc=""):
        """ Create an extension point. """

        return ExtensionPoint(id=id, trait_type=trait_type, desc=desc)


class SettableExtensionRegistryTestMixin:
    """ Base set of tests to test functionality of IExtensionPointRegistry
    that depends on ``IExtensionPointRegistry.set_extensions``.

    Test cases inheriting from this mixin should define a setUp method that
    defines self.registry as an instance of ExtensionPointRegistry.
    """

    def get_listener(self):
        """ Return a listener callable and the events list for inspecting
        the captured events.

        The event list should hold the call arguments to the listener.
        This provides the functionality of mock.Mock.call_args_list but
        without depending on all the magic offered by Mock.

        Returns
        -------
        listener: callable(ExtensionRegistry, ExtensionPointEvent)
        events : list
        """
        events = []

        def listener(registry, extension_point_event):
            events.append((registry, extension_point_event))

        return listener, events

    def test_add_extension_point_listener_with_matching_id(self):
        """ test adding extension point listener and its outcome."""

        registry = self.registry
        registry.add_extension_point(ExtensionPoint(id="my.ep"))

        listener, events = self.get_listener()
        registry.add_extension_point_listener(listener, "my.ep")

        # when
        old_extensions = registry.get_extensions("my.ep")
        new_extensions = [[1, 2]]
        registry.set_extensions("my.ep", new_extensions)

        # then
        self.assertEqual(len(events), 1)
        (actual_registry, actual_event), = events
        self.assertEqual(actual_event.extension_point_id, "my.ep")
        self.assertIsNone(actual_event.index)
        self.assertEqual(actual_event.added, new_extensions)
        self.assertEqual(actual_event.removed, old_extensions)

    def test_add_extension_point_listener_non_matching_id(self):
        """ test when the extension id does not match, listener is not fired.
        """

        registry = self.registry
        registry.add_extension_point(ExtensionPoint(id="my.ep"))
        registry.add_extension_point(ExtensionPoint(id="my.ep2"))

        listener, events = self.get_listener()
        registry.add_extension_point_listener(listener, "my.ep")

        # setting a different extension should not fire listener
        # when
        registry.set_extensions("my.ep2", [[]])

        # then
        self.assertEqual(len(events), 0)

    def test_add_extension_point_listener_none(self):
        """ Listen to all extension points if extension_point_id is none """

        registry = self.registry
        registry.add_extension_point(ExtensionPoint(id="my.ep"))
        registry.add_extension_point(ExtensionPoint(id="my.ep2"))

        listener, events = self.get_listener()
        registry.add_extension_point_listener(listener, None)

        # when
        registry.set_extensions("my.ep2", [[]])

        # then
        self.assertEqual(len(events), 1)

        # when
        registry.set_extensions("my.ep", [[]])

        # then
        self.assertEqual(len(events), 2)
