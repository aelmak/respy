""" This auxiliary module contains some functions that supports the
investigations of all admissible values.
"""

# standard library
import numpy as np

from robupy.python.py.ambiguity import transform_disturbances_ambiguity
from robupy.python.py.auxiliary import simulate_emax
from robupy.clsRobupy import RobupyCls


def distribute_arguments(parser):
    """ Distribute command line arguments.
    """
    # Process command line arguments
    args = parser.parse_args()

    # Extract arguments
    is_recompile = args.is_recompile
    num_procs = args.num_procs
    is_debug = args.is_debug
    levels = args.levels

    # Check arguments
    assert (isinstance(levels, list))
    assert (np.all(levels) >= 0.00)
    assert (is_recompile in [True, False])
    assert (is_debug in [True, False])
    assert (isinstance(num_procs, int))
    assert (num_procs > 0)

    # Finishing
    return levels, is_recompile, is_debug, num_procs


def criterion(x, num_draws, eps_relevant, period, k, payoffs_systematic,
        edu_max, edu_start, mapping_state_idx, states_all, num_periods,
        periods_emax, delta, sign=1):
    """ Simulate expected future value for alternative shock distributions.
    """
    # This is a slightly modified copy of the criterion function in the
    # ambiguity module. The ability to switch the sign was added to allow for
    # maximization as well as minimization.
    assert (sign in [1, -1])

    # Transformation of standard normal deviates to relevant distributions.
    eps_relevant_emax = transform_disturbances_ambiguity(eps_relevant, x)

    # Simulate the expected future value for a given parametrization.
    simulated, _, _ = simulate_emax(num_periods, num_draws, period, k,
                        eps_relevant_emax, payoffs_systematic, edu_max, edu_start,
                        periods_emax, states_all, mapping_state_idx, delta)

    # Finishing
    return sign*simulated


def get_robupy_obj(init_dict):
    """ Get the object to pass in the solution method.
    """
    # Initialize and process class
    robupy_obj = RobupyCls()
    robupy_obj.set_attr('init_dict', init_dict)
    robupy_obj.lock()
    # Finishing
    return robupy_obj
