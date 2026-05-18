import paramiko
import os
import sys

host = '8.155.5.163'
user = 'root'
pwd = 'Zpoi.1234'
remote_dir = '/opt/vuemonitor/deploy/downloads'

files = [
    r'D:\vuemonitor\client\release\XHS365-Setup-0.1.0.exe',
    r'D:\vuemonitor\client\release\XHS365-Setup-0.1.0.exe.blockmap',
    r'D:\vuemonitor\deploy\downloads\latest.yml',
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f"Connecting to {host}...")
try:
    ssh.connect(host, port=22, username=user, password=pwd, timeout=30, banner_timeout=60, auth_timeout=30)
    print("Connected!")
except Exception as e:
    print(f"Port 22 failed: {e}")
    print("Trying common alternative ports...")
    for port in [2222, 10022, 8022, 443]:
        try:
            ssh.connect(host, port=port, username=user, password=pwd, timeout=15, banner_timeout=30)
            print(f"Connected on port {port}!")
            break
        except Exception as e2:
            print(f"Port {port} failed: {e2}")
    else:
        print("All ports failed. Cannot connect to server via SSH.")
        sys.exit(1)

ssh.exec_command(f'mkdir -p {remote_dir}')

sftp = ssh.open_sftp()
for f in files:
    fname = os.path.basename(f)
    remote_path = f'{remote_dir}/{fname}'
    size = os.path.getsize(f)
    print(f"Uploading {fname} ({size / 1024 / 1024:.1f}MB)...")
    sftp.put(f, remote_path)
    print(f"  Done: {remote_path}")

sftp.close()
ssh.close()
print("\nAll files uploaded successfully!")
