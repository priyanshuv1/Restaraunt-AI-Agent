from alembic import op
import sqlalchemy as sa
revision="20261010_menu"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
 op.create_table("menu_items",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(120),nullable=False),sa.Column("category",sa.String(50),nullable=False),sa.Column("description",sa.Text(),nullable=False,server_default=""),sa.Column("price",sa.Numeric(10,2),nullable=False),sa.Column("is_available",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("dietary_tags",sa.String(250),nullable=False,server_default=""),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
 op.create_index("ix_menu_items_name","menu_items",["name"]); op.create_index("ix_menu_items_category","menu_items",["category"])
def downgrade():
 op.drop_index("ix_menu_items_category",table_name="menu_items"); op.drop_index("ix_menu_items_name",table_name="menu_items"); op.drop_table("menu_items")
