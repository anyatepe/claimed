#!/usr/bin/env python3
"""
Generate a simple metrics report from Locust CSV output.
"""

import csv
import sys
import os
from pathlib import Path


def parse_locust_stats(csv_file):
    """Parse Locust stats CSV and extract key metrics."""
    stats = {}
    
    if not os.path.exists(csv_file):
        print(f"Error: Stats file not found: {csv_file}")
        return None
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Type'] == 'Aggregated':
                stats = {
                    'total_requests': int(row['Request Count']),
                    'failures': int(row['Failure Count']),
                    'median_response_time': float(row['Median Response Time']),
                    'avg_response_time': float(row['Average Response Time']),
                    'min_response_time': float(row['Min Response Time']),
                    'max_response_time': float(row['Max Response Time']),
                    'requests_per_second': float(row['Requests/s']),
                    'p50': float(row['50%']),
                    'p66': float(row['66%']),
                    'p75': float(row['75%']),
                    'p80': float(row['80%']),
                    'p90': float(row['90%']),
                    'p95': float(row['95%']),
                    'p98': float(row['98%']),
                    'p99': float(row['99%']),
                    'p100': float(row['100%']),
                }
                break
    
    return stats


def generate_report(stats, output_file='metrics_report.txt'):
    """Generate a human-readable metrics report."""
    if not stats:
        print("No stats available to generate report.")
        return
    
    report = []
    report.append("=" * 60)
    report.append("SUMMARIZATION API LOAD TEST METRICS REPORT")
    report.append("=" * 60)
    report.append("")
    
    # Overall Statistics
    report.append("OVERALL STATISTICS")
    report.append("-" * 60)
    report.append(f"Total Requests:        {stats['total_requests']:,}")
    report.append(f"Failed Requests:       {stats['failures']:,}")
    success_rate = ((stats['total_requests'] - stats['failures']) / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
    report.append(f"Success Rate:          {success_rate:.2f}%")
    report.append(f"Requests per Second:   {stats['requests_per_second']:.2f} RPS")
    report.append("")
    
    # Response Time Statistics
    report.append("RESPONSE TIME STATISTICS (milliseconds)")
    report.append("-" * 60)
    report.append(f"Minimum:               {stats['min_response_time']:.2f} ms")
    report.append(f"Average:               {stats['avg_response_time']:.2f} ms")
    report.append(f"Median (P50):          {stats['median_response_time']:.2f} ms")
    report.append(f"Maximum:               {stats['max_response_time']:.2f} ms")
    report.append("")
    
    # Percentiles
    report.append("PERCENTILE STATISTICS (milliseconds)")
    report.append("-" * 60)
    report.append(f"50th percentile (P50): {stats['p50']:.2f} ms")
    report.append(f"66th percentile (P66): {stats['p66']:.2f} ms")
    report.append(f"75th percentile (P75): {stats['p75']:.2f} ms")
    report.append(f"80th percentile (P80): {stats['p80']:.2f} ms")
    report.append(f"90th percentile (P90): {stats['p90']:.2f} ms")
    report.append(f"95th percentile (P95): {stats['p95']:.2f} ms")
    report.append(f"98th percentile (P98): {stats['p98']:.2f} ms")
    report.append(f"99th percentile (P99): {stats['p99']:.2f} ms")
    report.append(f"100th percentile (P100): {stats['p100']:.2f} ms")
    report.append("")
    
    report.append("=" * 60)
    
    report_text = "\n".join(report)
    
    # Print to console
    print(report_text)
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(report_text)
    
    print(f"\nReport saved to: {output_file}")


def main():
    """Main function."""
    # Default CSV file location
    csv_file = "reports/stats_stats.csv"
    
    # Allow override via command line argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    output_file = "metrics_report.txt"
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print(f"Parsing Locust stats from: {csv_file}")
    stats = parse_locust_stats(csv_file)
    
    if stats:
        generate_report(stats, output_file)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
