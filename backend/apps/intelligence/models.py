from django.db import models

from apps.core.models import TimeStampedModel, UUIDPrimaryKeyModel
from apps.documents.models import Document
from apps.intelligence.choices import ExtractionType, ProposalStatus, SummaryStatus
from apps.parsing.models import ParsedDocument


class GeneratedSummary(UUIDPrimaryKeyModel, TimeStampedModel):
    """Grounded procurement summary for a document."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="generated_summaries",
    )
    status = models.CharField(
        max_length=32,
        choices=SummaryStatus.choices,
        default=SummaryStatus.PENDING,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True, db_index=True)
    summary_json = models.JSONField(default=dict, blank=True)
    model_metadata = models.JSONField(default=dict, blank=True)
    total_tokens = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    last_error = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"Summary v{self.version} for {self.document_id} [{self.status}]"


class GeneratedProposal(UUIDPrimaryKeyModel, TimeStampedModel):
    """AI-generated technical proposal draft for a document."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="generated_proposals",
    )
    status = models.CharField(
        max_length=32,
        choices=ProposalStatus.choices,
        default=ProposalStatus.PENDING,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True, db_index=True)
    proposal_json = models.JSONField(default=dict, blank=True)
    bidder_profile_snapshot = models.JSONField(default=dict, blank=True)
    model_metadata = models.JSONField(default=dict, blank=True)
    total_tokens = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    last_error = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"Proposal v{self.version} for {self.document_id} [{self.status}]"


class GeneratedCommercialProposal(UUIDPrimaryKeyModel, TimeStampedModel):
    """AI-generated commercial proposal draft with deterministic pricing workbench."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="generated_commercial_proposals",
    )
    status = models.CharField(
        max_length=32,
        choices=ProposalStatus.choices,
        default=ProposalStatus.PENDING,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True, db_index=True)
    commercial_json = models.JSONField(default=dict, blank=True)
    vendor_profile = models.JSONField(default=dict, blank=True)
    workbench = models.JSONField(default=dict, blank=True)
    model_metadata = models.JSONField(default=dict, blank=True)
    total_tokens = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    last_error = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"Commercial proposal v{self.version} for {self.document_id} [{self.status}]"


class DocumentChunk(UUIDPrimaryKeyModel, TimeStampedModel):
    """Section-aware semantic chunk for extraction."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    parsed_document = models.ForeignKey(
        ParsedDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
        null=True,
        blank=True,
    )
    section_title = models.CharField(max_length=512)
    page_start = models.PositiveIntegerField(default=1)
    page_end = models.PositiveIntegerField(default=1)
    chunk_order = models.PositiveIntegerField(default=0)
    chunk_text = models.TextField()
    char_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["chunk_order"]
        indexes = [
            models.Index(fields=["document", "chunk_order"]),
        ]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_order} ({self.section_title})"


class ExtractedInsight(UUIDPrimaryKeyModel, TimeStampedModel):
    """Structured procurement extraction with source grounding."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="extracted_insights",
    )
    generated_summary = models.ForeignKey(
        GeneratedSummary,
        on_delete=models.CASCADE,
        related_name="insights",
        null=True,
        blank=True,
    )
    extraction_type = models.CharField(
        max_length=64,
        choices=ExtractionType.choices,
        db_index=True,
    )
    payload = models.JSONField(
        default=dict,
        help_text='{"items": [{"requirement", "page", "section", "source_text", "confidence"}]}',
    )
    confidence_score = models.FloatField(default=0.0)
    model_name = models.CharField(max_length=128, blank=True)
    prompt_version = models.CharField(max_length=32, blank=True)
    token_usage = models.JSONField(default=dict, blank=True)
    chunk_ids = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["extraction_type"]
        indexes = [
            models.Index(fields=["document", "extraction_type"]),
            models.Index(fields=["generated_summary", "extraction_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.extraction_type} ({self.document_id})"
