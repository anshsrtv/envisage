""" An extensible workbench window. """


# Enthought library imports.
import enthought.pyface.workbench.api as pyface

from enthought.envisage.api import IApplication, ExtensionPoint
from enthought.envisage.ui.action.api import ActionSet
from enthought.pyface.workbench.api import IPerspective
from enthought.traits.api import Instance, Property

# Local imports.
from workbench_action_manager_builder import WorkbenchActionManagerBuilder
from workbench_editor_manager import WorkbenchEditorManager


class WorkbenchWindow(pyface.WorkbenchWindow):
    """ An extensible workbench window. """

    # Extension point Ids.
    ACTIONS      = 'enthought.envisage.ui.workbench.actions'
    VIEWS        = 'enthought.envisage.ui.workbench.views'
    PERSPECTIVES = 'enthought.envisage.ui.workbench.perspectives'
    
    #### 'WorkbenchWindow' interface ##########################################

    # The application that the view is part of.
    #
    # This is equivalent to 'self.workbench.application', and is provided just
    # as a convenience since windows often want access to the application.
    application = Property(Instance(IApplication))

    #### Private interface ####################################################

    # The workbench menu and tool bar builder.
    _action_manager_builder = Instance(WorkbenchActionManagerBuilder)
    
    # Contributed action sets.
    _action_sets = ExtensionPoint(id=ACTIONS)
    
    # Contributed views (views are contributed as factories not view instances
    # as each workbench window requires its own).
    _view_factories = ExtensionPoint(id=VIEWS)

    # Contributed perspectives.
    _perspectives = ExtensionPoint(id=PERSPECTIVES)

    ###########################################################################
    # 'pyface.WorkbenchWindow' interface.
    ###########################################################################

    #### Trait initializers ###################################################

    def _editor_manager_default(self):
        """ Trait initializer. """

        return WorkbenchEditorManager(window=self)
    
    def _icon_default(self):
        """ Trait initializer. """

        return self.workbench.application.icon
    
    def _perspectives_default(self):
        """ Trait initializer. """

        perspectives = []
        for factory_or_perspective in self._perspectives:
            # Is the contribution an actual perspective, or is it a factory
            # that can create a perspective?
            perspective = IPerspective(factory_or_perspective, None)
            if perspective is None:
                perspective = factory_or_perspective()

            perspectives.append(perspective)
                
        return perspectives

    def _title_default(self):
        """ Trait initializer. """

        return self.workbench.application.name

    def _views_default(self):
        """ Trait initializer. """

        return [factory(window=self) for factory in self._view_factories]
    
    ###########################################################################
    # 'pyface.Window' interface.
    ###########################################################################

    #### Trait initializers ###################################################
    
    def _menu_bar_manager_default(self):
        """ Trait initializer. """

        return self._action_manager_builder.create_menu_bar_manager('MenuBar')

    def _tool_bar_managers_default(self):
        """ Trait initializer. """

        return self._action_manager_builder.create_tool_bar_managers('ToolBar')

    ###########################################################################
    # 'WorkbenchWindow' interface.
    ###########################################################################

    #### Trait properties #####################################################

    def _get_application(self):
        """ Property getter. """

        return self.workbench.application

    ###########################################################################
    # Private interface.
    ###########################################################################

    #### Trait initializers ###################################################

    def __action_manager_builder_default(self):
        """ Trait initializer. """

        action_sets = []
        for factory_or_action_set in self._action_sets:
            if not isinstance(factory_or_action_set, ActionSet):
                action_sets.append(factory_or_action_set())

            else:
                action_sets.append(factory_or_action_set)

        action_manager_builder = WorkbenchActionManagerBuilder(
            window=self, action_sets=action_sets
        )

        for action_set in self._action_sets:
            action_set.on_trait_change(
                self._on_action_set_enabled_changed, 'enabled'
            )

            action_set.on_trait_change(
                self._on_action_set_visible_changed, 'visible'
            )

        return action_manager_builder

    #### Trait change handlers ################################################

    def _on_action_set_enabled_changed(self, obj, trait_name, old, new):
        """ Dynamic trait change handler. """

        self._update_tool_bars(obj, 'visible', new)

        return

    def _on_action_set_visible_changed(self, obj, trait_name, old, new):
        """ Dynamic trait change handler. """

        self._update_tool_bars(obj, 'visible', new)
                    
        return

    #### Methods ##############################################################

    def _update_tool_bars(self, action_set, trait_name, value):
        """ Update the state of the tool bars in an action set. """

        for tool_bar in action_set.tool_bars:
            for tool_bar_manager in self.tool_bar_managers:
                if tool_bar_manager.id == tool_bar.id:
                    setattr(tool_bar_manager, trait_name, value)

        return
        
#### EOF ######################################################################
