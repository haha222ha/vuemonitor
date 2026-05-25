import http from 'k6/http';
import { check, sleep } from 'k6';
import { getAuthHeaders, checkResponse, API_BASE } from './common.js';

export const options = {
    stages: [
        { duration: '30s', target: 200 },
        { duration: '3m', target: 500 },
        { duration: '30s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<5000'],
        http_req_failed: ['rate<0.1'],
        errors: ['rate<0.1'],
    },
};

export default function () {
    const auth = getAuthHeaders();

    const res = http.get(`${API_BASE}/products`, auth);
    checkResponse(res, 'products');

    if (Math.random() < 0.3) {
        const dashboardRes = http.get(`${API_BASE}/dashboard/stats`, auth);
        checkResponse(dashboardRes, 'dashboard');
    }

    if (Math.random() < 0.1) {
        const createRes = http.post(`${API_BASE}/products`, JSON.stringify({
            name: `StressTest_${__VU}_${Date.now()}`,
            url: `https://xiaohongshu.com/item/test_${__VU}`,
            platform: 'xhs',
        }), auth);
        checkResponse(createRes, 'create-product', 201);
    }

    sleep(Math.random() * 0.5);
}
