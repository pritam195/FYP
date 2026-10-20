# -*- coding: utf-8 -*-
"""
Stage 3 Postprocessing: Tumor Radius Sweep & Fig. 9 Recreation
==============================================================
Paper: Zhao et al., "Miniaturized and wideband metasurface antenna sensor for breast tumor detection",
       Sensors and Actuators A: Physical 394 (2025) 116973.

Loads the reflection coefficient data from the 4 tumor radius cases:
  r in [0.0 (no tumor), 3.0, 5.0, 10.0] mm
Generates:
  1. High-resolution comparison plot matching Fig. 9
  2. Numerical summary table of resonant frequencies, shifts, and -10 dB bandwidths
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_PATH = os.path.join(PROJECT_DIR, 'results')

CASES = [
    (0.0, 'stage3_s11_r0.0mm.csv', 'Without tumor',        '#e41a1c', '-'),
    (3.0, 'stage3_s11_r3.0mm.csv', 'Tumor (r = 3 mm)',     '#377eb8', '-'),
    (5.0, 'stage3_s11_r5.0mm.csv', 'Tumor (r = 5 mm)',     '#000000', '-'),
    (10.0,'stage3_s11_r10.0mm.csv','Tumor (r = 10 mm)',    '#8c510a', '-')
]

# Paper reference resonant frequencies from Fig. 9 (digitized approximate)
PAPER_REF = {
    0.0:  {'f_res': 6.00, 'min_s11': -30.0},
    3.0:  {'f_res': 6.25, 'min_s11': -33.5},
    5.0:  {'f_res': 6.29, 'min_s11': -36.5},
    10.0: {'f_res': 6.30, 'min_s11': -33.0}
}


def postprocess_tumor_sweep():
    print(f"\n{'='*70}")
    print("Stage 3: Postprocessing Tumor Radius Sweep (Fig. 9)")
    print(f"{'='*70}\n")

    summary_rows = []
    plot_data = []

    f_res_ref_0 = None

    for radius, csv_name, label, color, linestyle in CASES:
        csv_file = os.path.join(RESULTS_PATH, csv_name)
        if not os.path.exists(csv_file):
            print(f"[Warning] Missing file: {csv_file}")
            continue

        data = np.loadtxt(csv_file, delimiter=',', skiprows=1)
        freq_ghz = data[:, 0]
        s11_db   = data[:, 1]

        # Restrict search for main resonance to 5.0 - 7.5 GHz band
        mask_res = (freq_ghz >= 5.0) & (freq_ghz <= 7.5)
        f_search = freq_ghz[mask_res]
        s11_search = s11_db[mask_res]

        min_idx = np.argmin(s11_search)
        f_res = f_search[min_idx]
        min_s11 = s11_search[min_idx]

        if radius == 0.0:
            f_res_ref_0 = f_res
            delta_f = 0.0
        else:
            delta_f = (f_res - f_res_ref_0) * 1000.0 if f_res_ref_0 is not None else 0.0

        # -10 dB bandwidth
        b_10 = freq_ghz[s11_db <= -10.0]
        if len(b_10) > 0:
            f_low = b_10[0]
            f_high = b_10[-1]
            bw = f_high - f_low
            bw_str = f"{f_low:.2f} - {f_high:.2f} GHz ({bw:.2f} GHz)"
        else:
            bw_str = "None"
            f_low = f_high = bw = np.nan

        summary_rows.append({
            'radius_mm': radius,
            'label': label,
            'f_res_ghz': f_res,
            'delta_f_mhz': delta_f,
            'min_s11_db': min_s11,
            'bw_str': bw_str,
            'paper_f_res': PAPER_REF[radius]['f_res'],
            'paper_min_s11': PAPER_REF[radius]['min_s11']
        })

        plot_data.append((freq_ghz, s11_db, label, color, linestyle))

    if not plot_data:
        print("[Error] No data found to plot!")
        return

    # Print Summary Table
    print(f"{'Case':<20} | {'f_res (GHz)':<12} | {'Paper f_res':<12} | {'Delta_f (MHz)':<14} | {'Min S11 (dB)':<13} | {'-10 dB Bandwidth'}")
    print("-" * 95)
    for row in summary_rows:
        print(f"{row['label']:<20} | {row['f_res_ghz']:<12.3f} | {row['paper_f_res']:<12.2f} | {row['delta_f_mhz']:<14.1f} | {row['min_s11_db']:<13.2f} | {row['bw_str']}")

    # Save summary CSV
    summary_csv = os.path.join(RESULTS_PATH, 'stage3_tumor_radius_summary.csv')
    with open(summary_csv, 'w') as f:
        f.write("Radius_mm,Label,f_res_GHz,Delta_f_MHz,Min_S11_dB,Paper_f_res_GHz,Paper_Min_S11_dB,Bandwidth\n")
        for r in summary_rows:
            f.write(f"{r['radius_mm']},{r['label']},{r['f_res_ghz']:.4f},{r['delta_f_mhz']:.2f},{r['min_s11_db']:.2f},{r['paper_f_res']:.2f},{r['paper_min_s11']:.2f},\"{r['bw_str']}\"\n")
    print(f"\nSaved summary table to: {summary_csv}")

    # =========================================================================
    # Generate Comparison Plot Matching Fig. 9
    # =========================================================================
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

    for freq_ghz, s11_db, label, color, linestyle in plot_data:
        ax.plot(freq_ghz, s11_db, color=color, linestyle=linestyle, linewidth=2.2, label=label)

    # Styling per Fig. 9
    ax.axhline(-10.0, color='gray', linestyle=':', linewidth=1.0, alpha=0.7)
    ax.set_xlim(4.0, 10.0)
    ax.set_ylim(-40.0, 0.0)
    ax.set_xlabel('Frequency (GHz)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Reflection Coefficient (dB)', fontsize=13, fontweight='bold')
    ax.set_title('Stage 3: Simulated Reflection Coefficients vs. Tumor Radius (Zhao et al. Fig. 9)',
                 fontsize=12, fontweight='bold', pad=12)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='lower right', frameon=True, fancybox=True, framealpha=0.9, fontsize=11)

    plt.tight_layout()
    out_plot = os.path.join(RESULTS_PATH, 'stage3_tumor_radius_s11.png')
    plt.savefig(out_plot, dpi=300)
    plt.close()
    print(f"Saved recreation plot to: {out_plot}")


if __name__ == '__main__':
    postprocess_tumor_sweep()
