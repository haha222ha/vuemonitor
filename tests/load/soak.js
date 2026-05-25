import http from 'k6/http';
import { check, sleep } from 'k6';
import { getAuthHeaders, checkResponse, API_BASE } from './common.js';

export const options = {
    stages: [
        { duration: '5m', target: 50 },
        { duration: '20m', target: 50 },
        { duration: '5m', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<3000'],
        http_req_failed: ['rate<0.05'],
        errors: ['rate<0.05'],
    },
};

export default function () {
    const auth = getAuthHeaders();

    const res = http.get(`${API_BASE}/products`, auth);
    checkResponse(res, 'products');

    const dashboardRes = http.get(`${API_BASE}/dashboard/stats`, auth);
    checkResponse(dashboardRes, 'dashboard');

    sleep(Math.random() * 3 + 2);
}
