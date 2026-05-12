import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.middleware.auth import CurrentUser
from app.models.user import User
from app.models.team import Team, TeamMember, TeamSharedRule, TeamSharedProduct, TeamInvitation
from app.models.monitor import MonitorRule
from app.models.product import Product

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    role: str = Field("member", pattern="^(admin|member|viewer)$")


class ShareRuleRequest(BaseModel):
    rule_id: str
    can_edit: bool = False


class ShareProductRequest(BaseModel):
    product_id: str
    can_edit: bool = False


@router.post("")
async def create_team(
    req: TeamCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = Team(
        name=req.name,
        description=req.description,
        owner_id=user.id,
    )
    db.add(team)
    await db.flush()

    member = TeamMember(
        team_id=team.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db.add(member)
    await db.flush()

    return {"code": 0, "data": {"id": str(team.id), "name": team.name}}


@router.get("")
async def list_teams(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Team).join(TeamMember).where(TeamMember.user_id == user.id, TeamMember.status == "active")
    )
    teams = result.scalars().all()

    items = []
    for t in teams:
        member_count = (await db.execute(
            select(func.count()).select_from(TeamMember).where(
                TeamMember.team_id == t.id, TeamMember.status == "active"
            )
        )).scalar() or 0

        items.append({
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "owner_id": str(t.owner_id),
            "is_owner": t.owner_id == user.id,
            "member_count": member_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {"code": 0, "data": items}


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db)

    members_result = await db.execute(
        select(TeamMember, User).join(User, TeamMember.user_id == User.id).where(
            TeamMember.team_id == team.id, TeamMember.status == "active"
        )
    )
    members = []
    for member, u in members_result.all():
        members.append({
            "id": str(member.id),
            "user_id": str(u.id),
            "nickname": u.nickname,
            "email": u.email,
            "avatar_url": u.avatar_url,
            "role": member.role,
            "joined_at": member.created_at.isoformat() if member.created_at else None,
        })

    return {
        "code": 0,
        "data": {
            "id": str(team.id),
            "name": team.name,
            "description": team.description,
            "owner_id": str(team.owner_id),
            "is_owner": team.owner_id == user.id,
            "members": members,
            "created_at": team.created_at.isoformat() if team.created_at else None,
        },
    }


@router.put("/{team_id}")
async def update_team(
    team_id: str,
    req: TeamUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="admin")

    if req.name is not None:
        team.name = req.name
    if req.description is not None:
        team.description = req.description

    return {"code": 0, "message": "更新成功"}


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="owner")
    await db.delete(team)
    return {"code": 0, "message": "团队已删除"}


@router.post("/{team_id}/invite")
async def invite_member(
    team_id: str,
    req: InviteMemberRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="admin")

    target = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not target:
        raise NotFoundException(message="该邮箱用户不存在")

    existing = (await db.execute(
        select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == target.id)
    )).scalar_one_or_none()
    if existing and existing.status == "active":
        raise BadRequestException(message="该用户已在团队中")

    token = secrets.token_hex(32)
    invitation = TeamInvitation(
        team_id=team.id,
        inviter_id=user.id,
        invitee_email=req.email,
        role=req.role,
        token=token,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()

    return {"code": 0, "data": {"invitation_id": str(invitation.id), "token": token}}


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    invitation = (await db.execute(
        select(TeamInvitation).where(TeamInvitation.token == token, TeamInvitation.status == "pending")
    )).scalar_one_or_none()

    if not invitation:
        raise NotFoundException(message="邀请不存在或已过期")
    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        raise BadRequestException(message="邀请已过期")

    target_user = (await db.execute(select(User).where(User.email == invitation.invitee_email))).scalar_one_or_none()
    if not target_user or target_user.id != user.id:
        raise ForbiddenException(message="此邀请不是发给您的")

    member = TeamMember(
        team_id=invitation.team_id,
        user_id=user.id,
        role=invitation.role,
        invited_by=invitation.inviter_id,
        status="active",
    )
    db.add(member)
    invitation.status = "accepted"
    await db.flush()

    return {"code": 0, "message": "已加入团队"}


@router.delete("/{team_id}/members/{member_id}")
async def remove_member(
    team_id: str,
    member_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="admin")

    member = (await db.execute(
        select(TeamMember).where(TeamMember.id == uuid.UUID(member_id), TeamMember.team_id == team.id)
    )).scalar_one_or_none()
    if not member:
        raise NotFoundException(message="成员不存在")
    if member.role == "owner":
        raise ForbiddenException(message="不能移除团队所有者")

    await db.delete(member)
    return {"code": 0, "message": "成员已移除"}


@router.post("/{team_id}/share/rule")
async def share_rule(
    team_id: str,
    req: ShareRuleRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="admin")

    rule = (await db.execute(
        select(MonitorRule).where(MonitorRule.id == uuid.UUID(req.rule_id), MonitorRule.user_id == user.id)
    )).scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="监控规则不存在")

    existing = (await db.execute(
        select(TeamSharedRule).where(
            TeamSharedRule.team_id == team.id, TeamSharedRule.rule_id == rule.id
        )
    )).scalar_one_or_none()
    if existing:
        existing.can_edit = req.can_edit
        return {"code": 0, "message": "共享权限已更新"}

    shared = TeamSharedRule(
        team_id=team.id,
        rule_id=rule.id,
        shared_by=user.id,
        can_edit=req.can_edit,
    )
    db.add(shared)
    await db.flush()

    return {"code": 0, "message": "规则已共享"}


@router.post("/{team_id}/share/product")
async def share_product(
    team_id: str,
    req: ShareProductRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="admin")

    product = (await db.execute(
        select(Product).where(Product.id == uuid.UUID(req.product_id), Product.user_id == user.id)
    )).scalar_one_or_none()
    if not product:
        raise NotFoundException(message="商品不存在")

    existing = (await db.execute(
        select(TeamSharedProduct).where(
            TeamSharedProduct.team_id == team.id, TeamSharedProduct.product_id == product.id
        )
    )).scalar_one_or_none()
    if existing:
        existing.can_edit = req.can_edit
        return {"code": 0, "message": "共享权限已更新"}

    shared = TeamSharedProduct(
        team_id=team.id,
        product_id=product.id,
        shared_by=user.id,
        can_edit=req.can_edit,
    )
    db.add(shared)
    await db.flush()

    return {"code": 0, "message": "商品已共享"}


@router.get("/{team_id}/shared")
async def list_shared(
    team_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_with_access(team_id, user.id, db, min_role="member")

    shared_rules = (await db.execute(
        select(TeamSharedRule).where(TeamSharedRule.team_id == team.id)
    )).scalars().all()

    shared_products = (await db.execute(
        select(TeamSharedProduct).where(TeamSharedProduct.team_id == team.id)
    )).scalars().all()

    return {
        "code": 0,
        "data": {
            "rules": [
                {
                    "id": str(r.id),
                    "rule_id": str(r.rule_id),
                    "shared_by": str(r.shared_by),
                    "can_edit": r.can_edit,
                }
                for r in shared_rules
            ],
            "products": [
                {
                    "id": str(p.id),
                    "product_id": str(p.product_id),
                    "shared_by": str(p.shared_by),
                    "can_edit": p.can_edit,
                }
                for p in shared_products
            ],
        },
    }


ROLE_HIERARCHY = {"owner": 3, "admin": 2, "member": 1, "viewer": 0}


async def _get_team_with_access(
    team_id: str,
    user_id: uuid.UUID,
    db: AsyncSession,
    min_role: str = "member",
) -> Team:
    team = (await db.execute(select(Team).where(Team.id == uuid.UUID(team_id)))).scalar_one_or_none()
    if not team:
        raise NotFoundException(message="团队不存在")

    member = (await db.execute(
        select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user_id, TeamMember.status == "active")
    )).scalar_one_or_none()

    if not member:
        raise ForbiddenException(message="您不是该团队成员")

    required_level = ROLE_HIERARCHY.get(min_role, 0)
    user_level = ROLE_HIERARCHY.get(member.role, 0)

    if user_level < required_level:
        raise ForbiddenException(message="权限不足")

    return team
