MODULE nrtype
 IMPLICIT NONE
 SAVE
 ! data types
 INTEGER,      PARAMETER :: I4B = SELECTED_INT_KIND(9)
 INTEGER,      PARAMETER :: I2B = SELECTED_INT_KIND(4)
 INTEGER,      PARAMETER :: I1B = SELECTED_INT_KIND(2)
 INTEGER,      PARAMETER :: SP = KIND(1.0)
 INTEGER,      PARAMETER :: DP = KIND(1.0D0)
 INTEGER,      PARAMETER :: QP = KIND(1.0D0)
 INTEGER,      PARAMETER :: rkind = DP
 !INTEGER,      PARAMETER :: QP = SELECTED_REAL_KIND(32)
 INTEGER,      PARAMETER :: SPC = KIND((1.0,1.0))
 INTEGER,      PARAMETER :: DPC = KIND((1.0D0,1.0D0))
 INTEGER,      PARAMETER :: LGT = KIND(.true.)
 ! constants
 REAL(SP),     PARAMETER :: PI=3.141592653589793238462643383279502884197_sp
 REAL(SP),     PARAMETER :: PIO2=1.57079632679489661923132169163975144209858_sp
 REAL(SP),     PARAMETER :: TWOPI=6.283185307179586476925286766559005768394_sp
 REAL(SP),     PARAMETER :: SQRT2=1.41421356237309504880168872420969807856967_sp
 REAL(SP),     PARAMETER :: EULER=0.5772156649015328606065120900824024310422_sp
 real(rkind),     PARAMETER :: PI_D=3.141592653589793238462643383279502884197_rkind
 real(rkind),     PARAMETER :: PIO2_D=1.57079632679489661923132169163975144209858_rkind
 real(rkind),     PARAMETER :: TWOPI_D=6.283185307179586476925286766559005768394_rkind
 ! missing values
 real(rkind),     parameter :: nr_quadMissing=-9999._qp   ! missing quadruple precision number
 real(rkind),     parameter :: nr_realMissing=-9999._rkind   ! missing double precision number
 integer(i4b), parameter :: nr_integerMissing=-9999    ! missing integer
 ! data types for HDS pothole storage
 ! useful shortcuts
 real(rkind),  parameter  :: zero      = 0.0_rkind
 real(rkind),  parameter  :: half      = 0.5_rkind
 real(rkind),  parameter  :: one       = 1.0_rkind
 real(rkind),  parameter  :: two       = 2.0_rkind
 ! real(rkind),  parameter  :: verySmall = 1.0e-12_rkind
 ! physical constants
 real(rkind),  parameter  :: rho_w     = 1000._rkind  ! density of water (kg m-3)
END MODULE nrtype
