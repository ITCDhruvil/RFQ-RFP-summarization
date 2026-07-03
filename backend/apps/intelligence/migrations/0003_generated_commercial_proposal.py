# Generated manually for commercial proposal engine

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_alter_document_status"),
        ("intelligence", "0002_generated_proposal"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeneratedCommercialProposal",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_current", models.BooleanField(db_index=True, default=True)),
                ("commercial_json", models.JSONField(blank=True, default=dict)),
                ("vendor_profile", models.JSONField(blank=True, default=dict)),
                ("workbench", models.JSONField(blank=True, default=dict)),
                ("model_metadata", models.JSONField(blank=True, default=dict)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("last_error", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generated_commercial_proposals",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["document", "is_current"],
                        name="intelligenc_documen_comm_idx",
                    )
                ],
            },
        ),
    ]
