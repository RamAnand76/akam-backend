"""initial

Revision ID: 0001
Revises: 
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('device_id', sa.String(length=200), nullable=False),
    sa.Column('fcm_token', sa.String(length=500), nullable=True),
    sa.Column('device_platform', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('token_generation', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_device_id'), 'users', ['device_id'], unique=False)
    op.create_table('clusters',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('card_style', sa.String(length=50), nullable=False),
    sa.Column('color_accent', sa.String(length=7), nullable=True),
    sa.Column('centroid', sa.Text(), nullable=True),
    sa.Column('member_count', sa.Integer(), nullable=False),
    sa.Column('is_manual', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('last_active', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clusters_user_id'), 'clusters', ['user_id'], unique=False)
    op.create_table('events',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('emoji', sa.String(length=10), nullable=True),
    sa.Column('date_start', sa.Date(), nullable=False),
    sa.Column('date_end', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('linked_cluster_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_user_id'), 'events', ['user_id'], unique=False)
    op.create_table('folders',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('parent_id', sa.String(length=36), nullable=True),
    sa.Column('item_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_folders_user_id'), 'folders', ['user_id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('client_message_id', sa.String(length=36), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('input_mode', sa.String(length=10), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('parent_message_id', sa.String(length=36), nullable=True),
    sa.Column('branch_depth', sa.Integer(), nullable=False),
    sa.Column('branch_index', sa.Integer(), nullable=False),
    sa.Column('display_mode', sa.String(length=30), nullable=False),
    sa.Column('suggested_replies', sa.Text(), nullable=False),
    sa.Column('intent_detected', sa.String(length=50), nullable=True),
    sa.Column('session_date', sa.Date(), nullable=False),
    sa.Column('embedding', sa.Text(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['parent_message_id'], ['messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_parent_message_id'), 'messages', ['parent_message_id'], unique=False)
    op.create_index(op.f('ix_messages_user_id'), 'messages', ['user_id'], unique=False)
    op.create_index('ix_messages_user_parent', 'messages', ['user_id', 'parent_message_id'], unique=False)
    op.create_index('ix_messages_user_session', 'messages', ['user_id', 'session_date'], unique=False)
    op.create_table('nodes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('display_type', sa.String(length=50), nullable=False),
    sa.Column('body_preview', sa.Text(), nullable=True),
    sa.Column('tags', sa.Text(), nullable=False),
    sa.Column('pos_x', sa.Float(), nullable=True),
    sa.Column('pos_y', sa.Float(), nullable=True),
    sa.Column('embedding', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('metadata_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('last_active', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_nodes_user_id'), 'nodes', ['user_id'], unique=False)
    op.create_index('ix_nodes_user_type', 'nodes', ['user_id', 'type'], unique=False)
    op.create_table('notifications',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.String(length=500), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('nudges',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('priority', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('person_node_id', sa.String(length=36), nullable=True),
    sa.Column('cluster_id', sa.String(length=36), nullable=True),
    sa.Column('pattern_id', sa.String(length=36), nullable=True),
    sa.Column('cta_primary_json', sa.Text(), nullable=True),
    sa.Column('cta_secondary_json', sa.Text(), nullable=True),
    sa.Column('deep_link', sa.String(length=500), nullable=True),
    sa.Column('action_taken', sa.String(length=50), nullable=True),
    sa.Column('shown', sa.Boolean(), nullable=False),
    sa.Column('shown_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_nudges_user_id'), 'nudges', ['user_id'], unique=False)
    op.create_index('ix_nudges_user_shown', 'nudges', ['user_id', 'shown'], unique=False)
    op.create_table('patterns',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patterns_user_id'), 'patterns', ['user_id'], unique=False)
    op.create_table('recommendations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('subtitle', sa.String(length=200), nullable=True),
    sa.Column('action_type', sa.String(length=50), nullable=False),
    sa.Column('meta_data', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendations_user_id'), 'recommendations', ['user_id'], unique=False)
    op.create_table('relationship_scores',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('person_node_id', sa.String(length=36), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('delta', sa.String(length=20), nullable=False),
    sa.Column('delta_direction', sa.String(length=10), nullable=False),
    sa.Column('last_computed', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_relationship_scores_person_node_id'), 'relationship_scores', ['person_node_id'], unique=False)
    op.create_index(op.f('ix_relationship_scores_user_id'), 'relationship_scores', ['user_id'], unique=False)
    op.create_table('user_preferences',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('timezone', sa.String(length=50), nullable=False),
    sa.Column('quiet_hours_start', sa.String(length=5), nullable=False),
    sa.Column('quiet_hours_end', sa.String(length=5), nullable=False),
    sa.Column('sunday_digest_enabled', sa.Boolean(), nullable=False),
    sa.Column('nudges_per_day', sa.Integer(), nullable=False),
    sa.Column('types_enabled', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)
    op.create_table('cluster_edges',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('cluster_a', sa.String(length=36), nullable=False),
    sa.Column('cluster_b', sa.String(length=36), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('shared_count', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['cluster_a'], ['clusters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['cluster_b'], ['clusters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cluster_a', 'cluster_b', name='uq_cluster_pair')
    )
    op.create_index(op.f('ix_cluster_edges_cluster_a'), 'cluster_edges', ['cluster_a'], unique=False)
    op.create_index(op.f('ix_cluster_edges_cluster_b'), 'cluster_edges', ['cluster_b'], unique=False)
    op.create_index(op.f('ix_cluster_edges_user_id'), 'cluster_edges', ['user_id'], unique=False)
    op.create_table('edges',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('source_node_id', sa.String(length=36), nullable=False),
    sa.Column('target_node_id', sa.String(length=36), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('edge_type', sa.String(length=50), nullable=True),
    sa.Column('co_occurrence', sa.Integer(), nullable=False),
    sa.Column('llm_labeled', sa.Boolean(), nullable=False),
    sa.Column('last_decay', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['source_node_id'], ['nodes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['target_node_id'], ['nodes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_node_id', 'target_node_id', name='uq_source_target_edge')
    )
    op.create_index(op.f('ix_edges_source_node_id'), 'edges', ['source_node_id'], unique=False)
    op.create_index(op.f('ix_edges_target_node_id'), 'edges', ['target_node_id'], unique=False)
    op.create_index(op.f('ix_edges_user_id'), 'edges', ['user_id'], unique=False)
    op.create_index('ix_edges_user_weight', 'edges', ['user_id', 'weight'], unique=False)
    op.create_table('event_panels',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('label', sa.String(length=100), nullable=False),
    sa.Column('color', sa.String(length=7), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_panels_event_id'), 'event_panels', ['event_id'], unique=False)
    op.create_index(op.f('ix_event_panels_user_id'), 'event_panels', ['user_id'], unique=False)
    op.create_table('files',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('folder_id', sa.String(length=36), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('media_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_files_folder_id'), 'files', ['folder_id'], unique=False)
    op.create_index(op.f('ix_files_user_id'), 'files', ['user_id'], unique=False)
    op.create_table('message_cluster_memberships',
    sa.Column('message_id', sa.String(length=36), nullable=False),
    sa.Column('cluster_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('is_partial', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('message_id', 'cluster_id')
    )
    op.create_index(op.f('ix_message_cluster_memberships_user_id'), 'message_cluster_memberships', ['user_id'], unique=False)
    op.create_table('event_panel_items',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('panel_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('text', sa.String(length=500), nullable=True),
    sa.Column('done', sa.Boolean(), nullable=False),
    sa.Column('image_url', sa.String(length=2000), nullable=True),
    sa.Column('location', sa.String(length=500), nullable=True),
    sa.Column('person_name', sa.String(length=200), nullable=True),
    sa.Column('person_node_id', sa.String(length=36), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['panel_id'], ['event_panels.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_panel_items_panel_id'), 'event_panel_items', ['panel_id'], unique=False)
    op.create_index(op.f('ix_event_panel_items_user_id'), 'event_panel_items', ['user_id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_event_panel_items_user_id'), table_name='event_panel_items')
    op.drop_index(op.f('ix_event_panel_items_panel_id'), table_name='event_panel_items')
    op.drop_table('event_panel_items')
    op.drop_index(op.f('ix_message_cluster_memberships_user_id'), table_name='message_cluster_memberships')
    op.drop_table('message_cluster_memberships')
    op.drop_index(op.f('ix_files_user_id'), table_name='files')
    op.drop_index(op.f('ix_files_folder_id'), table_name='files')
    op.drop_table('files')
    op.drop_index(op.f('ix_event_panels_user_id'), table_name='event_panels')
    op.drop_index(op.f('ix_event_panels_event_id'), table_name='event_panels')
    op.drop_table('event_panels')
    op.drop_index('ix_edges_user_weight', table_name='edges')
    op.drop_index(op.f('ix_edges_user_id'), table_name='edges')
    op.drop_index(op.f('ix_edges_target_node_id'), table_name='edges')
    op.drop_index(op.f('ix_edges_source_node_id'), table_name='edges')
    op.drop_table('edges')
    op.drop_index(op.f('ix_cluster_edges_user_id'), table_name='cluster_edges')
    op.drop_index(op.f('ix_cluster_edges_cluster_b'), table_name='cluster_edges')
    op.drop_index(op.f('ix_cluster_edges_cluster_a'), table_name='cluster_edges')
    op.drop_table('cluster_edges')
    op.drop_index(op.f('ix_user_preferences_user_id'), table_name='user_preferences')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_relationship_scores_user_id'), table_name='relationship_scores')
    op.drop_index(op.f('ix_relationship_scores_person_node_id'), table_name='relationship_scores')
    op.drop_table('relationship_scores')
    op.drop_index(op.f('ix_recommendations_user_id'), table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_index(op.f('ix_patterns_user_id'), table_name='patterns')
    op.drop_table('patterns')
    op.drop_index('ix_nudges_user_shown', table_name='nudges')
    op.drop_index(op.f('ix_nudges_user_id'), table_name='nudges')
    op.drop_table('nudges')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_nodes_user_type', table_name='nodes')
    op.drop_index(op.f('ix_nodes_user_id'), table_name='nodes')
    op.drop_table('nodes')
    op.drop_index('ix_messages_user_session', table_name='messages')
    op.drop_index('ix_messages_user_parent', table_name='messages')
    op.drop_index(op.f('ix_messages_user_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_parent_message_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_folders_user_id'), table_name='folders')
    op.drop_table('folders')
    op.drop_index(op.f('ix_events_user_id'), table_name='events')
    op.drop_table('events')
    op.drop_index(op.f('ix_clusters_user_id'), table_name='clusters')
    op.drop_table('clusters')
    op.drop_index(op.f('ix_users_device_id'), table_name='users')
    op.drop_table('users')

