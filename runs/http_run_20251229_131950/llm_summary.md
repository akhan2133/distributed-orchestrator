**Summary of Baseline vs Failure Run**

The failure run showed some notable differences compared to the baseline:
* **Throughput**: The run's average throughput (11.34 rps) was 4.35% higher than the baseline (10.87 rps), despite failure injection.
* **Latency**: 
  * P50 latency decreased by 0.73 ms (from 90.92 ms to 90.19 ms).
  * P95 latency increased by 5.72 ms (from 115.91 ms to 121.62 ms).
* **Error rate**: The run experienced an error rate of 7.79%, whereas the baseline had no errors.
* **Anomaly windows**: Three anomaly windows were detected:
  * 30-47 seconds
  * 49-50 seconds
  * 81 seconds
* **Recovery time**: The system took approximately 51 seconds to recover from the failure. This indicates that the system can recover relatively quickly, which is a positive sign for reliability. However, the presence of anomalies and a non-zero error rate suggest that there is still room for improvement to ensure high reliability.