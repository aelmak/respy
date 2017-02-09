""" This module serves as the interface between the PYTHON code and the
FORTRAN implementations.
"""
import pandas as pd
import numpy as np
import subprocess
import os

from respy.python.shared.shared_auxiliary import dist_class_attributes
from respy.python.shared.shared_constants import OPT_EST_FORT
from respy.python.shared.shared_constants import MISSING_FLOAT
from respy.python.shared.shared_constants import HUGE_FLOAT
from respy.python.shared.shared_constants import EXEC_DIR


def resfort_interface(respy_obj, request, data_array=None):
    """ This function provides the interface to the FORTRAN functionality.
    """
    # Distribute class attributes
    optim_paras, num_periods, edu_start, is_debug, edu_max, delta, \
        num_draws_emax, seed_emax, is_interpolated, num_points_interp, \
        is_myopic, min_idx, tau, num_procs, num_agents_sim, \
        num_draws_prob, num_agents_est, seed_prob, seed_sim, paras_fixed, \
        optimizer_options, optimizer_used, maxfun, paras_fixed, \
        preconditioning, measure, file_sim, paras_bounds = \
            dist_class_attributes(respy_obj, 'optim_paras', 'num_periods',
                'edu_start', 'is_debug', 'edu_max',
                'delta', 'num_draws_emax', 'seed_emax', 'is_interpolated',
                'num_points_interp', 'is_myopic', 'min_idx', 'tau',
                'num_procs', 'num_agents_sim', 'num_draws_prob',
                'num_agents_est', 'seed_prob', 'seed_sim', 'paras_fixed',
                'optimizer_options', 'optimizer_used', 'maxfun', 'paras_fixed',
                'preconditioning', 'measure', 'file_sim',
                'paras_bounds')

    precond_type, precond_minimum, precond_eps = preconditioning

    if request == 'estimate':
        # Check that selected optimizer is in line with version of program.
        if maxfun > 0:
            assert optimizer_used in OPT_EST_FORT

        assert data_array is not None
        # If an evaluation is requested, then a specially formatted dataset is
        # written to a scratch file. This eases the reading of the dataset in
        # FORTRAN.
        write_dataset(data_array)

    args = (optim_paras, is_interpolated, num_draws_emax, num_periods,
            num_points_interp, is_myopic, edu_start, is_debug, edu_max,
            min_idx, delta)

    args = args + (num_draws_prob, num_agents_est, num_agents_sim, seed_prob,
        seed_emax, tau, num_procs, request, seed_sim, optimizer_options,
        optimizer_used, maxfun, paras_fixed, precond_eps, precond_type,
        precond_minimum, measure, file_sim, paras_bounds, data_array)

    write_resfort_initialization(*args)

    # Call executable
    if num_procs == 1:
        cmd = [EXEC_DIR + '/resfort']
        subprocess.check_call(cmd)
    elif num_procs > 1:
        cmd = ['mpiexec', '-n', '1', EXEC_DIR + '/resfort']
        subprocess.check_call(cmd)
    else:
        raise AssertionError

    # Return arguments depends on the request.
    if request == 'simulate':
        results = get_results(num_periods, min_idx, num_agents_sim, 'simulate')
        args = (results[:-1], results[-1])
    elif request == 'estimate':
        args = None
    else:
        raise AssertionError

    return args


def get_results(num_periods, min_idx, num_agents_sim, which):
    """ Add results to container.
    """
    # Get the maximum number of states. The special treatment is required as
    # it informs about the dimensions of some of the arrays that are
    # processed below.
    max_states_period = int(np.loadtxt('.max_states_period.resfort.dat'))

    os.unlink('.max_states_period.resfort.dat')

    shape = (num_periods, num_periods, num_periods, min_idx, 2)
    mapping_state_idx = read_data('mapping_state_idx', shape).astype('int')

    shape = (num_periods,)
    states_number_period = \
        read_data('states_number_period', shape).astype('int')

    shape = (num_periods, max_states_period, 4)
    states_all = read_data('states_all', shape).astype('int')

    shape = (num_periods, max_states_period, 4)
    periods_rewards_systematic = read_data('periods_rewards_systematic', shape)

    shape = (num_periods, max_states_period)
    periods_emax = read_data('periods_emax', shape)

    # In case of  a simulation, we can also process the simulated dataset.
    if which == 'simulate':
        shape = (num_periods * num_agents_sim, 8)
        data_array = read_data('simulated', shape)
    else:
        raise AssertionError

    # Update class attributes with solution
    args = (periods_rewards_systematic, states_number_period,
        mapping_state_idx, periods_emax, states_all, data_array)

    # Finishing
    return args


def read_data(label, shape):
    """ Read results
    """
    file_ = '.' + label + '.resfort.dat'

    # This special treatment is required as it is crucial for this data
    # to stay of integer type. All other data is transformed to float in
    # the replacement of missing values.
    if label == 'states_number_period':
        data = np.loadtxt(file_, dtype=np.int64)
    else:
        data = np.loadtxt(file_)

    data = np.reshape(data, shape)

    # Cleanup
    os.unlink(file_)

    # Finishing
    return data


def write_resfort_initialization(optim_paras, is_interpolated, num_draws_emax,
        num_periods, num_points_interp, is_myopic, edu_start, is_debug, edu_max,
        min_idx, delta, num_draws_prob, num_agents_est, num_agents_sim,
        seed_prob, seed_emax, tau, num_procs, request, seed_sim,
        optimizer_options, optimizer_used, maxfun, paras_fixed, precond_eps,
        precond_type, precond_minimum, measure, file_sim, paras_bounds,
        data_array):
    """ Write out model request to hidden file .model.resfort.ini.
    """

    # Auxiliary objects
    if data_array is not None:
        num_obs = data_array.shape[0]
    else:
        num_obs = -1

    # Write out to link file
    with open('.model.resfort.ini', 'w') as file_:

        # BASICS
        line = '{0:10d}\n'.format(num_periods)
        file_.write(line)

        line = '{0:25.15f}\n'.format(delta)
        file_.write(line)

        # WORK
        for num in [optim_paras['coeffs_a'], optim_paras['coeffs_b']]:
            fmt_ = ' {:25.15f}' * 6 + '\n'
            file_.write(fmt_.format(*num))

        # EDUCATION
        num = optim_paras['coeffs_edu']
        line = ' {:25.15f} {:25.15f} {:25.15f}\n'.format(*num)
        file_.write(line)

        line = '{0:10d} '.format(edu_start)
        file_.write(line)

        line = '{0:10d}\n'.format(edu_max)
        file_.write(line)

        # HOME
        line = ' {0:25.15f}\n'.format(optim_paras['coeffs_home'][0])
        file_.write(line)

        # SHOCKS
        for j in range(4):
            fmt_ = ' {:25.15f}' * 4 + '\n'
            file_.write(fmt_.format(*optim_paras['shocks_cholesky'][j, :]))

        # SOLUTION
        line = '{0:10d}\n'.format(num_draws_emax)
        file_.write(line)

        line = '{0:10d}\n'.format(seed_emax)
        file_.write(line)

        # AMBIGUITY
        line = '"{0}"'.format(measure)
        file_.write(line + '\n')

        line = '{0:25.15f}\n'.format(optim_paras['level'][0])
        file_.write(line)

        # PROGRAM
        line = '{0}'.format(is_debug)
        file_.write(line + '\n')
        line = '{0:10d}\n'.format(num_procs)
        file_.write(line)

        # INTERPOLATION
        line = '{0}'.format(is_interpolated)
        file_.write(line + '\n')

        line = '{0:10d}\n'.format(num_points_interp)
        file_.write(line)

        # ESTIMATION
        line = '{0:10d}\n'.format(maxfun)
        file_.write(line)

        line = '{0:10d}\n'.format(num_agents_est)
        file_.write(line)

        line = '{0:10d}\n'.format(num_draws_prob)
        file_.write(line)

        line = '{0:10d}\n'.format(seed_prob)
        file_.write(line)

        line = '{0:25.15f}\n'.format(tau)
        file_.write(line)

        line = '{0:10d}\n'.format(num_obs)
        file_.write(line)

        # PRECONDITIONING
        line = '{0}\n'.format(precond_type)
        file_.write(line)

        line = '{0:25.15f}\n'.format(precond_minimum)
        file_.write(line)

        line = '{0:25.15f}\n'.format(precond_eps)
        file_.write(line)

        # SIMULATION
        line = '{0:10d}\n'.format(num_agents_sim)
        file_.write(line)

        line = '{0:10d}\n'.format(seed_sim)
        file_.write(line)

        line = '"{0}"'.format(file_sim)
        file_.write(line + '\n')

        # Auxiliary
        line = '{0:10d}\n'.format(min_idx)
        file_.write(line)

        line = '{0}'.format(is_myopic)
        file_.write(line + '\n')

        fmt = '{:} ' * 27
        line = fmt.format(*paras_fixed)
        file_.write(line + '\n')

        # Request
        line = '"{0}"'.format(request)
        file_.write(line + '\n')

        # Directory for executables
        exec_dir = os.path.dirname(os.path.realpath(__file__)) + '/bin'

        line = '"{0}"'.format(exec_dir)
        file_.write(line + '\n')

        # Optimizers
        line = '"{0}"\n'.format(optimizer_used)
        file_.write(line)

        for optimizer in ['FORT-NEWUOA', 'FORT-BOBYQA']:
            line = '{0:10d}\n'.format(optimizer_options[optimizer]['npt'])
            file_.write(line)

            line = '{0:10d}\n'.format(optimizer_options[optimizer]['maxfun'])
            file_.write(line)

            line = ' {0:25.15f}\n'.format(optimizer_options[optimizer]['rhobeg'])
            file_.write(line)

            line = ' {0:25.15f}\n'.format(optimizer_options[optimizer]['rhoend'])
            file_.write(line)

        line = ' {0:25.15f}\n'.format(optimizer_options['FORT-BFGS']['gtol'])
        file_.write(line)

        line = ' {0:25.15f}\n'.format(optimizer_options['FORT-BFGS']['stpmx'])
        file_.write(line)

        line = '{0:10d}\n'.format(optimizer_options['FORT-BFGS']['maxiter'])
        file_.write(line)

        line = '{0:25.15f}\n'.format(optimizer_options['FORT-BFGS']['eps'])
        file_.write(line)

        line = ' {0:25.15f}\n'.format(optimizer_options['FORT-SLSQP']['ftol'])
        file_.write(line)

        line = '{0:10d}\n'.format(optimizer_options['FORT-SLSQP']['maxiter'])
        file_.write(line)

        line = '{0:25.15f}\n'.format(optimizer_options['FORT-SLSQP']['eps'])
        file_.write(line)

        # Transform bounds
        bounds_lower = []
        bounds_upper = []
        for i in range(27):
            bounds_lower += [paras_bounds[i][0]]
            bounds_upper += [paras_bounds[i][1]]

        for i in range(27):
            if bounds_lower[i] is None:
                bounds_lower[i] = -MISSING_FLOAT

        for i in range(27):
            if bounds_upper[i] is None:
                bounds_upper[i] = MISSING_FLOAT

        fmt_ = ' {:25.15f}' * 27
        line = fmt_.format(*bounds_lower)
        file_.write(line + '\n')

        line = fmt_.format(*bounds_upper)
        file_.write(line + '\n')


def write_dataset(data_array):
    """ Write the dataset to a temporary file. Missing values are set
    to large values.
    """
    # Transfer to data frame as this allows to fill the missing values with
    # HUGE FLOAT. The numpy array is passed in to align the interfaces across
    # implementations
    data_frame = pd.DataFrame(data_array)
    with open('.data.resfort.dat', 'w') as file_:
        data_frame.to_string(file_, index=False,
            header=None, na_rep=str(HUGE_FLOAT))

    # An empty line is added as otherwise this might lead to problems on the
    # TRAVIS servers. The FORTRAN routine read_dataset() raises an error.
    with open('.data.resfort.dat', 'a') as file_:
        file_.write('\n')
