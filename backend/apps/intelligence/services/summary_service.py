import json
import logging

from django.conf import settings
from django.utils import timezone

from apps.documents.models import Document
from apps.intelligence.choices import SummaryStatus
from apps.intelligence.models import ExtractedInsight, GeneratedSummary
from apps.intelligence.prompts.templates import SUMMARY_SYSTEM_PROMPT, summary_user_prompt
from apps.intelligence.services.grounding import detect_missing_extractions
from apps.intelligence.services.openai_service import OpenAIService
from apps.intelligence.services.summary_postprocess import postprocess_summary

logger = logging.getLogger(__name__)


class SummaryService:
    @staticmethod
    def build_extractions_context(insights: list[ExtractedInsight]) -> str:
        payload = {}
        for insight in insights:
            payload[insight.extraction_type] = {
                "confidence_score": insight.confidence_score,
                "items": insight.payload.get("items", []),
            }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    @staticmethod
    def generate_final_summary(
        document: Document,
        summary: GeneratedSummary,
        insights: list[ExtractedInsight],
    ) -> GeneratedSummary:
        client = OpenAIService()
        context = SummaryService.build_extractions_context(insights)
        user = summary_user_prompt(context, document.original_filename)

        data, usage = client.chat_json(system=SUMMARY_SYSTEM_PROMPT, user=user)
        data = postprocess_summary(data, insights, document=document)

        present_types = {i.extraction_type for i in insights if i.payload.get("items")}
        missing = detect_missing_extractions(present_types)

        data["_meta"] = {
            "model": client.model,
            "prompt_version": settings.INTELLIGENCE_PROMPT_VERSION,
            "generated_at": timezone.now().isoformat(),
            "missing_extraction_types": missing,
            "insight_count": len(insights),
            "token_usage": usage,
        }

        summary.summary_json = data
        summary.model_metadata = {
            "model": client.model,
            "prompt_version": settings.INTELLIGENCE_PROMPT_VERSION,
            "missing_sections": missing,
        }
        summary.total_tokens = usage.get("total_tokens", 0)
        summary.status = SummaryStatus.COMPLETED
        summary.completed_at = timezone.now()
        summary.save()

        document.metadata = {
            **document.metadata,
            "intelligence": {
                "summary_id": str(summary.id),
                "version": summary.version,
                "total_tokens": summary.total_tokens,
            },
        }
        document.save(update_fields=["metadata", "updated_at"])

        logger.info("summary_generated document_id=%s version=%s", document.id, summary.version)
        return summary
