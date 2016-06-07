!*****************************************************************************
!***************************************************************************** 
PROGRAM resfort_scalar

    !/* external modules        */
   
    USE resfort_library

    !/* setup                   */

    IMPLICIT NONE

    !/* objects                 */

    REAL(our_dble)                  :: shocks_cholesky(4, 4)
    REAL(our_dble)                  :: coeffs_home(1)
    REAL(our_dble)                  :: coeffs_edu(3)
    REAL(our_dble)                  :: coeffs_a(6)
    REAL(our_dble)                  :: coeffs_b(6)
    REAL(our_dble)                  :: crit_val

!------------------------------------------------------------------------------
! Algorithm
!------------------------------------------------------------------------------

    ! Read specification of model. This is the FORTRAN replacement for the RespyCls instance that carries the model parametrization for the PYTHON/F2PY implementations.
    CALL read_specification(coeffs_a, coeffs_b, coeffs_edu, coeffs_home, shocks_cholesky)

    ! This part creates (or reads from disk) the draws for the Monte Carlo integration of the EMAX. For is_debugging purposes, these might also be read in from disk or set to zero/one.   
    CALL create_draws(periods_draws_emax, num_draws_emax, seed_emax)

    ! Execute on request.
    IF (request == 'solve') THEN

        ! Solve the model for a given parametrization.    
        CALL fort_solve(periods_payoffs_systematic, states_number_period, mapping_state_idx, periods_emax, states_all, coeffs_a, coeffs_b, coeffs_edu, coeffs_home, shocks_cholesky, periods_draws_emax)

    ELSE IF (request == 'evaluate') THEN

        ! This part creates (or reads from disk) the draws for the Monte Carlo integration of the choice probabilities. For is_debugging purposes, these might also be read in from disk or set to zero/one.   
        CALL create_draws(periods_draws_prob, num_draws_prob, seed_prob)

        ! Read observed dataset from disk.
        CALL read_dataset(data_array, num_agents_est)

        ! Solve the model for a given parametrization.    
        CALL fort_solve(periods_payoffs_systematic, states_number_period, mapping_state_idx, periods_emax, states_all, coeffs_a, coeffs_b, coeffs_edu, coeffs_home, shocks_cholesky, periods_draws_emax)

        CALL fort_evaluate(crit_val, periods_payoffs_systematic, mapping_state_idx, periods_emax, states_all, shocks_cholesky, data_array, periods_draws_prob)

    END IF

    ! Store results. These are read in by the PYTHON wrapper and added to the RespyCls instance.
    CALL store_results(mapping_state_idx, states_all, periods_payoffs_systematic, states_number_period, periods_emax, crit_val)


!******************************************************************************
!******************************************************************************
END PROGRAM