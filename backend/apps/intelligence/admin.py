from django.contrib import admin

from apps.intelligence.models import DocumentChunk, ExtractedInsight, GeneratedSummary


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ("chunk_order", "section_title", "char_count")


class ExtractedInsightInline(admin.TabularInline):
    model = ExtractedInsight
    extra = 0
    readonly_fields = ("extraction_type", "confidence_score")


@admin.register(GeneratedSummary)
class GeneratedSummaryAdmin(admin.ModelAdmin):
    list_display = ("document", "version", "status", "is_current", "total_tokens", "created_at")
    list_filter = ("status", "is_current")
    inlines = [ExtractedInsightInline]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_order", "section_title", "page_start", "char_count")
    search_fields = ("section_title",)
