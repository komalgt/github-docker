import boto3
import csv
from datetime import datetime, timedelta
import os

REGION = os.environ.get('AWS_DEFAULT_REGION', 'ap-south-1')
CLUSTER = os.environ['ECS_CLUSTER']
SERVICE = os.environ['ECS_SERVICE']
OUTFILE = "ecs_metrics.csv"

cloudwatch = boto3.client('cloudwatch', region_name=REGION)

METRICS = [
    {"MetricName": "CPUUtilization", "Stat": "Average", "Unit": "Percent"},
    {"MetricName": "MemoryUtilization", "Stat": "Average", "Unit": "Percent"},
    {"MetricName": "RunningTaskCount", "Stat": "Average", "Unit": "Count"},
    # Add more ECS metrics as needed
]

# Set time range to October 3rd, 2025 (UTC)
start = datetime(2025, 10, 5, 0, 0, 0)   # 2025-10-03 00:00:00 UTC
end   = datetime(2025, 10, 7, 23, 59, 59) # 2025-10-03 23:59:59 UTC

def get_metric(metric):
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/ECS',
        MetricName=metric["MetricName"],
        Dimensions=[
            {'Name': 'ClusterName', 'Value': CLUSTER},
            {'Name': 'ServiceName', 'Value': SERVICE},
        ],
        StartTime=start,
        EndTime=end,
        Period=3600,  # 1 hour granularity
        Statistics=[metric["Stat"]],
        Unit=metric["Unit"]
    )
    datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
    return datapoints[-1][metric["Stat"]] if datapoints else None

with open(OUTFILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Metric", "Value", "TimeRange"])
    for metric in METRICS:
        value = get_metric(metric)
        writer.writerow([
            metric["MetricName"],
            value if value is not None else "n/a",
            f"{start.isoformat()} to {end.isoformat()}"
        ])

print(f"Metrics written to {OUTFILE}")
