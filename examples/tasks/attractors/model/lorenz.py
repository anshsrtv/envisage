# System library imports.
from scipy import arange, array
from scipy.integrate import odeint

# Enthought libary imports.
from enthought.traits.api import Adapter, Array, Float, HasTraits, Instance, \
     Property, Str, Unicode, adapts, cached_property, implements
from enthought.traits.ui.api import View, Item

# Local imports
from i_model_3d import IModel3d, IModel3dIPlottable2dMixin
from i_plottable_2d import IPlottable2d


class Lorenz(HasTraits):
    """ The model object for the Lorenz attractor.
    """

    implements(IModel3d)

    # Equation parameters.
    prandtl = Float(10.0, auto_set=False, enter_set=True)
    rayleigh = Float(28.0, auto_set=False, enter_set=True)
    beta = Float(8.0 / 3.0, auto_set=False, enter_set=True)

    # Integration parameters.
    initial_point = Array(value=[0.0, 1.0, 0.0])
    time_start = Float(0.0)
    time_stop = Float(100.0)
    time_step = Float(0.01)
    times = Property(Array, depends_on='time_start, time_stop, time_step')

    # Integration results.
    points = Property(Array, depends_on=['prandtl', 'rayleigh', 'beta',
                                         'initial_point', 'times'])

    # Configuration view.
    view = View(Item('prandtl'),
                Item('rayleigh'),
                Item('beta'),
                Item('initial_point'),
                Item('time_start'),
                Item('time_stop'),
                Item('time_step'),
                resizable=True)

    def compute_step(self, point, time):
        x, y, z = point
        return array([ self.prandtl * (y - x),
                       x * (self.rayleigh - z) - y,
                       x * y - self.beta * z ])

    @cached_property
    def _get_points(self):
        return odeint(self.compute_step, self.initial_point, self.times)

    @cached_property
    def _get_times(self):
        return arange(self.time_start, self.time_stop, self.time_step)


class LorenzIPlottable2dAdapter(Adapter, IModel3dIPlottable2dMixin):

    implements(IPlottable2d)
    
    adaptee = Instance(Lorenz)

    plot_type = Str('line')
    title = Unicode('Lorenz Attractor')

adapts(LorenzIPlottable2dAdapter, Lorenz, IPlottable2d)
