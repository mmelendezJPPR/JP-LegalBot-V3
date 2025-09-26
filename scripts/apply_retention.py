#!/usr/bin/env python3
import argparse
from ai_system.privacy import apply_retention_policy

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=365, help='Retention days')
args = parser.parse_args()
res = apply_retention_policy(retention_days=args.days)
print('Retention result:', res)
