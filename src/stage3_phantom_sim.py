# -*- coding: utf-8 -*-
"""
Stage 3: Hemispherical Breast Phantom Simulation & Tumor Radius Sweep
====================================================================
Paper: Zhao et al., "Miniaturized and wideband metasurface antenna sensor for breast tumor detection",
       Sensors and Actuators A: Physical 394 (2025) 116973.

Simulates the metasurface antenna sensor coupled to a 3-layer hemispherical breast phantom:
  - Skin:            r1 = 50 mm, thickness = 5 mm,  eps_r = 36.0, sigma = 4.0 S/m
  - Fat:             r2 = 45 mm, thickness = 15 mm, eps_r = 9.0,  sigma = 0.4 S/m
  - Fibro-glandular: r3 = 30 mm, core radius,      eps_r = 13.0, sigma = 0.45 S/m
  - Tumor:           r in [0, 3, 5, 10] mm,         eps_r = 50.0, sigma = 4.0 S/m
  - Sensor-to-skin apex gap: d1 = 1.0 mm
  - Default tumor center distance from sensor top: d = 16.0 mm (z_tumor = 4.5 + d = 20.5 mm)

Recreates:
  - Fig. 9: Simulated reflection coefficients for tumors with different radii (0, 3, 5, 10 mm)
  - Resonant frequency shifts and bandwidth comparison with Fig. 17 and Table 6.
"""

import os, sys, time, argparse
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from CSXCAD  import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

# Paths
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
    SENSOR_TO_SKIN_GAP_D1, TUMOR_DIST_DEFAULT, TISSUE_PROPERTIES,
    FDTD_NRTS, FDTD_END_CRITERIA, NUM_THREADS
)

RESULTS_PATH = os.path.join(PROJECT_DIR, 'results')
os.makedirs(RESULTS_PATH, exist_ok=True)


def build_phantom_model(FDTD, CSX, tumor_radius=0.0, tumor_dist=16.0, tumor_pos_xy=(0.0, 0.0)):
    """
    Builds the metasurface antenna and the 3-layer hemispherical breast phantom with optional tumor.
    """
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(UNIT)

    # =========================================================================
    # 1. Materials
    # =========================================================================
    # Substrate & Copper
    eps_sub = [SUBSTRATE_EPS_R] * 3
    kap_sub = [SUBSTRATE_KAPPA] * 3
    sub_mat = CSX.AddMaterial('f4bm', epsilon=eps_sub, kappa=kap_sub)
    copper  = CSX.AddMetal('copper')

    # Biological tissues (3D isotropic permittivity & conductivity)
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

    # Vacuum / Air property for chest cut plane
    air_mat   = CSX.AddMaterial('air_cut', epsilon=[1.0]*3, kappa=[0.0]*3)

    # =========================================================================
    # 2. Antenna Stackup & Geometry (z in [0.0, 4.5 mm])
    # =========================================================================
    # Substrate box
    sub_mat.AddBox([-BOARD_L_X/2, -BOARD_L_Y/2, 0.0],
                   [ BOARD_L_X/2,  BOARD_L_Y/2, H_TOTAL], priority=0)

    # Bottom Metallization (z = 0): CPW Feed & Transverse Coupling Slot
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

    # Middle Metasurface: 4x4 cells at z = 2.0 mm and z = 4.0 mm with 96 vias
    z_mid_bot = H_BOT          # 2.0 mm
    z_mid_top = H_BOT + H_MID  # 4.0 mm

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

    # Top Metasurface (z = 4.5 mm): 4x4 Rectangular Patches
    z_top = H_TOTAL  # 4.5 mm
    for xc in xc_arr:
        for yc in yc_arr:
            xp_lo = xc - TOP_L1 / 2.0
            xp_hi = xc + TOP_L1 / 2.0
            yp_lo = yc - TOP_W1 / 2.0
            yp_hi = yc + TOP_W1 / 2.0
            copper.AddBox([xp_lo, yp_lo, z_top], [xp_hi, yp_hi, z_top], priority=10)

    # =========================================================================
    # 3. Hemispherical Breast Phantom Geometry
    # =========================================================================
    # Coordinate system:
    # Sensor top: z = 4.5 mm
    # Gap d1 = 1.0 mm -> skin apex touches z = 4.5 + 1.0 = 5.5 mm
    # Outer radius r1 = 50.0 mm -> sphere center is at (0, 0, 5.5 + 50.0) = (0, 0, 55.5 mm)
    z_apex = z_top + SENSOR_TO_SKIN_GAP_D1          # 5.5 mm
    z_center = z_apex + PHANTOM_R1_SKIN_OUTER       # 55.5 mm
    center_phantom = [0.0, 0.0, z_center]

    # Skin sphere (outer radius 50 mm, priority 20)
    skin_mat.AddSphere(center_phantom, radius=PHANTOM_R1_SKIN_OUTER, priority=20)

    # Fat sphere (outer radius 45 mm, priority 30, overrides skin in interior)
    fat_mat.AddSphere(center_phantom, radius=PHANTOM_R2_FAT_OUTER, priority=30)

    # Fibro-glandular core (outer radius 30 mm, priority 40, overrides fat in center)
    gland_mat.AddSphere(center_phantom, radius=PHANTOM_R3_GLAND_OUTER, priority=40)

    # Tumor sphere (priority 50, overrides surrounding tissue)
    z_tumor = z_top + tumor_dist
    x_tumor = tumor_pos_xy[0]
    y_tumor = tumor_pos_xy[1]
    if tumor_radius > 0.0:
        tumor_mat.AddSphere([x_tumor, y_tumor, z_tumor], radius=tumor_radius, priority=50)

    # Chest wall flat cut: all space above z = z_center (z >= 55.5 mm) is cut away (air, priority 60)
    # Covering full transverse extent well past phantom
    cut_margin = 80.0
    air_mat.AddBox([-cut_margin, -cut_margin, z_center],
                   [ cut_margin,  cut_margin, z_center + cut_margin], priority=60)

    # =========================================================================
    # 4. Mesh Generation
    # =========================================================================
    res_coarse = 1.4   # mm
    res_phantom = 1.0  # mm inside tissue

    # X-mesh lines
    x_key = [
        -cut_margin,
        -PHANTOM_R1_SKIN_OUTER, -PHANTOM_R2_FAT_OUTER, -PHANTOM_R3_GLAND_OUTER,
        -BOARD_L_X/2, stub_left_outer, stub_left_inner,
        -(CPW_W3/2 + CPW_S3), -CPW_W3/2, 0.0, CPW_W3/2, (CPW_W3/2 + CPW_S3),
        stub_right_inner, stub_right_outer, BOARD_L_X/2,
        PHANTOM_R3_GLAND_OUTER, PHANTOM_R2_FAT_OUTER, PHANTOM_R1_SKIN_OUTER,
        cut_margin
    ]
    for xc in xc_arr:
        x_key.extend([xc - TOP_L1/2, xc + TOP_L1/2, xc - MID_L2/2, xc + MID_L2/2])
        for dx in VIA_POS_X_OFFSETS:
            x_key.append(xc + dx)
    if tumor_radius > 0.0:
        x_key.extend([x_tumor - tumor_radius, x_tumor, x_tumor + tumor_radius])

    mesh.AddLine('x', np.unique(x_key))
    mesh.SmoothMeshLines('x', res_coarse, ratio=1.4)

    # Y-mesh lines
    y_key = [
        -cut_margin,
        -PHANTOM_R1_SKIN_OUTER, -PHANTOM_R2_FAT_OUTER, -PHANTOM_R3_GLAND_OUTER,
        -BOARD_L_Y/2, -14.0, -SLOT_S5/2, -SLOT_S4/2, 0.0, SLOT_S4/2, SLOT_S5/2, BOARD_L_Y/2,
        PHANTOM_R3_GLAND_OUTER, PHANTOM_R2_FAT_OUTER, PHANTOM_R1_SKIN_OUTER,
        cut_margin
    ]
    for yc in yc_arr:
        y_u_lo = yc + MID_G2 / 2.0
        y_u_hi = y_u_lo + MID_W2
        y_d_hi = yc - MID_G2 / 2.0
        y_d_lo = y_d_hi - MID_W2
        y_key.extend([
            yc - TOP_W1/2, yc + TOP_W1/2,
            y_d_lo, y_d_hi, y_u_lo, y_u_hi,
            (y_u_lo + y_u_hi)/2, (y_d_lo + y_d_hi)/2
        ])
    if tumor_radius > 0.0:
        y_key.extend([y_tumor - tumor_radius, y_tumor, y_tumor + tumor_radius])

    mesh.AddLine('y', np.unique(y_key))
    mesh.SmoothMeshLines('y', res_coarse, ratio=1.4)

    # Z-mesh lines
    z_air_bot = -25.0
    z_air_top = z_center + 25.0
    z_key = [
        z_air_bot,
        -0.5, -0.2, -0.08, 0.0, 0.08, 0.2, 0.5,
        z_mid_bot - 0.1, z_mid_bot, z_mid_bot + 0.1,
        (z_mid_bot + z_mid_top) / 2.0,
        z_mid_top - 0.1, z_mid_top, z_mid_top + 0.1,
        z_top - 0.1, z_top,
        z_apex, z_apex + 5.0,  # skin thickness
        z_center - PHANTOM_R3_GLAND_OUTER,  # 25.5 mm (gland bottom)
        z_center,                           # 55.5 mm (chest wall)
        z_air_top
    ]
    if tumor_radius > 0.0:
        z_key.extend([z_tumor - tumor_radius, z_tumor, z_tumor + tumor_radius])

    mesh.AddLine('z', np.unique(z_key))
    mesh.SmoothMeshLines('z', res_coarse, ratio=1.4)

    # =========================================================================
    # 5. CPW Excitation Port
    # =========================================================================
    port_len = 8.0  # mm
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

    return port, mesh


def run_single_simulation(tumor_radius=0.0, tumor_dist=16.0, tumor_pos_xy=(0.0, 0.0), case_name=None):
    """
    Runs openEMS simulation for a single breast phantom configuration and returns S11.
    """
    if case_name is None:
        case_name = f"r{tumor_radius:.1f}mm_d{tumor_dist:.1f}mm"

    sim_dir = os.path.join(PROJECT_DIR, 'sim', f'stage3_{case_name}')
    os.makedirs(sim_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"Running Stage 3 Case: {case_name}")
    print(f"Tumor Radius = {tumor_radius:.1f} mm, Distance d = {tumor_dist:.1f} mm, Position = {tumor_pos_xy}")
    print(f"Sim dir: {sim_dir}")
    print(f"{'='*70}\n")

    FDTD = openEMS(NrTS=FDTD_NRTS, EndCriteria=FDTD_END_CRITERIA)
    FDTD.SetGaussExcite(F0, FC)
    FDTD.SetBoundaryCond(['PML_8'] * 6)

    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)

    port, mesh = build_phantom_model(FDTD, CSX, tumor_radius, tumor_dist, tumor_pos_xy)

    nx = len(mesh.GetLines('x'))
    ny = len(mesh.GetLines('y'))
    nz = len(mesh.GetLines('z'))
    print(f"FDTD Grid: {nx} x {ny} x {nz} = {(nx-1)*(ny-1)*(nz-1):,} cells")

    # Write CSX geometry XML
    csx_file = os.path.join(sim_dir, f'{case_name}.xml')
    CSX.Write2XML(csx_file)

    # Run FDTD
    t0 = time.time()
    FDTD.Run(sim_dir, cleanup=True)
    wall_time = time.time() - t0
    print(f"\n[FDTD Complete] Wall time: {wall_time/60.0:.2f} min ({wall_time:.1f} s)")

    # Post-process Port S11
    f_arr = np.linspace(F_MIN, F_MAX, 801)
    port.CalcPort(sim_dir, f_arr)

    s11 = port.uf_ref / port.uf_inc
    s11_db = 20.0 * np.log10(np.abs(s11))

    # Save to CSV
    csv_file = os.path.join(RESULTS_PATH, f'stage3_s11_{case_name}.csv')
    data_out = np.column_stack([
        f_arr / 1e9,
        s11_db,
        np.abs(s11),
        np.angle(s11, deg=True),
        np.real(port.uf_inc),
        np.real(port.uf_ref),
        np.real(port.if_inc),
        np.real(port.if_ref)
    ])
    header = 'freq_GHz,S11_dB,S11_mag,S11_deg,uf_inc_re,uf_ref_re,if_inc_re,if_ref_re'
    np.savetxt(csv_file, data_out, delimiter=',', header=header, comments='')
    print(f"Saved S11 data to: {csv_file}")

    # Save S1P Touchstone
    s1p_file = os.path.join(RESULTS_PATH, f'stage3_{case_name}.s1p')
    with open(s1p_file, 'w') as f:
        f.write('# GHz S DB R 50\n')
        f.write(f'! openEMS Stage 3 Simulation: {case_name}\n')
        for freq, s_db, s_ang in zip(f_arr / 1e9, s11_db, np.angle(s11, deg=True)):
            f.write(f'{freq:10.5f} {s_db:12.5f} {s_ang:12.5f}\n')
    print(f"Saved Touchstone to: {s1p_file}")

    # Metrics
    min_idx = np.argmin(s11_db)
    f_res = f_arr[min_idx] / 1e9
    min_s11 = s11_db[min_idx]
    below_10db = f_arr[s11_db <= -10.0] / 1e9
    bw_str = f"{below_10db[0]:.2f} - {below_10db[-1]:.2f} GHz" if len(below_10db) > 0 else "None"

    print(f"Results for {case_name}:")
    print(f"  Resonant Frequency: {f_res:.3f} GHz (Min S11 = {min_s11:.2f} dB)")
    print(f"  -10 dB Bandwidth:   {bw_str}")

    return {
        'case_name': case_name,
        'f_arr': f_arr,
        's11_db': s11_db,
        'f_res': f_res,
        'min_s11': min_s11,
        'below_10db': below_10db,
        'wall_time': wall_time
    }


def run_tumor_radius_sweep():
    """
    Runs the 4-case Tumor Radius Sweep: r = 0, 3, 5, 10 mm at d = 16 mm.
    """
    radii = [0.0, 3.0, 5.0, 10.0]
    results = {}

    for r in radii:
        name = f"r{r:.1f}mm"
        # Check if already simulated to avoid unnecessary re-runs
        csv_file = os.path.join(RESULTS_PATH, f'stage3_s11_{name}.csv')
        if os.path.exists(csv_file):
            print(f"\n[Found existing results] Loading {csv_file}")
            data = np.loadtxt(csv_file, delimiter=',', skiprows=1)
            f_arr = data[:, 0] * 1e9
            s11_db = data[:, 1]
            min_idx = np.argmin(s11_db)
            f_res = f_arr[min_idx] / 1e9
            min_s11 = s11_db[min_idx]
            below_10db = f_arr[s11_db <= -10.0] / 1e9
            results[r] = {
                'case_name': name,
                'f_arr': f_arr,
                's11_db': s11_db,
                'f_res': f_res,
                'min_s11': min_s11,
                'below_10db': below_10db,
                'wall_time': 0.0
            }
        else:
            res = run_single_simulation(tumor_radius=r, tumor_dist=16.0, case_name=name)
            results[r] = res

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stage 3: Breast Phantom Simulation")
    parser.add_argument('--radius', type=float, default=None, help="Tumor radius in mm (e.g. 0.0, 3.0, 5.0, 10.0)")
    parser.add_argument('--dist', type=float, default=16.0, help="Tumor distance d in mm (default: 16.0)")
    parser.add_argument('--sweep', action='store_true', help="Run full tumor radius sweep (0, 3, 5, 10 mm)")
    args = parser.parse_args()

    if args.sweep:
        run_tumor_radius_sweep()
    elif args.radius is not None:
        name = f"r{args.radius:.1f}mm"
        run_single_simulation(tumor_radius=args.radius, tumor_dist=args.dist, case_name=name)
    else:
        # Default: run tumor-free case first
        print("No specific argument passed. Running tumor-free case (r = 0.0 mm)...")
        run_single_simulation(tumor_radius=0.0, tumor_dist=16.0, case_name="r0.0mm")
