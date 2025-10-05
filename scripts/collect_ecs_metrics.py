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

end = datetime.utcnow()
start = end - timedelta(hours=1)  # Last hour

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
        Period=300,  # 5 minutes
        Statistics=[metric["Stat"]],
        Unit=metric["Unit"]
    )
    datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
    # Pick the latest datapoint, or None
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
