### Fine-tuning post-sorting artifact detection
Sometimes physiological units are detected as artifacts. If this happens often in your data, it is probably a good idea to change the `artifact_criteria` in `options.py`.

The following criteria refer to the mean waveform of a unit.

Name | Value | Unit is an artifact if...
-----|-------|---------------------------
`maxima` | 5 | it has more than _5_ local maxima
`maxima_1_2_ration` | 2 | its largest maximum is less than _twice_ its second largest maximum
`max_min_ratio` | 1.5 | its largest maximum is less than _1.5_ times its minimum
`ptp` | 1 | its maximum is less than _once_ the peak-to-peak value in the second half

A cluster is marked as an artifact if it meets _any_ of these criteria.

The output of `css-combine` shows which of the artifact criteria each cluster meets. Use `css-combine --no-plots` to quickly check modified values of `artifact_criteria`.
