import http from 'k6/http';
import { check, sleep } from 'k6';
import { getAuthHeaders, checkResponse, API_BASE } from './common.js';

export const options = {
    stages: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<3000'],
        http_req_failed: ['rate<0.05'],
        errors: ['rate<0.05'],
    },
};

export default function () {
    const auth = getAuthHeaders();

    const endpoints = [
        { name: 'products', fn: () => http.get(`${API_BASE}/products`, auth) },
        { name: 'dashboard', fn: () => http.get(`${API_BASE}/dashboard/stats`, auth) },
        { name: 'monitor-rules', fn: () => http.get(`${API_BASE}/monitor/rules`, auth) },
        { name: 'notifications', fn: () => http.get(`${API_BASE}/notifications`, auth) },
        { name: 'ai-templates', fn: () => http.get(`${API_BASE}/ai/templates`, auth) },
    ];

    const idx = Math.floor(Math.random() * endpoints.length);
    const endpoint = endpoints[idx];
    const res = endpoint.fn();
    checkResponse(res, endpoint.name);

    sleep(Math.random() * 2 + 1);
}
