"""Criteo step 2: ATE with CIs, two-model uplift, holdout evaluation, targeting policy.
Usage: python src/criteo_step2_uplift.py [csv] [outcome: visit|conversion] [sample_rows]
Tip: 'visit' (~4-5% base rate) is much less noisy than 'conversion' (~0.3%); run both."""
import sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from criteo_common import connect, sample_rows

CSV = sys.argv[1] if len(sys.argv) > 1 else "data/criteo-uplift-v2.1.csv.gz"
OUTCOME = sys.argv[2] if len(sys.argv) > 2 else "visit"
SAMPLE_N = int(sys.argv[3]) if len(sys.argv) > 3 else 3_000_000
FEATS = [f"f{i}" for i in range(12)]
rng = np.random.default_rng(42)

run, engine, _ = connect(CSV)

# ---- 1. Average treatment effect on the FULL data (computed in SQL) ----
print("=== Average treatment effect (full data, treated - control) ===")
for m in ["visit", "conversion"]:
    r = run(f"SELECT treatment, COUNT(*) n, SUM({m}) x FROM criteo GROUP BY treatment ORDER BY treatment")
    n0, x0, n1, x1 = r.n[0], r.x[0], r.n[1], r.x[1]
    p0, p1 = x0 / n0, x1 / n1
    d = p1 - p0
    se = np.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
    pool = (x0 + x1) / (n0 + n1)
    z = d / np.sqrt(pool * (1 - pool) * (1 / n0 + 1 / n1))
    print(f"{m}: control={p0:.4%} treated={p1:.4%} diff={d*100:+.4f} pp "
          f"95% CI [{(d-1.96*se)*100:+.4f}, {(d+1.96*se)*100:+.4f}] pp "
          f"relative lift={d/p0:+.1%} p={2*(1-stats.norm.cdf(abs(z))):.2g}")

# ---- 2. Two-model (T-learner) uplift on a random sample ----
print(f"\n=== Uplift model on outcome='{OUTCOME}' (sample={SAMPLE_N:,}) ===")
df = sample_rows(run, engine, SAMPLE_N)
train, hold = train_test_split(df, test_size=0.4, random_state=42, stratify=df.treatment)
params = dict(max_depth=4, learning_rate=0.05, max_iter=200, random_state=42)
m_t = HistGradientBoostingClassifier(**params).fit(train[train.treatment == 1][FEATS], train[train.treatment == 1][OUTCOME])
m_c = HistGradientBoostingClassifier(**params).fit(train[train.treatment == 0][FEATS], train[train.treatment == 0][OUTCOME])
hold = hold.copy()
hold["score"] = m_t.predict_proba(hold[FEATS])[:, 1] - m_c.predict_proba(hold[FEATS])[:, 1]

# ---- 3. Evaluate on holdout using the real randomized treatment labels ----
def seg_uplift(g):
    t, c = g[g.treatment == 1][OUTCOME], g[g.treatment == 0][OUTCOME]
    d = t.mean() - c.mean()
    se = np.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    return d, se

hold = hold.sort_values("score", ascending=False).reset_index(drop=True)
hold["decile"] = pd.qcut(hold.index, 10, labels=range(1, 11))
print("Actual uplift by predicted-uplift decile (1 = highest predicted):")
dec = []
for k, g in hold.groupby("decile", observed=True):
    d, se = seg_uplift(g)
    dec.append((int(k), len(g), d * 100, (d - 1.96 * se) * 100, (d + 1.96 * se) * 100))
dec = pd.DataFrame(dec, columns=["decile", "n", "uplift_pp", "ci_lo", "ci_hi"])
print(dec.round(4).to_string(index=False))
dec.to_csv("reports/uplift_by_decile.csv", index=False)

ate_d, _ = seg_uplift(hold)
print("\n=== Targeting policy (incremental outcomes per 1,000 users in holdout) ===")
print(f"Treat everyone: ATE = {ate_d*100:+.4f} pp -> {ate_d*1000:.2f} incremental per 1,000 users")
pol = []
for frac in [0.1, 0.2, 0.3, 0.5]:
    top = hold.iloc[: int(len(hold) * frac)]
    d, se = seg_uplift(top)
    # incremental outcomes per 1,000 *total* users if only the top `frac` is treated
    inc_policy = d * frac * 1000
    inc_all = ate_d * 1000
    pol.append((frac, d * 100, inc_policy, inc_policy / inc_all))
    print(f"Treat top {frac:.0%}: uplift in segment={d*100:+.4f} pp "
          f"(95% CI [{(d-1.96*se)*100:+.4f}, {(d+1.96*se)*100:+.4f}]) | "
          f"captures {inc_policy/inc_all:.0%} of treat-everyone's incremental outcomes "
          f"while treating {frac:.0%} of users")

# ---- 4. Qini-style curve ----
fr = np.linspace(0.02, 1, 50)
inc = []
for f in fr:
    d, _ = seg_uplift(hold.iloc[: int(len(hold) * f)])
    inc.append(d * f * 1000)
plt.figure(figsize=(6, 4))
plt.plot(fr * 100, inc, label="Model-ranked targeting")
plt.plot(fr * 100, fr * ate_d * 1000, "--", label="Random targeting")
plt.xlabel("% of users treated (highest predicted uplift first)")
plt.ylabel(f"Incremental {OUTCOME} per 1,000 users")
plt.title("Uplift gain curve (holdout)"); plt.legend(); plt.tight_layout()
plt.savefig(f"reports/qini_{OUTCOME}.png", dpi=150)
print(f"\nSaved reports/qini_{OUTCOME}.png, reports/uplift_by_decile.csv")
