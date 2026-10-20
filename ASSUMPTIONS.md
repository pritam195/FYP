# Engineering Assumptions & Physical Model Justifications

Project: Reproduction and Validation of Zhao et al., "Miniaturized and wideband metasurface antenna sensor for breast tumor detection", Sensors and Actuators A: Physical 394 (2025) 116973.

---

## 1. Dielectric Substrate Loss Modeling
- **Substrate Specification:** F4BM laminate, $\varepsilon_r = 3.5$, loss tangent $\tan\delta = 0.0042$.
- **FDTD Conductivity Conversion:** In openEMS FDTD, dielectric loss is modeled via effective electrical conductivity $\kappa$ ($S/m$):
  $$\kappa = \omega \varepsilon_0 \varepsilon_r \tan\delta = 2\pi f_0 \varepsilon_0 \varepsilon_r \tan\delta$$
- **Reference Frequency Used:** $f_0 = 6.87\text{ GHz}$ (the nominal design center frequency listed in paper Table 5).
- **Resulting Conductivity:**
  $$\kappa = 2\pi \times (6.87 \times 10^9) \times (8.8541878 \times 10^{-12}) \times 3.5 \times 0.0042 = 5.618 \times 10^{-3}\text{ S/m}$$
- **Verification:** Since $\tan\delta \ll 1$, this narrow-band dielectric loss approximation accurately captures substrate loss throughout the 4.6--9.2 GHz passband without requiring complex multi-pole Debye fitting for the low-loss PTFE laminate.

---

## 2. Geometry Reconstructions & Clarifications

### A. 4.5 mm Substrate Stackup
- The paper specifies 3 layers of F4BM:
  - Top layer thickness: $h_1 = 0.5\text{ mm}$
  - Middle layer thickness: $h_0 = 2.0\text{ mm}$
  - Bottom layer thickness: $h_2 = 2.0\text{ mm}$
  - Total thickness: $h = h_1 + h_0 + h_2 = 0.5 + 2.0 + 2.0 = 4.5\text{ mm}$.
- Coordinate setup (z-axis):
  - $z = 0$: Bottom ground plane / CPW feed structure.
  - $z \in [0, 2.0]\text{ mm}$: Bottom dielectric layer ($h_2 = 2.0\text{ mm}$).
  - $z = 2.0\text{ mm}$: Lower copper metallization of middle layer.
  - $z \in [2.0, 4.0]\text{ mm}$: Middle dielectric layer ($h_0 = 2.0\text{ mm}$).
  - $z = 4.0\text{ mm}$: Upper copper metallization of middle layer.
  - $z \in [4.0, 4.5]\text{ mm}$: Top dielectric layer ($h_1 = 0.5\text{ mm}$).
  - $z = 4.5\text{ mm}$: Top single-layer $4\times 4$ patch array.

### B. Middle Layer Strips & Periodicity
- **Unit Cell Periodicity:**
  - $x$-period: $P_x = l_1 + s_1 = 7.8 + 0.7 = 8.5\text{ mm}$ (top layer) matches $l_2 + s_2 = 6.0 + 2.5 = 8.5\text{ mm}$ (middle layer).
  - $y$-period: $P_y = w_1 + g_1 = 5.6 + 1.0 = 6.6\text{ mm}$ (top layer).
- **Middle Layer Strips:**
  - In each unit cell, there is a pair of strips of length $l_2 = 6.0\text{ mm}$ and width $w_2 = 1.6\text{ mm}$, separated by gap $g_2 = 0.8\text{ mm}$.
  - The vertical pair height is $2 \times 1.6 + 0.8 = 4.0\text{ mm}$.
  - The gap between adjacent cell pairs is $6.6 - 4.0 = 2.6\text{ mm}$.
  - The centerline-to-centerline vertical spacing between strips across cells is $2.6 + 1.6 = 4.2\text{ mm}$, which exactly matches $g_3 = 4.2\text{ mm}$ specified in the text and dimensioned in Fig. 1(c).
  - The $2\times 2$ sub-block corresponds to $w_{unit} = 2 \times 6.6 = 13.2\text{ mm}$ and $l_{unit} = 2 \times 8.5 = 17.0\text{ mm}$, exactly as stated in Section 2.2.

### C. Vias
- **Via Count & Arrangement:** Visual inspection of the fabricated prototype (Fig. 10b) and schematic (Fig. 1c) confirms each strip has 3 vias in a line along the length $l_2 = 6.0\text{ mm}$ ($x$-direction).
- **Total Vias:** $3 \text{ vias/strip} \times 2 \text{ strips/unit} \times 16 \text{ units} = 96\text{ vias}$.
- **Via Diameter:** Unspecified in text. Standard PCB drill diameter of $0.35\text{ mm}$ (range $0.30\text{--}0.40\text{ mm}$) is adopted.
- **Sensitivity Check:** A sensitivity sweep over via diameter ($0.30\text{ mm}, 0.35\text{ mm}, 0.40\text{ mm}$) will be conducted in Stage 2 to quantify the effect on S11 and resonance frequency.

### D. CPW Feeding Topology
- Inspection of Fig. 1(d) and Fig. 10(c) shows a $50\,\Omega$ CPW feed line:
  - Center conductor width: $w_3 = 3.0\text{ mm}$
  - Side gaps: $s_3 = 0.2\text{ mm}$
  - Substrate: $\varepsilon_r = 3.5$, thickness $2.0\text{ mm}$ (yielding quasi-TEM characteristic impedance $Z_0 \approx 48.8\,\Omega$).
- The line extends length $l_3 = 21.5\text{ mm}$ from the edge ($y = -22\text{ mm}$) to $y = -0.5\text{ mm}$.
- At the end of the line, the CPW center conductor short-circuits directly into the upper ground plane across the transverse slot.
- Transverse slot: branches horizontally left and right with width $s_4 = 1.0\text{ mm}$ and length $w_4 = 9.6\text{ mm}$, terminating in enlarged capacitive stubs of size $w_5 \times s_5 = 2.0 \times 2.0\text{ mm}$.
- Excitation mechanism: The CPW short-circuit current drives an alternating magnetic dipole / electric field aperture across the transverse slot, which electromagnetically couples upward into the middle and top metasurface layers.

---

## 3. Hemispherical Breast Model & SAR
- **Boundary Condition on Flat Face:** The flat face of the hemisphere is assumed open to air (or backed by PML) unless a chest wall is modeled.
- **Tumor Distance Default:** For Fig. 9 (S11 vs radius), distance is set to $d = 16\text{ mm}$ as specified in the staged guidelines.
- **Tissue Densities for Local SAR:** Standard biological mass densities:
  - Skin: $\rho = 1100\text{ kg/m}^3$
  - Fat: $\rho = 930\text{ kg/m}^3$
  - Fibro-glandular: $\rho = 1050\text{ kg/m}^3$
  - Tumor: $\rho = 1050\text{ kg/m}^3$
  Values will be presented for both $1\text{ W}$ input power (paper reference) and $1\text{ mW}$ input power (safe operating level).
