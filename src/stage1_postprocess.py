# -*- coding: utf-8 -*-
"""
Stage 1: Post-Processing & Far-Field Analysis
=============================================
Processes the completed FDTD simulation in `sim/stage1_antenna`:
  - Port S11 & Input Impedance (compared to Fig. 11)
  - Broadside Realized Gain vs Frequency (compared to Fig. 12)
  - 2D Radiation Patterns (E- and H-planes at 5.73, 6.98, 8.51, 9.02 GHz vs Fig. 13)
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
    FDTD_NRTS, FDTD_END_CRITERIA,
)
from stage1_antenna_fs import build_antenna

SIM_PATH     = os.path.join(PROJECT_DIR, 'sim', 'stage1_antenna')
RESULTS_PATH = os.path.join(PROJECT_DIR, 'results')
os.makedirs(RESULTS_PATH, exist_ok=True)

# Build virtual geometry to recreate port and nf2ff objects
FDTD = openEMS(NrTS=FDTD_NRTS, EndCriteria=FDTD_END_CRITERIA)
FDTD.SetGaussExcite(F0, FC)
FDTD.SetBoundaryCond(['PML_8'] * 6)
CSX = ContinuousStructure()
FDTD.SetCSX(CSX)

port, nf2ff, mesh = build_antenna(FDTD, CSX)

# -------------------------------------------------------------------------
# 1. Port Post-Processing
# -------------------------------------------------------------------------
print("1. Processing Port S-Parameters...")
f = np.linspace(F_MIN, F_MAX, 801)
port.CalcPort(SIM_PATH, f, ref_impedance=50.0)

s11    = port.uf_ref / port.uf_inc
s11_dB = 20.0 * np.log10(np.abs(s11))
Zin    = port.uf_tot / port.if_tot

# Save CSV
csv_s11 = os.path.join(RESULTS_PATH, 'stage1_s11.csv')
np.savetxt(csv_s11,
           np.column_stack([f / 1e9, s11_dB, np.real(Zin), np.imag(Zin)]),
           delimiter=',',
           header='f_GHz,S11_dB,Re_Zin_Ohm,Im_Zin_Ohm',
           comments='')
print(f"  -> {csv_s11}")

# Save S1P
s1p_path = os.path.join(RESULTS_PATH, 'stage1.s1p')
with open(s1p_path, 'w') as fh:
    fh.write('! Stage 1 Free-Space Antenna - openEMS\n')
    fh.write('# GHz S DB R 50\n')
    for i in range(len(f)):
        fh.write(f"{f[i]/1e9:.6f}  {s11_dB[i]:.4f}  {np.angle(s11[i], deg=True):.4f}\n")
print(f"  -> {s1p_path}")

# Plot S11 and Impedance
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
png_s11 = os.path.join(RESULTS_PATH, 'stage1_s11.png')
fig1.savefig(png_s11, dpi=150)
plt.close(fig1)
print(f"  Plot -> {png_s11}")

# -------------------------------------------------------------------------
# 2. Far-Field Realized Gain vs Frequency
# -------------------------------------------------------------------------
print("\n2. Processing Broadside Realized Gain...")
f_gain = np.linspace(4.0e9, 10.0e9, 31)

# Pass all frequencies at once with read_cached=True and explicit outfile
gain_res = nf2ff.CalcNF2FF(SIM_PATH, f_gain, [0.0], [0.0],
                           read_cached=True, outfile='gain_broadside.h5')

gain_broadside = []
for idx, fg in enumerate(f_gain):
    P_in = port.P_inc[np.argmin(np.abs(f - fg))]
    E_theta = gain_res.E_theta[idx][0, 0]
    E_phi   = gain_res.E_phi[idx][0, 0]
    U = 0.5 * (np.abs(E_theta)**2 + np.abs(E_phi)**2) / 376.73
    realized_gain_lin = 4.0 * np.pi * U / max(1e-35, P_in)
    gain_dBi = 10.0 * np.log10(max(1e-6, realized_gain_lin))
    gain_broadside.append(gain_dBi)

gain_broadside = np.array(gain_broadside)
csv_gain = os.path.join(RESULTS_PATH, 'stage1_gain.csv')
np.savetxt(csv_gain,
           np.column_stack([f_gain / 1e9, gain_broadside]),
           delimiter=',',
           header='f_GHz,Realized_Gain_dBi',
           comments='')
print(f"  -> {csv_gain}")

fig2, ax = plt.subplots(figsize=(8, 5), tight_layout=True)
ax.plot(f_gain / 1e9, gain_broadside, 'ro-', lw=2, ms=6, label='openEMS Realized Gain (θ=0°)')
ax.set_xlabel('Frequency (GHz)', fontsize=11)
ax.set_ylabel('Realized Gain (dBi)', fontsize=11)
ax.set_title('Free-Space Antenna Sensor — Realized Gain vs Frequency (Zhao et al. Fig. 12)', fontsize=12)
ax.set_xlim([4.0, 10.0])
ax.set_ylim([-5, 15])
ax.grid(True, alpha=0.3)
ax.legend()
png_gain = os.path.join(RESULTS_PATH, 'stage1_gain.png')
fig2.savefig(png_gain, dpi=150)
plt.close(fig2)
print(f"  Plot -> {png_gain}")

# -------------------------------------------------------------------------
# 3. 2D Radiation Patterns (Fig. 13 Frequencies)
# -------------------------------------------------------------------------
print("\n3. Processing 2D Radiation Patterns at Fig. 13 frequencies...")
theta_deg = np.linspace(-180.0, 180.0, 361)
patterns = {}

fig3, axes = plt.subplots(2, 2, figsize=(12, 10), tight_layout=True)

for idx, fp in enumerate(F_PATTERN):
    f_ghz = fp / 1e9
    P_in = port.P_inc[np.argmin(np.abs(f - fp))]

    # E-plane: phi = 90 deg (y-z plane)
    nf_E = nf2ff.CalcNF2FF(SIM_PATH, [fp], theta_deg, [90.0],
                           read_cached=True, outfile=f'pattern_E_{f_ghz:.2f}GHz.h5')
    E_th = nf_E.E_theta[0][:, 0]
    E_ph = nf_E.E_phi[0][:, 0]
    U_E = 0.5 * (np.abs(E_th)**2 + np.abs(E_ph)**2) / 376.73
    gain_E = 10.0 * np.log10(np.maximum(1e-6, 4.0 * np.pi * U_E / max(1e-35, P_in)))

    # H-plane: phi = 0 deg (x-z plane)
    nf_H = nf2ff.CalcNF2FF(SIM_PATH, [fp], theta_deg, [0.0],
                           read_cached=True, outfile=f'pattern_H_{f_ghz:.2f}GHz.h5')
    H_th = nf_H.E_theta[0][:, 0]
    H_ph = nf_H.E_phi[0][:, 0]
    U_H = 0.5 * (np.abs(H_th)**2 + np.abs(H_ph)**2) / 376.73
    gain_H = 10.0 * np.log10(np.maximum(1e-6, 4.0 * np.pi * U_H / max(1e-35, P_in)))

    patterns[f_ghz] = {'theta': theta_deg, 'gain_E': gain_E, 'gain_H': gain_H}

    csv_pat = os.path.join(RESULTS_PATH, f'stage1_pattern_{f_ghz:.2f}GHz.csv')
    np.savetxt(csv_pat,
               np.column_stack([theta_deg, gain_E, gain_H]),
               delimiter=',',
               header='theta_deg,Gain_E_plane_dBi,Gain_H_plane_dBi',
               comments='')

    # Subplot
    ax = axes[idx // 2, idx % 2]
    ax.plot(theta_deg, gain_E, 'r-', lw=2, label='E-plane (φ = 90°)')
    ax.plot(theta_deg, gain_H, 'b--', lw=2, label='H-plane (φ = 0°)')
    ax.set_xlabel('θ (degrees)', fontsize=10)
    ax.set_ylabel('Realized Gain (dBi)', fontsize=10)
    ax.set_title(f'Radiation Pattern at {f_ghz:.2f} GHz (Fig. 13)', fontsize=11)
    ax.set_xlim([-180, 180])
    ax.set_ylim([-25, 10])
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower center')

png_pat = os.path.join(RESULTS_PATH, 'stage1_radiation_patterns.png')
fig3.savefig(png_pat, dpi=150)
plt.close(fig3)
print(f"  Plot -> {png_pat}")

# -------------------------------------------------------------------------
# Summary Verdict
# -------------------------------------------------------------------------
passband_10dB = f[s11_dB <= -10.0]
bw_str = f"{passband_10dB[0]/1e9:.2f} - {passband_10dB[-1]/1e9:.2f} GHz" if len(passband_10dB) > 0 else "None"
peak_gain = np.max(gain_broadside)
f_peak_gain = f_gain[np.argmax(gain_broadside)] / 1e9

print(f"\n{'='*60}")
print("STAGE 1 COMPREHENSIVE VALIDATION SUMMARY")
print(f"  -10 dB Passband  : {bw_str} (Paper: 4.60 - 9.20 GHz)")
print(f"  S11 Minimum      : {np.min(s11_dB):.2f} dB at {f[np.argmin(s11_dB)]/1e9:.2f} GHz")
print(f"  Peak Gain        : {peak_gain:.2f} dBi at {f_peak_gain:.2f} GHz (Paper: ~5.8 dBi)")
print(f"  Gain at 6.87 GHz : {gain_broadside[np.argmin(np.abs(f_gain - 6.87e9))]:.2f} dBi")
print(f"{'='*60}\n")
