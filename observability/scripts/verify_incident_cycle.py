"""Read-only PagerDuty observer for an authorized local Grafana incident exercise."""

import argparse
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=720)
    args = parser.parse_args()
    config = dotenv_values(root / 'observability/.env', interpolate=False)
    spec = importlib.util.spec_from_file_location('bridge', root / 'observability/chart/files/discord_bridge.py')
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    started = datetime.now(timezone.utc)
    report = {'started_at': started.isoformat(), 'environment': 'local-compose',
              'service_id': config['PAGERDUTY_SERVICE_ID'], 'events': [], 'completed': False}
    seen = {}
    deadline = time.monotonic() + args.seconds
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    save()
    print('Observing new FIAP local test incidents; no events or messages are sent.', flush=True)
    while time.monotonic() < deadline:
        try:
            incidents = bridge.list_incidents(config['PAGERDUTY_API_TOKEN'], config['PAGERDUTY_SERVICE_ID'])
        except Exception as error:
            # URLs or headers from exceptions must never expose credentials.
            print('Read failed: ' + type(error).__name__, flush=True)
            time.sleep(10)
            continue
        for incident in incidents:
            if not incident.get('title', '').startswith('[FIAP TESTE LOCAL]'):
                continue
            created = datetime.fromisoformat(incident['created_at'].replace('Z', '+00:00'))
            if created < started:
                continue
            incident_id, status = incident['id'], incident['status']
            previous = seen.get(incident_id)
            if previous == status:
                continue
            seen[incident_id] = status
            event = {'observed_at': datetime.now(timezone.utc).isoformat(), 'incident_id': incident_id,
                     'status': status, 'title': incident['title'], 'created_at': incident['created_at']}
            report['events'].append(event)
            if status == 'resolved' and previous in ('triggered', 'acknowledged'):
                report['completed'] = True
            save()
            print(json.dumps(event), flush=True)
        if report['completed']:
            print('PagerDuty opening and resolution confirmed; verify Discord delivery separately.', flush=True)
            return
        time.sleep(10)
    raise SystemExit('Timed out without observing a complete PagerDuty cycle')


if __name__ == '__main__':
    main()
