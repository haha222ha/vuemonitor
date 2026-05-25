import http from 'k6/http';
import { check, sleep } from 'k6';
import { getAuthHeaders, checkResponse, API_BASE } from './common.js';

export const options = {
    stages: [
        { duration: '30s', target: 1 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'],
        http_req_failed: ['rate<0.1'],
        errors: ['rate<0.1'],
    },
};

export default function () {
    const auth = getAuthHeaders();

    const healthRes = http.get(`${API_BASE.replace('/api/v1', '')}/health`);
    checkResponse(healthRes, 'health');

    const meRes = http.get(`${API_BASE}/auth/me`, auth);
    checkResponse(meRes, 'auth/me');

    const productsRes = http.get(`${API_BASE}/products`, auth);
    checkResponse(productsRes, 'products');

    const dashboardRes = http.get(`${API_BASE}/dashboard/stats`, auth);
    checkResponse(dashboardRes, 'dashboard');

    const notificationsRes = http.get(`${API_BASE}/notifications`, auth);
    checkResponse(notificationsRes, 'notifications');

    sleep(1);
}
