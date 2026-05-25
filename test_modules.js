const http = require('http');

function api(method, path, token, body) {
  return new Promise((resolve, reject) => {
    const strBody = body ? JSON.stringify(body) : null;
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    if (strBody) headers['Content-Length'] = Buffer.byteLength(strBody);
    const req = http.request({
      hostname: '47.239.181.111', port: 8000, path: path,
      method: method, headers: headers, timeout: 15000
    }, res => {
      let b = ''; res.on('data', c => b += c);
      res.on('end', () => resolve({ status: res.statusCode, body: b.substring(0, 2000) }));
    });
    req.on('error', e => resolve({ err: e.message }));
    if (strBody) req.write(strBody);
    req.end();
  });
}

async function main() {
  const login = await api('POST', '/api/v1/auth/login', null, { account: 'dev@test.com', password: 'DevTest2024' });
  const loginData = JSON.parse(login.body);
  const token = loginData.access_token;
  console.log('LOGIN OK, token:', token.substring(0, 30) + '...\n');

  const endpoints = [
    ['GET', '/api/v1/discovery/hot-goods'],
    ['GET', '/api/v1/discovery/rising-goods'],
    ['GET', '/api/v1/discovery/stats'],
    ['GET', '/api/v1/sync/status'],
  ];
  for (const [m, p] of endpoints) {
    const r = await api(m, p, token);
    console.log(m + ' ' + p + ' -> ' + r.status + ' | ' + (r.body || r.err || ''));
  }
}
main().catch(e => console.error(e));