# Miniaturized and Wideband Metasurface Antenna Sensor for Breast Tumor Detection

Replication, validation, and computational electromagnetics (CEM) study of:
> Zhenyu Zhao, Le Chang, Yaozhong Cui, and Anxue Zhang, *"Miniaturized and wideband metasurface antenna sensor for breast tumor detection"*, **Sensors and Actuators A: Physical** 394 (2025) 116973.

Implemented using the **openEMS** finite-difference time-domain (FDTD) engine with Python interface.

---

## 1. Project Overview & Verification Status

| Staged Objective | Target Curves / Quantities | Status | Verification Summary |
| :--- | :--- | :--- | :--- |
| **Stage 0: CPW Line Sanity** | Characteristic impedance $Z_0$, insertion loss $S_{21}$ | **PASSED** | Numerical $Z_L = 41.70\,\Omega$ matches analytical grounded CPW ($41.76\,\Omega$) within **0.14%**; $S_{21} = -0.01\text{ dB}$. |
| **Stage 1: Free-Space Antenna** | $S_{11}$, Realized Gain, 2D Radiation Patterns (Fig. 11–13) | **PASSED** | Lower band edge: $4.49\text{ GHz}$ (paper: $4.60\text{ GHz}$); Center gain: $4.79\text{ dBi}$ (paper: $5.2\text{ dBi}$); clean broadside directivity with FTB $>8.8\text{ dB}$. |
| **Stage 3: Tumor Radius Sweep** | Reflection coefficient $S_{11}$ vs. $r \in [0, 3, 5, 10]\text{ mm}$ (Fig. 9 & 17) | **PASSED** | Tissue-loaded resonance at $6.24\text{ GHz}$; upward resonance shift verified; short-wavelength high-frequency sensitivity reproduced. |
| **Stage 4: Tumor Distance Sweep** | $S_{11}$ vs. $d \in [10.5, 16.0, 21.5]\text{ mm}$ (Table 3) | **PASSED** | Shallow tumor ($d=10.5\text{ mm}$ in fat) produces largest response; deep tumor ($d=21.5\text{ mm}$) approaches baseline. |
| **Stage 5: Local SAR Framework** | Peak local SAR per tissue layer normalized to 1 W (Table 2 & 3) | **IMPLEMENTED** | Automated 3D voxel tissue decomposition and 1 W accepted power normalization in `src/stage5_sar_sim.py`. |

---

## 2. Directory Layout

```
openEMS_x64_v0.37.0_msvc/
├── src/
│   ├── config.py                     # Central electromagnetic & geometric specifications
│   ├── stage0_cpw_sanity.py          # Grounded CPW calibration & Gwarek extraction
│   ├── stage1_antenna_fs.py          # Free-space antenna simulation (S11, Gain, NF2FF)
│   ├── stage1_postprocess.py         # Free-space gain and 2D radiation pattern generator
│   ├── stage3_phantom_sim.py         # Hemispherical breast phantom model & FDTD runner
│   ├── stage3_postprocess.py         # Tumor radius overlay plotter (reproducing Fig. 9)
│   ├── stage4_distance_postprocess.py# Tumor distance overlay plotter (reproducing Table 3)
│   ├── stage5_sar_sim.py             # 3D Local SAR simulation and tissue decomposition
│   └── run_all_sweeps.py             # Master automated batch runner for all phantom sweeps
├── results/
│   ├── stage0_cpw_sanity.png         # Stage 0 CPW S-parameters
│   ├── stage1_s11.png & .csv         # Stage 1 Free-space S11 curve
│   ├── stage1_gain.png & .csv        # Stage 1 Realized gain vs. frequency
│   ├── stage1_radiation_patterns.png # Stage 1 E/H-plane patterns at 5.73, 6.98, 8.51, 9.02 GHz
│   ├── stage3_tumor_radius_s11.png   # Stage 3 Fig. 9 reproduction
│   ├── stage3_tumor_radius_summary.csv
│   ├── stage4_tumor_distance_s11.png # Stage 4 Table 3 reproduction
│   └── stage4_distance_summary.csv
├── LOG.md                            # Complete engineering validation journal with numbers
└── ASSUMPTIONS.md                    # Explicit physical modeling justifications
```

---

## 3. How to Run & Reproduce

All commands should be executed from the project root directory in PowerShell:

### Stage 0: CPW Reference Line Calibration
```powershell
python src/stage0_cpw_sanity.py
```

### Stage 1: Free-Space Metasurface Antenna Sensor
```powershell
# Run FDTD simulation (~27 min on 8 threads)
python src/stage1_antenna_fs.py

# Post-process gain & 2D radiation patterns
python src/stage1_postprocess.py
```

### Stage 3 & 4: Hemispherical Breast Phantom & Tumor Sweeps
```powershell
# Run all sweeps sequentially (or resume existing runs)
python src/run_all_sweeps.py

# Generate Fig. 9 recreation plot
python src/stage3_postprocess.py

# Generate Table 3 distance recreation plot
python src/stage4_distance_postprocess.py
```

### Stage 5: Local SAR Evaluation
```powershell
python src/stage5_sar_sim.py
```

---

## 4. Hardware & Dependencies
- **OS:** Windows 11 (64-bit)
- **CEM Engine:** openEMS v0.37.0 MSVC (Multi-threaded SSE/OpenMP) + CSXCAD v0.7.0
- **Python Environment:** Python 3.14.7 (`numpy`, `scipy`, `matplotlib`, `h5py`, `pymupdf`)
