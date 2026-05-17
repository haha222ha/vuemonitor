<template>
  <div class="license fade-in">
    <PageHeader title="授权管理" subtitle="激活授权码以解锁完整功能" />

    <div class="license__content">
      <LicenseActivated
        v-if="licenseStore.isActivated"
        :license-store="licenseStore"
        :plan-tag-type="planTagType"
        :quota-items="quotaItems"
        @refresh="handleRefresh"
        @deactivate="handleDeactivate"
      />

      <LicenseActivateForm
        v-else
        :form="form"
        :rules="rules"
        :form-ref="formRef"
        :license-store="licenseStore"
        :device-info="deviceInfo"
        :format-license-key="formatLicenseKey"
        @activate="handleActivate"
      />

      <PlanComparison :plan-cards="planCards" :current-plan="licenseStore.plan" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import PageHeader from "../components/PageHeader.vue";
import LicenseActivated from "../components/license/LicenseActivated.vue";
import LicenseActivateForm from "../components/license/LicenseActivateForm.vue";
import PlanComparison from "../components/license/PlanComparison.vue";
import { useLicenseData } from "../composables/useLicenseData";

const {
  licenseStore, formRef, deviceInfo, form, rules,
  planTagType, quotaItems, planCards,
  formatLicenseKey, handleActivate, handleDeactivate, handleRefresh,
  init,
} = useLicenseData();

onMounted(() => { init(); });
</script>

<style scoped>
.license { padding: 0; }
.license__content { max-width: 800px; margin: 0 auto; }
</style>
