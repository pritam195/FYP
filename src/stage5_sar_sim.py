# -*- coding: utf-8 -*-
"""
Stage 5: Local Specific Absorption Rate (SAR) Analysis
======================================================
Paper: Zhao et al., Section 3.2, Fig. 7, Fig. 8, Table 2, Table 3.

Evaluates local SAR in 4 biological regions:
  - Skin:            rho = 1100 kg/m^3, eps_r = 36.0, sigma = 4.0 S/m
  - Fat:             rho =  930 kg/m^3, eps_r =  9.0, sigma = 0.4 S/m
  - Fibro-glandular: rho = 1050 kg/m^3, eps_r = 13.0, sigma = 0.45 S/m
  - Tumor:           rho = 1050 kg/m^3, eps_r = 50.0, sigma = 4.0 S/m

Calculates:
  1. Local SAR field: SAR(x, y, z) = sigma * |E|^2 / (2 * rho)
  2. Peak local SAR per tissue layer normalized to 1 W input power
  3. Recreates Fig. 7 (no tumor), Fig. 8 (r = 5 mm, d = 10.5 mm), and Tables 2 & 3.
"""

import os, sys, time, h5py
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from CSXCAD  import ContinuousStructure
from openEMS import openEMS

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
from config import (
    UNIT, F0, FC, F_MIN, F_MAX,
    SUBSTRATE_EPS_R, SUBSTRATE_KAPPA,
    BOARD_L_X, BOARD_L_Y,
    H_BOT, H_MID, H_TOP, H_TOTAL,
    TOP_N_X, TOP_N_Y, TOP_L1, TOP_W1,
    PERIOD_X, PERIOD_Y,
    MID_L2, MID_W2, MID_G2,
    VIA_DIAMETER, VIA_POS_X_OFFSETS,
    CPW_W3, CPW_S3, CPW_L3,
    SLOT_S4, SLOT_W4, SLOT_S5, SLOT_W5,
    PHANTOM_R1_SKIN_OUTER, PHANTOM_R2_FAT_OUTER, PHANTOM_R3_GLAND_OUTER,
    SENSOR_TO_SKIN_GAP_D1, TISSUE_PROPERTIES,
    FDTD_NRTS, FDTD_END_CRITERIA
)

RESULTS_PATH = os.path.join(PROJECT_DIR, 'results')
os.makedirs(RESULTS_PATH, exist_ok=True)


def build_sar_model(FDTD, CSX, tumor_radius=0.0, tumor_dist=16.0, f_sar=6.24e9):
    """
    Builds the metasurface antenna and breast phantom with frequency-domain SAR dump box.
    """
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(UNIT)

    # 1. Materials
    eps_sub = [SUBSTRATE_EPS_R] * 3
    kap_sub = [SUBSTRATE_KAPPA] * 3
    sub_mat = CSX.AddMaterial('f4bm', epsilon=eps_sub, kappa=kap_sub)
    copper  = CSX.AddMetal('copper')

    skin_prop  = TISSUE_PROPERTIES['skin']
    fat_prop   = TISSUE_PROPERTIES['fat']
    gland_prop = TISSUE_PROPERTIES['fibro_glandular']
    tumor_prop = TISSUE_PROPERTIES['tumor']

    skin_mat  = CSX.AddMaterial('skin',
                                epsilon=[skin_prop['eps_r']] * 3,
                                kappa=[skin_prop['sigma']] * 3)
    fat_mat   = CSX.AddMaterial('fat',
                                epsilon=[fat_prop['eps_r']] * 3,
                                kappa=[fat_prop['sigma']] * 3)
    gland_mat = CSX.AddMaterial('fibro_glandular',
                                epsilon=[gland_prop['eps_r']] * 3,
                                kappa=[gland_prop['sigma']] * 3)
    tumor_mat = CSX.AddMaterial('tumor',
                                epsilon=[tumor_prop['eps_r']] * 3,
                                kappa=[tumor_prop['sigma']] * 3)
    air_mat   = CSX.AddMaterial('air_cut', epsilon=[1.0]*3, kappa=[0.0]*3)

    # 2. Antenna
    sub_mat.AddBox([-BOARD_L_X/2, -BOARD_L_Y/2, 0.0],
                   [ BOARD_L_X/2,  BOARD_L_Y/2, H_TOTAL], priority=0)

    # CPW Feed & Slot
    copper.AddBox([-CPW_W3/2, -BOARD_L_Y/2, 0.0],
                  [ CPW_W3/2,  SLOT_S4/2,   0.0], priority=10)
    copper.AddBox([-BOARD_L_X/2,  SLOT_S4/2,   0.0],
                  [ BOARD_L_X/2,  BOARD_L_Y/2, 0.0], priority=10)
    copper.AddBox([-BOARD_L_X/2,          -BOARD_L_Y/2, 0.0],
                  [-(CPW_W3/2 + CPW_S3),  -SLOT_S4/2,   0.0], priority=10)
    copper.AddBox([ (CPW_W3/2 + CPW_S3),  -BOARD_L_Y/2, 0.0],
                  [ BOARD_L_X/2,          -SLOT_S4/2,   0.0], priority=10)

    stub_left_outer  = -(CPW_W3/2 + CPW_S3 + SLOT_W4 + SLOT_W5)
    stub_right_outer =  (CPW_W3/2 + CPW_S3 + SLOT_W4 + SLOT_W5)
    copper.AddBox([-BOARD_L_X/2,    -SLOT_S4/2, 0.0],
                  [ stub_left_outer, SLOT_S4/2, 0.0], priority=10)
    copper.AddBox([ stub_right_outer, -SLOT_S4/2, 0.0],
                  [ BOARD_L_X/2,       SLOT_S4/2, 0.0], priority=10)

    stub_left_inner  = -(CPW_W3/2 + CPW_S3 + SLOT_W4)
    stub_right_inner =  (CPW_W3/2 + CPW_S3 + SLOT_W4)
    copper.AddBox([stub_left_outer,  SLOT_S4/2, 0.0],
                  [stub_left_inner,  SLOT_S5/2, 0.0], priority=0)
    copper.AddBox([stub_left_outer, -SLOT_S5/2, 0.0],
                  [stub_left_inner, -SLOT_S4/2, 0.0], priority=0)

    # Middle layer strips & vias
    z_mid_bot = H_BOT
    z_mid_top = H_BOT + H_MID
    xc_arr = np.array([-1.5, -0.5, 0.5, 1.5]) * PERIOD_X
    yc_arr = np.array([-1.5, -0.5, 0.5, 1.5]) * PERIOD_Y

    for xc in xc_arr:
        for yc in yc_arr:
            y_u_lo = yc + MID_G2 / 2.0
            y_u_hi = y_u_lo + MID_W2
            y_d_hi = yc - MID_G2 / 2.0
            y_d_lo = y_d_hi - MID_W2
            x_s_lo = xc - MID_L2 / 2.0
            x_s_hi = xc + MID_L2 / 2.0
            for zm in [z_mid_bot, z_mid_top]:
                copper.AddBox([x_s_lo, y_u_lo, zm], [x_s_hi, y_u_hi, zm], priority=10)
                copper.AddBox([x_s_lo, y_d_lo, zm], [x_s_hi, y_d_hi, zm], priority=10)
            y_via_u = (y_u_lo + y_u_hi) / 2.0
            y_via_d = (y_d_lo + y_d_hi) / 2.0
            for dx in VIA_POS_X_OFFSETS:
                xv = xc + dx
                copper.AddCylinder([xv, y_via_u, z_mid_bot],
                                   [xv, y_via_u, z_mid_top],
                                   radius=VIA_DIAMETER / 2.0, priority=15)
                copper.AddCylinder([xv, y_via_d, z_mid_bot],
                                   [xv, y_via_d, z_mid_top],
                                   radius=VIA_DIAMETER / 2.0, priority=15)

    # Top patches
    z_top = H_TOTAL
    for xc in xc_arr:
        for yc in yc_arr:
            xp_lo = xc - TOP_L1 / 2.0
            xp_hi = xc + TOP_L1 / 2.0
            yp_lo = yc - TOP_W1 / 2.0
            yp_hi = yc + TOP_W1 / 2.0
            copper.AddBox([xp_lo, yp_lo, z_top], [xp_hi, yp_hi, z_top], priority=10)

    # 3. Phantom
    z_apex = z_top + SENSOR_TO_SKIN_GAP_D1
    z_center = z_apex + PHANTOM_R1_SKIN_OUTER
    center_phantom = [0.0, 0.0, z_center]

    skin_mat.AddSphere(center_phantom, radius=PHANTOM_R1_SKIN_OUTER, priority=20)
    fat_mat.AddSphere(center_phantom, radius=PHANTOM_R2_FAT_OUTER, priority=30)
    gland_mat.AddSphere(center_phantom, radius=PHANTOM_R3_GLAND_OUTER, priority=40)

    z_tumor = z_top + tumor_dist
    if tumor_radius > 0.0:
        tumor_mat.AddSphere([0.0, 0.0, z_tumor], radius=tumor_radius, priority=50)

    cut_margin = 80.0
    air_mat.AddBox([-cut_margin, -cut_margin, z_center],
                   [ cut_margin,  cut_margin, z_center + cut_margin], priority=60)

    # 4. SAR Dump Box (frequency domain, DumpType=20, DumpMode=2, FileType=1 for HDF5)
    dump_sar = CSX.AddDump('SAR')
    dump_sar.SetDumpType(20)
    dump_sar.SetDumpMode(2)
    dump_sar.SetFileType(1)
    dump_sar.SetFrequency(f_sar)
    dump_sar.AddBox([-PHANTOM_R1_SKIN_OUTER, -PHANTOM_R1_SKIN_OUTER, z_apex],
                    [ PHANTOM_R1_SKIN_OUTER,  PHANTOM_R1_SKIN_OUTER, z_center])

    # 5. Mesh
    res_coarse = 1.4
    x_key = [-cut_margin, -PHANTOM_R1_SKIN_OUTER, -PHANTOM_R2_FAT_OUTER, -PHANTOM_R3_GLAND_OUTER,
             -BOARD_L_X/2, stub_left_outer, stub_left_inner,
             -(CPW_W3/2 + CPW_S3), -CPW_W3/2, 0.0, CPW_W3/2, (CPW_W3/2 + CPW_S3),
             stub_right_inner, stub_right_outer, BOARD_L_X/2,
             PHANTOM_R3_GLAND_OUTER, PHANTOM_R2_FAT_OUTER, PHANTOM_R1_SKIN_OUTER, cut_margin]
    for xc in xc_arr:
        x_key.extend([xc - TOP_L1/2, xc + TOP_L1/2, xc - MID_L2/2, xc + MID_L2/2])
        for dx in VIA_POS_X_OFFSETS:
            x_key.append(xc + dx)
    if tumor_radius > 0.0:
        x_key.extend([-tumor_radius, 0.0, tumor_radius])
    mesh.AddLine('x', np.unique(x_key))
    mesh.SmoothMeshLines('x', res_coarse, ratio=1.4)

    y_key = [-cut_margin, -PHANTOM_R1_SKIN_OUTER, -PHANTOM_R2_FAT_OUTER, -PHANTOM_R3_GLAND_OUTER,
             -BOARD_L_Y/2, -14.0, -SLOT_S5/2, -SLOT_S4/2, 0.0, SLOT_S4/2, SLOT_S5/2, BOARD_L_Y/2,
             PHANTOM_R3_GLAND_OUTER, PHANTOM_R2_FAT_OUTER, PHANTOM_R1_SKIN_OUTER, cut_margin]
    for yc in yc_arr:
        y_u_lo = yc + MID_G2 / 2.0
        y_u_hi = y_u_lo + MID_W2
        y_d_hi = yc - MID_G2 / 2.0
        y_d_lo = y_d_hi - MID_W2
        y_key.extend([yc - TOP_W1/2, yc + TOP_W1/2, y_d_lo, y_d_hi, y_u_lo, y_u_hi])
    if tumor_radius > 0.0:
        y_key.extend([-tumor_radius, 0.0, tumor_radius])
    mesh.AddLine('y', np.unique(y_key))
    mesh.SmoothMeshLines('y', res_coarse, ratio=1.4)

    z_air_bot = -25.0
    z_air_top = z_center + 25.0
    z_key = [z_air_bot, -0.5, -0.2, -0.08, 0.0, 0.08, 0.2, 0.5,
             z_mid_bot - 0.1, z_mid_bot, z_mid_bot + 0.1,
             (z_mid_bot + z_mid_top) / 2.0,
             z_mid_top - 0.1, z_mid_top, z_mid_top + 0.1,
             z_top - 0.1, z_top,
             z_apex, z_apex + 5.0,
             z_center - PHANTOM_R3_GLAND_OUTER, z_center, z_air_top]
    if tumor_radius > 0.0:
        z_key.extend([z_tumor - tumor_radius, z_tumor, z_tumor + tumor_radius])
    mesh.AddLine('z', np.unique(z_key))
    mesh.SmoothMeshLines('z', res_coarse, ratio=1.4)

    port_len = 8.0
    port = FDTD.AddCPWPort(
        port_nr    = 1,
        metal_prop = copper,
        start      = [-CPW_W3/2, -BOARD_L_Y/2,            0.0],
        stop       = [ CPW_W3/2, -BOARD_L_Y/2 + port_len, 0.0],
        prop_dir   = 'y',
        exc_dir    = 'x',
        gap_width  = CPW_S3,
        excite     = 1.0,
        Feed_R     = 50.0,
        FeedShift  = 0.0,
        MeasPlaneShift = port_len / 2.0,
        priority   = 10,
    )
    return port, mesh, (z_apex, z_center, z_tumor)


def run_and_extract_sar(tumor_radius=0.0, tumor_dist=16.0, case_name="sar_baseline", f_sar=6.24e9):
    """
    Runs FDTD with SAR dump and decomposes peak local SAR per tissue layer.
    """
    sim_dir = os.path.join(PROJECT_DIR, 'sim', case_name)
    os.makedirs(sim_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"Running SAR Simulation: {case_name}")
    print(f"Tumor Radius = {tumor_radius:.1f} mm, Distance = {tumor_dist:.1f} mm, Freq = {f_sar/1e9:.3f} GHz")
    print(f"{'='*70}\n")

    FDTD = openEMS(NrTS=FDTD_NRTS, EndCriteria=FDTD_END_CRITERIA)
    FDTD.SetGaussExcite(F0, FC)
    FDTD.SetBoundaryCond(['PML_8'] * 6)

    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)

    port, mesh, (z_apex, z_center, z_tumor) = build_sar_model(FDTD, CSX, tumor_radius, tumor_dist, f_sar)

    t0 = time.time()
    FDTD.Run(sim_dir, cleanup=False)
    wall_time = time.time() - t0
    print(f"FDTD Finished in {wall_time/60.0:.2f} min ({wall_time:.1f} s)")

    # 1. Calc Port Power at f_sar
    f_arr = np.array([f_sar])
    port.CalcPort(sim_dir, f_arr)
    # Incident power and accepted power P_acc = P_inc - P_ref
    P_inc = float(np.abs(port.P_inc[0]))
    s11 = port.uf_ref[0] / port.uf_inc[0]
    P_acc = P_inc * (1.0 - np.abs(s11)**2)
    print(f"Port Power at {f_sar/1e9:.3f} GHz: P_inc = {P_inc:.4e} W, P_acc = {P_acc:.4e} W")

    # 2. Read SAR.h5
    sar_h5 = os.path.join(sim_dir, 'SAR.h5')
    if not os.path.exists(sar_h5):
        print(f"[Error] SAR.h5 not found in {sim_dir}")
        return None

    with h5py.File(sar_h5, 'r') as hf:
        # Voxel coordinates (mm)
        x_m = np.array(hf['Mesh/x'])
        y_m = np.array(hf['Mesh/y'])
        z_m = np.array(hf['Mesh/z'])
        # SAR raw grid (W/m^3 or W/kg unnormalized)
        sar_raw = np.array(hf['FieldData/FD/f0'])

    # 3. Spatial Tissue Decomposition
    # Grid cell centers
    X, Y, Z = np.meshgrid(x_m, y_m, z_m, indexing='ij')

    # Distance from hemispherical breast center (0, 0, z_center)
    R_sphere = np.sqrt(X**2 + Y**2 + (Z - z_center)**2)

    # Tissue masks:
    # Hemisphere: R_sphere <= 50.0 and Z <= z_center
    mask_in_breast = (R_sphere <= PHANTOM_R1_SKIN_OUTER) & (Z <= z_center)

    if tumor_radius > 0.0:
        R_tumor = np.sqrt(X**2 + Y**2 + (Z - z_tumor)**2)
        mask_tumor = (R_tumor <= tumor_radius)
    else:
        mask_tumor = np.zeros_like(mask_in_breast, dtype=bool)

    mask_skin  = mask_in_breast & (R_sphere > PHANTOM_R2_FAT_OUTER) & (~mask_tumor)
    mask_fat   = mask_in_breast & (R_sphere <= PHANTOM_R2_FAT_OUTER) & (R_sphere > PHANTOM_R3_GLAND_OUTER) & (~mask_tumor)
    mask_gland = mask_in_breast & (R_sphere <= PHANTOM_R3_GLAND_OUTER) & (~mask_tumor)

    # Normalize SAR to 1 W accepted input power:
    # openEMS dumps raw SAR unscaled by port power.
    # Scale factor = 1.0 W / P_acc
    scale_1W = 1.0 / max(1e-35, P_acc)
    sar_1W = sar_raw * scale_1W

    sar_skin_max  = float(np.max(sar_1W[mask_skin])) if np.any(mask_skin) else 0.0
    sar_fat_max   = float(np.max(sar_1W[mask_fat])) if np.any(mask_fat) else 0.0
    sar_gland_max = float(np.max(sar_1W[mask_gland])) if np.any(mask_gland) else 0.0
    sar_tumor_max = float(np.max(sar_1W[mask_tumor])) if (tumor_radius > 0 and np.any(mask_tumor)) else 0.0

    print(f"\nExtracted Peak Local SAR (Normalized to 1 W Input Power):")
    print(f"  Skin SAR:            {sar_skin_max:8.2f} W/kg")
    print(f"  Fat SAR:             {sar_fat_max:8.2f} W/kg")
    print(f"  Fibro-Glandular SAR: {sar_gland_max:8.2f} W/kg")
    if tumor_radius > 0.0:
        print(f"  Tumor SAR:           {sar_tumor_max:8.2f} W/kg")

    return {
        'case_name': case_name,
        'tumor_radius': tumor_radius,
        'tumor_dist': tumor_dist,
        'f_sar': f_sar,
        'sar_skin_max': sar_skin_max,
        'sar_fat_max': sar_fat_max,
        'sar_gland_max': sar_gland_max,
        'sar_tumor_max': sar_tumor_max,
        'wall_time': wall_time
    }


if __name__ == '__main__':
    # Default: Run Fig. 7 baseline (no tumor)
    run_and_extract_sar(tumor_radius=0.0, tumor_dist=16.0, case_name="sar_fig7_notumor")
