Experiment configuration files
==============================

Each subdirectory contains the configuration file for a single model. [`v01_drums_vel`](./v01_drums_vel/) is the main proposed model,
the rest are from the ablation study (section VI-C in the paper). **Generally, we find that [`v01_drums`](./v01_drums/) (which does not model 
velocity) performs considerably better on real-world MIDI files than the main proposed model.**

- [`v01_drums_vel`](./v01_drums_vel/model.yaml) ('dr. + vel.') supports both drums and velocity
- [`v01_drums`](./v01_drums/model.yaml) ('drums') does not support velocity
- [`v01_vel`](./v01_vel/model.yaml) ('velocity') does not support drums
- [`v01`](./v01/model.yaml) ('none') supports neither of the above
- [`v01_drums_vel_perf`](./v01_drums_vel_perf/model.yaml) ('dr. + vel. + 𝛥') is like `v01_drums_vel`, but uses the 𝛥-encoding

To use the [pre-trained model checkpoints](https://groove2groove.telecom-paris.fr/data/checkpoints/), extract them inside this directory (the checkpoint files for each model should end up next to the corresponding `model.yaml` file).
