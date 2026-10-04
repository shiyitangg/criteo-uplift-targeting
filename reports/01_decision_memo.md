# Decision Memo: Who Should Receive the Ad Campaign?

**To:** Marketing / Advertising Analytics  **From:** Shiyi Tang  **Date:** October 2026
**Decision requested:** Target everyone, or only a subset of users?

## Recommendation
**Target the top 20–30% of users ranked by predicted uplift, rather than everyone.** Start with the top 20%; extend to 30% if the cost per targeted user is low. Do not extend beyond 30%: returns per additional user fall sharply.

## Evidence
Data: 13,979,592 users from a randomized experiment (85% treated, 15% control). Covariate balance between arms was verified on all 12 features (all |SMD| < 0.05).

- **Ads work on average.** Assignment to the ad group raised conversions from 0.194% to 0.309% (+0.115 pp, 95% CI [0.109, 0.122]) and site visits from 3.82% to 4.85% (+1.03 pp, CI [1.01, 1.06]).
- **The effect is uneven.** Visit uplift ranges from about 0.05 pp to 9.4 pp across user segments, with non-overlapping confidence intervals.
- **A model can find the responsive users.** On a randomized holdout (users the model never saw):

| Target only the top… | Share of "target everyone" incremental conversions captured | Same, for visits |
|---|---|---|
| 10% | ~58% | ~60% |
| **20%** | **~74%** | ~80% |
| **30%** | **~78%** | ~88% |
| 50% | ~82% | ~94% |

Users in the top conversion decile had an actual uplift of +0.63 pp (CI [0.48, 0.78]), about six times the holdout average of +0.11 pp.

**Diminishing returns (approximate, derived from the table above).** Moving from the top 20% to 30% adds roughly 1 incremental conversion per 2,000 additional users targeted; from 30% to 50%, roughly 1 per 4,000. Targeting beyond 30% pays only if each targeted user costs very little relative to the value of a conversion.

## Risks and limitations
- **No cost or revenue data.** The analysis shows efficiency, not profit. Break-even depends on cost per targeted user versus value per conversion; the 30% cutoff should be revisited once those are known.
- **Intent-to-treat.** Only ~3.6% of treated users actually saw an ad, so all effects describe being assigned to the campaign, not seeing an ad.
- **Ranking is imperfect.** The model's lowest-scored decile showed a significantly positive conversion uplift (+0.16 pp, CI [0.09, 0.23]), so some responsive users are missed.
- **Single holdout split.** The percentages above are point estimates from one split and were not repeated across random seeds.
- **Anonymized features.** Drivers of response cannot be interpreted in business terms.

## Next steps
1. Run a live validation: within the targeted group, keep a randomized holdout with no ads to confirm the predicted uplift.
2. Add cost and revenue inputs to turn the 20% vs 30% choice into a profit calculation.
3. Repeat the evaluation across several random splits and compare against a model built specifically to estimate uplift.
4. Retrain periodically; user response patterns drift.
