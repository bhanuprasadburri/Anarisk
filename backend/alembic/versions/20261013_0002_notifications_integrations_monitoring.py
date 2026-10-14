"""notifications, integration configs, monitoring targets, password reset tokens, case evidence links,
user preferences; evidence_records.entity_id becomes nullable (evidence can be unlinked from an entity).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- users.preferences (notification/UI preferences) ----
    op.add_column('users', sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # ---- evidence may be unlinked from its entity (entity_id -> nullable) ----
    op.alter_column('evidence_records', 'entity_id', existing_type=sa.Uuid(), nullable=True)

    # ---- notifications ----
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('link_url', sa.String(length=512), nullable=True),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.Uuid(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    )
    op.create_index(op.f('ix_notifications_user_created'), 'notifications', ['user_id', sa.text('created_at DESC')], unique=False)
    op.create_index(op.f('ix_notifications_user_unread'), 'notifications', ['user_id', 'is_read'], unique=False)

    # ---- password reset tokens ----
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_reset_tokens_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_password_reset_tokens')),
        sa.UniqueConstraint('token_hash', name=op.f('uq_password_reset_tokens_token_hash')),
    )
    op.create_index(op.f('ix_password_reset_tokens_user'), 'password_reset_tokens', ['user_id'], unique=False)

    # ---- integration configs ----
    op.create_table(
        'integration_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=True),
        sa.Column('provider_key', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('config_encrypted', sa.Text(), nullable=True),
        sa.Column('config_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('connected_by_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('not_configured', 'configured', 'error')", name=op.f('ck_integration_configs_status_values')),
        sa.ForeignKeyConstraint(['connected_by_id'], ['users.id'], name=op.f('fk_integration_configs_connected_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_integration_configs_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_integration_configs')),
        sa.UniqueConstraint('organization_id', 'provider_key', name='uq_integration_configs_org_provider'),
    )
    op.create_index(op.f('ix_integration_configs_organization_id'), 'integration_configs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_integration_configs_provider_key'), 'integration_configs', ['provider_key'], unique=False)

    # ---- monitoring targets ----
    op.create_table(
        'monitoring_targets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('brand_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('package_id', sa.String(length=255), nullable=False),
        sa.Column('store', sa.String(length=32), nullable=False),
        sa.Column('store_url', sa.Text(), nullable=True),
        sa.Column('monitoring_status', sa.String(length=16), nullable=False),
        sa.Column('entity_id', sa.Uuid(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("monitoring_status IN ('active', 'paused')", name=op.f('ck_monitoring_targets_monitoring_status_values')),
        sa.CheckConstraint("store IN ('google_play', 'app_store', 'other')", name=op.f('ck_monitoring_targets_store_values')),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], name=op.f('fk_monitoring_targets_brand_id_brands'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_monitoring_targets_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entity_id'], ['digital_entities.id'], name=op.f('fk_monitoring_targets_entity_id_digital_entities'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_monitoring_targets')),
        sa.UniqueConstraint('brand_id', 'package_id', name='uq_monitoring_targets_brand_package'),
    )
    op.create_index(op.f('ix_monitoring_targets_brand_id'), 'monitoring_targets', ['brand_id'], unique=False)
    op.create_index(op.f('ix_monitoring_targets_entity_id'), 'monitoring_targets', ['entity_id'], unique=False)

    # ---- case <-> evidence links ----
    op.create_table(
        'case_evidence',
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('evidence_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('added_by_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['added_by_id'], ['users.id'], name=op.f('fk_case_evidence_added_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['case_id'], ['investigation_cases.id'], name=op.f('fk_case_evidence_case_id_investigation_cases'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_records.id'], name=op.f('fk_case_evidence_evidence_id_evidence_records'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('case_id', 'evidence_id', name=op.f('pk_case_evidence')),
    )
    op.create_index(op.f('ix_case_evidence_evidence_id'), 'case_evidence', ['evidence_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_case_evidence_evidence_id'), table_name='case_evidence')
    op.drop_table('case_evidence')
    op.drop_index(op.f('ix_monitoring_targets_entity_id'), table_name='monitoring_targets')
    op.drop_index(op.f('ix_monitoring_targets_brand_id'), table_name='monitoring_targets')
    op.drop_table('monitoring_targets')
    op.drop_index(op.f('ix_integration_configs_provider_key'), table_name='integration_configs')
    op.drop_index(op.f('ix_integration_configs_organization_id'), table_name='integration_configs')
    op.drop_table('integration_configs')
    op.drop_index(op.f('ix_password_reset_tokens_user'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_index(op.f('ix_notifications_user_unread'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_created'), table_name='notifications')
    op.drop_table('notifications')
    op.alter_column('evidence_records', 'entity_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_column('users', 'preferences')
