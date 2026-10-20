# -*- coding: utf-8 -*-
"""
Stage 1: Free-Space Metasurface Antenna Sensor
================================================
Implements and simulates the full free-space antenna sensor from Zhao et al. (2025):
  - Stackup: 3 F4BM layers (Total h = 4.5 mm, Board = 44 x 44 mm)
    * Bottom layer: h2 = 2.0 mm (z in [0, 2.0])
    * Middle layer: h0 = 2.0 mm (z in [2.0, 4.0])
    * Top layer:    h1 = 0.5 mm (z in [4.0, 4.5])
  - Ground plane (z = 0):
    * CPW feed (w3 = 3.0 mm, s3 = 0.2 mm) from y = -22 to y = 0.5 mm
    * Transverse coupling slot (s4 = 1.0 mm, w4 = 9.6 mm per branch)
    * Capacitive end stubs (w5 = 2.0 mm, s5 = 2.0 mm)
  - Middle metasurface (z = 2.0 mm and z = 4.0 mm):
    * 4x4 cells (Px = 8.5 mm, Py = 6.6 mm)
    * Two horizontal strips per cell (l2 = 6.0 mm, w2 = 1.6 mm, g2 = 0.8 mm)
    * 3 vias per strip (96 vias total, d = 0.35 mm) connecting z = 2.0 to 4.0 mm
  - Top metasurface (z = 4.5 mm):
    * 4x4 rectangular patch array (l1 = 7.8 mm, w1 = 5.6 mm)
  - NF2FF near-field to far-field transform for gain and radiation patterns.
"""

import os, sys, time
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
    UNIT, F0, FC, F_MIN, F_MAX, F_PATTERN,
    SUBSTRATE_EPS_R, SUBSTRATE_KAPPA,
    BOARD_L_X, BOARD_L_Y,
    H_BOT, H_MID, H_TOP, H_TOTAL,
    TOP_N_X, TOP_N_Y, TOP_L1, TOP_W1,
    PERIOD_X, PERIOD_Y,
    MID_L2, MID_W2, MID_G2,
    VIA_DIAMETER, VIA_POS_X_OFFSETS,
    CPW_W3, CPW_S3, CPW_L3,
    SLOT_S4, SLOT_W4, SLOT_S5, SLOT_W5,
    FDTD_NRTS, FDTD_END_CRITERIA,
)

SIM_PATH     = os.path.join(PROJECT_DIR, 'sim', 'stage1_antenna')
RESULTS_PATH = os.path.join(PROJECT_DIR, 'results')
os.makedirs(RESULTS_PATH, exist_ok=True)

def build_antenna(FDTD, CSX):
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(UNIT)

    # -------------------------------------------------------------------------
    # Materials
    # -------------------------------------------------------------------------
    eps_3d = [SUBSTRATE_EPS_R, SUBSTRATE_EPS_R, SUBSTRATE_EPS_R]
    kap_3d = [SUBSTRATE_KAPPA, SUBSTRATE_KAPPA, SUBSTRATE_KAPPA]
    sub_mat = CSX.AddMaterial('f4bm', epsilon=eps_3d, kappa=kap_3d)
    copper  = CSX.AddMetal('copper')

    # -------------------------------------------------------------------------
    # Substrate stackup: 3 layers from z = 0 to z = 4.5 mm
    # -------------------------------------------------------------------------
    sub_mat.AddBox([-BOARD_L_X/2, -BOARD_L_Y/2, 0.0],
                   [ BOARD_L_X/2,  BOARD_L_Y/2, H_TOTAL], priority=0)

    # -------------------------------------------------------------------------
    # Bottom Metallization (z = 0): CPW Feed & Transverse Coupling Slot
    # -------------------------------------------------------------------------
    # Feed line center strip: x in [-1.5, 1.5], y from -22.0 to +0.5 (continuous into upper ground)
    copper.AddBox([-CPW_W3/2, -BOARD_L_Y/2, 0.0],
                  [ CPW_W3/2,  SLOT_S4/2,   0.0], priority=10)

    # Upper solid ground: y in [SLOT_S4/2, BOARD_L_Y/2] = [0.5, 22.0]
    copper.AddBox([-BOARD_L_X/2,  SLOT_S4/2,   0.0],
                  [ BOARD_L_X/2,  BOARD_L_Y/2, 0.0], priority=10)

    # Lower ground planes flanking CPW feed: y in [-22.0, -SLOT_S4/2]
    # Left:  x in [-22.0, -(CPW_W3/2 + CPW_S3)] = [-22.0, -1.7]
    copper.AddBox([-BOARD_L_X/2,          -BOARD_L_Y/2, 0.0],
                  [-(CPW_W3/2 + CPW_S3),  -SLOT_S4/2,   0.0], priority=10)
    # Right: x in [+(CPW_W3/2 + CPW_S3), +22.0] = [1.7, 22.0]
    copper.AddBox([ (CPW_W3/2 + CPW_S3),  -BOARD_L_Y/2, 0.0],
                  [ BOARD_L_X/2,          -SLOT_S4/2,   0.0], priority=10)

    # Copper flanking transverse slot branches (y in [-0.5, 0.5]):
    # Outer ground beyond the end stubs:
    # Left stub ends at x = -(CPW_W3/2 + CPW_S3 + SLOT_W4 + SLOT_W5) = -(1.7 + 9.6 + 2.0) = -13.3 mm
    stub_left_outer  = -(CPW_W3/2 + CPW_S3 + SLOT_W4 + SLOT_W5)
    stub_right_outer =  (CPW_W3/2 + CPW_S3 + SLOT_W4 + SLOT_W5)
    copper.AddBox([-BOARD_L_X/2,    -SLOT_S4/2, 0.0],
                  [ stub_left_outer, SLOT_S4/2, 0.0], priority=10)
    copper.AddBox([ stub_right_outer, -SLOT_S4/2, 0.0],
                  [ BOARD_L_X/2,       SLOT_S4/2, 0.0], priority=10)

    # Around the stubs (size w5 x s5 = 2.0 x 2.0 mm, y in [-1.0, 1.0]):
    # Copper above stub: y in [SLOT_S4/2, SLOT_S5/2] = [0.5, 1.0] outside stub region
    stub_left_inner  = -(CPW_W3/2 + CPW_S3 + SLOT_W4)  # -11.3 mm
    stub_right_inner =  (CPW_W3/2 + CPW_S3 + SLOT_W4)  # +11.3 mm
    copper.AddBox([stub_left_outer,  SLOT_S4/2, 0.0],
                  [stub_left_inner,  SLOT_S5/2, 0.0], priority=0) # empty / vacuum
    copper.AddBox([stub_left_outer, -SLOT_S5/2, 0.0],
                  [stub_left_inner, -SLOT_S4/2, 0.0], priority=0)

    # -------------------------------------------------------------------------
    # Middle Metasurface: 4x4 cells at z = 2.0 mm and z = 4.0 mm with 96 vias
    # -------------------------------------------------------------------------
    z_mid_bot = H_BOT          # 2.0 mm
    z_mid_top = H_BOT + H_MID  # 4.0 mm

    # Cell center coordinates
    xc_arr = np.array([-1.5, -0.5, 0.5, 1.5]) * PERIOD_X  # [-12.75, -4.25, 4.25, 12.75]
    yc_arr = np.array([-1.5, -0.5, 0.5, 1.5]) * PERIOD_Y  # [-9.9,   -3.3,  3.3,  9.9]

    for xc in xc_arr:
        for yc in yc_arr:
            # Strip 1 (upper strip in cell): y in [yc + g2/2, yc + g2/2 + w2]
            y_u_lo = yc + MID_G2 / 2.0
            y_u_hi = y_u_lo + MID_W2
            # Strip 2 (lower strip in cell): y in [yc - g2/2 - w2, yc - g2/2]
            y_d_hi = yc - MID_G2 / 2.0
            y_d_lo = y_d_hi - MID_W2

            x_s_lo = xc - MID_L2 / 2.0
            x_s_hi = xc + MID_L2 / 2.0

            # Copper strips on both bottom and top of middle substrate
            for zm in [z_mid_bot, z_mid_top]:
                copper.AddBox([x_s_lo, y_u_lo, zm], [x_s_hi, y_u_hi, zm], priority=10)
                copper.AddBox([x_s_lo, y_d_lo, zm], [x_s_hi, y_d_hi, zm], priority=10)

            # 3 vias per strip connecting z_mid_bot to z_mid_top
            y_via_u = (y_u_lo + y_u_hi) / 2.0
            y_via_d = (y_d_lo + y_d_hi) / 2.0
            for dx in VIA_POS_X_OFFSETS:
                xv = xc + dx
                # Cylindrical metallic vias
                copper.AddCylinder([xv, y_via_u, z_mid_bot],
                                   [xv, y_via_u, z_mid_top],
                                   radius=VIA_DIAMETER / 2.0, priority=15)
                copper.AddCylinder([xv, y_via_d, z_mid_bot],
                                   [xv, y_via_d, z_mid_top],
                                   radius=VIA_DIAMETER / 2.0, priority=15)

    # -------------------------------------------------------------------------
    # Top Metasurface (z = 4.5 mm): 4x4 Rectangular Patches
    # -------------------------------------------------------------------------
    z_top = H_TOTAL  # 4.5 mm
    for xc in xc_arr:
        for yc in yc_arr:
            xp_lo = xc - TOP_L1 / 2.0
            xp_hi = xc + TOP_L1 / 2.0
            yp_lo = yc - TOP_W1 / 2.0
            yp_hi = yc + TOP_W1 / 2.0
            copper.AddBox([xp_lo, yp_lo, z_top], [xp_hi, yp_hi, z_top], priority=10)

    # -------------------------------------------------------------------------
    # Mesh Generation
    # -------------------------------------------------------------------------
    air_pad_xy = 30.0  # mm
    air_pad_z  = 35.0  # mm
    res_coarse = 1.3   # mm (~lambda_min/20 in air)
    res_edge   = 0.08  # mm across CPW gap

    # X-mesh lines
    x_key = [
        -BOARD_L_X/2 - air_pad_xy, -BOARD_L_X/2,
        stub_left_outer, stub_left_inner,
        -(CPW_W3/2 + CPW_S3), -CPW_W3/2, 0.0, CPW_W3/2, (CPW_W3/2 + CPW_S3),
        stub_right_inner, stub_right_outer,
        BOARD_L_X/2, BOARD_L_X/2 + air_pad_xy
    ]
    # Add patch and middle strip edges along x
    for xc in xc_arr:
        x_key.extend([xc - TOP_L1/2, xc + TOP_L1/2, xc - MID_L2/2, xc + MID_L2/2])
        for dx in VIA_POS_X_OFFSETS:
            x_key.append(xc + dx)

    mesh.AddLine('x', np.unique(x_key))
    mesh.SmoothMeshLines('x', res_coarse, ratio=1.4)

    # Y-mesh lines
    y_key = [
        -BOARD_L_Y/2 - air_pad_xy, -BOARD_L_Y/2,
        -14.0,  # port end
        -SLOT_S5/2, -SLOT_S4/2, 0.0, SLOT_S4/2, SLOT_S5/2,
        BOARD_L_Y/2, BOARD_L_Y/2 + air_pad_xy
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
    mesh.AddLine('y', np.unique(y_key))
    mesh.SmoothMeshLines('y', res_coarse, ratio=1.4)

    # Z-mesh lines
    z_key = [
        -air_pad_z,
        -0.5, -0.2, -0.08, 0.0, 0.08, 0.2, 0.5,
        z_mid_bot - 0.1, z_mid_bot, z_mid_bot + 0.1,
        (z_mid_bot + z_mid_top) / 2.0,
        z_mid_top - 0.1, z_mid_top, z_mid_top + 0.1,
        z_top - 0.1, z_top, z_top + 0.1,
        z_top + air_pad_z
    ]
    mesh.AddLine('z', np.unique(z_key))
    mesh.SmoothMeshLines('z', res_coarse, ratio=1.4)

    # -------------------------------------------------------------------------
    # CPW Excitation Port at board bottom edge
    # -------------------------------------------------------------------------
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
        MeasPlaneShift = port_len / 2.0,  # mid-port probe
        priority   = 10,
    )

    # -------------------------------------------------------------------------
    # NF2FF Box for Far-Field Realized Gain and Radiation Patterns
    # -------------------------------------------------------------------------
    nf2ff = FDTD.CreateNF2FFBox(
        opt_resolution=[res_coarse, res_coarse, res_coarse]
    )

    return port, nf2ff, mesh

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("Stage 1: Free-Space Metasurface Antenna Sensor (Zhao et al.)")
    print(f"{'='*60}\n")

    FDTD = openEMS(NrTS=FDTD_NRTS, EndCriteria=FDTD_END_CRITERIA)
    FDTD.SetGaussExcite(F0, FC)
    FDTD.SetBoundaryCond(['PML_8'] * 6)

    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)

    port, nf2ff, mesh = build_antenna(FDTD, CSX)

    nx = len(mesh.GetLines('x'))
    ny = len(mesh.GetLines('y'))
    nz = len(mesh.GetLines('z'))
    ncells = (nx - 1) * (ny - 1) * (nz - 1)
    print(f"Mesh: {nx} x {ny} x {nz} = {ncells:,} cells")

    os.makedirs(SIM_PATH, exist_ok=True)
    xml_path = os.path.join(SIM_PATH, 'stage1.xml')
    CSX.Write2XML(xml_path)
    print(f"Geometry XML written -> {xml_path}")

    # -------------------------------------------------------------------------
    # Execute FDTD Simulation
    # -------------------------------------------------------------------------
    print("\nStarting FDTD Engine...")
    t0 = time.perf_counter()
    FDTD.Run(SIM_PATH, cleanup=True)
    wall_time = time.perf_counter() - t0
    print(f"FDTD Simulation complete in {wall_time:.1f} s ({wall_time/60:.2f} min)\n")

    # -------------------------------------------------------------------------
    # Post-Processing: Port S11 & Input Impedance
    # -------------------------------------------------------------------------
    f = np.linspace(F_MIN, F_MAX, 801)
    port.CalcPort(SIM_PATH, f, ref_impedance=50.0)

    s11    = port.uf_ref / port.uf_inc
    s11_dB = 20.0 * np.log10(np.abs(s11))
    Zin    = port.uf_tot / port.if_tot

    # Save S11 CSV
    csv_s11 = os.path.join(RESULTS_PATH, 'stage1_s11.csv')
    np.savetxt(csv_s11,
               np.column_stack([f / 1e9, s11_dB, np.real(Zin), np.imag(Zin)]),
               delimiter=',',
               header='f_GHz,S11_dB,Re_Zin_Ohm,Im_Zin_Ohm',
               comments='')
    print(f"S11 CSV saved -> {csv_s11}")

    # Save Touchstone .s1p
    s1p_path = os.path.join(RESULTS_PATH, 'stage1.s1p')
    with open(s1p_path, 'w') as fh:
        fh.write('! Stage 1 Free-Space Metasurface Antenna Sensor - openEMS\n')
        fh.write('# GHz S DB R 50\n')
        for i in range(len(f)):
            fh.write(f"{f[i]/1e9:.6f}  {s11_dB[i]:.4f}  {np.angle(s11[i], deg=True):.4f}\n")
    print(f"Touchstone .s1p saved -> {s1p_path}")

    # -------------------------------------------------------------------------
    # Far-Field Post-Processing: Realized Gain vs Frequency
    # -------------------------------------------------------------------------
    print("\nCalculating Far-Field Realized Gain...")
    f_gain = np.linspace(4.0e9, 10.0e9, 31)
    gain_broadside = []

    for fg in f_gain:
        nf2ff_res = nf2ff.CalcNF2FF(SIM_PATH, fg, 0.0, 0.0)  # theta = 0, phi = 0 (broadside)
        P_in = port.P_inc[np.argmin(np.abs(f - fg))]
        # Realized gain = 4*pi*U_max / P_inc
        # In openEMS, E_norm{theta, phi} gives r*E, radiation intensity U = 0.5 * |rE|^2 / eta0
        E_theta = nf2ff_res.E_theta[0][0]
        E_phi   = nf2ff_res.E_phi[0][0]
        U = 0.5 * (np.abs(E_theta)**2 + np.abs(E_phi)**2) / 376.73
        realized_gain_lin = 4.0 * np.pi * U / max(1e-12, P_in)
        gain_dBi = 10.0 * np.log10(max(1e-6, realized_gain_lin))
        gain_broadside.append(gain_dBi)

    gain_broadside = np.array(gain_broadside)
    csv_gain = os.path.join(RESULTS_PATH, 'stage1_gain.csv')
    np.savetxt(csv_gain,
               np.column_stack([f_gain / 1e9, gain_broadside]),
               delimiter=',',
               header='f_GHz,Realized_Gain_dBi',
               comments='')
    print(f"Gain CSV saved -> {csv_gain}")

    # -------------------------------------------------------------------------
    # Far-Field 2D Radiation Patterns at Paper Frequencies
    # -------------------------------------------------------------------------
    print("\nCalculating 2D Radiation Patterns at Fig. 13 frequencies...")
    theta_deg = np.linspace(-180.0, 180.0, 361)
    patterns = {}

    for fp in F_PATTERN:
        f_ghz = fp / 1e9
        P_in = port.P_inc[np.argmin(np.abs(f - fp))]

        # E-plane: phi = 90 deg (y-z plane), theta sweep
        nf_E = nf2ff.CalcNF2FF(SIM_PATH, fp, theta_deg, 90.0)
        U_E = 0.5 * (np.abs(nf_E.E_theta[0])**2 + np.abs(nf_E.E_phi[0])**2) / 376.73
        gain_E = 10.0 * np.log10(np.maximum(1e-6, 4.0 * np.pi * U_E / max(1e-12, P_in)))

        # H-plane: phi = 0 deg (x-z plane), theta sweep
        nf_H = nf2ff.CalcNF2FF(SIM_PATH, fp, theta_deg, 0.0)
        U_H = 0.5 * (np.abs(nf_H.E_theta[0])**2 + np.abs(nf_H.E_phi[0])**2) / 376.73
        gain_H = 10.0 * np.log10(np.maximum(1e-6, 4.0 * np.pi * U_H / max(1e-12, P_in)))

        patterns[f_ghz] = {'theta': theta_deg, 'gain_E': gain_E, 'gain_H': gain_H}

        csv_pat = os.path.join(RESULTS_PATH, f'stage1_pattern_{f_ghz:.2f}GHz.csv')
        np.savetxt(csv_pat,
                   np.column_stack([theta_deg, gain_E, gain_H]),
                   delimiter=',',
                   header='theta_deg,Gain_E_plane_dBi,Gain_H_plane_dBi',
                   comments='')

    # -------------------------------------------------------------------------
    # Plots
    # -------------------------------------------------------------------------
    # 1. S11 Plot
    fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), tight_layout=True)
    ax1.plot(f / 1e9, s11_dB, 'b-', lw=2, label='openEMS FDTD (Stage 1)')
    ax1.axhline(-10, color='r', ls='--', alpha=0.7, label='-10 dB threshold')
    ax1.set_xlabel('Frequency (GHz)', fontsize=11)
    ax1.set_ylabel('|S₁₁| (dB)', fontsize=11)
    ax1.set_title('Free-Space Metasurface Antenna Sensor — Return Loss |S₁₁| (Zhao et al. Fig. 11)', fontsize=12)
    ax1.set_xlim([3.0, 11.0])
    ax1.set_ylim([-35, 2])
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower left')

    ax2.plot(f / 1e9, np.real(Zin), 'b-', lw=2, label='Re{Z_in}')
    ax2.plot(f / 1e9, np.imag(Zin), 'r--', lw=2, label='Im{Z_in}')
    ax2.axhline(50, color='gray', ls=':', alpha=0.5, label='50 Ω')
    ax2.set_xlabel('Frequency (GHz)', fontsize=11)
    ax2.set_ylabel('Input Impedance (Ω)', fontsize=11)
    ax2.set_title('Input Impedance Z_in vs Frequency', fontsize=12)
    ax2.set_xlim([3.0, 11.0])
    ax2.set_ylim([-50, 150])
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    fig1.savefig(os.path.join(RESULTS_PATH, 'stage1_s11.png'), dpi=150)
    plt.close(fig1)

    # 2. Realized Gain Plot
    fig2, ax = plt.subplots(figsize=(8, 5), tight_layout=True)
    ax.plot(f_gain / 1e9, gain_broadside, 'ro-', lw=2, ms=6, label='openEMS Realized Gain (θ=0°)')
    ax.set_xlabel('Frequency (GHz)', fontsize=11)
    ax.set_ylabel('Realized Gain (dBi)', fontsize=11)
    ax.set_title('Free-Space Antenna Sensor — Realized Gain vs Frequency (Zhao et al. Fig. 12)', fontsize=12)
    ax.set_xlim([4.0, 10.0])
    ax.set_ylim([0, 10])
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig2.savefig(os.path.join(RESULTS_PATH, 'stage1_gain.png'), dpi=150)
    plt.close(fig2)

    # 3. 2D Radiation Patterns (4 subplots)
    fig3, axes = plt.subplots(2, 2, figsize=(12, 10), tight_layout=True)
    for idx, (f_ghz, pat) in enumerate(patterns.items()):
        ax = axes[idx // 2, idx % 2]
        ax.plot(pat['theta'], pat['gain_E'], 'r-', lw=2, label='E-plane (φ = 90°)')
        ax.plot(pat['theta'], pat['gain_H'], 'b--', lw=2, label='H-plane (φ = 0°)')
        ax.set_xlabel('θ (degrees)', fontsize=10)
        ax.set_ylabel('Realized Gain (dBi)', fontsize=10)
        ax.set_title(f'Radiation Pattern at {f_ghz:.2f} GHz (Fig. 13)', fontsize=11)
        ax.set_xlim([-180, 180])
        ax.set_ylim([-25, 10])
        ax.grid(True, alpha=0.3)
        ax.legend(loc='lower center')
    fig3.savefig(os.path.join(RESULTS_PATH, 'stage1_radiation_patterns.png'), dpi=150)
    plt.close(fig3)

    # Summary
    passband_10dB = f[s11_dB <= -10]
    bw_str = f"{passband_10dB[0]/1e9:.2f} - {passband_10dB[-1]/1e9:.2f} GHz" if len(passband_10dB) > 0 else "None"
    print(f"\n{'='*60}")
    print("STAGE 1 SUMMARY")
    print(f"  Wall time        : {wall_time:.1f} s ({wall_time/60:.2f} min)")
    print(f"  -10 dB Bandwidth : {bw_str} (Paper: 4.60 - 9.20 GHz)")
    print(f"  Min S11          : {np.min(s11_dB):.2f} dB at {f[np.argmin(s11_dB)]/1e9:.2f} GHz")
    print(f"  Peak Gain        : {np.max(gain_broadside):.2f} dBi at {f_gain[np.argmax(gain_broadside)]/1e9:.2f} GHz (Paper: ~5.8 dBi)")
    print(f"{'='*60}\n")

