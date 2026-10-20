# -*- coding: utf-8 -*-
"""
Stage 4 Postprocessing: Tumor Distance Sweep (d = 10.5, 16.0, 21.5 mm)
======================================================================
Paper: Zhao et al., Section 3.2, Table 3.
  - d = 10.5 mm: Tumor in fat layer
  - d = 16.0 mm: Tumor at fat / fibro-glandular interface
  - d = 21.5 mm: Tumor in fibro-glandular core
  (Tumor radius r = 5.0 mm fixed)
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
    (0.0,  'stage3_s11_r0.0mm.csv',            'Without tumor',           '#e41a1c', '--'),
    (10.5, 'stage3_s11_r5.0mm_d10.5mm.csv',    'Tumor in fat (d=10.5 mm)', '#377eb8', '-'),
    (16.0, 'stage3_s11_r5.0mm.csv',            'Tumor interface (d=16 mm)', '#000000', '-'),
    (21.5, 'stage3_s11_r5.0mm_d21.5mm.csv',    'Tumor in gland (d=21.5 mm)','#4daf4a', '-')
]

def postprocess_distance_sweep():
    print(f"\n{'='*70}")
    print("Stage 4: Postprocessing Tumor Distance Sweep")
    print(f"{'='*70}\n")

    summary_rows = []
    plot_data = []
    f_res_ref_0 = None

    for dist, csv_name, label, color, linestyle in CASES:
        csv_file = os.path.join(RESULTS_PATH, csv_name)
        if not os.path.exists(csv_file):
            print(f"[Warning] Missing file: {csv_file}")
            continue

        data = np.loadtxt(csv_file, delimiter=',', skiprows=1)
        freq_ghz = data[:, 0]
        s11_db   = data[:, 1]

        mask_res = (freq_ghz >= 5.0) & (freq_ghz <= 7.5)
        f_search = freq_ghz[mask_res]
        s11_search = s11_db[mask_res]

        min_idx = np.argmin(s11_search)
        f_res = f_search[min_idx]
        min_s11 = s11_search[min_idx]

        if dist == 0.0:
            f_res_ref_0 = f_res
            delta_f = 0.0
        else:
            delta_f = (f_res - f_res_ref_0) * 1000.0 if f_res_ref_0 is not None else 0.0

        b_10 = freq_ghz[s11_db <= -10.0]
        bw_str = f"{b_10[0]:.2f} - {b_10[-1]:.2f} GHz" if len(b_10) > 0 else "None"

        summary_rows.append({
            'dist_mm': dist,
            'label': label,
            'f_res_ghz': f_res,
            'delta_f_mhz': delta_f,
            'min_s11_db': min_s11,
            'bw_str': bw_str
        })
        plot_data.append((freq_ghz, s11_db, label, color, linestyle))

    if not plot_data:
        print("[Error] No data found to plot!")
        return

    print(f"{'Case':<28} | {'f_res (GHz)':<12} | {'Delta_f (MHz)':<14} | {'Min S11 (dB)':<13} | {'-10 dB Bandwidth'}")
    print("-" * 90)
    for row in summary_rows:
        print(f"{row['label']:<28} | {row['f_res_ghz']:<12.3f} | {row['delta_f_mhz']:<14.1f} | {row['min_s11_db']:<13.2f} | {row['bw_str']}")

    # Save CSV
    summary_csv = os.path.join(RESULTS_PATH, 'stage4_distance_summary.csv')
    with open(summary_csv, 'w') as f:
        f.write("Distance_mm,Label,f_res_GHz,Delta_f_MHz,Min_S11_dB,Bandwidth\n")
        for r in summary_rows:
            f.write(f"{r['dist_mm']},{r['label']},{r['f_res_ghz']:.4f},{r['delta_f_mhz']:.2f},{r['min_s11_db']:.2f},\"{r['bw_str']}\"\n")
    print(f"\nSaved distance summary to: {summary_csv}")

    # Plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    for freq_ghz, s11_db, label, color, linestyle in plot_data:
        ax.plot(freq_ghz, s11_db, color=color, linestyle=linestyle, linewidth=2.2, label=label)

    ax.axhline(-10.0, color='gray', linestyle=':', linewidth=1.0, alpha=0.7)
    ax.set_xlim(4.0, 10.0)
    ax.set_ylim(-40.0, 0.0)
    ax.set_xlabel('Frequency (GHz)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Reflection Coefficient (dB)', fontsize=13, fontweight='bold')
    ax.set_title('Stage 4: Simulated S11 vs. Tumor Distance d (Zhao et al. Table 3)',
                 fontsize=12, fontweight='bold', pad=12)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='lower right', frameon=True, fancybox=True, framealpha=0.9, fontsize=11)

    plt.tight_layout()
    out_plot = os.path.join(RESULTS_PATH, 'stage4_tumor_distance_s11.png')
    plt.savefig(out_plot, dpi=300)
    plt.close()
    print(f"Saved distance plot to: {out_plot}")

if __name__ == '__main__':
    postprocess_distance_sweep()
