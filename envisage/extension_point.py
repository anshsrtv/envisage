# (C) Copyright 2007-2020 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in LICENSE.txt and may be redistributed only under
# the conditions described in the aforementioned license. The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#
# Thanks for using Enthought open source!
""" A trait type used to declare and access extension points. """


# Standard library imports.
import contextlib
import inspect
import warnings
import weakref

# Enthought library imports.
from traits.api import (
    List, TraitType, Undefined, provides
)
# See enthought/traits#1332
from traits.trait_list_object import TraitList

# Local imports.
from .i_extension_point import IExtensionPoint


def contributes_to(id):
    """ A factory for extension point decorators!

    As an alternative to making contributions via traits, you can use this
    decorator to mark any method on a 'Plugin' as contributing to an extension
    point (note this is *only* used on 'Plugin' instances!).

    e.g. Using a trait you might have something like::

        class MyPlugin(Plugin):
            messages = List(contributes_to='acme.messages')

            def _messages_default(self):
                return ['Hello', 'Hola']

    whereas, using the decorator, it would be::

        class MyPlugin(Plugin):
            @contributes_to('acme.messages')
            def _get_messages(self):
                return ['Hello', 'Hola']

    There is not much in it really, but the decorator version looks a little
    less like 'magic' since it doesn't require the developer to know about
    Traits default initializers. However, if you know that you will want to
    dynamically change your contributions then use the trait version  because
    all you have to do is change the value of the trait and the framework will
    react accordingly.

    """

    def decorator(fn):
        """ A decorator for marking methods as extension contributors. """

        fn.__extension_point__ = id

        return fn

    return decorator


# Exception message template.
INVALID_TRAIT_TYPE = (
    'extension points must be "List"s e.g. List, List(Int)'
    " but a value of %s was specified."
)


# Even though trait types do not themselves have traits, we can still
# declare that we implement an interface.
@provides(IExtensionPoint)
class ExtensionPoint(TraitType):
    """ A trait type used to declare and access extension points.

    Note that this is a trait *type* and hence does *NOT* have traits itself
    (i.e. it does *not* inherit from 'HasTraits').

    """

    ###########################################################################
    # 'ExtensionPoint' *CLASS* interface.
    ###########################################################################

    @staticmethod
    def bind(obj, trait_name, extension_point_id):
        """ Create a binding to an extension point. """

        from .extension_point_binding import bind_extension_point

        return bind_extension_point(obj, trait_name, extension_point_id)

    @staticmethod
    def connect_extension_point_traits(obj):
        """ Connect all of the 'ExtensionPoint' traits on an object. """

        for trait_name, trait in obj.traits(__extension_point__=True).items():
            trait.trait_type.connect(obj, trait_name)

        return

    @staticmethod
    def disconnect_extension_point_traits(obj):
        """ Disconnect all of the 'ExtensionPoint' traits on an object. """

        for trait_name, trait in obj.traits(__extension_point__=True).items():
            trait.trait_type.disconnect(obj, trait_name)

        return

    ###########################################################################
    # 'object' interface.
    ###########################################################################

    def __init__(self, trait_type=List, id=None, **metadata):
        """ Constructor. """

        # We add '__extension_point__' to the metadata to make the extension
        # point traits easier to find with the 'traits' and 'trait_names'
        # methods on 'HasTraits'.
        metadata["__extension_point__"] = True
        super().__init__(**metadata)

        # The trait type that describes the extension point.
        #
        # If we are handed a trait type *class* e.g. List, instead of a trait
        # type *instance* e.g. List() or List(Int) etc, then we instantiate it.
        if inspect.isclass(trait_type):
            trait_type = trait_type()

        # Currently, we only support list extension points (we may in the
        # future want to allow other collections e.g. dictionaries etc).
        if not isinstance(trait_type, List):
            raise TypeError(INVALID_TRAIT_TYPE % trait_type)

        self.trait_type = trait_type

        # The Id of the extension point.
        if id is None:
            raise ValueError("an extension point must have an Id")

        self.id = id

        # A dictionary that is used solely to keep a reference to all extension
        # point listeners alive until their associated objects are garbage
        # collected.
        #
        # Dict(weakref.ref(Any), Dict(Str, Callable))
        self._obj_to_listeners_map = weakref.WeakKeyDictionary()

        return

    def __repr__(self):
        """ String representation of an ExtensionPoint object """
        return "ExtensionPoint(id={!r})".format(self.id)

    ###########################################################################
    # 'TraitType' interface.
    ###########################################################################

    def _get_cache_name(self, trait_name):
        """ Return the cache name for the extension point value associated
        with a given trait.
        """
        return "__envisage_{}".format(trait_name)

    def _update_cache(self, obj, trait_name):
        """ Update the internal cached value for the extension point and
        fire change event.

        Parameters
        ----------
        obj : HasTraits
            The object on which an ExtensionPoint is defined.
        trait_name : str
            The name of the trait for which ExtensionPoint is defined.
        """
        cache_name = self._get_cache_name(trait_name)
        old = obj.__dict__.get(cache_name, Undefined)
        new = (
            _ExtensionPointValue(
                _get_extensions(obj, trait_name),
            )
        )
        new._set_reference(obj, trait_name)
        obj.__dict__[cache_name] = new
        obj.trait_property_changed(trait_name, old, new)

    def get(self, obj, trait_name):
        """ Trait type getter. """
        cache_name = self._get_cache_name(trait_name)
        if cache_name not in obj.__dict__:
            self._update_cache(obj, trait_name)

        value = obj.__dict__[cache_name]
        # validate again
        self.trait_type.validate(obj, trait_name, value[:])
        return value

    def set(self, obj, name, value):
        """ Trait type setter. """

        extension_registry = self._get_extension_registry(obj)

        # Note that some extension registry implementations may not support the
        # setting of extension points (the default, plugin extension registry
        # for exxample ;^).
        extension_registry.set_extensions(self.id, value)

    ###########################################################################
    # 'ExtensionPoint' interface.
    ###########################################################################

    def connect(self, obj, trait_name):
        """ Connect the extension point to a trait on an object.

        This allows the object to react when contributions are added or
        removed from the extension point.

        fixme: It would be nice to be able to make the connection automatically
        but we would need a slight tweak to traits to allow the trait type to
        be notified when a new instance that uses the trait type is created.

        """

        def listener(extension_registry, event):
            """ Listener called when an extension point is changed. """

            # If an index was specified then we fire an '_items' changed event.
            if event.index is not None:
                name = trait_name + "_items"
                old = Undefined
                new = event

                extensions = getattr(obj, trait_name)

                if isinstance(event.index, slice):
                    with extensions._internal_sync():
                        if event.added:
                            extensions[event.index] = event.added
                        else:
                            del extensions[event.index]
                else:
                    slice_ = slice(
                        event.index, event.index + len(event.removed)
                    )
                    with extensions._internal_sync():
                        extensions[slice_] = event.added

                # For on_trait_change('name_items')
                obj.trait_property_changed(name, old, new)

            # Otherwise, we fire a normal trait changed event.
            else:
                name = trait_name
                old = event.removed
                new = event.added
                self._update_cache(obj, name)
            return

        extension_registry = self._get_extension_registry(obj)

        # Add the listener to the extension registry.
        extension_registry.add_extension_point_listener(listener, self.id)

        # Save a reference to the listener so that it does not get garbage
        # collected until its associated object does.
        listeners = self._obj_to_listeners_map.setdefault(obj, {})
        listeners[trait_name] = listener

        return

    def disconnect(self, obj, trait_name):
        """ Disconnect the extension point from a trait on an object. """

        extension_registry = self._get_extension_registry(obj)

        listener = self._obj_to_listeners_map[obj].get(trait_name)
        if listener is not None:
            # Remove the listener from the extension registry.
            extension_registry.remove_extension_point_listener(
                listener, self.id
            )

            # Clean up.
            del self._obj_to_listeners_map[obj][trait_name]

        return

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_extension_registry(self, obj):
        """ Return the extension registry in effect for an object. """

        extension_registry = getattr(obj, "extension_registry", None)
        if extension_registry is None:
            raise ValueError(
                'The "ExtensionPoint" trait type can only be used in '
                "objects that have a reference to an extension registry "
                'via their "extension_registry" trait. '
                "Extension point Id <%s>" % self.id
            )

        return extension_registry


class _ExtensionPointValue(TraitList):
    """ An instance of _ExtensionPointValue is the value being returned while
    retrieving the attribute value for an ExtensionPoint trait.

    For a given trait ``name`` created using the ExtensionPoint trait type,
    historically one can get notifications for changes to the extension point
    by listening to the "name_items" trait using ``on_trait_change``. However,
    the ExtensionPoint value is not a persisted list that can be mutated.
    In Traits 6.1, a new notification framework is introduced: ``observe``.
    Since the naming of "name_items" clashes with listening to mutation on a
    persisted Traits list/dict/set in the older framework, tt is then is
    tempting to migrate ``on_trait_change("name_items")`` to
    ``observe("name:items")``. This class is defined to support such a
    migration while preventing the list of extensions to be mutated directly.

    Assumptions on the internal values being synchronized with the registry
    is error-prone, and more importantly, rely on the listener on the extension
    registry to be hooked up before any changes on the registry has happened.
    The latter is hard to guarantee. Therefore we always resort to the
    extension registry to get any values. The registry should hold the
    single source of truth.

    The listener machinery, however, does assume the list is synchronized so
    that the index, removed, added on the change event object is correct.
    So we make an effort to synchronize the values, but also make an effort
    to prevent users from modifying the values on the list.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Flag to control access for mutating the list. Only internal
        # code can mutate the list. See _internal_sync
        self._internal_use = False

    def _set_reference(self, object, name):
        """ Set references to the HasTraits object and trait name this
        ExtensionPointValue is defined for.

        Parameters
        ----------
        obj : HasTraits
            The object on which an ExtensionPoint is defined.
        trait_name : str
            The name of the trait for which ExtensionPoint is defined.
        """
        # FIXME: Do we need weakref here for the object?
        self._object = object
        self._name = name

    def __eq__(self, other):
        if self._internal_use:
            return super().__eq__(other)
        return _get_extensions(self._object, self._name) == other

    def __getitem__(self, key):
        if self._internal_use:
            return super().__getitem__(key)
        return _get_extensions(self._object, self._name)[key]

    def __len__(self):
        if self._internal_use:
            return super().__len__()
        return len(_get_extensions(self._object, self._name))

    @contextlib.contextmanager
    def _internal_sync(self):
        """ Context manager to temporarily allow mutation. This should be
        used by Envisage internal code only.
        """
        self._internal_use = True
        try:
            yield
        finally:
            self._internal_use = False

    # Reimplement TraitList interface to avoid any mutation.
    # The original implementation of __setitem__ and __delitem__ can be used
    # by internal code.

    def __delitem__(self, key):
        """ Reimplemented TraitList.__delitem__ """

        # This is used by internal code

        if not self._internal_use:
            warnings.warn(
                "Extension point cannot be mutated directly.",
                RuntimeWarning,
                stacklevel=2,
            )
            return

        super().__delitem__(key)

    def __iadd__(self, value):
        """ Reimplemented TraitList.__iadd__ """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )
        return self[:]

    def __imul__(self, value):
        """ Reimplemented TraitList.__imul__ """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )
        return self[:]

    def __setitem__(self, key, value):
        """ Reimplemented TraitList.__setitem__ """

        # This is used by internal code

        if not self._internal_use:
            warnings.warn(
                "Extension point cannot be mutated directly.",
                RuntimeWarning,
                stacklevel=2,
            )
            return

        super().__setitem__(key, value)

    def append(self, object):
        """ Reimplemented TraitList.append """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )

    def clear(self):
        """ Reimplemented TraitList.clear """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )

    def extend(self, iterable):
        """ Reimplemented TraitList.extend """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )

    def insert(self, index, object):
        """ Reimplemented TraitList.insert """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )

    def pop(self, index=-1):
        """ Reimplemented TraitList.pop """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )

    def remove(self, value):
        """ Reimplemented TraitList.remove """
        # We should not need it for internal use either.
        warnings.warn(
            "Extension point cannot be mutated directly.",
            RuntimeWarning,
            stacklevel=2,
        )


def _get_extensions(object, name):
    """ Return the extensions reported by the extension registry for the
    given object and the name of a trait whose type is an ExtensionPoint.

    Parameters
    ----------
    object : HasTraits
        Object on which an ExtensionPoint is defined
    name : str
        Name of the trait whose trait type is an ExtensionPoint.

    Returns
    -------
    extensions : list
        All the extensions for the extension point.
    """
    extension_point = object.trait(name).trait_type
    extension_registry = extension_point._get_extension_registry(object)

    # Get the extensions to this extension point.
    return extension_registry.get_extensions(extension_point.id)
