import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

data = np.loadtxt('results/stage3_s11_r0.0mm.csv', delimiter=',', skiprows=1)
f = data[:, 0]
s11 = data[:, 1]

print("Frequency range:", f[0], "to", f[-1], "GHz")
min_idx, _ = find_peaks(-s11, prominence=1)
print("Local minima in S11:")
for idx in min_idx:
    print(f"  f = {f[idx]:.3f} GHz: S11 = {s11[idx]:.2f} dB")

plt.figure(figsize=(8, 5), dpi=150)
plt.plot(f, s11, 'r-', lw=2, label='openEMS r=0.0mm (no tumor)')
plt.axhline(-10, color='gray', ls='--', alpha=0.7)
plt.xlim(4, 10)
plt.ylim(-40, 0)
plt.xlabel('Frequency (GHz)', fontsize=12, fontweight='bold')
plt.ylabel('Reflection Coefficient (dB)', fontsize=12, fontweight='bold')
plt.title('Stage 3: Breast Phantom Baseline (r = 0.0 mm)', fontsize=12, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig('results/stage3_r0.0mm_check.png', dpi=150)
print("Saved results/stage3_r0.0mm_check.png")
