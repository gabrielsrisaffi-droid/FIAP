"""Create an isolated, ignored Terraform directory for a confirmed Academy account.

Copies only source and provider locks, never prior state, backend metadata or secrets.
Does not call AWS or Terraform and never overwrites an existing destination.
"""

import argparse
import ipaddress
import json
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account', required=True)
    parser.add_argument('--operator-ip', required=True)
    args = parser.parse_args()
    if len(args.account) != 12 or not args.account.isdigit():
        parser.error('Expected a 12-digit account ID')
    address = ipaddress.IPv4Address(args.operator_ip)
    root = Path(__file__).resolve().parents[2]
    relative = Path('tmp') / ('phase4-aws-' + args.account)
    target = root / relative
    if target.exists():
        raise SystemExit('Destination already exists; review and reuse it without overwriting')
    check = subprocess.run(['git', 'check-ignore', '-q', '--', (relative / 'probe').as_posix()],
                           cwd=root, capture_output=True)
    if check.returncode != 0:
        raise SystemExit('Destination must be ignored by Git before preparation')
    for name in ('bootstrap', 'platform'):
        source, destination = root / 'infra' / name, target / name
        destination.mkdir(parents=True)
        for path in list(source.glob('*.tf')) + list(source.glob('.terraform.lock.hcl')):
            shutil.copy2(path, destination / path.name)
        # Provider override pins the account even if the local credential profile changes.
        (destination / 'account_override.tf').write_text(
            'provider "aws" {\n  allowed_account_ids = ["' + args.account + '"]\n'
            '  default_tags {\n    tags = { Project = "togglemaster", Phase = "4", '
            'Environment = "academy-lab", ManagedBy = "Terraform" }\n  }\n}\n', encoding='utf-8')
    bucket = 'togglemaster-fase4-tfstate-' + args.account
    (target / 'bootstrap' / 'terraform.tfvars.json').write_text(json.dumps(
        {'bucket_prefix': 'togglemaster-fase4-tfstate', 'aws_region': 'us-east-1'}, indent=2), encoding='utf-8')
    settings = {'aws_region': 'us-east-1', 'enable_eks': True, 'enable_rds': True,
                'enable_redis': True, 'eks_node_desired_size': 2, 'eks_node_min_size': 2,
                'eks_node_max_size': 2, 'eks_public_access_cidrs': [str(address) + '/32']}
    (target / 'platform' / 'terraform.tfvars.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    (target / 'platform' / 'backend.hcl').write_text(
        'bucket = "' + bucket + '"\nkey = "platform/terraform.tfstate"\nregion = "us-east-1"\n'
        'encrypt = true\nuse_lockfile = true\n', encoding='utf-8')
    print('Prepared isolated Terraform source at ' + str(target))
    print('No previous state was copied. Account guard, private databases and /32 EKS access configured.')


if __name__ == '__main__':
    main()
