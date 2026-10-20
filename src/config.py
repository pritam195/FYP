# -*- coding: utf-8 -*-
"""
Global Configuration for Metasurface Antenna Sensor & Breast Phantom Simulation
Paper: Zhao et al., "Miniaturized and wideband metasurface antenna sensor for breast tumor detection",
       Sensors and Actuators A: Physical 394 (2025) 116973.

All dimensions are in millimeters (mm) unless explicitly stated.
All frequencies are in Hertz (Hz).
"""

import numpy as np

# Physical constants
C0 = 299792458.0           # Speed of light in vacuum (m/s)
EPS0 = 8.8541878128e-12    # Vacuum permittivity (F/m)
MU0 = 4.0 * np.pi * 1e-7   # Vacuum permeability (H/m)
ETA0 = np.sqrt(MU0 / EPS0) # Free-space wave impedance (~376.73 Ohms)

# Unit definition for openEMS
UNIT = 1e-3  # Drawing unit = 1 mm (1e-3 m)

# ==============================================================================
# 1. FREQUENCY & EXCITATION SPECIFICATIONS
# ==============================================================================
F_MIN = 3.0e9              # Minimum frequency of interest (3.0 GHz)
F_MAX = 11.0e9             # Maximum frequency of interest (11.0 GHz)
F0 = 7.0e9                 # Center frequency of Gaussian excitation (7.0 GHz)
FC = 4.0e9                 # 20-dB cutoff frequency (covers 3 to 11 GHz)
F_CENTER_DESIGN = 6.87e9   # Nominal center frequency from paper (Table 5: 6.87 GHz)

# Key pattern calculation frequencies from paper (Fig. 13)
F_PATTERN = [5.73e9, 6.98e9, 8.51e9, 9.02e9]

# ==============================================================================
# 2. SUBSTRATE & MATERIALS
# ==============================================================================
# Substrate: F4BM (PTFE / fiberglass woven laminate)
SUBSTRATE_EPS_R = 3.5
SUBSTRATE_TAND = 0.0042
# Equivalent dielectric conductivity kappa = omega * eps_0 * eps_r * tan_d at center frequency
SUBSTRATE_KAPPA = (2.0 * np.pi * F_CENTER_DESIGN) * EPS0 * SUBSTRATE_EPS_R * SUBSTRATE_TAND
# Kappa ~ 5.6183e-3 S/m

# Layer thicknesses (z-direction, mm)
H_TOP = 0.5       # Top layer thickness h1 = 0.5 mm
H_MID = 2.0       # Middle layer thickness h0 = 2.0 mm
H_BOT = 2.0       # Bottom layer thickness h2 = 2.0 mm
H_TOTAL = 4.5     # Total substrate thickness h = 4.5 mm

# Board lateral dimensions (mm)
BOARD_L_X = 44.0  # Board length along x
BOARD_L_Y = 44.0  # Board length along y

# ==============================================================================
# 3. TOP LAYER: 4x4 RADIATING PATCH ARRAY
# ==============================================================================
TOP_N_X = 4       # Number of columns (along x)
TOP_N_Y = 4       # Number of rows (along y)
TOP_L1 = 7.8      # Patch length in x (mm)
TOP_W1 = 5.6      # Patch width in y (mm)
TOP_S1 = 0.7      # Gap between patches in x (mm)
TOP_G1 = 1.0      # Gap between patches in y (mm)

# Derived lattice periods and overall extents
PERIOD_X = TOP_L1 + TOP_S1  # 8.5 mm period along x
PERIOD_Y = TOP_W1 + TOP_G1  # 6.6 mm period along y
ARRAY_SPAN_X = TOP_N_X * TOP_L1 + (TOP_N_X - 1) * TOP_S1  # 33.3 mm
ARRAY_SPAN_Y = TOP_N_Y * TOP_W1 + (TOP_N_Y - 1) * TOP_G1  # 25.4 mm

# ==============================================================================
# 4. MIDDLE LAYER: 4x4 GROUPS OF DUAL-STRIP METALLIC PATCHES & VIAS
# ==============================================================================
MID_N_X = 4       # Number of columns (along x)
MID_N_Y = 4       # Number of rows (along y)
MID_L2 = 6.0      # Strip length along x (mm)
MID_W2 = 1.6      # Single strip width along y (mm)
MID_G2 = 0.8      # Gap between the two strips in the same unit cell along y (mm)
MID_S2 = 2.5      # Inter-cell gap along x (mm): MID_L2 + MID_S2 = 8.5 mm (matches PERIOD_X)
MID_G3 = 4.2      # Centerline-to-centerline vertical spacing between strips across cells (mm)
# Note: Edge-to-edge gap between adjacent cell pairs along y is MID_G3 - MID_W2 = 2.6 mm.
# Total vertical unit cell period = 2*MID_W2 + MID_G2 + (MID_G3 - MID_W2) = 6.6 mm (matches PERIOD_Y)

# Vias connecting top and bottom of middle layer (across H_MID = 2.0 mm)
VIA_COUNT_PER_STRIP = 3       # 3 vias per strip, 6 vias per cell, 96 total
VIA_DIAMETER = 0.35           # Nominal via drill diameter (mm), range [0.30, 0.40]
VIA_POS_X_OFFSETS = [-1.8, 0.0, 1.8]  # x-offsets from strip center (mm)

# ==============================================================================
# 5. BOTTOM LAYER: CPW FEED & TRANSVERSE COUPLING SLOT
# ==============================================================================
CPW_W3 = 3.0      # CPW center conductor width (mm)
CPW_S3 = 0.2      # CPW gap width on each side (mm)
CPW_L3 = 21.5     # CPW feed line length from board edge (-BOARD_L_Y/2) to slot (mm)
CPW_Z0_NOMINAL = 50.0  # Nominal line impedance (~48.8 Ohms theoretical)

SLOT_S4 = 1.0     # Coupling slot width along y (mm)
SLOT_W4 = 9.6     # Coupling slot length per branch along x from CPW edge (mm)
SLOT_S5 = 2.0     # Widened end stub width along y (mm)
SLOT_W5 = 2.0     # Widened end stub length along x (mm)

# ==============================================================================
# 6. HEMISPHERICAL BREAST PHANTOM SPECIFICATIONS (Section 3.1, Fig. 6)
# ==============================================================================
# Concentric spherical radii (mm)
PHANTOM_R1_SKIN_OUTER = 50.0   # Outer radius of skin layer (r1 = 50 mm)
PHANTOM_R2_FAT_OUTER  = 45.0   # Outer radius of fat layer / inner skin (r2 = 45 mm, thickness 5 mm)
PHANTOM_R3_GLAND_OUTER= 30.0   # Outer radius of fibro-glandular / inner fat (r3 = 30 mm, fat thickness 15 mm)
# Fibro-glandular core thickness = 30 mm (occupies 0 to r3)

# Tumor specifications
TUMOR_RADIUS_DEFAULT = 5.0     # Default tumor radius (mm)
TUMOR_RADIUS_SWEEP = [0.0, 3.0, 5.0, 10.0]  # Radius sweep values (mm)

# Distances from antenna sensor (z-distance or radial depth)
SENSOR_TO_SKIN_GAP_D1 = 1.0    # Gap between antenna top and skin bottom (d1 = 1 mm)
TUMOR_DIST_SWEEP = [10.5, 16.0, 21.5]  # Distance sweep d (mm)
TUMOR_DIST_DEFAULT = 16.0      # Default tumor distance (mm)

# Tissue dielectric properties at microwave frequencies (Section 3.1)
TISSUE_PROPERTIES = {
    'skin': {
        'eps_r': 36.0,
        'sigma': 4.0,     # S/m
        'density': 1100.0  # kg/m^3 (standard biological density)
    },
    'fat': {
        'eps_r': 9.0,
        'sigma': 0.4,     # S/m
        'density': 930.0   # kg/m^3
    },
    'fibro_glandular': {
        'eps_r': 13.0,
        'sigma': 0.45,    # S/m
        'density': 1050.0  # kg/m^3
    },
    'tumor': {
        'eps_r': 50.0,
        'sigma': 4.0,     # S/m
        'density': 1050.0  # kg/m^3
    }
}

# 5 Tumor locations per Fig. 18 (azimuthal / positional sweep)
# Defined in Stage 4 detailed module

# ==============================================================================
# 7. NUMERICAL & MESH SETTINGS
# ==============================================================================
FDTD_NRTS = 60000              # Maximum timesteps
FDTD_END_CRITERIA = 1e-4       # Energy decay threshold (-40 dB)
NUM_THREADS = 8                # Use all CPU logical processors

# PML absorbing boundary setup
PML_CELLS = 8                  # Number of PML layers (PML_8)
AIR_MARGIN_LAMBDA_FRACTION = 0.25 # Air buffer >= lambda_max / 4 at lowest frequency (3 GHz -> ~25 mm)
AIR_MARGIN_MM = 30.0           # 30 mm air buffer on lateral and radiation boundaries

# Discretization limits (mm)
MESH_AIR_MAX = 2.0             # Max cell size in air (lambda_min / 14 ~ 2.0 mm)
MESH_DIEL_MAX = 1.0            # Max cell size in F4BM dielectric (lambda_min,diel / 15 ~ 1.0 mm)
MESH_FINE_SLOT = 0.10          # Resolution around CPW 0.2 mm slot (2 cells across gap)
MESH_FINE_Z_TOP = 0.15         # Resolution across 0.5 mm top layer (3-4 cells)
MESH_SMOOTH_RATIO = 1.4        # Maximum grid expansion ratio for SmoothMeshLines
