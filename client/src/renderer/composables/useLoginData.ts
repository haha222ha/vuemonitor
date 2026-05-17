import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

export function useLoginData() {
  const router = useRouter();
  const authStore = useAuthStore();
  const loading = ref(false);
  const regLoading = ref(false);
  const showRegister = ref(false);
  const loginFormRef = ref<FormInstance>();
  const regFormRef = ref<FormInstance>();

  const form = reactive({ account: "", password: "" });
  const regForm = reactive({ email: "", nickname: "", password: "" });

  const loginRules: FormRules = {
    account: [{ required: true, message: "请输入昵称或邮箱", trigger: "blur" }],
    password: [{ required: true, message: "请输入密码", trigger: "blur" }],
  };

  const emailPattern = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;

  const regRules: FormRules = {
    nickname: [
      { required: true, message: "请输入昵称", trigger: "blur" },
      { min: 2, max: 20, message: "昵称长度2-20个字符", trigger: "blur" },
    ],
    email: [
      {
        validator: (_rule: any, value: string, callback: any) => {
          if (!value || value.trim() === "") {
            callback();
          } else if (!emailPattern.test(value.trim())) {
            callback(new Error("邮箱格式不正确"));
          } else {
            callback();
          }
        },
        trigger: "blur",
      },
    ],
    password: [
      { required: true, message: "请输入密码", trigger: "blur" },
      { min: 8, message: "密码至少8位", trigger: "blur" },
      {
        validator: (_rule: any, value: string, callback: any) => {
          if (value && !/[A-Z]/.test(value)) {
            callback(new Error("密码需包含大写字母"));
          } else if (value && !/[a-z]/.test(value)) {
            callback(new Error("密码需包含小写字母"));
          } else if (value && !/[0-9]/.test(value)) {
            callback(new Error("密码需包含数字"));
          } else {
            callback();
          }
        },
        trigger: "blur",
      },
    ],
  };

  async function handleLogin() {
    const valid = await loginFormRef.value?.validate().catch(() => false);
    if (!valid) return;
    loading.value = true;
    try {
      await authStore.login(form.account, form.password);
      router.push("/dashboard");
      ElMessage.success("登录成功");
    } catch {
      ElMessage.error("登录失败，请检查账号和密码");
    } finally {
      loading.value = false;
    }
  }

  async function handleRegister() {
    const valid = await regFormRef.value?.validate().catch(() => false);
    if (!valid) return;
    regLoading.value = true;
    try {
      await authStore.register(regForm.email || undefined, regForm.nickname, regForm.password);
      ElMessage.success("注册成功，请登录");
      showRegister.value = false;
      form.account = regForm.nickname;
      form.password = regForm.password;
      regForm.email = "";
      regForm.nickname = "";
      regForm.password = "";
    } catch (e: any) {
      const msg = e?.response?.data?.message || e?.message || "注册失败，请稍后重试";
      ElMessage.error(msg);
    } finally {
      regLoading.value = false;
    }
  }

  return {
    loading, regLoading, showRegister,
    loginFormRef, regFormRef,
    form, regForm, loginRules, regRules,
    handleLogin, handleRegister,
  };
}
