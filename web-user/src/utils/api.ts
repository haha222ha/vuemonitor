import axios from "axios";
import { ElMessage } from "element-plus";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_info");
      if (window.location.pathname.startsWith("/dashboard")) {
        window.location.href = "/login";
      }
    } else if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message);
    }
    return Promise.reject(error);
  }
);

export default api;
