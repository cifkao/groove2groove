Experiment configuration files
==============================

Each subdirectory corresponds to one model from the paper. [`v01_drums_vel`](./v01_drums_vel/) is the main proposed model,
the rest are from the ablation study (section VI-C in the paper). **Generally, we find that [`v01_drums`](./v01_drums/) (which does not model 
elocity) performs considerably better on real-world MIDI files than the main proposed model.**

- [`v01_drums_vel`](./v01_drums_vel/) ('dr. + vel.') supports both drums and velocity
- [`v01_drums`](./v01_drums/) ('drums') does not support velocity
- [`v01_vel`](./v01_vel/) ('velocity') does not support drums
- [`v01`](./v01/) ('none') supports neither of the above
- [`v01_drums_vel_perf`](./v01_drums_vel_perf/) ('dr. + vel. + 𝛥') is like `v01_drums_vel`, but uses the 𝛥-encoding
