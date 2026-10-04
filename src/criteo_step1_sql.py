"""Criteo step 1: SQL checks, covariate balance, heterogeneity by feature quartile.
Usage: python src/criteo_step1_sql.py [path_to_csv_or_gz]"""
import sys, re
import numpy as np, pandas as pd
from criteo_common import connect

CSV = sys.argv[1] if len(sys.argv) > 1 else "data/criteo-uplift-v2.1.csv.gz"
run, engine, _ = connect(CSV)
n = run("SELECT COUNT(*) AS n FROM criteo")["n"][0]
print(f"Engine: {engine} | rows loaded: {n:,}\n")
pd.set_option("display.width", 160)

sql_text = open("sql/01_criteo_checks.sql").read()
queries = [q.strip() for q in sql_text.split(";") if "SELECT" in q]
for t, q in zip(re.findall(r"-- (Q\d\..*)", sql_text), queries):
    print(t); print(run(q).to_string(index=False), "\n")

# Standardized mean difference for every feature (|SMD| < 0.1 = well balanced)
print("Covariate balance (standardized mean difference, treated - control):")
smd = {}
for i in range(12):
    f = f"f{i}"
    r = run(f"SELECT treatment, AVG({f}) m, AVG({f}*{f}) - AVG({f})*AVG({f}) v FROM criteo GROUP BY treatment ORDER BY treatment")
    pooled_sd = np.sqrt((r.v[0] + r.v[1]) / 2)
    smd[f] = (r.m[1] - r.m[0]) / pooled_sd
print(pd.Series(smd).round(4).to_string(), "\n")

# Heterogeneity: effect within value-based quartiles of each feature, with 95% CIs.
# (Cut points computed once; ties stay in one bucket, so results are reproducible.)
def cutpoints(f):
    try:
        r = run(f"SELECT quantile_cont({f}, 0.25) a, quantile_cont({f}, 0.5) b, quantile_cont({f}, 0.75) c FROM criteo")
        return float(r.a[0]), float(r.b[0]), float(r.c[0])
    except Exception:
        v = run(f"SELECT {f} FROM criteo")[f].values
        return tuple(float(x) for x in np.quantile(v, [0.25, 0.5, 0.75]))

def diff_ci(x0, n0, x1, n1):
    p0, p1 = x0 / n0, x1 / n1
    se = np.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
    d = p1 - p0
    return d * 100, (d - 1.96 * se) * 100, (d + 1.96 * se) * 100

tmpl = open("sql/02_criteo_hte_template.sql").read()
rows = []
for i in range(12):
    f = f"f{i}"
    q1, q2, q3 = cutpoints(f)
    d = run(tmpl.format(feat=f, q1=q1, q2=q2, q3=q3))
    for b, g in d.groupby("bucket"):
        if set(g.treatment) != {0, 1}:
            continue
        c, t = g[g.treatment == 0].iloc[0], g[g.treatment == 1].iloc[0]
        v, vlo, vhi = diff_ci(c.visit_sum, c.n, t.visit_sum, t.n)
        cv, clo, chi = diff_ci(c.conv_sum, c.n, t.conv_sum, t.n)
        rows.append({"feature": f, "bucket": int(b), "n_ctrl": int(c.n), "n_trt": int(t.n),
                     "visit_uplift_pp": v, "visit_lo": vlo, "visit_hi": vhi,
                     "conv_uplift_pp": cv, "conv_lo": clo, "conv_hi": chi})
hte = pd.DataFrame(rows)
print("Uplift (treated - control, pp) by feature bucket, with 95% CI:")
print(hte.round(3).to_string(index=False))
hte.to_csv("reports/hte_by_feature_bucket.csv", index=False)
spread = hte.groupby("feature").visit_uplift_pp.agg(lambda s: s.max() - s.min()).sort_values(ascending=False)
print("\nFeatures with largest visit-uplift spread across buckets:\n", spread.round(3).head(5).to_string())
