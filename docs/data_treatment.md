# `CLCT_threshold_corrected.ipynb` in one page

**Question:** above what CLCT value should ICON be called "cloudy", when compared against a binary
satellite cloud mask?

**Why it's not trivial:** CLCT is a continuous 0–100% areal fraction on a triangular mesh; the NWCSAF
`cma` is a hard 0/1 bit per 3 km satellite pixel, seen from 36 000 km away at a 54° angle. Every step
below fixes one way those two don't line up.

| # | step | what we do | why |
|---|---|---|---|
| 1 | **Regrid** | Clip every ICON triangle against every satellite cell, weight by exact overlap area | CLCT is a *fraction* — averaging must conserve cloud area. Not interpolation |
| 2 | **Match times** | Pair satellite slot `T−15min` with model hour `T` | The filename is the *start* of a 12.4 min scan; we're imaged 11 min into it |
| 3 | **Parallax** | Shift each cloudy pixel south by 1.38 × its cloud-top height; clear pixels by terrain height | MSG reports cloud 3–4 cells too far north. Cells hidden behind shifted cloud become *unobserved*, not clear |
| 4 | **Screen** | Drop only snow/ice cloud types | There the mask may be genuinely *wrong*. Fractional and thin cirrus are **kept** — real detections of real partial cloud |
| 5 | **Reduce** | Store per-bin counts of cloudy/clear pixels, discard the fields | Makes 1000 bootstrap replicates cheap. Binning is exact, and asserted so |
| 6 | **Split** | Calibrate on 4–6 Oct, evaluate on 7–10 Oct — **separately for day and night** | Each threshold is fitted and scored on the same illumination class |
| 7 | **Fit** | Maximise Youden's J = POD − POFD; bootstrap in time blocks | J ignores base rate. Resample *time*, not pixels — neighbouring pixels aren't independent |
| 8 | **Plot** | 801/802 rows × mask, both thresholds, raw CLCT; MOVERO bias underneath | Each frame uses the threshold for its own illumination class |

## Results — two thresholds, not one

| | tau* | J | POD | POFD | freq. bias |
|---|---|---|---|---|---|
| **day** | **66%** | 0.569 | 0.845 | 0.276 | 1.03 |
| **night** (incl. twilight) | **77%** | 0.472 | 0.757 | 0.285 | 1.05 |

Night needs a **higher** threshold: without visible channels the mask relies on IR contrast, misses low
cloud against warm ground, and reports less cloud — so ICON needs more CLCT before the two agree. Night
is also a genuinely harder problem (J 0.47 vs 0.57), which a single pooled number hid.

A single global threshold came out at 71% — fitting **neither** class, and 11 points is wider than the
day confidence interval (63–72%), so this was a real bias rather than noise.

**DWD's 12.5%** (= 1 okta) is decisively worse in both, and worst at night:

| | J | frequency bias |
|---|---|---|
| day, tau* 66% | **0.569** | **1.03** |
| day, DWD 12.5% | 0.416 | 1.33 |
| night, tau* 77% | **0.472** | **1.05** |
| night, DWD 12.5% | 0.342 | **1.60** |

At its own threshold the cloud field is essentially unbiased; at one okta it becomes a 33–60%
over-forecast **purely from where the cut is made.**

## Three things to say out loud when presenting it

- **The threshold is a range, not a number.** J is flat near its optimum (day plateau 49–80%). Quote it
  to the nearest 5%.
- **The sample is small.** 144 hours decorrelating over ~5 h — effective N ≈ 5 (day) and ≈ 9 (night).
  Enough to separate 66/77% from 12.5%; not enough to rank 801 against 802.
- **A fixed threshold is most wrong where the diurnal signal is.** `tau*` swings 58% (midday) to 84%
  (03–05 UTC) across the day. Since this project is chasing a diurnally varying spin-up bias, part of a
  diurnal error pattern seen through *one* fixed threshold may be a thresholding artefact rather than
  model behaviour. Worth checking what the operational chain binarises at.

## Context

MOVERO first-guess CLCT bias, all Swiss stations: **801 +0.56 octa, 802 +0.33 octa** — both
over-forecasting cloud, 802 (T_2M/RH_2M excluded) less so. Note 1 okta *is* the DWD threshold, so a
+0.56 octa bias is over half the margin by which that threshold decides cloud/no-cloud.

---

*Time-matching convention: `conventions.md`. Everything above is derived at runtime from the files
themselves, not hardcoded.*
