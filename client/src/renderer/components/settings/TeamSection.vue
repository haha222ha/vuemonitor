<template>
  <div class="settings-section">
    <h2 class="section-title">团队管理</h2>
    <div class="settings-card">
      <div class="team-header">
        <el-button type="primary" @click="$emit('show-create-team')">创建团队</el-button>
        <el-button @click="$emit('fetch-teams')">刷新</el-button>
      </div>
      <div v-if="teamsLoading" style="padding: 24px"><el-skeleton :rows="3" animated /></div>
      <div v-else-if="teams.length > 0" class="team-list">
        <div v-for="team in teams" :key="team.id" class="team-item" @click="$emit('select-team', team.id)">
          <div class="team-item__info">
            <div class="team-item__name">{{ team.name }}</div>
            <div class="team-item__meta">
              <span>{{ team.member_count }} 成员</span>
              <span v-if="team.is_owner" class="team-item__owner">所有者</span>
              <span class="team-item__date">{{ team.created_at?.substring(0, 10) }}</span>
            </div>
          </div>
          <div class="team-item__actions">
            <el-button v-if="team.is_owner" size="small" text type="danger" @click.stop="$emit('delete-team', team.id)">删除</el-button>
          </div>
        </div>
      </div>
      <div v-else class="team-empty">
        <p>暂无团队</p>
        <p class="team-empty__desc">创建团队与成员共享监控规则和商品数据</p>
      </div>
    </div>

    <div v-if="currentTeam" class="settings-card" style="margin-top: 20px">
      <h3 class="section-subtitle">{{ currentTeam.name }} - 成员列表</h3>
      <div v-if="teamMembers.length > 0" class="member-list">
        <div v-for="member in teamMembers" :key="member.id" class="member-item">
          <div class="member-avatar">{{ (member.nickname || member.email || 'U')[0].toUpperCase() }}</div>
          <div class="member-info">
            <span class="member-name">{{ member.nickname || member.email }}</span>
            <el-tag size="small" :type="member.role === 'owner' ? 'warning' : member.role === 'admin' ? '' : 'info'">{{ teamRoleLabel(member.role) }}</el-tag>
          </div>
          <div class="member-actions">
            <el-button v-if="currentTeam.is_owner && member.role !== 'owner'" size="small" text type="danger" @click="$emit('remove-member', currentTeam.id, member.id)">移除</el-button>
          </div>
        </div>
      </div>
      <div v-if="currentTeam.is_owner || currentTeam.role === 'admin'" class="invite-section">
        <el-input v-model="inviteEmailModel" placeholder="输入邮箱邀请成员" style="flex: 1" />
        <el-select v-model="inviteRoleModel" style="width: 120px">
          <el-option value="member" label="成员" />
          <el-option value="viewer" label="查看者" />
          <el-option value="admin" label="管理员" />
        </el-select>
        <el-button type="primary" @click="$emit('invite-member')" :loading="inviting">邀请</el-button>
      </div>
    </div>

    <el-dialog v-model="showCreateTeamDialogModel" title="创建团队" width="480px" class="modern-dialog">
      <el-form :model="createTeamForm" label-width="80px">
        <el-form-item label="团队名称">
          <el-input v-model="createTeamForm.name" placeholder="输入团队名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createTeamForm.description" type="textarea" :rows="3" placeholder="团队描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateTeamDialogModel = false">取消</el-button>
        <el-button type="primary" :loading="creatingTeam" @click="$emit('create-team')">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  teams: any[];
  teamsLoading: boolean;
  currentTeam: any;
  teamMembers: any[];
  inviteEmail: string;
  inviteRole: string;
  inviting: boolean;
  showCreateTeamDialog: boolean;
  creatingTeam: boolean;
  createTeamForm: any;
  teamRoleLabel: (role: string) => string;
}>();

const emit = defineEmits<{
  'fetch-teams': [];
  'show-create-team': [];
  'select-team': [teamId: string];
  'delete-team': [teamId: string];
  'remove-member': [teamId: string, memberId: string];
  'invite-member': [];
  'create-team': [];
  'update:inviteEmail': [value: string];
  'update:inviteRole': [value: string];
  'update:showCreateTeamDialog': [value: boolean];
}>();

const inviteEmailModel = computed({
  get: () => props.inviteEmail,
  set: (v: string) => emit('update:inviteEmail', v),
});
const inviteRoleModel = computed({
  get: () => props.inviteRole,
  set: (v: string) => emit('update:inviteRole', v),
});
const showCreateTeamDialogModel = computed({
  get: () => props.showCreateTeamDialog,
  set: (v: boolean) => emit('update:showCreateTeamDialog', v),
});
</script>

<style scoped>
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.section-subtitle { margin: 0 0 16px; font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.team-header { display: flex; gap: 8px; margin-bottom: 16px; }
.team-list { display: flex; flex-direction: column; gap: 8px; }
.team-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--color-bg-page); border-radius: var(--radius-base); cursor: pointer; transition: all 0.2s; border: 2px solid transparent; }
.team-item:hover { border-color: var(--color-primary-light); background: var(--color-bg-card); }
.team-item__info { flex: 1; }
.team-item__name { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); margin-bottom: 4px; }
.team-item__meta { display: flex; gap: 12px; font-size: var(--text-xs); color: var(--color-text-secondary); }
.team-item__owner { color: var(--color-warning); font-weight: 500; }
.team-item__date { color: var(--color-text-tertiary); }
.team-item__actions { display: flex; gap: 4px; }
.team-empty { text-align: center; padding: 32px 0; color: var(--color-text-secondary); }
.team-empty__desc { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: 4px; }
.member-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.member-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; background: var(--color-bg-page); border-radius: var(--radius-base); }
.member-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--gradient-hero); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px; font-weight: 600; flex-shrink: 0; }
.member-info { flex: 1; display: flex; align-items: center; gap: 8px; }
.member-name { font-size: var(--text-sm); color: var(--color-text-primary); font-weight: 500; }
.member-actions { display: flex; gap: 4px; }
.invite-section { display: flex; gap: 8px; align-items: center; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.modern-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.modern-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.modern-dialog :deep(.el-dialog__body) { padding: 24px; }
.modern-dialog :deep(.el-dialog__footer) { padding: 16px 24px; border-top: 1px solid var(--color-border-light); }
@media (max-width: 768px) { .invite-section { flex-direction: column; } .invite-section .el-select { width: 100% !important; } }
</style>
