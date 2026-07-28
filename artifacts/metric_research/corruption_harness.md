# Metric Research Corruption Harness

Status: research only. Production metrics were not changed.

## Metric Runtime

| Metric | Mean runtime ms | Practical on CPU | Multimodal-future risk |
| --- | ---: | --- | --- |
| current_visual_similarity | 0.046 | True | True |
| temporal_motion_similarity | 0.0667 | True | False |
| frame_difference_trajectory_similarity | 0.0819 | True | False |
| object_track_displacement_similarity | 0.4778 | True | True |

## Corruption Sensitivity

### frame_freeze

| Metric | Monotonic | Sensitivity | Scores |
| --- | --- | ---: | --- |
| current_visual_similarity | True | 3.4421 | [100.0, 99.8142, 99.5707, 99.0739, 96.5579] |
| temporal_motion_similarity | True | 0.9048 | [100.0, 99.6743, 99.3649, 98.9275, 99.0952] |
| frame_difference_trajectory_similarity | False | 95.6803 | [100.0, 67.475, 36.7072, 0.0, 4.3197] |
| object_track_displacement_similarity | True | 24.3068 | [100.0, 99.0793, 97.7903, 95.0282, 75.6932] |

### temporal_scramble

| Metric | Monotonic | Sensitivity | Scores |
| --- | --- | ---: | --- |
| current_visual_similarity | True | 3.1965 | [100.0, 99.5255, 98.4494, 97.7652, 96.8035] |
| temporal_motion_similarity | False | 2.1721 | [100.0, 99.1178, 97.4448, 97.0415, 97.8279] |
| frame_difference_trajectory_similarity | False | 56.7642 | [100.0, 40.0255, 0.0, 0.0, 43.2358] |
| object_track_displacement_similarity | True | 22.0971 | [100.0, 97.0537, 89.3197, 84.532, 77.9029] |

### blur

| Metric | Monotonic | Sensitivity | Scores |
| --- | --- | ---: | --- |
| current_visual_similarity | True | 0.4007 | [100.0, 99.9161, 99.7882, 99.685, 99.5993] |
| temporal_motion_similarity | True | 0.467 | [100.0, 99.8747, 99.6998, 99.5934, 99.533] |
| frame_difference_trajectory_similarity | True | 11.1826 | [100.0, 99.5729, 97.9028, 93.6997, 88.8174] |
| object_track_displacement_similarity | True | 0.0 | [100.0, 100.0, 100.0, 100.0, 100.0] |

### dropped_frames

| Metric | Monotonic | Sensitivity | Scores |
| --- | --- | ---: | --- |
| current_visual_similarity | True | 0.377 | [100.0, 99.8492, 99.623, 99.623, 99.623] |
| temporal_motion_similarity | True | 0.8226 | [100.0, 99.671, 99.1774, 99.1774, 99.1774] |
| frame_difference_trajectory_similarity | True | 86.5894 | [100.0, 65.3642, 13.4106, 13.4106, 13.4106] |
| object_track_displacement_similarity | True | 1.8414 | [100.0, 99.2634, 98.1586, 98.1586, 98.1586] |

### speed_changes

| Metric | Monotonic | Sensitivity | Scores |
| --- | --- | ---: | --- |
| current_visual_similarity | True | 1.5474 | [100.0, 99.4627, 99.0068, 98.728, 98.4526] |
| temporal_motion_similarity | True | 1.0948 | [100.0, 99.3847, 99.1544, 99.0623, 98.9052] |
| frame_difference_trajectory_similarity | True | 71.4706 | [100.0, 81.8967, 63.9505, 46.1614, 28.5294] |
| object_track_displacement_similarity | True | 8.4705 | [100.0, 97.422, 95.2123, 93.3709, 91.5295] |

### spatial_shifts

| Metric | Monotonic | Sensitivity | Scores |
| --- | --- | ---: | --- |
| current_visual_similarity | True | 0.7884 | [100.0, 99.8029, 99.6058, 99.4087, 99.2116] |
| temporal_motion_similarity | True | 0.7966 | [100.0, 99.6058, 99.2116, 99.2075, 99.2034] |
| frame_difference_trajectory_similarity | True | 0.0 | [100.0, 100.0, 100.0, 100.0, 100.0] |
| object_track_displacement_similarity | True | 8.8388 | [100.0, 97.7903, 95.5806, 93.3709, 91.1612] |
