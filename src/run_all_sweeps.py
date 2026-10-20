# -*- coding: utf-8 -*-
"""
Automation Runner for Remaining Phantom Sweeps:
  - Tumor Radius Sweep: r = 5.0 mm, r = 10.0 mm (r=0 and r=3 already running/done)
  - Distance Sweep: d = 10.5 mm, d = 21.5 mm (d=16.0 mm done with r=5)
"""

import os, sys, time
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from stage3_phantom_sim import run_single_simulation
from stage3_postprocess import postprocess_tumor_sweep

SWEEP_CASES = [
    # Tumor Radius Sweep (d = 16.0 mm)
    {'radius': 5.0,  'dist': 16.0, 'name': 'r5.0mm'},
    {'radius': 10.0, 'dist': 16.0, 'name': 'r10.0mm'},
    # Distance Sweep (r = 5.0 mm)
    {'radius': 5.0,  'dist': 10.5, 'name': 'r5.0mm_d10.5mm'},
    {'radius': 5.0,  'dist': 21.5, 'name': 'r5.0mm_d21.5mm'},
]

def main():
    print(f"\n{'='*70}")
    print("Master Batch Runner: Remaining Stage 3 & 4 Sweeps")
    print(f"{'='*70}\n")

    for case in SWEEP_CASES:
        csv_file = os.path.join(PROJECT_DIR, 'results', f"stage3_s11_{case['name']}.csv")
        if os.path.exists(csv_file):
            print(f"[Skip] {case['name']} already exists at {csv_file}")
            continue

        print(f"\n---> Starting simulation: {case['name']} (radius={case['radius']} mm, dist={case['dist']} mm)")
        run_single_simulation(
            tumor_radius=case['radius'],
            tumor_dist=case['dist'],
            case_name=case['name']
        )

    # Post-process full radius sweep
    print("\nRunning postprocessing for full radius sweep...")
    postprocess_tumor_sweep()
    print("\n[Complete] All remaining sweeps executed and postprocessed successfully.")

if __name__ == '__main__':
    main()
