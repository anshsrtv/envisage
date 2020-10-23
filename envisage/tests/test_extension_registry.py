# (C) Copyright 2007-2020 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in LICENSE.txt and may be redistributed only under
# the conditions described in the aforementioned license. The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#
# Thanks for using Enthought open source!
""" Tests for the base extension registry. """

# Standard library imports.
import contextlib
import unittest

# Enthought library imports.
from envisage.api import Application, ExtensionPoint
from envisage.api import ExtensionRegistry
from traits.api import List

from envisage.extension_registry import ObservableExtensionRegistry
from envisage.tests.test_extension_registry_mixin import (
    ExtensionRegistryTestMixin,
    SettableExtensionRegistryTestMixin,
    ListeningExtensionRegistryTestMixin,
)


class ExtensionRegistryTestCase(
        ExtensionRegistryTestMixin,
        SettableExtensionRegistryTestMixin,
        ListeningExtensionRegistryTestMixin,
        unittest.TestCase,
    ):
    """ Tests for the base extension registry. """

    def setUp(self):
        """ Prepares the test fixture before each test method is called. """

        # We do all of the testing via the application to make sure it offers
        # the same interface!
        self.registry = Application(extension_registry=ExtensionRegistry())

    def test_remove_non_empty_extension_point(self):
        """ remove non-empty extension point """

        registry = self.registry

        # Add an extension point...
        registry.add_extension_point(self.create_extension_point("my.ep"))

        # ... with some extensions...
        registry.set_extensions("my.ep", [42])

        # ...and remove it!
        registry.remove_extension_point("my.ep")

        # Make sure there are no extension points.
        extension_points = registry.get_extension_points()
        self.assertEqual(0, len(extension_points))

        # And that the extensions are gone too.
        self.assertEqual([], registry.get_extensions("my.ep"))

    def test_set_extensions(self):
        """ set extensions """

        registry = self.registry

        # Add an extension *point*.
        registry.add_extension_point(self.create_extension_point("my.ep"))

        # Set some extensions.
        registry.set_extensions("my.ep", [1, 2, 3])

        # Make sure we can get them.
        self.assertEqual([1, 2, 3], registry.get_extensions("my.ep"))


class ObservableExtensionRegistryTestCase(
        ExtensionRegistryTestMixin,
        SettableExtensionRegistryTestMixin,
        ListeningExtensionRegistryTestMixin,
        unittest.TestCase,
    ):
    """ Tests for the base (?) observable extension registry. """

    def setUp(self):
        self.registry = ObservableExtensionRegistry()

    def test_mutate_original_extensions_mutate_registry(self):
        with self.assertRaises(AssertionError):
            # ObservableExtensionRegistry and ExtensionRegistry disagree
            # on this test. We can't make ObservableExtensionRegistry do the
            # same thing if we want to observe a nested List on a dict,
            # because Traits List always instantiates a new instance of
            # TraitList at assignment.
            super().test_mutate_original_extensions_mutate_registry()

    def test_nonmethod_listener_lifetime(self):
        with self.assertRaises(AssertionError):
            # Traits observe only holds a weak reference if the handler
            # is a method. In the case of a normal function, a strong
            # reference is held. But ExtensionPointRegistry holds a weak
            # reference regardless. Not sure if that is justified.
            super().test_nonmethod_listener_lifetime()
