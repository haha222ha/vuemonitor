import os
import re

files_to_fix = [
    'client/src/main/collect/chromium-worker.ts',
    'client/src/main/collect/concurrency-controller.ts',
    'client/src/main/collect/data-mart.ts',
    'client/src/main/collect/local-scheduler.ts',
    'client/src/main/communication/ws-client.ts',
    'client/src/main/license/license-manager.ts',
    'client/src/main/permission/permission-cache.ts',
    'client/src/main/recovery/crash-recovery.ts',
    'client/src/main/services/performance-monitor.ts',
    'client/src/main/sync/cloud-sync.ts',
    'client/src/main/update/auto-updater.ts',
]

total = 0
for fpath in files_to_fix:
    full = os.path.join('d:/vuemonitor', fpath)
    if not os.path.exists(full):
        continue
    with open(full, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace('logger.warning(', 'logger.warn(')
    
    if new_content != content:
        count = content.count('logger.warning(')
        with open(full, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {count} logger.warning -> logger.warn in {fpath}')
        total += count

print(f'\nTotal: {total}')
