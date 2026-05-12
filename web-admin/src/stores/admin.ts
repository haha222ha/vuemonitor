import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export const useAdminStore = defineStore("admin", () => {
  const token = ref(localStorage.getItem("admin_token") || "");
  const username = ref(localStorage.getItem("admin_username") || "管理员");
  const isLoggedIn = computed(() => !!token.value);

  async function login(usernameInput: string, password: string) {
    const { data } = await api.post("/admin/login", { username: usernameInput, password });
    token.value = data.access_token;
    username.value = usernameInput;
    localStorage.setItem("admin_token", data.access_token);
    localStorage.setItem("admin_username", usernameInput);
  }

  function logout() {
    token.value = "";
    username.value = "";
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_username");
  }

  return { token, username, isLoggedIn, login, logout };
});