"""add_data_partitioning

Revision ID: 2a5a19c0a534
Revises: 5c95691ca0d1
Create Date: 2026-07-10 20:26:18.703664

"""
from typing import Sequence, Union

from alembic import op

revision: str = "2a5a19c0a534"
down_revision: Union[str, None] = "5c95691ca0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION create_partition_if_not_exists(
            parent_table TEXT,
            partition_date TIMESTAMPTZ
        ) RETURNS void LANGUAGE plpgsql AS $$
        DECLARE
            partition_name TEXT;
            partition_start TEXT;
            partition_end TEXT;
        BEGIN
            partition_name := parent_table || '_' || to_char(partition_date, 'YYYY_MM');
            partition_start := to_char(partition_date, 'YYYY-MM-DD"T"HH24:MI:SS"Z"');
            partition_end := to_char(
                date_trunc('month', partition_date) + interval '1 month',
                'YYYY-MM-DD"T"HH24:MI:SS"Z"'
            );

            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = partition_name
            ) THEN
                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                    partition_name, parent_table, partition_start, partition_end
                );
            END IF;
        END;
        $$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION auto_create_partition()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            col_val TIMESTAMPTZ;
            partition_date TIMESTAMPTZ;
        BEGIN
            col_val := NEW.start_time;
            partition_date := date_trunc('month', col_val);
            PERFORM create_partition_if_not_exists(TG_RELNAME::TEXT, partition_date);
            RETURN NEW;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS auto_create_partition() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS create_partition_if_not_exists(TEXT, TIMESTAMPTZ) CASCADE")
