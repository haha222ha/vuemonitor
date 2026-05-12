import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const BASE_PATH = import.meta.env.BASE_URL || "/admin/";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("admin_token");
      const loginPath = `${BASE_PATH}login`.replace(/\/+/g, "/");
      window.location.href = loginPath;
    }
    return Promise.reject(error);
  }
);

export default api;
