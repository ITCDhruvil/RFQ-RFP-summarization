from rest_framework.response import Response
from rest_framework.views import APIView

from apps.processing.serializers import ProcessingJobDetailSerializer
from apps.processing.services.job_service import ProcessingJobService


class ProcessingJobDetailView(APIView):
    def get(self, request, job_id):
        job = ProcessingJobService.get_job(job_id)
        serializer = ProcessingJobDetailSerializer(job)
        return Response(serializer.data)
