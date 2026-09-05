from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.operational_alert import AlertRule, AlertRuleActuatorModel, AlertRuleActuatorModelProfile, AlertRuleProfile, AlertRuleRevision, AlertRuleSensorModel, AlertRuleSensorModelProfile
from app.models.actuator_model import ActuatorModelFeedbackDefinition
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.schemas.operational_alert import AlertRuleCreate, AlertRuleProfileCreate, AlertRuleProfileRead, AlertRuleRead, AlertRuleRevisionCreate, RuleValidationRead
from app.services.alert_evaluators import validate_condition_config
from app.services.audit_service import write_audit

router = APIRouter(prefix="/admin/alert-rules", tags=["Global alert rules"])

def _load_rule_query():
    return select(AlertRule).options(selectinload(AlertRule.current_revision), selectinload(AlertRule.revisions), selectinload(AlertRule.sensor_models), selectinload(AlertRule.actuator_models)).execution_options(populate_existing=True)


async def _rule(db: AsyncSession, rule_id: int) -> AlertRule:
    item = await db.scalar(_load_rule_query().where(AlertRule.id == rule_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy tắc cảnh báo")
    return item


async def _missing_configuration(db: AsyncSession, item: AlertRule, revision: AlertRuleRevision) -> list[str]:
    missing = validate_condition_config(item.evaluator_type, revision.condition_config)
    if not missing:
        return []
    profiles = list((await db.scalars(select(AlertRuleProfile).where(AlertRuleProfile.rule_id == item.id, AlertRuleProfile.is_enabled.is_(True)))).all())
    if profiles and all(not validate_condition_config(item.evaluator_type, {**revision.condition_config, **profile.config}) for profile in profiles):
        return []
    return missing


@router.get("", response_model=list[AlertRuleRead])
async def list_rules(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> list[AlertRule]:
    del admin
    return list((await db.scalars(_load_rule_query().order_by(AlertRule.code))).unique().all())


@router.get("/{rule_id}", response_model=AlertRuleRead)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> AlertRule:
    del admin
    return await _rule(db, rule_id)


@router.get("/{rule_id}/profiles", response_model=list[AlertRuleProfileRead])
async def list_profiles(rule_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> list[AlertRuleProfileRead]:
    del admin
    await _rule(db, rule_id)
    profiles = list((await db.scalars(select(AlertRuleProfile).where(AlertRuleProfile.rule_id == rule_id).order_by(AlertRuleProfile.name))).all())
    actuator_links = (await db.execute(select(AlertRuleActuatorModelProfile.profile_id, AlertRuleActuatorModelProfile.actuator_model_id).where(AlertRuleActuatorModelProfile.profile_id.in_([item.id for item in profiles])))).all() if profiles else []
    sensor_links = (await db.execute(select(AlertRuleSensorModelProfile.profile_id, AlertRuleSensorModelProfile.sensor_model_id).where(AlertRuleSensorModelProfile.profile_id.in_([item.id for item in profiles])))).all() if profiles else []
    return [AlertRuleProfileRead.model_validate({
        "id": item.id, "rule_id": item.rule_id, "code": item.code, "name": item.name,
        "config": item.config, "is_enabled": item.is_enabled, "created_at": item.created_at,
        "updated_at": item.updated_at,
        "actuator_model_ids": [model_id for profile_id, model_id in actuator_links if profile_id == item.id],
        "sensor_model_ids": [model_id for profile_id, model_id in sensor_links if profile_id == item.id],
    }) for item in profiles]


@router.post("/{rule_id}/profiles", response_model=AlertRuleProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(rule_id: int, payload: AlertRuleProfileCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> AlertRuleProfile:
    item = await _rule(db, rule_id)
    merged = {**(item.current_revision.condition_config if item.current_revision else {}), **payload.config}
    missing = validate_condition_config(item.evaluator_type, merged)
    if missing:
        raise HTTPException(status_code=409, detail={"message": "Hồ sơ còn thiếu cấu hình", "missing_fields": missing})
    if item.target_type == "SENSOR":
        if payload.actuator_model_ids or not payload.sensor_model_ids:
            raise HTTPException(status_code=422, detail="Quy tắc cảm biến phải chọn ít nhất một Mẫu cảm biến")
        sensor_models = list((await db.scalars(select(SensorModel).where(SensorModel.id.in_(set(payload.sensor_model_ids)), SensorModel.is_active.is_(True), SensorModel.is_deleted.is_(False)))).all())
        if len(sensor_models) != len(set(payload.sensor_model_ids)):
            raise HTTPException(status_code=422, detail="Có Mẫu cảm biến không khả dụng")
        expected_unit = merged.get("unit") or merged.get("expected_unit")
        if expected_unit and any(model.unit != expected_unit for model in sensor_models):
            raise HTTPException(status_code=422, detail=f"Đơn vị Mẫu cảm biến phải là {expected_unit}")
        if len({model.unit for model in sensor_models}) > 1:
            raise HTTPException(status_code=422, detail="Các Mẫu cảm biến trong cùng hồ sơ phải có cùng đơn vị")
    else:
        if payload.sensor_model_ids or not payload.actuator_model_ids:
            raise HTTPException(status_code=422, detail="Quy tắc cơ cấu chấp hành phải chọn ít nhất một Mẫu cơ cấu chấp hành")
        feedback_role = str(merged.get("feedback_role") or "RUNNING_CURRENT")
        configured_ids = set((await db.scalars(select(ActuatorModelFeedbackDefinition.actuator_model_id).where(ActuatorModelFeedbackDefinition.actuator_model_id.in_(set(payload.actuator_model_ids)), ActuatorModelFeedbackDefinition.feedback_role == feedback_role, ActuatorModelFeedbackDefinition.is_enabled.is_(True)))).all())
        if configured_ids != set(payload.actuator_model_ids):
            label = "Điện áp cấp" if feedback_role == "SUPPLY_VOLTAGE" else "Dòng điện hoạt động"
            raise HTTPException(status_code=422, detail=f"Mỗi Mẫu cơ cấu chấp hành đã chọn phải có phản hồi {label}")
    profile = AlertRuleProfile(rule_id=rule_id, code=payload.code, name=payload.name, config=payload.config, is_enabled=True)
    db.add(profile)
    try:
        await db.flush()
        db.add_all([AlertRuleActuatorModelProfile(profile_id=profile.id, actuator_model_id=model_id) for model_id in set(payload.actuator_model_ids)])
        db.add_all([AlertRuleSensorModelProfile(profile_id=profile.id, sensor_model_id=model_id) for model_id in set(payload.sensor_model_ids)])
        existing_actuator_ids = set((await db.scalars(select(AlertRuleActuatorModel.actuator_model_id).where(AlertRuleActuatorModel.rule_id == rule_id))).all())
        existing_sensor_ids = set((await db.scalars(select(AlertRuleSensorModel.sensor_model_id).where(AlertRuleSensorModel.rule_id == rule_id))).all())
        db.add_all([AlertRuleActuatorModel(rule_id=rule_id, actuator_model_id=model_id) for model_id in set(payload.actuator_model_ids) - existing_actuator_ids])
        db.add_all([AlertRuleSensorModel(rule_id=rule_id, sensor_model_id=model_id) for model_id in set(payload.sensor_model_ids) - existing_sensor_ids])
        await write_audit(db, user_id=admin.id, action="ALERT_RULE_PROFILE_CREATED", entity_type="ALERT_RULE", entity_id=item.id, new_data={"rule_code": item.code, "profile_code": profile.code, "actuator_model_ids": payload.actuator_model_ids, "sensor_model_ids": payload.sensor_model_ids})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Mã hồ sơ hoặc liên kết model đã tồn tại") from exc
    await db.refresh(profile)
    return profile


@router.post("", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(payload: AlertRuleCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> AlertRule:
    missing = validate_condition_config(payload.evaluator_type, payload.revision.condition_config)
    item = AlertRule(code=payload.code, name=payload.name, target_type=payload.target_type, evaluator_type=payload.evaluator_type, is_enabled=True)
    db.add(item)
    try:
        await db.flush()
        revision = AlertRuleRevision(rule_id=item.id, revision=1, status="INCOMPLETE" if missing else "DRAFT", created_by=admin.id, source_reference="Tạo trên giao diện quản trị", source_order=0, **payload.revision.model_dump())
        db.add(revision)
        await db.flush()
        item.current_revision_id = revision.id
        await write_audit(db, user_id=admin.id, action="ALERT_RULE_CREATED", entity_type="ALERT_RULE", entity_id=item.id, new_data={"code": item.code, "revision": 1})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Mã quy tắc đã tồn tại") from exc
    return await _rule(db, item.id)


@router.post("/{rule_id}/revisions", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_revision(rule_id: int, payload: AlertRuleRevisionCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> AlertRule:
    item = await _rule(db, rule_id)
    next_revision = int(await db.scalar(select(func.max(AlertRuleRevision.revision)).where(AlertRuleRevision.rule_id == rule_id)) or 0) + 1
    missing = validate_condition_config(item.evaluator_type, payload.condition_config)
    revision = AlertRuleRevision(rule_id=rule_id, revision=next_revision, status="INCOMPLETE" if missing else "DRAFT", created_by=admin.id, source_reference="Bản sửa đổi trên giao diện quản trị", source_order=item.current_revision.source_order if item.current_revision else 0, **payload.model_dump())
    db.add(revision)
    await db.flush()
    item.current_revision_id = revision.id
    await write_audit(db, user_id=admin.id, action="ALERT_RULE_REVISION_CREATED", entity_type="ALERT_RULE", entity_id=item.id, new_data={"code": item.code, "revision": next_revision})
    await db.commit()
    return await _rule(db, rule_id)


@router.post("/{rule_id}/validate", response_model=RuleValidationRead)
async def validate_rule(rule_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> RuleValidationRead:
    item = await _rule(db, rule_id)
    revision = item.current_revision
    if revision is None:
        return RuleValidationRead(valid=False, missing_fields=["revision"])
    missing = await _missing_configuration(db, item, revision)
    if revision.status not in {"PUBLISHED", "RETIRED"}:
        revision.status = "INCOMPLETE" if missing else "VALIDATED"
        await db.commit()
    return RuleValidationRead(valid=not missing, missing_fields=missing)


@router.post("/{rule_id}/publish", response_model=AlertRuleRead)
async def publish_rule(rule_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> AlertRule:
    item = await _rule(db, rule_id)
    revision = item.current_revision
    if revision is None:
        raise HTTPException(status_code=409, detail="Quy tắc chưa có bản sửa đổi")
    missing = await _missing_configuration(db, item, revision)
    if missing:
        raise HTTPException(status_code=409, detail={"message": "Quy tắc còn thiếu cấu hình", "missing_fields": missing})
    if revision.status == "RETIRED":
        raise HTTPException(status_code=409, detail="Bản sửa đổi đã ngừng sử dụng")
    previous = list((await db.scalars(select(AlertRuleRevision).where(AlertRuleRevision.rule_id == rule_id, AlertRuleRevision.status == "PUBLISHED", AlertRuleRevision.id != revision.id))).all())
    for old in previous:
        old.status = "RETIRED"
    revision.status = "PUBLISHED"
    revision.published_by = admin.id
    revision.published_at = datetime.now(UTC)
    item.is_enabled = True
    await write_audit(db, user_id=admin.id, action="ALERT_RULE_PUBLISHED", entity_type="ALERT_RULE", entity_id=item.id, new_data={"code": item.code, "revision": revision.revision})
    await db.commit()
    return await _rule(db, rule_id)


@router.post("/{rule_id}/retire", response_model=AlertRuleRead)
async def retire_rule(rule_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)) -> AlertRule:
    item = await _rule(db, rule_id)
    published = list((await db.scalars(select(AlertRuleRevision).where(AlertRuleRevision.rule_id == rule_id, AlertRuleRevision.status == "PUBLISHED"))).all())
    for revision in published:
        revision.status = "RETIRED"
    item.is_enabled = False
    await write_audit(db, user_id=admin.id, action="ALERT_RULE_RETIRED", entity_type="ALERT_RULE", entity_id=item.id, new_data={"code": item.code})
    await db.commit()
    return await _rule(db, rule_id)
