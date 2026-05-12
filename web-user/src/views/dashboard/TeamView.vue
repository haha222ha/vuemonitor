<template>
  <div class="team-page">
    <div class="page-header">
      <h2>团队协作</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建团队
      </el-button>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="team-list-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>我的团队</span>
              <el-input v-model="searchQuery" placeholder="搜索团队..." prefix-icon="Search" clearable size="small" style="width: 200px" />
            </div>
          </template>
          <div v-if="filteredTeams.length === 0" class="empty-state">
            <el-empty description="暂无团队，创建一个开始协作吧" />
          </div>
          <div v-else class="team-grid">
            <div v-for="team in filteredTeams" :key="team.id" class="team-card" @click="selectTeam(team)">
              <div class="team-card-header">
                <el-avatar :size="40" :style="{ background: getTeamColor(team.name) }">
                  {{ team.name[0] }}
                </el-avatar>
                <div class="team-card-info">
                  <div class="team-name">{{ team.name }}</div>
                  <div class="team-desc">{{ team.description || "暂无描述" }}</div>
                </div>
              </div>
              <div class="team-card-meta">
                <span><el-icon><User /></el-icon> {{ team.member_count || 1 }} 成员</span>
                <el-tag size="small" :type="getRoleTagType(team.my_role)">{{ getRoleLabel(team.my_role) }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="invite-card">
          <template #header><span>邀请加入</span></template>
          <el-form @submit.prevent="handleInvite">
            <el-form-item label="邀请码">
              <el-input v-model="inviteToken" placeholder="输入邀请码加入团队" />
            </el-form-item>
            <el-button type="primary" :loading="inviteLoading" @click="handleInvite" style="width: 100%">加入团队</el-button>
          </el-form>
        </el-card>

        <el-card v-if="selectedTeam" shadow="never" class="detail-card" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>{{ selectedTeam.name }}</span>
              <el-dropdown v-if="selectedTeam.my_role === 'owner' || selectedTeam.my_role === 'admin'" trigger="click">
                <el-button :icon="MoreFilled" circle size="small" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="showEditDialog = true">编辑团队</el-dropdown-item>
                    <el-dropdown-item @click="confirmDeleteTeam" divided style="color: #f56c6c">解散团队</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
          <div class="detail-section">
            <h4>成员列表</h4>
            <div class="member-list">
              <div v-for="member in teamMembers" :key="member.id" class="member-item">
                <el-avatar :size="28">{{ member.nickname?.[0] || "?" }}</el-avatar>
                <span class="member-name">{{ member.nickname || member.email }}</span>
                <el-tag size="small" :type="getRoleTagType(member.role)">{{ getRoleLabel(member.role) }}</el-tag>
                <el-button
                  v-if="canManageMembers && member.role !== 'owner'"
                  :icon="Delete"
                  circle
                  size="small"
                  text
                  type="danger"
                  @click="removeMember(member)"
                />
              </div>
            </div>
            <el-button
              v-if="canManageMembers"
              type="primary"
              link
              size="small"
              @click="showInviteDialog = true"
              style="margin-top: 8px"
            >
              + 邀请成员
            </el-button>
          </div>

          <div class="detail-section" style="margin-top: 16px">
            <h4>共享资源</h4>
            <el-tabs v-model="sharedTab">
              <el-tab-pane label="监控规则" name="rules">
                <div v-if="sharedRules.length === 0" class="empty-hint">暂无共享规则</div>
                <div v-for="rule in sharedRules" :key="rule.id" class="shared-item">
                  <span>{{ rule.name || "未命名规则" }}</span>
                  <el-tag size="small" type="info">{{ rule.can_edit ? "可编辑" : "只读" }}</el-tag>
                </div>
              </el-tab-pane>
              <el-tab-pane label="商品" name="products">
                <div v-if="sharedProducts.length === 0" class="empty-hint">暂无共享商品</div>
                <div v-for="product in sharedProducts" :key="product.id" class="shared-item">
                  <span>{{ product.product_name || product.platform_product_id }}</span>
                  <el-tag size="small" type="info">{{ product.can_edit ? "可编辑" : "只读" }}</el-tag>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="showCreateDialog" title="创建团队" width="480px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="团队名称" required>
          <el-input v-model="createForm.name" placeholder="输入团队名称" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="团队描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="描述团队用途" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditDialog" title="编辑团队" width="480px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="团队名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="团队描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showInviteDialog" title="邀请成员" width="480px">
      <el-form :model="inviteForm" label-width="80px">
        <el-form-item label="邮箱" required>
          <el-input v-model="inviteForm.email" placeholder="输入成员邮箱" type="email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="inviteForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="成员" value="member" />
            <el-option label="观察者" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInviteDialog = false">取消</el-button>
        <el-button type="primary" :loading="inviteMemberLoading" @click="handleInviteMember">发送邀请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, User, Delete, MoreFilled } from "@element-plus/icons-vue";
import api from "../../utils/api";

interface Team {
  id: string;
  name: string;
  description?: string;
  my_role: string;
  member_count?: number;
  created_at?: string;
}

interface Member {
  id: string;
  user_id: string;
  nickname?: string;
  email?: string;
  role: string;
}

const teams = ref<Team[]>([]);
const selectedTeam = ref<Team | null>(null);
const teamMembers = ref<Member[]>([]);
const sharedRules = ref<any[]>([]);
const sharedProducts = ref<any[]>([]);
const searchQuery = ref("");
const sharedTab = ref("rules");

const showCreateDialog = ref(false);
const showEditDialog = ref(false);
const showInviteDialog = ref(false);
const createLoading = ref(false);
const editLoading = ref(false);
const inviteLoading = ref(false);
const inviteMemberLoading = ref(false);

const createForm = ref({ name: "", description: "" });
const editForm = ref({ name: "", description: "" });
const inviteForm = ref({ email: "", role: "member" });
const inviteToken = ref("");

const filteredTeams = computed(() => {
  if (!searchQuery.value) return teams.value;
  const q = searchQuery.value.toLowerCase();
  return teams.value.filter((t) => t.name.toLowerCase().includes(q) || (t.description || "").toLowerCase().includes(q));
});

const canManageMembers = computed(() => {
  if (!selectedTeam.value) return false;
  return ["owner", "admin"].includes(selectedTeam.value.my_role);
});

function getTeamColor(name: string) {
  const colors = ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#06b6d4"];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function getRoleLabel(role: string) {
  const map: Record<string, string> = { owner: "所有者", admin: "管理员", member: "成员", viewer: "观察者" };
  return map[role] || role;
}

function getRoleTagType(role: string) {
  const map: Record<string, string> = { owner: "danger", admin: "warning", member: "", viewer: "info" };
  return map[role] || "info";
}

async function fetchTeams() {
  try {
    const { data } = await api.get("/teams");
    teams.value = data?.data?.items || data?.data || [];
  } catch {
    teams.value = [];
  }
}

async function selectTeam(team: Team) {
  selectedTeam.value = team;
  editForm.value = { name: team.name, description: team.description || "" };
  await Promise.all([fetchMembers(team.id), fetchShared(team.id)]);
}

async function fetchMembers(teamId: string) {
  try {
    const { data } = await api.get(`/teams/${teamId}/members`);
    teamMembers.value = data?.data || [];
  } catch {
    teamMembers.value = [];
  }
}

async function fetchShared(teamId: string) {
  try {
    const { data } = await api.get(`/teams/${teamId}/shared`);
    sharedRules.value = data?.data?.rules || [];
    sharedProducts.value = data?.data?.products || [];
  } catch {
    sharedRules.value = [];
    sharedProducts.value = [];
  }
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning("请输入团队名称");
    return;
  }
  createLoading.value = true;
  try {
    await api.post("/teams", createForm.value);
    ElMessage.success("团队创建成功");
    showCreateDialog.value = false;
    createForm.value = { name: "", description: "" };
    await fetchTeams();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "创建失败");
  } finally {
    createLoading.value = false;
  }
}

async function handleEdit() {
  if (!selectedTeam.value) return;
  editLoading.value = true;
  try {
    await api.put(`/teams/${selectedTeam.value.id}`, editForm.value);
    ElMessage.success("团队信息已更新");
    showEditDialog.value = false;
    await fetchTeams();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "更新失败");
  } finally {
    editLoading.value = false;
  }
}

async function confirmDeleteTeam() {
  if (!selectedTeam.value) return;
  try {
    await ElMessageBox.confirm("确定要解散该团队吗？此操作不可恢复。", "解散团队", { type: "warning" });
    await api.delete(`/teams/${selectedTeam.value.id}`);
    ElMessage.success("团队已解散");
    selectedTeam.value = null;
    await fetchTeams();
  } catch {}
}

async function handleInvite() {
  if (!inviteToken.value.trim()) {
    ElMessage.warning("请输入邀请码");
    return;
  }
  inviteLoading.value = true;
  try {
    await api.post(`/teams/invitations/${inviteToken.value.trim()}/accept`);
    ElMessage.success("已加入团队");
    inviteToken.value = "";
    await fetchTeams();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "加入失败");
  } finally {
    inviteLoading.value = false;
  }
}

async function handleInviteMember() {
  if (!selectedTeam.value || !inviteForm.value.email.trim()) {
    ElMessage.warning("请输入邮箱");
    return;
  }
  inviteMemberLoading.value = true;
  try {
    await api.post(`/teams/${selectedTeam.value.id}/invite`, inviteForm.value);
    ElMessage.success("邀请已发送");
    showInviteDialog.value = false;
    inviteForm.value = { email: "", role: "member" };
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "邀请失败");
  } finally {
    inviteMemberLoading.value = false;
  }
}

async function removeMember(member: Member) {
  try {
    await ElMessageBox.confirm(`确定要移除成员 ${member.nickname || member.email} 吗？`, "移除成员", { type: "warning" });
    await api.delete(`/teams/${selectedTeam.value!.id}/members/${member.user_id}`);
    ElMessage.success("成员已移除");
    await fetchMembers(selectedTeam.value!.id);
  } catch {}
}

onMounted(() => {
  fetchTeams();
});
</script>

<style scoped>
.team-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  color: #e0e0e6;
  font-size: 20px;
  margin: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #e0e0e6;
}

.team-list-card,
.invite-card,
.detail-card {
  background: #1a1a24;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.team-list-card :deep(.el-card__header),
.invite-card :deep(.el-card__header),
.detail-card :deep(.el-card__header) {
  border-bottom-color: rgba(255, 255, 255, 0.06);
  color: #e0e0e6;
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.team-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.team-card:hover {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.3);
}

.team-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.team-card-info {
  flex: 1;
  min-width: 0;
}

.team-name {
  color: #e0e0e6;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.team-desc {
  color: #6a6a7a;
  font-size: 12px;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.team-card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #8a8a9a;
}

.team-card-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-state {
  padding: 40px 0;
}

.detail-section h4 {
  color: #e0e0e6;
  font-size: 14px;
  margin: 0 0 12px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
}

.member-name {
  flex: 1;
  color: #c0c0cc;
  font-size: 13px;
}

.shared-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: #c0c0cc;
  font-size: 13px;
}

.empty-hint {
  color: #6a6a7a;
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
}
</style>
