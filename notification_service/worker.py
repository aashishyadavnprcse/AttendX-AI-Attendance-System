"""
AttendX Notification Service — CLI & Microservice Worker Entrypoint
Can be launched as a background cron daemon or executed on-demand via CLI flags.
"""

import argparse
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from notification_service.scheduler import start_scheduler, execute_daily_parent_alerts


def main():
    parser = argparse.ArgumentParser(
        description="AttendX Automated WhatsApp Parent Notification Microservice"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Execute the absence detection and notification job immediately once.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the scan and preview dynamic messages without dispatching live messages.",
    )

    args = parser.parse_args()

    if args.run_now or args.dry_run:
        execute_daily_parent_alerts(dry_run=args.dry_run)
    else:
        start_scheduler()


if __name__ == "__main__":
    main()
