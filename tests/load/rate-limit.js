import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const API_BASE = __ENV.API_BASE || 'http://localhost:8000/api/v1';
const rateLimitTriggered = new Rate('rate_limit_triggered');

export const options = {
    stages: [
        { duration: '10s', target: 10 },
        { duration: '20s', target: 10 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        rate_limit_triggered: ['rate > 0'],
    },
};

export default function () {
    const email = `ratelimit_${__VU}@test.com`;
    const body = JSON.stringify({ email, password: 'wrong_password' });
    const headers = { 'Content-Type': 'application/json' };

    const res = http.post(`${API_BASE}/auth/login`, body, { headers });

    const is429 = res.status === 429;
    rateLimitTriggered.add(is429);

    check(res, {
        'login responded': (r) => r.status === 200 || r.status === 401 || r.status === 429,
    });

    sleep(0.5);
}
