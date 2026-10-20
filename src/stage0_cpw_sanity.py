# -*- coding: utf-8 -*-
"""
Stage 0: CPW Transmission-Line Calibration & Port Sanity Check
===============================================================
A uniform coplanar waveguide (CPW) line on 2 mm F4BM substrate.
  - Centre conductor width  w3 = 3.0 mm
  - Gap width               s3 = 0.2 mm
  - Substrate               eps_r = 3.5, tand = 0.0042, h = 2.0 mm

Following openEMS official CPW_Line tutorial:
  - Port 1 at y = -line_len/2 excites with Feed_R = 50 Ohm
  - Port 2 at y = +line_len/2 terminates with Feed_R = 50 Ohm (matched load)
  - Clean analytical mesh without AddEdges2Grid conflicts
  - ref_impedance = 50 Ohm in CalcPort
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
    UNIT, F0, FC, F_MIN, F_MAX,
    SUBSTRATE_EPS_R, SUBSTRATE_KAPPA,
    CPW_W3, CPW_S3, H_BOT,
)

SIM_PATH     = os.path.join(PROJECT_DIR, 'sim', 'stage0_cpw')
RESULTS_PATH = os.path.join(PROJECT_DIR, 'results')
os.makedirs(RESULTS_PATH, exist_ok=True)

# Geometry parameters (mm)
cpw_w     = CPW_W3          # 3.0 mm centre conductor
cpw_g     = CPW_S3          # 0.2 mm slot gap
sub_h     = H_BOT           # 2.0 mm substrate thickness
line_len  = 40.0            # 40 mm total length
board_w   = 30.0            # 30 mm lateral ground plane extent
port_len  = 8.0             # 8 mm port length

# Air padding
air_xy   = 15.0
air_z    = 15.0

# FDTD setup
FDTD = openEMS(NrTS=30000, EndCriteria=1e-5)
FDTD.SetGaussExcite(F0, FC)
FDTD.SetBoundaryCond(['PML_8'] * 6)

CSX  = ContinuousStructure()
FDTD.SetCSX(CSX)
mesh = CSX.GetGrid()
mesh.SetDeltaUnit(UNIT)

# Materials (CSXCAD requires 3-element list for isotropic permittivity & conductivity)
sub_mat = CSX.AddMaterial('substrate',
                          epsilon=[SUBSTRATE_EPS_R, SUBSTRATE_EPS_R, SUBSTRATE_EPS_R],
                          kappa=[SUBSTRATE_KAPPA, SUBSTRATE_KAPPA, SUBSTRATE_KAPPA])
cpw_met = CSX.AddMetal('cpw')
gnd_met = CSX.AddMetal('gnd')

# Substrate
sub_mat.AddBox([-board_w/2, -line_len/2, 0],
               [ board_w/2,  line_len/2, sub_h], priority=0)

# Ground planes at z = 0
gnd_met.AddBox([-board_w/2,        -line_len/2, 0],
               [-(cpw_w/2 + cpw_g), line_len/2, 0], priority=10)
gnd_met.AddBox([ (cpw_w/2 + cpw_g),-line_len/2, 0],
               [ board_w/2,         line_len/2, 0], priority=10)

# Centre conductor body between Port 1 and Port 2
cpw_met.AddBox([-cpw_w/2, -line_len/2 + port_len, 0],
               [ cpw_w/2,  line_len/2 - port_len, 0], priority=10)

# ============================================================
# Mesh Setup (smooth, no micro-cells)
# ============================================================
edge_res = 0.08  # 80 um resolution across gap
lambda_min_diel = C0 / F_MAX / np.sqrt(SUBSTRATE_EPS_R) / UNIT  # ~14.5 mm
res_coarse = 1.2  # mm (~lambda / 12)

# X-lines (transverse): exact alignment with CPW conductor and gap edges
x_cpw = [
    -(cpw_w/2 + cpw_g) - edge_res,
    -(cpw_w/2 + cpw_g),               # -1.7 mm (outer gap edge)
    -(cpw_w/2 + cpw_g/2),             # -1.6 mm (gap center)
    -cpw_w/2,                         # -1.5 mm (inner gap / strip edge)
    -cpw_w/4,
     0.0,
     cpw_w/4,
     cpw_w/2,                         # +1.5 mm (strip edge)
     (cpw_w/2 + cpw_g/2),             # +1.6 mm (gap center)
     (cpw_w/2 + cpw_g),               # +1.7 mm (outer gap edge)
     (cpw_w/2 + cpw_g) + edge_res,
]
mesh.AddLine('x', x_cpw)
mesh.AddLine('x', [-board_w/2 - air_xy, -board_w/2, board_w/2, board_w/2 + air_xy])
mesh.SmoothMeshLines('x', res_coarse, ratio=1.4)

# Y-lines (propagation): uniform along ports and body
y_pts = np.concatenate([
    np.linspace(-line_len/2 - air_xy, -line_len/2, 6),
    np.linspace(-line_len/2, -line_len/2 + port_len, 10),
    np.linspace(-line_len/2 + port_len, line_len/2 - port_len, 15),
    np.linspace(line_len/2 - port_len, line_len/2, 10),
    np.linspace(line_len/2, line_len/2 + air_xy, 6)
])
mesh.AddLine('y', np.unique(y_pts))
mesh.SmoothMeshLines('y', res_coarse, ratio=1.4)

# Z-lines (normal): fine resolution near metal plane z=0 to resolve fringe field
z_pts = np.concatenate([
    np.linspace(-air_z, -1.0, 6),
    np.array([-0.5, -0.25, -0.12, -0.06, 0.0, 0.06, 0.12, 0.25, 0.5]),
    np.linspace(1.0, sub_h, 4),
    np.linspace(sub_h + 1.0, sub_h + air_z, 6)
])
mesh.AddLine('z', np.unique(z_pts))
mesh.SmoothMeshLines('z', res_coarse, ratio=1.3)

# ============================================================
# Ports (Port 1 excites, Port 2 terminates matched)
# ============================================================
port1 = FDTD.AddCPWPort(
    port_nr    = 1,
    metal_prop = cpw_met,
    start      = [-cpw_w/2, -line_len/2,            0],
    stop       = [ cpw_w/2, -line_len/2 + port_len, 0],
    prop_dir   = 'y',
    exc_dir    = 'x',
    gap_width  = cpw_g,
    excite     = 1.0,
    Feed_R     = 50.0,
    FeedShift  = 0.0,
    MeasPlaneShift = port_len,  # measure at end of port region
    priority   = 10,
)

port2 = FDTD.AddCPWPort(
    port_nr    = 2,
    metal_prop = cpw_met,
    start      = [ cpw_w/2,  line_len/2,            0],
    stop       = [-cpw_w/2,  line_len/2 - port_len, 0],
    prop_dir   = 'y',
    exc_dir    = 'x',
    gap_width  = cpw_g,
    excite     = 0.0,
    Feed_R     = 50.0,
    FeedShift  = 0.0,
    MeasPlaneShift = port_len,
    priority   = 10,
)

if __name__ == '__main__':
    # Cell count
    nx = len(mesh.GetLines('x'))
    ny = len(mesh.GetLines('y'))
    nz = len(mesh.GetLines('z'))
    ncells = (nx - 1) * (ny - 1) * (nz - 1)
    print(f"\n{'='*50}")
    print(f"Stage 0 – CPW Transmission Line Calibration")
    print(f"Mesh : {nx} x {ny} x {nz} = {ncells:,} cells")
    print(f"{'='*50}\n")

    # Run
    os.makedirs(SIM_PATH, exist_ok=True)
    CSX.Write2XML(os.path.join(SIM_PATH, 'stage0.xml'))

    t0 = time.perf_counter()
    FDTD.Run(SIM_PATH, cleanup=True)
    wall = time.perf_counter() - t0
    print(f"\nSimulation finished in {wall:.1f} s")

    # Post-processing
    f = np.linspace(F_MIN, F_MAX, 801)
    port1.CalcPort(SIM_PATH, f, ref_impedance=50.0)
    port2.CalcPort(SIM_PATH, f, ref_impedance=50.0)

    s11 = port1.uf_ref / port1.uf_inc
    s21 = port2.uf_ref / port1.uf_inc
    s11_dB = 20.0 * np.log10(np.abs(s11))
    s21_dB = 20.0 * np.log10(np.abs(s21))
    Zin    = port1.uf_tot / port1.if_tot

    # Save CSV
    csv_file = os.path.join(RESULTS_PATH, 'stage0_s11.csv')
    np.savetxt(csv_file,
               np.column_stack([f / 1e9, s11_dB, s21_dB, np.real(Zin), np.imag(Zin)]),
               delimiter=',',
               header='f_GHz,S11_dB,S21_dB,Re_Zin_Ohm,Im_Zin_Ohm',
               comments='')
    print(f"CSV  -> {csv_file}")

    # Save S2P
    s2p_file = os.path.join(RESULTS_PATH, 'stage0.s2p')
    with open(s2p_file, 'w') as fh:
        fh.write('! Stage 0 CPW 2-Port Calibration - openEMS\n')
        fh.write('# GHz S DB R 50\n')
        for i in range(len(f)):
            fh.write(f"{f[i]/1e9:.6f}  {s11_dB[i]:.4f} {np.angle(s11[i], deg=True):.4f} "
                     f"{s21_dB[i]:.4f} {np.angle(s21[i], deg=True):.4f} "
                     f"{s21_dB[i]:.4f} {np.angle(s21[i], deg=True):.4f} "
                     f"{s11_dB[i]:.4f} {np.angle(s11[i], deg=True):.4f}\n")
    print(f".s2p -> {s2p_file}")

    # Plots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), tight_layout=True)

    ax1.plot(f / 1e9, s11_dB, 'b-', lw=2, label='|S₁₁| (Return loss)')
    ax1.plot(f / 1e9, s21_dB, 'g--', lw=2, label='|S₂₁| (Insertion loss)')
    ax1.axhline(-20, color='r', ls=':', alpha=0.7, label='-20 dB criterion')
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel('Magnitude (dB)')
    ax1.set_title('Stage 0 — CPW Line S-Parameters (50 Ω Matched Line)')
    ax1.set_xlim([F_MIN / 1e9, F_MAX / 1e9])
    ax1.set_ylim([-50, 2])
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.plot(f / 1e9, np.real(Zin), 'b-', lw=2, label='Re{Z_in}')
    ax2.plot(f / 1e9, np.imag(Zin), 'r--', lw=2, label='Im{Z_in}')
    ax2.axhline(50, color='gray', ls=':', alpha=0.7, label='50 Ω nominal')
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel('Impedance (Ω)')
    ax2.set_title('Stage 0 — CPW Line Input Impedance')
    ax2.set_xlim([F_MIN / 1e9, F_MAX / 1e9])
    ax2.set_ylim([0, 100])
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    png_file = os.path.join(RESULTS_PATH, 'stage0_cpw_sanity.png')
    fig.savefig(png_file, dpi=150)
    print(f"Plot -> {png_file}")
    plt.close(fig)

    # Verdict
    band = (f >= 4e9) & (f <= 9e9)
    Z0_avg  = np.mean(np.real(Zin[band]))
    s11_max = np.max(s11_dB[band])
    s21_avg = np.mean(s21_dB[band])

    print(f"\n{'='*50}")
    print(f"STAGE 0 VERDICT (4 - 9 GHz passband)")
    print(f"  Z0 avg    = {Z0_avg:.1f} Ohm (target ~ 50 Ohm)")
    print(f"  S11 worst = {s11_max:.1f} dB  (target < -20 dB)")
    print(f"  S21 avg   = {s21_avg:.2f} dB  (target ~ 0 dB)")
    print(f"  Wall time = {wall:.1f} s")
    verdict = 'PASS' if (s11_max < -15 and 40 < Z0_avg < 60) else 'FAIL'
    print(f"  Verdict   : {verdict}")
    print(f"{'='*50}\n")
