import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const API_BASE = __ENV.API_BASE || 'http://localhost:8000/api/v1';
const errorRate = new Rate('errors');
const latencyTrend = new Trend('api_latency');

export function getAuthHeaders() {
    const email = `loadtest_${__VU}@test.com`;
    const registerRes = http.post(`${API_BASE}/auth/register`, JSON.stringify({
        email,
        password: 'LoadTest2024!',
        display_name: `VU${__VU}`,
    }), { headers: { 'Content-Type': 'application/json' } });

    let token;
    if (registerRes.status === 200 || registerRes.status === 201) {
        token = registerRes.json('data.access_token') || registerRes.json('access_token');
    }

    if (!token) {
        const loginRes = http.post(`${API_BASE}/auth/login`, JSON.stringify({
            email,
            password: 'LoadTest2024!',
        }), { headers: { 'Content-Type': 'application/json' } });
        token = loginRes.json('data.access_token') || loginRes.json('access_token');
    }

    return { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
}

export function checkResponse(res, name, expectedStatus = 200) {
    const passed = check(res, {
        [`${name} status ${expectedStatus}`]: (r) => r.status === expectedStatus,
    });
    errorRate.add(!passed);
    latencyTrend.add(res.timings.duration);
    return passed;
}

export { API_BASE, errorRate, latencyTrend };
